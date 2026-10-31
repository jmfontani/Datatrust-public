#!/usr/bin/env python3
"""150_pesos_hibrido_bge.py — comparacion PAREADA de pesos del hibrido, con BGE en produccion.

POR QUE
El usuario pidio "deja 0.3/0.7". En la convencion del proyecto el par se escribe
(semantico/lexico), asi que 0,3/0,7 significa semantico 0,3 - lexico 0,7, que es lo
CONTRARIO del 0,7/0,3 actual medido. Antes de cambiar produccion hay que medir, porque
el unico dato previo de BGE con distinto peso es 1,0/0,0 (0,5694), y el 0,3/0,7 NO esta
medido.

QUE MIDE
Las mismas 214 consultas y el mismo instrumento canonico que las Fases E/F/G, contra
/search de produccion (BGE-M3, embedding_bge), con tres repartos de peso:
  (0.7, 0.3) actual
  (1.0, 0.0) solo semantico  [ya medido: 0,5694 — se recalcula para control]
  (0.3, 0.7) invertido       [lo pedido, si el par se lee (sem/lex)]
Mas la comparacion pareada de cada uno contra el actual.

USO
  python3 150_pesos_hibrido_bge.py
"""
import json
import math
import statistics
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.gt_metrics import EtiquetasGT, evaluar, intervalo_confianza  # noqa: E402

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
API = "http://localhost:8000/search"
TOP_K = 10
PESOS = {
    "actual (0.7/0.3)": (0.7, 0.3),
    "semantico (1.0/0.0)": (1.0, 0.0),
    "invertido (0.3/0.7)": (0.3, 0.7),
}


def busca(q, sem, lex, top_k=TOP_K):
    body = {"query": q, "top_k": top_k, "semantic_weight": sem, "lexical_weight": lex}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=300).read())
    return d.get("results") or []


def main():
    consultas = ([json.loads(l) for l in (ENTREG / "ground_truth.jsonl")
                  .read_text(encoding="utf-8").splitlines() if l.strip()]
                 + [json.loads(l) for l in (ENTREG / "consultas_limpias.jsonl")
                    .read_text(encoding="utf-8").splitlines() if l.strip()])
    gt = EtiquetasGT(ENTREG / "gt_etiquetas_v5.json")
    print(f"  consultas: {len(consultas)} · etiquetas: {len(gt)}", flush=True)

    nd = {k: [] for k in PESOS}
    p5 = {k: [] for k in PESOS}
    mr = {k: [] for k in PESOS}
    cb = {k: [] for k in PESOS}
    t0 = time.time()

    for i, q in enumerate(consultas):
        qid = q["id"]
        for nom, (sem, lex) in PESOS.items():
            try:
                filas = busca(q["query"], sem, lex)
            except Exception as e:
                print(f"  fallo {nom} en {qid}: {str(e)[:60]}", flush=True)
                filas = []
            res = [{"dataset_id": f["id"]} for f in filas]
            m = evaluar(qid, res, gt, k_precision=5, k_ndcg=TOP_K)
            nd[nom].append(m["ndcg_at_10"])
            p5[nom].append(m["precision_at_5"])
            mr[nom].append(m["mrr"])
            cb[nom].append(m["cobertura_top10"])
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(consultas)} ({time.time()-t0:.0f}s)", flush=True)

    print()
    print("### METRICAS POR REPARTO DE PESOS (BGE-M3, GT v5, 214 consultas) ###")
    print(f"  {'pesos':22} {'nDCG@10':>8} {'IC95':>20} {'P@5':>7} {'MRR':>7} {'cob':>6}")
    met = {}
    for nom in PESOS:
        mu, lo, hi = intervalo_confianza(nd[nom])
        met[nom] = {"ndcg": mu, "ic95": [lo, hi], "p5": statistics.mean(p5[nom]),
                    "mrr": statistics.mean(mr[nom]), "cobertura": statistics.mean(cb[nom])}
        print(f"  {nom:22} {mu:8.4f} [{lo:.4f} · {hi:.4f}] {statistics.mean(p5[nom]):7.4f}"
              f" {statistics.mean(mr[nom]):7.4f} {statistics.mean(cb[nom]):5.1%}")

    print()
    print("### COMPARACION PAREADA CONTRA EL ACTUAL (0.7/0.3) ###")
    comps = []
    for nom in PESOS:
        if nom.startswith("actual"):
            continue
        dif = [a - b for a, b in zip(nd[nom], nd["actual (0.7/0.3)"])]
        mu, lo, hi = intervalo_confianza(dif)
        cruza = (lo is None or hi is None) or (lo < 0 < hi)
        comps.append({"a": nom, "b": "actual (0.7/0.3)", "diff": mu,
                      "ic95_diff": [lo, hi], "cruza_cero": cruza, "n_pares": len(dif)})
        print(f"  {nom:22} {mu:+.4f}  IC95 [{lo:+.4f} · {hi:+.4f}]  "
              f"{'EMPATE (cruza cero)' if cruza else 'DISTINGUIBLE'}")

    (ENTREG / "fase_h_PESOS.json").write_text(json.dumps(
        {"consultas": len(consultas), "top_k": TOP_K, "motor": "bge (embedding_bge)",
         "pesos": {k: list(v) for k, v in PESOS.items()},
         "metricas": met, "comparaciones": comps,
         "ndcg_por_consulta": {k: nd[k] for k in PESOS}},
        ensure_ascii=False), encoding="utf-8")
    print("\n  guardado: entregables/fase_h_PESOS.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
