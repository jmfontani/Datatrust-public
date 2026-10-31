#!/usr/bin/env python3
"""157_metricas_snapshot.py — metricas desde el SNAPSHOT de produccion, sin tocar la API.

Recalcula P@5, P@10, nDCG@10, MRR y cobertura sobre los rankings COMPLETOS guardados
(`fase_h_SNAPSHOT_DESPUES.json`), con el ground truth que se le pase. No llama a la API:
un ranking guardado permite recalcular cualquier metrica a cualquier k y con cualquier GT.

Usa SIEMPRE el modulo canonico `utils/gt_metrics.py` (nunca reimplementar la formula).

Uso:
  python 157_metricas_snapshot.py --gt gt_etiquetas_v5.json
  python 157_metricas_snapshot.py --gt gt_etiquetas_v6.json
  python 157_metricas_snapshot.py --gt gt_etiquetas_v5.json --salida fase_h_METRICAS_v5.json
"""
import argparse
import json
import statistics as st
import sys
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.gt_metrics import (EtiquetasGT, evaluar, precision_at_k,  # noqa: E402
                              intervalo_confianza, mejora_minima_detectable)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", default="gt_etiquetas_v5.json")
    ap.add_argument("--snapshot", default="fase_h_SNAPSHOT_DESPUES.json")
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()

    gt = EtiquetasGT(ENTREG / args.gt)
    snap = json.loads((ENTREG / args.snapshot).read_text(encoding="utf-8"))["rankings"]
    query_ids = list(snap)

    filas = []
    for qid in query_ids:
        res = [{"dataset_id": r["dataset_id"]} for r in snap[qid]]
        e = evaluar(qid, res, gt, k_precision=5, k_ndcg=10)
        e["precision_at_10"] = round(precision_at_k(res, gt, qid, k=10), 4)
        filas.append(e)

    def bloque(sub, nombre):
        n = len(sub)
        p5 = [f["precision_at_5"] for f in sub]
        p10 = [f["precision_at_10"] for f in sub]
        nd = [f["ndcg_at_10"] for f in sub]
        mr = [f["mrr"] for f in sub]
        cob = sum(f["cobertura_top10"] for f in sub) / n
        sinj = sum(f["n_sin_juicio"] for f in sub)
        return {
            "conjunto": nombre, "n_consultas": n,
            "p_at_5": round(st.mean(p5), 4),
            "p_at_10": round(st.mean(p10), 4),
            "ndcg_at_10": round(st.mean(nd), 4),
            "ndcg_ic95": intervalo_confianza(nd),
            "mrr": round(st.mean(mr), 4),
            "cobertura_top10": round(cob, 4),
            "sin_juicio_en_top10": sinj,
            "mejora_minima_detectable_ndcg": mejora_minima_detectable(nd),
            "consultas_saturadas_p5_1": sum(1 for f in sub if f["precision_at_5"] == 1.0),
            "consultas_p5_0": sum(1 for f in sub if f["precision_at_5"] == 0.0),
        }

    humanas = [f for f in filas if not f["query_id"].startswith("limp_")]
    out = {
        "gt": args.gt, "snapshot": args.snapshot,
        "instrumento": "gt_v5_juez / gt_v6 (escala 0/1/2, relevancia por dataset_id)",
        "nota": "Metricas calculadas sobre rankings guardados; no se ha consultado la API.",
        "global_214": bloque(filas, "las 214 consultas"),
        "humanas_47": bloque(humanas, "las 47 consultas humanas"),
        "por_consulta": filas,
    }
    print(f"{'conjunto':22} {'n':>4} {'P@5':>7} {'P@10':>7} {'nDCG@10':>8} {'MRR':>7} {'cob':>7} {'sin juicio':>11}")
    for b in (out["global_214"], out["humanas_47"]):
        print(f"{b['conjunto']:22} {b['n_consultas']:>4} {b['p_at_5']:>7.4f} {b['p_at_10']:>7.4f} "
              f"{b['ndcg_at_10']:>8.4f} {b['mrr']:>7.4f} {b['cobertura_top10']:>7.4f} {b['sin_juicio_en_top10']:>11}")
    if args.salida:
        (ENTREG / args.salida).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n  escrito: entregables/{args.salida}")


if __name__ == "__main__":
    main()
