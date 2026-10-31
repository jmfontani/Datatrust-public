#!/usr/bin/env python3
"""
112_evaluar_fase_b.py — FASE B, paso 4. Cierre: re-evaluar con el pool completo.

Compara la linea base (Fase A, pool de junio) con la medicion sobre el pool
ampliado de la Fase B. Lo que debe mejorar es la COBERTURA, y con ella deja de
ser un intervalo para pasar a ser una cifra.

Reporta, por sistema:
  * nDCG@10, P@5, MRR con su intervalo de confianza
  * COBERTURA del pool (la mejora esperada)
  * cuantas etiquetas nuevas entraron en juego
  * la mejora minima detectable (que con mas cobertura y mas juicios baja)
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.gt_metrics import (EtiquetasGT, evaluar, intervalo_confianza,
                              mejora_minima_detectable)

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
GT = ENTREG / "ground_truth.jsonl"
ETIQ_A = ENTREG / "gt_etiquetas.json"
ETIQ_B = ENTREG / "gt_etiquetas_v2.json"
API = "http://localhost:8000/search"

SISTEMAS = {
    "actual (0.7/0.3)": {"semantic_weight": 0.7, "lexical_weight": 0.3},
    "semantico (1.0/0.0)": {"semantic_weight": 1.0, "lexical_weight": 0.0},
    "lexico (0.0/1.0)": {"semantic_weight": 0.0, "lexical_weight": 1.0},
}


def busca(query, top_k, **kw):
    body = {"query": query, "top_k": top_k}
    body.update(kw)
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=90).read())
    except Exception as e:
        return None, str(e)
    return (d.get("results") or d.get("datasets") or []), None


def carga_gt():
    return [json.loads(l) for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()]


def evalua_con(gt, consultas, sistemas, top_k):
    out = {}
    for nom, kw in sistemas.items():
        filas = []
        for q in consultas:
            res, err = busca(q["query"], top_k, **kw)
            if err:
                continue
            filas.append(evaluar(q["id"], res, gt))
        if not filas:
            continue
        p5 = [f["precision_at_5"] for f in filas]
        nd = [f["ndcg_at_10"] for f in filas]
        mr = [f["mrr"] for f in filas]
        cob = [f["cobertura_top10"] for f in filas]
        out[nom] = {
            "n": len(filas),
            "p5": intervalo_confianza(p5),
            "ndcg": intervalo_confianza(nd),
            "mrr": intervalo_confianza(mr),
            "cobertura": round(sum(cob)/len(cob), 4),
            "juzgados": round(sum(f["n_juzgados"] for f in filas)/len(filas), 1),
            "sin_juicio": round(sum(f["n_sin_juicio"] for f in filas)/len(filas), 1),
            "mmd": mejora_minima_detectable(nd),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()

    consultas = carga_gt()
    hay_b = ETIQ_B.exists()
    print("=" * 74)
    print("CIERRE DE LA FASE B: pool ampliado")
    print("=" * 74)
    print(f"\n  consultas: {len(consultas)}   top_k: {args.top_k}")
    print(f"  etiquetas Fase A: {len(EtiquetasGT(ETIQ_A))}")
    if hay_b:
        gb = EtiquetasGT(ETIQ_B)
        print(f"  etiquetas Fase B: {len(gb)}")
    else:
        print("  !! no existe gt_etiquetas_v2.json: solo se mide la Fase A")

    resultados = {}
    print("\n### A) LINEA BASE (pool de junio · Fase A) ###")
    a = evalua_con(EtiquetasGT(ETIQ_A), consultas, SISTEMAS, args.top_k)
    for nom, r in a.items():
        print(f"  {nom:24} nDCG {r['ndcg'][0]:.4f} "
              f"IC95% [{r['ndcg'][1]:.4f} · {r['ndcg'][2]:.4f}]  "
              f"cob {r['cobertura']:.0%}  juzgados {r['juzgados']}")
    resultados["A_linea_base"] = a

    gb = EtiquetasGT(ETIQ_B) if hay_b else None
    if gb is not None:
        print("\n### B) POOL AMPLIADO (Fase B) ###")
        b = evalua_con(gb, consultas, SISTEMAS, args.top_k)
        for nom, r in b.items():
            print(f"  {nom:24} nDCG {r['ndcg'][0]:.4f} "
                  f"IC95% [{r['ndcg'][1]:.4f} · {r['ndcg'][2]:.4f}]  "
                  f"cob {r['cobertura']:.0%}  juzgados {r['juzgados']}")
        resultados["B_pool_ampliado"] = b

        print("\n### COMPARACION ###")
        print(f"  {'sistema':24} {'nDCG A':>8} {'nDCG B':>8} {'delta':>8} "
              f"{'cob A':>7} {'cob B':>7} {'MMD B':>7}")
        print("  " + "-" * 72)
        for nom in SISTEMAS:
            if nom not in a or nom not in b:
                continue
            da = b[nom]["ndcg"][0] - a[nom]["ndcg"][0]
            print(f"  {nom:24} {a[nom]['ndcg'][0]:>8.4f} {b[nom]['ndcg'][0]:>8.4f} "
                  f"{da:>+8.4f} {a[nom]['cobertura']:>6.0%} "
                  f"{b[nom]['cobertura']:>6.0%} {b[nom]['mmd']:>7.4f}")

        print("\n  MEJORA ESPERADA: no que suba el nDCG, sino que SUBA LA COBERTURA")
        print("  y BAJE la mejora minima detectable. Con mas juicios, la misma")
        print("  diferencia se vuelve distinguible; con mas cobertura, la cifra")
        print("  deja de ser un intervalo ancho.")

        print("\n### ¿que aporta el pool ampliado? ###")
        nuevas = set(gb._et) - set(EtiquetasGT(ETIQ_A)._et)
        print(f"  etiquetas nuevas: {len(nuevas)}")
        from collections import Counter
        dist = Counter(int(v) for k, v in gb._et.items() if k in nuevas)
        print(f"  distribucion de las nuevas: {dict(sorted(dist.items()))}")
        if dist[2]:
            print(f"  -> {dist[2]} fichas nuevas marcadas RESPONDE: antes contaban")
            print(f"     como no relevantes y penalizaban al motor que las encontraba.")

    if args.salida:
        Path(args.salida).write_text(json.dumps({
            "meta": {"fase": "B", "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
                     "top_k": args.top_k, "n_consultas": len(consultas)},
            "resultados": resultados,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n  guardado: {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
