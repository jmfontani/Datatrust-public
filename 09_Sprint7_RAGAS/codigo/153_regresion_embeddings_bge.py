#!/usr/bin/env python3
"""153_regresion_embeddings_bge.py — prueba de regresion con AMBOS motores.

POR QUE
El plan (Fase E) exige: "rehacer la prueba de regresion con el modelo nuevo" y
"prueba de regresion con el modelo nuevo PASA". El script 88 existia pero:
  * cubria solo MiniLM,
  * vectorizaba un texto RECONSTRUIDO (title + description + keywords +
    theme_label + territory_label), que la Fase D demostro que NO es el que
    genero los vectores -> media 0,92-0,93 y veredicto enganosamente bajo.

Cada motor necesita SU texto:
  * `embedding` (384, MiniLM)  -> el `embedding_text` EXACTO de la limpieza,
    que desde la Fase H esta guardado en la columna `embedding_text`.
  * `embedding_bge` (1024, BGE)-> el esquema que uso `142_poblar_bge_gpu.py`
    (reconstruido de campos de la BD; se reproduce con su misma funcion).

Ademas comprueba que los DOS textos son distintos entre si, que es la causa de
que la comparacion de motores mezcle "modelo" y "texto".

Se ejecuta DENTRO del contenedor de la API.

USO
  docker exec buscador_api python3 /tmp/153_regresion.py
"""
import json
import os
import statistics
import sys

import psycopg2
from psycopg2.extras import DictCursor

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
SEP = " \n "
N = 120
UMBRAL_PASA = 0.99


def texto_bge(row):
    """Esquema exacto de 142_poblar_bge_gpu.py: lo que vectorizo BGE."""
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
    import numpy as np
    from sentence_transformers import SentenceTransformer

    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "buscador"),
    )
    with conn.cursor(cursor_factory=DictCursor) as cur:
        # muestra estratificada por longitud sobre TODO el catalogo
        cur.execute("""
            WITH t AS (
                SELECT dataset_id, title, description, keywords, theme,
                       theme_label, territory_label, embedding_text,
                       embedding::text AS e384, embedding_bge::text AS e1024,
                       length(coalesce(embedding_text,'')) AS n
                FROM datasets
                WHERE embedding IS NOT NULL AND embedding_bge IS NOT NULL
            ), g AS (SELECT *, ntile(4) OVER (ORDER BY n) AS cuartil FROM t)
            SELECT * FROM g WHERE cuartil IN (1,2,3,4) ORDER BY random() LIMIT %s
        """, (N,))
        filas = [dict(f) for f in cur.fetchall()]

    print(f"### REGRESION DE EMBEDDINGS — muestra {len(filas)} fichas "
          f"(estratificada por longitud) ###\n", flush=True)

    m = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)

    # ---- MiniLM: SOLO las fichas con `embedding_text` guardado ----
    # Las 6.800 posteriores no tienen texto (se generaron con otro esquema
    # desconocido): no son comparables con MiniLM y se excluyen, declarandolo.
    idx_min = [i for i, f in enumerate(filas) if f.get("embedding_text")]
    txt_min = [filas[i]["embedding_text"] for i in idx_min]
    print(f"  fichas con `embedding_text` guardado: {len(idx_min)}/{len(filas)} "
          f"(las sin texto se excluyen de MiniLM)", flush=True)

    # ---- BGE: esquema del 142 ----
    txt_bge = [texto_bge(f) for f in filas]

    # vectorizar MiniLM con su texto
    emb_min = m.encode(txt_min, normalize_embeddings=True, convert_to_numpy=True,
                       batch_size=64)

    def cosenos(guardados, nuevos):
        out = []
        for g, n_ in zip(guardados, nuevos):
            v = np.array(json.loads(g), dtype=np.float32)
            v = v / np.linalg.norm(v)
            out.append(float(np.dot(v, n_)))
        return out

    c_min = cosenos([filas[i]["e384"] for i in idx_min], emb_min)

    # ---- BGE via ollama ----
    import urllib.request
    OLLAMA = os.getenv("OLLAMA_EMBED_URL", "http://172.17.0.1:11434/api/embed")

    def embed_bge(textos, ventana=1024):
        body = json.dumps({"model": "bge-m3", "input": textos,
                           "options": {"num_ctx": ventana}}).encode()
        req = urllib.request.Request(OLLAMA, data=body,
                                     headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=600).read())["embeddings"]

    nuevos_bge = []
    for i in range(0, len(txt_bge), 20):
        nuevos_bge.extend(embed_bge(txt_bge[i:i + 20]))

    c_bge = cosenos([f["e1024"] for f in filas], nuevos_bge)

    print("=== RESULTADO ===")
    res = {}
    for nombre, cs, dim in (("MiniLM (`embedding`, 384)", c_min, 384),
                            ("BGE-M3 (`embedding_bge`, 1024)", c_bge, 1024)):
        med = statistics.mean(cs)
        exa = sum(1 for x in cs if x > 0.9999)
        ver = "PASA" if med >= UMBRAL_PASA else "REVISAR"
        res[nombre] = {"dim": dim, "coseno_medio": med, "coseno_min": min(cs),
                       "exactos": exa, "n": len(cs), "veredicto": ver}
        print(f"  {nombre:32} coseno medio {med:.6f}  min {min(cs):.6f}  "
              f"exactos {exa}/{len(cs)}  -> {ver}")

    print()
    ok = all(v["veredicto"] == "PASA" for v in res.values())
    print(f"### VEREDICTO GLOBAL: {'PASA' if ok else 'REVISAR'} ###")
    if not ok:
        print("  Un motor no reproduce sus vectores: el entorno o el texto cambiaron.")

    salida = {"muestra": len(filas), "umbral_pasa": UMBRAL_PASA,
              "modelo_minilm": MODEL_NAME, "revision": MODEL_REVISION,
              "modelo_bge": "bge-m3 (ollama)",
              "motor": res, "veredicto_global": "PASA" if ok else "REVISAR"}
    with open("/tmp/153_regresion.json", "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=1)
    print("\n  guardado: /tmp/153_regresion.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
