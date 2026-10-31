#!/usr/bin/env python3
"""
132_evaluar_216.py — evaluacion final: 216 consultas, GT v3, criterio corregido.

POR QUE REUTILIZA utils/gt_metrics.py Y NO REIMPLEMENTA
La primera version de este script calculaba el nDCG con ganancia exponencial
(2^nivel - 1) y con el ideal tomado solo del top_k. El modulo canonico usa
ganancia LINEAL y el ideal tomado de TODOS los juicios de la consulta. Son dos
metricas distintas: sus cifras no son comparables entre si. Medir con dos varas
distintas y enfrentarlas seria un error de metodo, asi que aqui se importa el
modulo y se usa el mismo criterio que el 112 y la Fase A/B.

COMPARACION PAREADA
Los tres sistemas se evaluan sobre LAS MISMAS 216 consultas. Eso permite
compararlos con la diferencia por consulta (pareada), que es mas potente que
comparar dos medias independientes: elimina la varianza entre consultas, que es
la dominante. El intervalo se calcula sobre las DIFERENCIAS, no sobre cada media.

Por eso la mejora detectable de la diferencia sale bastante menor que la de cada
media por separado: es la ganancia real de tener 216 consultas pareadas.
"""
import argparse
import json
import statistics
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.gt_metrics import (EtiquetasGT, evaluar, intervalo_confianza,   # noqa: E402
                              mejora_minima_detectable)

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
GT_VIEJO = ENTREG / "ground_truth.jsonl"
NUEVAS = ENTREG / "consultas_validadas.jsonl"
GT_V3 = ENTREG / "gt_etiquetas_v3.json"
API = "http://localhost:8000/search"

SISTEMAS = {
    "actual (0.7/0.3)": {"semantic_weight": 0.7, "lexical_weight": 0.3},
    "semantico (1.0/0.0)": {"semantic_weight": 1.0, "lexical_weight": 0.0},
    "lexico (0.0/1.0)": {"semantic_weight": 0.0, "lexical_weight": 1.0},
}


def busca(q, top_k, api=None, **kw):
    body = {"query": q, "top_k": top_k}
    body.update(kw)
    req = urllib.request.Request(api or API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=120).read())
    except Exception as e:
        return [], str(e)[:80]
    return d.get("results") or d.get("datasets") or [], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--api", default=API,
                    help="endpoint /search: produccion o el clon de la fase F")
    ap.add_argument("--salida", default=None)
    ap.add_argument("--nuevas", default=str(NUEVAS),
                    help="fichero jsonl con las consultas anadidas a las 47 humanas")
    ap.add_argument("--etiquetas", default=str(GT_V3), help="GT a usar")
    args = ap.parse_args()

    consultas = ([json.loads(l) for l in GT_VIEJO.read_text(encoding="utf-8").splitlines() if l.strip()]
                 + [json.loads(l) for l in Path(args.nuevas).read_text(encoding="utf-8").splitlines() if l.strip()])
    gt = EtiquetasGT(args.etiquetas)
    sin_id = [q for q in consultas if not q.get("id")]
    if sin_id:
        raise SystemExit(f"ERROR: {len(sin_id)} consultas sin id; el GT se indexa por id")

    print("=" * 84)
    print("EVALUACION FINAL · 216 consultas · GT v3 · criterio de ambito corregido")
    print("=" * 84)
    print(f"\n  consultas : {len(consultas)}  (47 originales + 169 nuevas)")
    print(f"  etiquetas : {len(gt)}")
    print(f"  top_k     : {args.top_k}")
    print(f"  nDCG      : ganancia LINEAL (igual que Fase A/B), ideal de todos los juicios")
    print(f"  P@5/MRR   : umbral nivel 2 (estricto)\n")

    por_consulta = {nom: {} for nom in SISTEMAS}
    for nom, kw in SISTEMAS.items():
        fallos = 0
        for q in consultas:
            res, err = busca(q["query"], args.top_k, api=args.api, **kw)
            if err:
                fallos += 1
                continue
            m = evaluar(q["id"], res, gt, k_precision=5, k_ndcg=args.top_k)
            m["cobertura"] = m["cobertura_top10"]
            por_consulta[nom][q["id"]] = m
        print(f"  {nom:22} evaluado" + (f"  ({fallos} fallos de API)" if fallos else ""))

    salida = {"consultas": len(consultas), "etiquetas": len(gt),
              "top_k": args.top_k, "sistemas": {}, "comparaciones": []}

    print(f"\n### A) METRICAS POR SISTEMA ###\n")
    print(f"  {'sistema':22} {'nDCG@10':>8} {'IC95':>20} {'P@5':>7} {'MRR':>7} {'cob':>6}")
    print(f"  {'-'*22} {'-'*8} {'-'*20} {'-'*7} {'-'*7} {'-'*6}")
    for nom in SISTEMAS:
        vals = por_consulta[nom]
        nd = [v["ndcg_at_10"] for v in vals.values()]
        media, lo, hi = intervalo_confianza(nd)
        p5 = statistics.mean([v["precision_at_5"] for v in vals.values()])
        mr = statistics.mean([v["mrr"] for v in vals.values()])
        cob = statistics.mean([v["cobertura"] for v in vals.values()])
        salida["sistemas"][nom] = {
            "ndcg": media, "ic95": [lo, hi], "n": len(nd),
            "desv": round(statistics.stdev(nd), 4) if len(nd) > 1 else 0,
            "p5": round(p5, 4), "mrr": round(mr, 4), "cobertura": round(cob, 4),
            "mmd_media": mejora_minima_detectable(nd),
        }
        print(f"  {nom:22} {media:8.4f} [{lo:.4f} · {hi:.4f}] {p5:7.4f} {mr:7.4f} {cob:6.0%}")

    print(f"\n### B) COMPARACION PAREADA (mismas consultas) ###\n")
    print(f"  La comparacion pareada elimina la varianza ENTRE consultas, que es la")
    print(f"  dominante. Por eso distingue diferencias que las medias sueltas no.\n")
    print(f"  {'comparacion':34} {'diff':>8} {'IC95 de la diff':>22} {'veredicto':>16}")
    print(f"  {'-'*34} {'-'*8} {'-'*22} {'-'*16}")
    nombres = list(SISTEMAS)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            comun = sorted(set(por_consulta[a]) & set(por_consulta[b]))
            diffs = [por_consulta[a][q]["ndcg_at_10"] - por_consulta[b][q]["ndcg_at_10"]
                     for q in comun]
            if len(diffs) < 2:
                continue
            dm = statistics.mean(diffs)
            _, dlo, dhi = intervalo_confianza(diffs)
            if dlo is None or dhi is None:
                continue
            mmd = mejora_minima_detectable(diffs)
            sig = (dlo > 0 and dhi > 0) or (dlo < 0 and dhi < 0)
            veredicto = "DISTINGUIBLE" if sig else "no distinguible"
            salida["comparaciones"].append({
                "a": a, "b": b, "diff": round(dm, 4), "ic95_diff": [dlo, dhi],
                "mmd": mmd, "significativo": bool(sig), "n_pares": len(comun)})
            etq = f"{a.split()[0]} vs {b.split()[0]}"
            print(f"  {etq:34} {dm:+8.4f} [{dlo:+.4f} · {dhi:+.4f}]   {veredicto:>16}")

    print(f"\n### C) POTENCIA: LO QUE DICEN 216 CONSULTAS ###\n")
    nd = [v["ndcg_at_10"] for v in por_consulta["actual (0.7/0.3)"].values()]
    print(f"  desviacion del nDCG@10 entre consultas : {statistics.stdev(nd):.4f}")
    print(f"  mejora detectable de una MEDIA aislada : {mejora_minima_detectable(nd):.4f}")
    diffs = [por_consulta["actual (0.7/0.3)"][q]["ndcg_at_10"]
             - por_consulta["semantico (1.0/0.0)"][q]["ndcg_at_10"]
             for q in por_consulta["actual (0.7/0.3)"]]
    print(f"  mejora detectable de la DIFERENCIA     : {mejora_minima_detectable(diffs):.4f}")
    print(f"\n  (el plan estimo 0,106 con 47 consultas y ~0,050 con 216;")
    print(f"   esas cifras eran de una media aislada, no de una diferencia pareada)")

    if args.salida:
        Path(args.salida).write_text(json.dumps(salida, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
        print(f"\n  guardado: {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
