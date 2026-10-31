#!/usr/bin/env python3
"""
146_hibrido_pareado.py — comparacion PAREADA del hibrido: MiniLM vs BGE-M3.

POR QUE NO SIRVE EL 132
El 132 da medias por sistema, pero no guarda el nDCG de cada consulta, y sin los
pares no se puede hacer la comparacion pareada (que es la que elimina la varianza
entre consultas, dominante aqui). Tampoco mide la cobertura por motor, que es el
control obligatorio: con el pool construido con otros motores, parte de lo que un
motor nuevo devuelve puede no estar juzgado.

QUE HACE
Lanza las 214 consultas contra los DOS endpoints (produccion y el clon), recupera
el top-10 de cada uno en la misma sesion, y evalua con el instrumento canonico.
Guarda el nDCG por consulta para poder comparar pareado.

USO
  python3 146_hibrido_pareado.py
"""
import json
import math
import statistics
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.gt_metrics import EtiquetasGT, evaluar, intervalo_confianza   # noqa: E402

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
ENDPOINTS = {
    "minilm": "http://localhost:8000/search",
    "bge": "http://localhost:8002/search",
}
TOP_K = 10


def busca(api, q, top_k=TOP_K):
    body = {"query": q, "top_k": top_k}
    req = urllib.request.Request(api, data=json.dumps(body).encode(),
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

    nd = {k: [] for k in ENDPOINTS}
    p5, mr, cb = {k: [] for k in ENDPOINTS}, {k: [] for k in ENDPOINTS}, {k: [] for k in ENDPOINTS}
    sin_juzgar = {k: 0 for k in ENDPOINTS}
    total_res = {k: 0 for k in ENDPOINTS}
    t0 = time.time()

    for i, q in enumerate(consultas):
        qid = q["id"]
        for nom, api in ENDPOINTS.items():
            try:
                filas = busca(api, q["query"])
            except Exception as e:
                print(f"  fallo {nom} en {qid}: {str(e)[:60]}", flush=True)
                filas = []
            res = [{"dataset_id": f["id"]} for f in filas]
            for f in filas:
                total_res[nom] += 1
                if gt.nivel(qid, f["id"]) is None:
                    sin_juzgar[nom] += 1
            m = evaluar(qid, res, gt, k_precision=5, k_ndcg=TOP_K)
            nd[nom].append(m["ndcg_at_10"]); p5[nom].append(m["precision_at_5"])
            mr[nom].append(m["mrr"]); cb[nom].append(m["cobertura_top10"])
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(consultas)} ({time.time()-t0:.0f}s)", flush=True)

    print()
    print("### CONTROL DE INSTRUMENTO ###")
    for nom in ENDPOINTS:
        cob = 1 - sin_juzgar[nom] / total_res[nom] if total_res[nom] else 0
        print(f"  {nom:7}: cobertura {cob:6.1%} ({total_res[nom]-sin_juzgar[nom]} juzgados, "
              f"{sin_juzgar[nom]} SIN juzgar de {total_res[nom]})")

    print()
    print("### METRICAS HIBRIDO (0,7/0,3), mismo GT v5, mismas consultas ###")
    print(f"  {'motor':8} {'nDCG@10':>8} {'IC95':>20} {'P@5':>7} {'MRR':>7} {'cob':>6}")
    met = {}
    for nom in ENDPOINTS:
        mu, lo, hi = intervalo_confianza(nd[nom])
        met[nom] = {"ndcg": mu, "ic95": [lo, hi], "p5": statistics.mean(p5[nom]),
                    "mrr": statistics.mean(mr[nom]),
                    "cobertura_pool": statistics.mean(cb[nom])}
        print(f"  {nom:8} {mu:8.4f} [{lo:.4f} · {hi:.4f}] {statistics.mean(p5[nom]):7.4f}"
              f" {statistics.mean(mr[nom]):7.4f} {statistics.mean(cb[nom]):5.1%}")

    print()
    print("### COMPARACION PAREADA (hibrido BGE - hibrido MiniLM) ###")
    dif = [a - b for a, b in zip(nd["bge"], nd["minilm"])]
    mu, lo, hi = intervalo_confianza(dif)
    ee = statistics.stdev(dif) / math.sqrt(len(dif))
    mmd = 1.96 * ee
    cruza = (lo is None or hi is None) or (lo < 0 < hi)
    print(f"  diferencia : {mu:+.4f}  IC95 [{lo:+.4f} · {hi:+.4f}]")
    print(f"  mejora minima detectable: {mmd:.4f}")
    print()
    if cruza:
        print("  VEREDICTO: NO se puede concluir que BGE-M3 mejore el HIBRIDO")
    elif mu > mmd:
        print("  VEREDICTO: BGE-M3 MEJORA EL HIBRIDO (supera lo detectable)")
    else:
        print(f"  VEREDICTO: mejora en la direccion esperada pero {mu:.4f} < {mmd:.4f}: no concluyente")
    print()
    print(f"  consultas donde BGE gana  : {sum(1 for d in dif if d > 0.001)}")
    print(f"  consultas donde empata    : {sum(1 for d in dif if abs(d) <= 0.001)}")
    print(f"  consultas donde MiniLM gana: {sum(1 for d in dif if d < -0.001)}")

    salida = {"consultas": len(consultas), "top_k": TOP_K,
              "metricas": met, "comparacion_pareada": {"diff": mu, "ic95": [lo, hi], "mmd": mmd,
                                                       "cruza_cero": cruza, "n": len(dif)},
              "ndcg_por_consulta": {"minilm": nd["minilm"], "bge": nd["bge"]},
              "consultas_ids": [q["id"] for q in consultas]}
    (ENTREG / "fase_f_HIBRIDO_PAREADO.json").write_text(
        json.dumps(salida, ensure_ascii=False), encoding="utf-8")
    print("\n  guardado: entregables/fase_f_HIBRIDO_PAREADO.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
