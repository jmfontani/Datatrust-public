#!/usr/bin/env python3
"""
147_precision_10.py — P@5 y P@10 del hibrido, con cache de rankings.

POR QUE
El instrumento canonico (gt_metrics.evaluar) usa k_precision=5, asi que P@10 no
estaba calculado en ningun entregable de las fases E ni F. Y no se puede derivar
de lo guardado: nDCG y MRR no lo contienen, y los rankings por consulta no se
guardaron (solo el ndcg de cada una).

QUE HACE
  1. Lanza las 214 consultas contra los DOS motores hibridos (MiniLM y BGE-M3).
  2. GUARDA los rankings completos por consulta en cache_resultados_faseg.json
     -> permite calcular cualquier metrica a cualquier k sin volver a consultar.
  3. Calcula P@5, P@10, P@10/P@5, MRR, nDCG@10 y COBERTURA de cada motor.

COBERTURA: se imprime siempre, porque P@k sobre resultados sin juzgar no es
interpretable. El denominador es k (el no juzgado ocupa puesto y desplaza).

USO
  python3 147_precision_10.py            # mide y guarda
  python3 147_precision_10.py --desde-cache   # recalcula sin consultar
"""
import argparse
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
CACHE = ENTREG / "cache_resultados_faseg.json"
ENDPOINTS = {
    "minilm (0.7/0.3)": "http://localhost:8000/search",
    "bge (0.7/0.3)": "http://localhost:8002/search",
}
TOP_K = 10


def busca(api, q, top_k=TOP_K):
    body = {"query": q, "top_k": top_k}
    req = urllib.request.Request(api, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=300).read())
    return [{"dataset_id": x["id"], "score": x.get("score")} for x in (d.get("results") or [])]


def recolectar(consultas):
    ran = {k: {} for k in ENDPOINTS}
    t0 = time.time()
    for i, q in enumerate(consultas):
        for nom, api in ENDPOINTS.items():
            try:
                ran[nom][q["id"]] = busca(api, q["query"])
            except Exception as e:
                print(f"  fallo {nom} en {q['id']}: {str(e)[:60]}", flush=True)
                ran[nom][q["id"]] = []
        if (i + 1) % 40 == 0:
            print(f"  {i+1}/{len(consultas)} ({time.time()-t0:.0f}s)", flush=True)
    return ran


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde-cache", action="store_true")
    args = ap.parse_args()

    consultas = ([json.loads(l) for l in (ENTREG / "ground_truth.jsonl")
                  .read_text(encoding="utf-8").splitlines() if l.strip()]
                 + [json.loads(l) for l in (ENTREG / "consultas_limpias.jsonl")
                    .read_text(encoding="utf-8").splitlines() if l.strip()])
    gt = json.loads((ENTREG / "gt_etiquetas_v5.json").read_text(encoding="utf-8"))["etiquetas"]
    print(f"  consultas: {len(consultas)} · etiquetas: {len(gt)}", flush=True)

    if args.desde_cache and CACHE.exists():
        ran = json.loads(CACHE.read_text(encoding="utf-8"))
        print("  rankings leidos de cache")
    else:
        print("  consultando los dos motores...", flush=True)
        ran = recolectar(consultas)
        CACHE.write_text(json.dumps(ran, ensure_ascii=False), encoding="utf-8")
        print(f"  cache guardada: {CACHE.name}")

    print()
    print("### PRECISION A 5 Y 10 · HIBRIDO 0,7/0,3 · GT v5 · umbral nivel 2 ###")
    print(f"  {'motor':18} {'P@5':>7} {'P@10':>7} {'P@10/P@5':>9} {'MRR':>7} "
          f"{'nDCG@10':>8} {'cob@5':>7} {'cob@10':>7}")
    salida = {}
    for nom in ENDPOINTS:
        filas = [ran[nom][q["id"]] for q in consultas]
        p5, p10, mr, nd, c5, c10 = [], [], [], [], [], []
        for q, res in zip(consultas, filas):
            niveles = [gt.get(f"{q['id']}|{r['dataset_id']}") for r in res]
            niv5, niv10 = niveles[:5], niveles[:10]
            rel5 = sum(1 for x in niv5 if x is not None and x >= 2)
            rel10 = sum(1 for x in niv10 if x is not None and x >= 2)
            p5.append(rel5 / min(5, len(res)) if res else 0.0)
            p10.append(rel10 / min(10, len(res)) if res else 0.0)
            c5.append(sum(1 for x in niv5 if x is not None) / len(niv5) if niv5 else 0.0)
            c10.append(sum(1 for x in niv10 if x is not None) / len(niv10) if niv10 else 0.0)
            rr = 0.0
            for i, x in enumerate(niv10):
                if x is not None and x >= 2:
                    rr = 1.0 / (i + 1); break
            mr.append(rr)
            import math
            dcg = sum((x or 0) / math.log2(i + 2) for i, x in enumerate(niv10))
            pref = f"{q['id']}|"
            todos = sorted((int(v) for k, v in gt.items() if k.startswith(pref)), reverse=True)[:TOP_K]
            idcg = sum(v / math.log2(i + 2) for i, v in enumerate(todos))
            nd.append(dcg / idcg if idcg else 0.0)
        m = {"p5": statistics.mean(p5), "p10": statistics.mean(p10),
             "p10_sobre_p5": statistics.mean(p10) / statistics.mean(p5) if statistics.mean(p5) else 0.0,
             "mrr": statistics.mean(mr), "ndcg10": statistics.mean(nd),
             "cobertura_p5": statistics.mean(c5), "cobertura_p10": statistics.mean(c10),
             "n": len(consultas)}
        salida[nom] = m
        print(f"  {nom:18} {m['p5']:7.4f} {m['p10']:7.4f} {m['p10_sobre_p5']:9.2f} "
              f"{m['mrr']:7.4f} {m['ndcg10']:8.4f} {m['cobertura_p5']:6.1%} {m['cobertura_p10']:6.1%}")

    print()
    print("### DIFERENCIA PAREADA BGE - MiniLM ###")
    for met in ("p5", "p10"):
        dif = []
        for q in consultas:
            va, vb = [], []
            for r in ran["minilm (0.7/0.3)"][q["id"]][: (5 if met == "p5" else 10)]:
                va.append(gt.get(f"{q['id']}|{r['dataset_id']}"))
            for r in ran["bge (0.7/0.3)"][q["id"]][: (5 if met == "p5" else 10)]:
                vb.append(gt.get(f"{q['id']}|{r['dataset_id']}"))
            k = 5 if met == "p5" else 10
            ra = sum(1 for x in va[:k] if x is not None and x >= 2) / k
            rb = sum(1 for x in vb[:k] if x is not None and x >= 2) / k
            dif.append(rb - ra)
        mu = statistics.mean(dif)
        ee = statistics.stdev(dif) / (len(dif) ** 0.5)
        print(f"  {met:5}: {mu:+.4f}  IC95 [{mu-1.96*ee:+.4f} · {mu+1.96*ee:+.4f}]  "
              f"{'DISTINGUIBLE' if (mu-1.96*ee) > 0 else 'no distinguible'}")

    salida["_cache"] = str(CACHE)
    (ENTREG / "fase_g_PRECISION.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n  guardado: entregables/fase_g_PRECISION.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
