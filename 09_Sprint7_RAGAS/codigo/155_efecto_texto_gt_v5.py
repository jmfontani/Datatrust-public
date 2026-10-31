#!/usr/bin/env python3
"""155_efecto_texto_gt_v5.py — mide el efecto TEXTO sobre el GT v5 canonico.

PREGUNTA
La Fase E aisló el efecto MODELO con texto constante (+0,2743, GT v5). El efecto
TEXTO (modelo constante) se midió solo con el GT v4 y sin IC pareado (doc Fase E,
§3: 0,3539 vs 0,3497). Sobre el GT v5 canónico no se ha medido nunca.

QUE HACE
MiniLM con DOS textos sobre el MISMO GT v5 canonico (10.653 etiquetas),
vectorizando la consulta cruda (como la API en producción):
  A. columna `embedding`            -> texto de la limpieza (embedding_text)
  B. columna `embedding_minilm_aprox` -> esquema del 142 (reconstruido)
Comparación pareada B - A = efecto del texto, modelo constante.

USO
  python3 155_efecto_texto_gt_v5.py
"""
import json
import os
import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import psycopg2
from psycopg2.extras import DictCursor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.gt_metrics import EtiquetasGT, evaluar, intervalo_confianza  # noqa: E402

ENT = Path(os.environ.get(
    "ECO_ENTREG",
    str(Path(__file__).resolve().parent.parent / "entregables")))
DB = dict(host=os.getenv("POSTGRES_HOST", "postgres"), port=5432, dbname="buscador",
          user="postgres", password="postgres")
MINILM = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MINILM_REV = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
TOP_K = 10


def main():
    consultas = ([json.loads(l) for l in (ENT / "ground_truth.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
                 + [json.loads(l) for l in (ENT / "consultas_limpias.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()])
    gt = EtiquetasGT(ENT / "gt_etiquetas_v5.json")
    print(f"  consultas: {len(consultas)} · etiquetas: {len(gt)}", flush=True)

    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(MINILM, revision=MINILM_REV)

    conn = psycopg2.connect(**DB)
    nd = {"limpieza": [], "aprox": []}
    t0 = time.time()

    with conn.cursor(cursor_factory=DictCursor) as cur:
        for i, q in enumerate(consultas):
            qid, texto_q = q["id"], q["query"]
            qv = m.encode(texto_q, normalize_embeddings=True).tolist()
            lit = "[" + ",".join(map(str, qv)) + "]"
            vals = {}
            for nom, col in (("limpieza", "embedding"), ("aprox", "embedding_minilm_aprox")):
                cur.execute(
                    f"SELECT dataset_id FROM datasets WHERE {col} IS NOT NULL "
                    f"ORDER BY {col} <=> %s::vector LIMIT %s", (lit, TOP_K))
                filas = cur.fetchall()
                res = [{"dataset_id": f["dataset_id"]} for f in filas]
                mtr = evaluar(qid, res, gt, k_precision=5, k_ndcg=TOP_K)
                vals[nom] = mtr["ndcg_at_10"]
                nd[nom].append(mtr["ndcg_at_10"])
            if (i + 1) % 20 == 0:
                print(f"  {i+1}/{len(consultas)} ({time.time()-t0:.0f}s)", flush=True)

    print("\n### EFECTO DEL TEXTO (MiniLM constante, GT v5 canonico) ###")
    for nom in nd:
        mu, lo, hi = intervalo_confianza(nd[nom])
        print(f"  {nom:9}: nDCG@10 {mu:.4f}  IC95 [{lo:.4f} · {hi:.4f}]")
    dif = [a - b for a, b in zip(nd["aprox"], nd["limpieza"])]
    mu, lo, hi = intervalo_confianza(dif)
    cruza = (lo is None or hi is None) or (lo < 0 < hi)
    print(f"\n  pareada aprox - limpieza: {mu:+.4f}  IC95 [{lo:+.4f} · {hi:+.4f}]"
          f"  -> {'EMPATE (no atribuible)' if cruza else 'DISTINGUIBLE'}")

    (ENT / "fase_h_EFECTO_TEXTO.json").write_text(json.dumps(
        {"consultas": len(consultas), "gt": "gt_etiquetas_v5.json",
         "columnas": {"limpieza": "embedding", "aprox": "embedding_minilm_aprox"},
         "metricas": {k: {"ndcg": statistics.mean(v)} for k, v in nd.items()},
         "efecto_texto": {"diff": mu, "ic95": [lo, hi], "cruza_cero": cruza}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n  guardado: entregables/fase_h_EFECTO_TEXTO.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())