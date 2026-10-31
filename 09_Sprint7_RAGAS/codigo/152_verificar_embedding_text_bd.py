#!/usr/bin/env python3
"""152_verificar_embedding_text_bd.py — el texto guardado reproduce el vector?

POR QUE
Poblar la columna no demuestra que sirva. La pregunta de la Fase D era: ¿se puede
reconstruir el vector desde la BD? Ahora que el texto está EN la BD, hay que
comprobarlo sobre vectores reales, no sobre el JSONL.

QUE HACE
Toma una muestra estratificada por longitud de `embedding_text` (cortas / medias /
largas), vectoriza el texto QUE AHORA ESTA EN LA BD con el mismo modelo y revision
del catalogo, y compara por coseno contra el vector guardado en `embedding`.

Se ejecuta DENTRO del contenedor de la API (tiene sentence-transformers y
psycopg2); el texto se vectoriza en el mismo regimen que el catalogo.

USO (desde el host)
  docker exec buscador_api python3 /app/api/../<ruta>  ->  se copia al contenedor
  Mejor: se ejecuta con python3 dentro del contenedor vía docker exec -i
"""
import json
import os
import random
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

MUESTRA = 60
MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"


def conexion():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "buscador"),
    )


def main():
    from sentence_transformers import SentenceTransformer
    import numpy as np

    modelo = SentenceTransformer(MODELO, revision=REVISION)

    conn = conexion()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # muestra estratificada por longitud del texto guardado
    print("=== muestra estratificada por longitud de embedding_text ===", flush=True)
    cur.execute("""
        WITH t AS (
            SELECT dataset_id, embedding_text, embedding,
                   length(embedding_text) AS n
            FROM datasets
            WHERE embedding_text IS NOT NULL AND embedding IS NOT NULL
        ), g AS (
            SELECT *, ntile(3) OVER (ORDER BY n) AS tercio FROM t
        )
        SELECT dataset_id, embedding_text, embedding, tercio
        FROM g
        WHERE dataset_id IN (
            SELECT dataset_id FROM g WHERE tercio = 1 ORDER BY random() LIMIT %s
        ) OR dataset_id IN (
            SELECT dataset_id FROM g WHERE tercio = 2 ORDER BY random() LIMIT %s
        ) OR dataset_id IN (
            SELECT dataset_id FROM g WHERE tercio = 3 ORDER BY random() LIMIT %s
        )
    """, (MUESTRA // 3,) * 3)
    filas = cur.fetchall()
    print(f"  fichas en la muestra: {len(filas)}", flush=True)

    resultados = []
    for f in filas:
        txt = f["embedding_text"]
        # vector guardado -> lista de floats
        vec_guardado = np.array([float(x) for x in str(f["embedding"]).strip("[]").split(",")])
        nuevo = modelo.encode(txt, normalize_embeddings=True)
        # coseno (ambos normalizados -> producto escalar)
        cos = float(np.dot(vec_guardado, nuevo))
        resultados.append({"dataset_id": f["dataset_id"], "tercio": f["tercio"],
                           "n_chars": len(txt), "coseno": cos})

    print("\n=== RESULTADO POR TERCIO DE LONGITUD ===", flush=True)
    import statistics
    for t in (1, 2, 3):
        g = [r["coseno"] for r in resultados if r["tercio"] == t]
        if not g:
            continue
        et = {1: "cortas", 2: "medias", 3: "largas"}[t]
        print(f"  {et:7} n={len(g):3}  coseno medio {statistics.mean(g):.6f}  "
              f"min {min(g):.6f}  exactos(>0,9999) {sum(1 for x in g if x > 0.9999)}/{len(g)}",
              flush=True)

    todos = [r["coseno"] for r in resultados]
    print(f"\n  GLOBAL  n={len(todos)}  coseno medio {statistics.mean(todos):.6f}  "
          f"min {min(todos):.6f}  exactos {sum(1 for x in todos if x > 0.9999)}/{len(todos)}")

    veredicto = statistics.mean(todos) > 0.999
    print(f"\n  VEREDICTO: el texto guardado {'REPRODUCE' if veredicto else 'NO reproduce'} el vector")

    salida = {"muestra": len(filas), "modelo": MODELO, "revision": REVISION,
              "coseno_medio": statistics.mean(todos), "coseno_min": min(todos),
              "exactos": sum(1 for x in todos if x > 0.9999),
              "reproduce": bool(veredicto),
              "por_tercio": {str(t): [r["coseno"] for r in resultados if r["tercio"] == t]
                             for t in (1, 2, 3)},
              "detalle": resultados}
    ruta = "/tmp/verificacion_embedding_text_bd.json"
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=1)
    print(f"\n  guardado: {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
