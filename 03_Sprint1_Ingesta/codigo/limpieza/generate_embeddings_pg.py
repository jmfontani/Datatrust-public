#!/usr/bin/env python3
"""
generate_embeddings_pg.py — genera embeddings para datasets en PostgreSQL.

CORREGIDO 2026-09-28 (Fase D): el texto vectorizado era incorrecto.

QUE CAMBIA Y POR QUE
La version anterior vectorizaba:

    title || ' ' || description || ' ' || keywords || ' ' || theme_label || ' ' || territory_label

Pero los 87.661 vectores originales del catalogo NO se generaron con ese texto.
Se generaron con el campo `embedding_text` de la limpieza (clean_datasets.py):

    title_es \\n title_en \\n description_es_clean
             \\n Temas: <temas> \\n Palabras clave: <keywords> \\n Territorio: <territorio>

Evidencia: 139_verificar_embedding_text_original.py reproduce el vector guardado con
coseno 0.999979 (39/40 exactos); con el texto anterior solo 0.935 y en fichas cortas
0.86. Ver docs/FASE-D-HALLAZGO-EMBEDDINGS.md.

Consecuencia del bug: toda ficha NUEVA quedaba vectorizada en un regimen distinto
del 92,8 % del catalogo, de forma silenciosa. Se corrige aqui.

MODO DE TEXTO (--texto)
  embedding   (por defecto) usa el esquema de la limpieza: los campos de la BD
              reconstruidos con los mismos prefijos y separadores.
  concatenado  comportamiento antiguo (title + description + ...). Solo para
              reproducir el pasado; no usar en ingesta.

NOTA sobre fichas con `embedding_text` original disponible: si el dataset_id existe
en `datos/processed/datasets_clean.jsonl`, se puede usar --fuente-jsonl para tomar
el texto EXACTO con el que se generaron (mas fiel que reconstruirlo).

Uso:
    python generate_embeddings_pg.py [--batch-size 64] [--texto embedding]
    python generate_embeddings_pg.py --forzar          # recalcula TODO
    python generate_embeddings_pg.py --forzar --limite 1000
    python generate_embeddings_pg.py --fuente-jsonl datos/processed/datasets_clean.jsonl
"""
import argparse
import json
import os
import time
import logging
from pathlib import Path

import psycopg2
from psycopg2.extras import DictCursor, execute_values

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Revision fijada (ver docs/PINNING-DEPENDENCIAS.md).
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
EMBEDDING_DIM = 384
BATCH_SIZE = 64

# separador exacto de clean_datasets.py: " \n " (espacio, salto, espacio)
SEP = " \n "


def pg_connect():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "buscador"),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD", "postgres"),
    )


def texto_esquema_limpieza(row):
    """Reconstruye el embedding_text con los prefijos de clean_datasets.py.

    ⚠️ ES UNA APROXIMACION, NO REPRODUCE EL TEXTO ORIGINAL.

    Medido (80 fichas cortas, coseno contra el vector guardado):
      - esquema reconstruido desde la BD : 0,923 (5/80 exactos)
      - embedding_text original          : 0,999963 (55/56 exactos)

    Por que no reproduce: la limpieza (clean_datasets.py) construyo el original con
    campos que la BD ya no conserva tal cual:
      * title_es Y title_en (la BD guarda `title` fusionado)
      * description_es_clean (limpiada y TRUNCADA a 1000 chars)
      * temas NORMALIZADOS: `theme` guarda la etiqueta ("demografia") pero
        `theme_label` guarda el URI (89.958 fichas) -> hay que usar `theme`
      * territorio INFERIDO (puede no coincidir con territory_label)

    CONSECUENCIA DE DISENO: la unica forma de que un vector sea reproducible es
    GUARDAR el texto con el que se genero. La BD no lo guarda. Por eso se ofrece
    `--fuente-jsonl` (para las originales) y se recomienda anadir una columna
    `embedding_text` para que la ingesta futura sea trazable.

    Usa `theme` (etiqueta), NO `theme_label` (URI): con el URI el coseno cae a 0,897.
    """
    partes = []
    if (row.get("title") or "").strip():
        partes.append(row["title"].strip())
    if (row.get("description") or "").strip():
        partes.append(row["description"].strip())
    # `theme` lleva la etiqueta; `theme_label` lleva el URI en el 95% del catalogo
    tema = row.get("theme") or row.get("theme_label")
    if tema and not str(tema).startswith("http"):
        partes.append("Temas: " + tema)
    if row.get("keywords"):
        partes.append("Palabras clave: " + ", ".join(row["keywords"]))
    if row.get("territory_label"):
        partes.append("Territorio: " + row["territory_label"])
    return SEP.join(partes)


def texto_concatenado(row):
    """Comportamiento antiguo (el bug). Solo para reproducir el pasado."""
    return (f"{row.get('title') or ''} {row.get('description') or ''} "
            f"{' '.join(row.get('keywords') or [])} "
            f"{row.get('theme_label') or ''} {row.get('territory_label') or ''}")


SQL_BASE = """
    SELECT dataset_id, title, description, keywords, theme, theme_label,
           territory_label
    FROM datasets
    WHERE {filtro}
    LIMIT %s
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    ap.add_argument("--texto", choices=["embedding", "concatenado"], default="embedding",
                    help="esquema del texto a vectorizar (por defecto: el de la limpieza)")
    ap.add_argument("--forzar", action="store_true",
                    help="recalcula TODOS los embeddings, no solo los nulos")
    ap.add_argument("--limite", type=int, default=None, help="maximo de fichas a procesar")
    ap.add_argument("--fuente-jsonl", default=None,
                    help="datasets_clean.jsonl con el embedding_text EXACTO de las originales")
    ap.add_argument("--backup", default=None,
                    help="crea una tabla de backup antes de sobrescribir (obligatorio con --forzar)")
    args = ap.parse_args()

    if args.forzar and not args.backup:
        logger.error("Con --forzar hay que pasar --backup <nombre_tabla>: "
                     "sobrescribir vectores sin vuelta atras no es aceptable.")
        return 1

    start = time.perf_counter()
    conn = pg_connect()
    conn.autocommit = False
    logger.info("Conectado a PostgreSQL")

    # texto EXACTO de las originales, si se aporta
    exactos = {}
    if args.fuente_jsonl:
        with open(args.fuente_jsonl, encoding="utf-8") as fh:
            for line in fh:
                ds = json.loads(line)
                exactos[ds["identifier"]] = ds.get("embedding_text", "")
        logger.info(f"Textos exactos cargados de {args.fuente_jsonl}: {len(exactos)}")

    with conn.cursor(cursor_factory=DictCursor) as cur:
        filtro = "TRUE" if args.forzar else "embedding IS NULL"
        cur.execute(f"SELECT COUNT(*) AS n FROM datasets WHERE {filtro}")
        total_pending = cur.fetchone()["n"]
        logger.info(f"Datasets a procesar: {total_pending}"
                    f"{' (FORZANDO recálculo de todos)' if args.forzar else ' (solo nulos)'}")
        if total_pending == 0:
            logger.info("Nada que hacer.")
            return 0

        if args.forzar:
            cur.execute(f"DROP TABLE IF EXISTS {args.backup}")
            cur.execute(f"CREATE TABLE {args.backup} AS "
                        f"SELECT dataset_id, embedding FROM datasets")
            conn.commit()
            cur.execute(f"SELECT COUNT(*) AS n FROM {args.backup}")
            logger.info(f"Backup creado: {args.backup} con {cur.fetchone()['n']} vectores")

    logger.info(f"Cargando modelo {MODEL_NAME}@{MODEL_REVISION[:8]}...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)
    logger.info(f"Modelo cargado (dim {model.get_sentence_embedding_dimension()}, "
                f"max_seq_length {model.max_seq_length})")

    processed = 0
    usados_exactos = 0
    with conn.cursor(cursor_factory=DictCursor) as cur:
        while True:
            if args.limite and processed >= args.limite:
                break
            n = args.batch_size
            if args.limite:
                n = min(n, args.limite - processed)
            filtro = "TRUE" if args.forzar else "embedding IS NULL"
            cur.execute(SQL_BASE.format(filtro=filtro), (n,))
            rows = cur.fetchall()
            if not rows:
                break

            texts = []
            for row in rows:
                did = row["dataset_id"]
                if args.fuente_jsonl and did in exactos:
                    texts.append(exactos[did] or texto_esquema_limpieza(row))
                    usados_exactos += 1
                else:
                    t = (texto_esquema_limpieza(row) if args.texto == "embedding"
                         else texto_concatenado(row))
                    texts.append(t or did)

            embeddings = model.encode(
                texts, show_progress_bar=False, convert_to_numpy=True,
                normalize_embeddings=True,
            )

            # pgvector espera el literal '[v1,v2,...]' (con corchetes).
            # OJO: pasar una lista de Python produce '{...}' y psycopg2 falla con
            # "malformed vector literal: Vector contents must start with [". Este bug
            # estaba latente en la version anterior y habria roto la proxima ingesta.
            #
            # FASE H (30-sep): ademas del vector se guarda el TEXTO con el que se
            # genero (embedding_text). Sin el, el vector no es reproducible ni
            # auditable: la Fase D demostro que reconstruirlo desde otros campos da
            # coseno 0,923. Invariante: la columna SIEMPRE contiene el texto exacto
            # que produjo el vector de esa fila (exacto si --fuente-jsonl lo tiene,
            # reconstruido si no). Se sobreescribe con lo usado, nunca queda viejo.
            valores = [("[" + ",".join(map(str, emb.tolist())) + "]", txt, row["dataset_id"])
                       for row, emb, txt in zip(rows, embeddings, texts)]
            execute_values(cur,
                           "UPDATE datasets AS d SET embedding = v.emb::vector, "
                           "embedding_text = v.txt "
                           "FROM (VALUES %s) AS v(emb, txt, dataset_id) "
                           "WHERE d.dataset_id = v.dataset_id",
                           valores, template="(%s, %s, %s)")
            conn.commit()

            processed += len(rows)
            elapsed = time.perf_counter() - start
            rate = processed / elapsed if elapsed else 0
            restante = (total_pending - processed) / rate / 60 if rate else 0
            logger.info(f"Procesados: {processed}/{total_pending} ({rate:.0f}/s, "
                        f"quedan ~{restante:.1f} min)")

    elapsed = time.perf_counter() - start
    logger.info("=== COMPLETADO ===")
    logger.info(f"Embeddings generados: {processed}")
    if args.fuente_jsonl:
        logger.info(f"  de los cuales con embedding_text EXACTO: {usados_exactos}")
    logger.info(f"Tiempo total: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
