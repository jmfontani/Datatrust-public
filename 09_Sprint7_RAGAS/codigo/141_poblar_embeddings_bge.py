#!/usr/bin/env python3
"""
141_poblar_embeddings_bge.py — FASE E, paso 1: calcular BGE-M3 en paralelo.

DECISION DE METODO (importante)
El plan decia "ampliar la columna 384 -> 1024 y recalcular en un solo movimiento".
Se hace de forma NO destructiva:

  * se ANADE `embedding_bge vector(1024)` en vez de convertir `embedding`
  * los 384 dims actuales NO se tocan -> el buscador sigue en produccion intacto
  * vuelta atras = `ALTER TABLE datasets DROP COLUMN embedding_bge`
  * permite medir BGE-M3 contra MiniLM con el MISMO instrumento, sin cambiar
    la API entre las dos mediciones (comparacion limpia, motor vs motor)

TEXTO QUE SE VECTORIZA
El esquema de la limpieza (SEP = " \\n "):
    title \\n description \\n Temas: X \\n Palabras clave: Y \\n Territorio: Z
Usa `theme` (etiqueta), NO `theme_label` (que lleva el URI en el 95 % del catalogo).
Mismo texto para comparar los dos modelos: si se cambiara el texto a la vez que el
modelo, la diferencia mediria las dos cosas mezcladas.

Es REANUDABLE: solo procesa filas con embedding_bge IS NULL. Si se corta, se
relanza y continua donde estaba.

USO
  python3 141_poblar_embeddings_bge.py                 # solo nulos
  python3 141_poblar_embeddings_bge.py --limite 5000   # prueba corta
  python3 141_poblar_embeddings_bge.py --recrear       # DROP + recalcula todo
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

MODELO = "BAAI/bge-m3"
DIM = 1024
SEP = " \n "

# VENTANA (max_seq_length). Es la decision que fija el coste. Medido sobre 100
# fichas reales (media 136 tokens, p90 203, max 1135) a ~5 tokens/char:
#     128  -> 7,6/s -> 3,5 h | cubre ENTERA el 65 % de las fichas
#     512  -> 5,1/s -> 5,2 h |  96 %
#    1024  -> 3,6/s -> 7,3 h |  99 %
#    2048  -> 3,4/s -> 7,8 h | 100 %
#     8192 -> 3,3/s -> 7,9 h | 100 % (nativa de BGE-M3)
# La ventana debe ser la NATIVA del modelo al comparar motores: dejar BGE-M3 en
# 128 heredaria la limitacion del modelo viejo y el argumento de migrar se cae.
VENTANA = 1024


def texto(row):
    """Esquema de la limpieza. `theme` lleva la etiqueta; `theme_label` el URI."""
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
    ap.add_argument("--batch-size", type=int, default=16,
                    help="BGE-M3 es ~560M params; batch pequeno para no agotar RAM")
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--recrear", action="store_true",
                    help="borra la columna y recalcula todo desde cero")
    ap.add_argument("--ventana", type=int, default=VENTANA,
                    help="max_seq_length (128->3,5h, 512->5,2h, 1024->7,3h, 2048->7,8h)")
    args = ap.parse_args()

    conn = psycopg2.connect(**DB)
    conn.autocommit = False

    with conn.cursor() as cur:
        if args.recrear:
            cur.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS embedding_bge")
            conn.commit()
            print("  columna embedding_bge eliminada")
        cur.execute("ALTER TABLE datasets ADD COLUMN IF NOT EXISTS embedding_bge vector(%s)",
                    (DIM,))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM datasets WHERE embedding_bge IS NULL")
        pend = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM datasets")
        total = cur.fetchone()[0]
    print(f"  catalogo: {total} filas · pendientes de BGE-M3: {pend}")
    if pend == 0:
        print("  nada que hacer (ya estan todos)")
        return 0
    if args.limite:
        pend = min(pend, args.limite)

    t0 = time.time()
    print(f"  cargando {MODELO} ...", flush=True)
    from sentence_transformers import SentenceTransformer
    modelo = SentenceTransformer(MODELO)
    modelo.max_seq_length = args.ventana
    print(f"  modelo listo: dim {modelo.get_embedding_dimension()}, "
          f"ventana {modelo.max_seq_length}", flush=True)

    hechos = 0
    with conn.cursor(cursor_factory=DictCursor) as cur:
        while True:
            if args.limite and hechos >= args.limite:
                break
            n = args.batch_size
            if args.limite:
                n = min(n, args.limite - hechos)
            cur.execute("""SELECT dataset_id, title, description, keywords,
                                  theme, theme_label, territory_label
                           FROM datasets WHERE embedding_bge IS NULL
                           ORDER BY dataset_id LIMIT %s""", (n,))
            filas = cur.fetchall()
            if not filas:
                break

            textos = [texto(f) or f["dataset_id"] for f in filas]
            embs = modelo.encode(textos, batch_size=args.batch_size,
                                 normalize_embeddings=True, convert_to_numpy=True,
                                 show_progress_bar=False)
            # pgvector exige el literal '[...]': una lista de Python produce '{...}'
            # y falla con "malformed vector literal: Vector contents must start with [".
            valores = [("[" + ",".join(map(str, e.tolist())) + "]", f["dataset_id"])
                       for f, e in zip(filas, embs)]
            execute_values(cur,
                           "UPDATE datasets AS d SET embedding_bge = v.emb::vector "
                           "FROM (VALUES %s) AS v(emb, dataset_id) "
                           "WHERE d.dataset_id = v.dataset_id",
                           valores, template="(%s, %s)")
            conn.commit()
            hechos += len(filas)
            t = time.time() - t0
            v = hechos / t if t else 0
            rest = (pend - hechos) / v / 60 if v else 0
            if hechos % (args.batch_size * 10) < args.batch_size:
                print(f"  {hechos}/{pend} ({v:.1f}/s, quedan ~{rest/60:.1f} h)", flush=True)

    print(f"\n  COMPLETADO: {hechos} embeddings BGE-M3 en {(time.time()-t0)/60:.1f} min")
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM datasets WHERE embedding_bge IS NOT NULL")
        print(f"  filas con embedding_bge: {cur.fetchone()[0]}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
