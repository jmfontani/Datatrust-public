#!/usr/bin/env python3
"""
144_bge_mismo_texto.py — elimina el CONFOUND de texto de la Fase E.

EL DEFECTO QUE CORRIGE
La comparacion 143 enfrento:
    MiniLM -> columna `embedding`, generada desde el `embedding_text` de la LIMPIEZA
    BGE-M3 -> texto reconstruido por mi (`texto()` en el script 142)

Es decir, cambie DOS cosas a la vez: el modelo y el texto. Si BGE-M3 sale mejor o
peor, no se sabe si es por el modelo o por el texto. Y el texto reconstruido es una
APROXIMACION: reproduce el vector guardado a coseno 0,923, no a 1,0, porque la
limpieza transformo campos que la base de datos ya no conserva (titulo en ingles,
descripcion limpiada, territorio inferido).

LA CORRECCION
Se recalcula MiniLM sobre EXACTAMENTE el mismo texto que uso BGE-M3, en una columna
paralela. Asi la comparacion modelo-contra-modelo tiene el texto CONSTANTE.

    BGE-M3(approx)  vs  MiniLM(approx)   -> diferencia atribuible SOLO al modelo

La columna `embedding` original no se toca.

Tambien se mide cuanto cambia el ranking SOLO por el texto
    MiniLM(crudo) vs MiniLM(approx)      -> magnitud del confound que se elimina

USO
  python3 144_bge_mismo_texto.py --limite 2000     # prueba
  python3 144_bge_mismo_texto.py                   # catalogo completo
"""
import argparse
import os
import time

import psycopg2
from psycopg2.extras import DictCursor, execute_values

DB = dict(host=os.environ.get("DB_HOST", "buscador_postgres"),
          port=int(os.environ.get("DB_PORT", 5432)),
          dbname=os.environ.get("DB_NAME", "buscador"),
          user=os.environ.get("DB_USER", "postgres"),
          password=os.environ.get("DB_PASSWORD", "postgres"))

MINILM = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MINILM_REV = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
SEP = " \n "
COLUMNA = "embedding_minilm_aprox"


def texto(row):
    """IDENTICO al del script 142. Debe serlo: ese es el punto del ejercicio."""
    p = []
    if (row.get("title") or "").strip():
        p.append(row["title"].strip())
    if (row.get("description") or "").strip():
        p.append(row["description"].strip())
    tema = row.get("theme") or row.get("theme_label")
    if tema and not str(tema).startswith("http"):
        p.append("Temas: " + tema)
    if row.get("keywords"):
        p.append("Palabras clave: " + ", ".join(row["keywords"]))
    if row.get("territory_label"):
        p.append("Territorio: " + row["territory_label"])
    return SEP.join(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lote", type=int, default=256)
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--recrear", action="store_true")
    args = ap.parse_args()

    from sentence_transformers import SentenceTransformer
    print(f"  cargando MiniLM@{MINILM_REV[:8]} ...", flush=True)
    m = SentenceTransformer(MINILM, revision=MINILM_REV)

    conn = psycopg2.connect(**DB)
    with conn.cursor() as cur:
        if args.recrear:
            cur.execute(f"ALTER TABLE datasets DROP COLUMN IF EXISTS {COLUMNA}")
            conn.commit()
        cur.execute(f"ALTER TABLE datasets ADD COLUMN IF NOT EXISTS {COLUMNA} vector(384)")
        conn.commit()
        cur.execute(f"SELECT COUNT(*) FROM datasets WHERE {COLUMNA} IS NULL")
        pend = cur.fetchone()[0]
    print(f"  pendientes: {pend}", flush=True)
    if args.limite:
        pend = min(pend, args.limite)
    if pend == 0:
        print("  nada que hacer")
        return 0

    t0 = time.time()
    hechos = 0
    with conn.cursor(cursor_factory=DictCursor) as cur:
        while hechos < pend:
            n = min(args.lote, pend - hechos)
            cur.execute(f"""SELECT dataset_id, title, description, keywords,
                                   theme, theme_label, territory_label
                            FROM datasets WHERE {COLUMNA} IS NULL
                            ORDER BY dataset_id LIMIT %s""", (n,))
            filas = cur.fetchall()
            if not filas:
                break
            textos = [texto(f) or f["dataset_id"] for f in filas]
            embs = m.encode(textos, batch_size=32, normalize_embeddings=True,
                            convert_to_numpy=True, show_progress_bar=False)
            vals = [("[" + ",".join(map(str, e.tolist())) + "]", f["dataset_id"])
                    for f, e in zip(filas, embs)]
            execute_values(cur,
                           f"UPDATE datasets AS d SET {COLUMNA} = v.emb::vector "
                           "FROM (VALUES %s) AS v(emb, dataset_id) "
                           "WHERE d.dataset_id = v.dataset_id",
                           vals, template="(%s, %s)")
            conn.commit()
            hechos += len(filas)
            t = time.time() - t0
            v = hechos / t if t else 0
            print(f"  {hechos}/{pend} ({v:.0f}/s, quedan ~{(pend-hechos)/v/60:.1f} min)"
                  if v else f"  {hechos}/{pend}", flush=True)

    print(f"\n  COMPLETADO: {hechos} en {(time.time()-t0)/60:.1f} min")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
