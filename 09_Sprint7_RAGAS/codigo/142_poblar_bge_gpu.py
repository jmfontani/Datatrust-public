#!/usr/bin/env python3
"""
142_poblar_bge_gpu.py — FASE E: BGE-M3 con GPU (ollama) + columna paralela.

POR QUE ASI
Medido antes de lanzar:
  * sentence-transformers en CPU:  3,6-7,6 fichas/s segun ventana -> 3,5-8 h
  * ollama con GPU (ROCm):         ~5,3 fichas/s con textos reales -> ~5 h
  * equivalencia de los dos BGE-M3: coseno 0,999902 (20 textos) -> es el mismo modelo

El plan estimaba 45 min. Era incorrecto por un factor ~10: 94.461 fichas con un
modelo de 560M parametros en CPU no pueden tardar 45 min. Los 45 min salian de
medir con textos de longitud de prueba, no del catalogo real (media 136 tokens,
pero cola hasta 1135 y un maximo de 156.973 caracteres).

DECISIONES
  * Columna PARALELA `embedding_bge vector(1024)`: `embedding` (384) no se toca,
    el buscador sigue sirviendo en produccion, y la vuelta atras es DROP COLUMN.
  * VENTANA explicita via `num_ctx`. Sin fijarla se hereda el valor por defecto
    de ollama, que es justo el tipo de ajuste oculto que invalida una comparacion.
  * Mismo TEXTO que el modelo actual (esquema de la limpieza): si se cambiara el
    texto a la vez que el modelo, la diferencia mediria las dos cosas mezcladas.
  * REANUDABLE: solo procesa filas con embedding_bge IS NULL.

USO
  python3 142_poblar_bge_gpu.py --ventana 1024
  python3 142_poblar_bge_gpu.py --ventana 128 --limite 500     # prueba
  python3 142_poblar_bge_gpu.py --recrear --ventana 1024       # desde cero
"""
import argparse
import json
import os
import time
import urllib.request

import psycopg2
from psycopg2.extras import DictCursor, execute_values

DB = dict(host=os.environ.get("DB_HOST", "buscador_postgres"),
          port=int(os.environ.get("DB_PORT", 5432)),
          dbname=os.environ.get("DB_NAME", "buscador"),
          user=os.environ.get("DB_USER", "postgres"),
          password=os.environ.get("DB_PASSWORD", "postgres"))

OLLAMA = os.environ.get("OLLAMA_URL", "http://172.17.0.1:11434/api/embed")
MODELO = "bge-m3"
DIM = 1024
SEP = " \n "


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


def embed(textos, ventana, intentos=3):
    """Llama a ollama. num_ctx explicito para no heredar el valor por defecto."""
    body = json.dumps({"model": MODELO, "input": textos,
                       "options": {"num_ctx": ventana}}).encode()
    for i in range(intentos):
        try:
            req = urllib.request.Request(OLLAMA, data=body,
                                         headers={"Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(req, timeout=1800).read())
            return d["embeddings"]
        except Exception as e:
            if i == intentos - 1:
                raise
            print(f"     reintento {i+1} tras error: {str(e)[:70]}", flush=True)
            time.sleep(5 * (i + 1))
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lote", type=int, default=64)
    ap.add_argument("--ventana", type=int, default=1024,
                    help="num_ctx: 128->3,5h | 512->5,2h | 1024->7,3h | 8192->7,9h (CPU)")
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--recrear", action="store_true")
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
    print(f"  catalogo: {total} · pendientes: {pend} · lote: {args.lote} · ventana: {args.ventana}")
    if pend == 0:
        print("  nada que hacer")
        return 0
    if args.limite:
        pend = min(pend, args.limite)
    print(f"  ETA estimada: {pend/5.3/3600:.1f} h a ~5,3 fichas/s\n", flush=True)

    t0 = time.time()
    hechos = 0
    with conn.cursor(cursor_factory=DictCursor) as cur:
        while True:
            if args.limite and hechos >= args.limite:
                break
            n = args.lote
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
            try:
                embs = embed(textos, args.ventana)
            except Exception as e:
                print(f"  LOTE FALLIDO ({len(textos)} fichas): {str(e)[:120]}", flush=True)
                # desplazar para no quedarse en bucle infinito sobre el mismo lote
                hechos += 1
                continue

            # pgvector exige '[...]'; una lista de Python produce '{...}' y falla
            vals = [("[" + ",".join(map(str, e)) + "]", f["dataset_id"])
                    for f, e in zip(filas, embs)]
            execute_values(cur,
                           "UPDATE datasets AS d SET embedding_bge = v.emb::vector "
                           "FROM (VALUES %s) AS v(emb, dataset_id) "
                           "WHERE d.dataset_id = v.dataset_id",
                           vals, template="(%s, %s)")
            conn.commit()
            hechos += len(filas)
            t = time.time() - t0
            v = hechos / t if t else 0
            rest = (pend - hechos) / v if v else 0
            if hechos % (args.lote * 5) < args.lote:
                print(f"  {hechos}/{pend} ({v:.1f}/s, quedan ~{rest/3600:.2f} h)", flush=True)

    print(f"\n  COMPLETADO: {hechos} en {(time.time()-t0)/3600:.2f} h")
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM datasets WHERE embedding_bge IS NOT NULL")
        print(f"  filas con embedding_bge: {cur.fetchone()[0]}/{total}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
