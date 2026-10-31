#!/usr/bin/env python3
"""
145_construir_pool_conjunto.py — pool de juicios que SI cubre BGE-M3.

EL PROBLEMA QUE RESUELVE
Los 6.114 juicios existentes se construyeron con el motor ACTUAL y sus variantes
(semantico, lexico). BGE-M3 no participo, asi que cada ficha que BGE devuelve y
nunca se juzgo cuenta como 0 en el nDCG — y el motor parece peor de lo que es.

Medido: la cobertura de BGE sobre los juicios existentes es 34 %, frente al 71-85 %
de MiniLM. Con esa asimetria la comparacion es invalida por construccion: mide la
historia del pool, no la calidad del motor.

LA SOLUCION
Construir el pool CONJUNTO: para cada consulta, la union de los top-N de los dos
motores que se quieren comparar. Asi los dos tienen las mismas oportunidades de
acertar y el nDCG es interpretable.

    pool = top-N(MiniLM_aprox) U top-N(BGE)  -  pares ya juzgados

MiniLM se toma de la columna de TEXTO CONSTANTE (`embedding_minilm_aprox`), la
misma que usa BGE, para que el pool no reintroduzca el confound de texto.

Solo se juzga lo NUEVO. Los 6.114 juicios existentes se conservan intactos.

USO
  python3 145_construir_pool_conjunto.py --top 20
  python3 145_construir_pool_conjunto.py --top 20 --salida ../entregables/pool_conjunto.json
"""
import argparse
import json
from pathlib import Path

import psycopg2
from psycopg2.extras import DictCursor

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
DB = dict(host="buscador_postgres", port=5432, dbname="buscador",
          user="postgres", password="postgres")

MOTORES = {"minilm_aprox": "embedding_minilm_aprox", "bge": "embedding_bge"}
MAX_DESC = 800


def buscar(cur, col, qv_lit, top, where=""):
    cur.execute(f"""SELECT dataset_id, title, description, publisher, theme,
                           territory, url, language,
                           1 - ({col} <=> %s::vector) AS sim
                    FROM datasets WHERE {col} IS NOT NULL {where}
                    ORDER BY {col} <=> %s::vector LIMIT %s""",
                (qv_lit, qv_lit, top))
    return cur.fetchall()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--salida", default=str(ENTREG / "pool_conjunto.json"))
    args = ap.parse_args()

    consultas = ([json.loads(l) for l in (ENTREG / "ground_truth.jsonl")
                  .read_text(encoding="utf-8").splitlines() if l.strip()]
                 + [json.loads(l) for l in (ENTREG / "consultas_limpias.jsonl")
                    .read_text(encoding="utf-8").splitlines() if l.strip()])
    gt = json.loads((ENTREG / "gt_etiquetas_v4.json")
                    .read_text(encoding="utf-8"))["etiquetas"]
    print(f"  consultas: {len(consultas)} · juicios existentes: {len(gt)}")

    # un solo modelo para vectorizar consultas: BGE via ollama
    import urllib.request
    import numpy as np

    def emb(textos, modelo):
        if modelo == "bge":
            body = json.dumps({"model": "bge-m3", "input": textos,
                               "options": {"num_ctx": 1024}}).encode()
            req = urllib.request.Request("http://172.17.0.1:11434/api/embed",
                                         data=body,
                                         headers={"Content-Type": "application/json"})
            return np.array(json.loads(urllib.request.urlopen(req, timeout=600).read())
                            ["embeddings"], dtype=np.float32)
        from sentence_transformers import SentenceTransformer
        raise RuntimeError("MiniLM se carga aparte")

    from sentence_transformers import SentenceTransformer
    m_min = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                                revision="e8f8c211226b894fcb81acc59f3b34ba3efd5f42")

    conn = psycopg2.connect(**DB)
    pool = {}
    nuevas = 0
    ya = 0
    with conn.cursor(cursor_factory=DictCursor) as cur:
        for i, q in enumerate(consultas):
            qid, texto = q["id"], q["query"]
            entradas = {}
            for nom, col in MOTORES.items():
                if nom == "bge":
                    qv = emb([texto], "bge")[0].tolist()
                else:
                    qv = m_min.encode(texto, normalize_embeddings=True).tolist()
                lit = "[" + ",".join(map(str, qv)) + "]"
                for rank, r in enumerate(buscar(cur, col, lit, args.top), start=1):
                    did = r["dataset_id"]
                    e = entradas.setdefault(did, {
                        "dataset_id": did,
                        "title": (r["title"] or "")[:300],
                        "description": (r["description"] or "")[:MAX_DESC],
                        "publisher": r["publisher"], "tema": r["theme"],
                        "territorio": r["territory"], "url": r["url"],
                        "sistemas": [], "ranks": {}, "sims": {},
                        "query_id": qid, "query": texto})
                    if nom not in e["sistemas"]:
                        e["sistemas"].append(nom)
                    e["ranks"][nom] = rank
                    e["sims"][nom] = round(float(r["sim"]), 4)
            # separar lo ya juzgado de lo nuevo
            pool[qid] = {}
            for did, e in entradas.items():
                if f"{qid}|{did}" in gt:
                    ya += 1
                else:
                    pool[qid][did] = e
                    nuevas += 1
            if (i + 1) % 25 == 0:
                print(f"  {i+1}/{len(consultas)} · nuevos {nuevas}", flush=True)

    Path(args.salida).write_text(json.dumps(pool, ensure_ascii=False), encoding="utf-8")
    print()
    print("### POOL CONJUNTO ###")
    print(f"  pares ya juzgados (no se repiten) : {ya}")
    print(f"  pares NUEVOS a juzgar             : {nuevas}")
    print(f"  consultas con al menos 1 nuevo    : "
          f"{sum(1 for v in pool.values() if v)}/{len(consultas)}")
    print(f"  guardado: {args.salida}")
    print()
    print(f"  coste estimado del juicio: {nuevas/0.55/3600:.1f} h a ~0,55 pares/s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
