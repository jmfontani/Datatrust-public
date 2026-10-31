#!/usr/bin/env python3
"""
105_evaluar_v2.py — FASE A, paso 3. Evaluador con el criterio del JUICIO.

Diferencia con eval_ragas_core.py (el actual):
  * la relevancia sale del indice de juicios por dataset_id, no de patrones
  * los documentos SIN JUICIO se excluyen y se contabilizan (cobertura)
  * metricas: P@5, nDCG@10 gradado y MRR
  * se reporta el INTERVALO DE CONFIANZA y la MEJORA MINIMA DETECTABLE

Uso:
  python 105_evaluar_v2.py                       # 47 consultas, 3 sistemas
  python 105_evaluar_v2.py --top-k 10 --salida ../entregables/fase_a_baseline.json
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

GT = Path(__file__).resolve().parent.parent / "entregables" / "ground_truth.jsonl"
API = "http://localhost:8000/search"

# Sistemas a comparar. El lexico NO usa embeddings: sirve de referencia
# independiente del encoder.
SISTEMAS = {
    "actual (0.7/0.3)": {"semantic_weight": 0.7, "lexical_weight": 0.3},
    "semantico (1.0/0.0)": {"semantic_weight": 1.0, "lexical_weight": 0.0},
    "lexico (0.0/1.0)": {"semantic_weight": 0.0, "lexical_weight": 1.0},
}


def carga_gt(ruta):
    out = []
    for ln in ruta.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                pass
    return out


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--salida", default=None)
    ap.add_argument("--sistemas", default=None,
                    help="lista separada por comas; por defecto los tres")
    args = ap.parse_args()

    gt = EtiquetasGT()
    consultas = carga_gt(GT)
    print("=" * 74)
    print("EVALUACION CON EL CRITERIO DEL JUICIO (Fase A)")
    print("=" * 74)
    print(f"\n  indice de juicios : {len(gt)} etiquetas")
    print(f"  consultas         : {len(consultas)}")
    print(f"  top_k             : {args.top_k}")
    print(f"  juez              : {gt.meta.get('juez','?')}")

    sistemas = SISTEMAS
    if args.sistemas:
        nombres = [s.strip() for s in args.sistemas.split(",")]
        sistemas = {k: v for k, v in SISTEMAS.items() if k in nombres}

    resultados = {}
    for nombre, kw in sistemas.items():
        print(f"\n### sistema: {nombre} ###\n")
        print(f"  {'consulta':14} {'juzg':>5} {'P@5':>6} {'nDCG@10':>8} "
              f"{'MRR':>6} {'cobert':>7}")
        print("  " + "-" * 52)

        filas = []
        t0 = time.time()
        for q in consultas:
            qid = q.get("id")
            res, err = busca(q["query"], args.top_k, **kw)
            if err:
                print(f"  {qid:14} ERROR {err[:40]}")
                continue
            m = evaluar(qid, res, gt)
            filas.append(m)
            print(f"  {qid:14} {m['n_juzgados']:>5} {m['precision_at_5']:>6.2f} "
                  f"{m['ndcg_at_10']:>8.3f} {m['mrr']:>6.3f} "
                  f"{m['cobertura_top10']:>6.0%}")
        dt = time.time() - t0

        if not filas:
            continue

        def col(k):
            return [f[k] for f in filas]

        p5 = col("precision_at_5")
        nd = col("ndcg_at_10")
        mr = col("mrr")
        cob = col("cobertura_top10")

        mp5, lp5, hp5 = intervalo_confianza(p5)
        mnd, lnd, hnd = intervalo_confianza(nd)
        mmr, lmr, hmr = intervalo_confianza(mr)

        print(f"\n  --- agregado ({len(filas)} consultas, {dt:.0f} s) ---")
        print(f"  P@5     {mp5:.4f}   IC95% [{lp5:.4f} · {hp5:.4f}]")
        print(f"  nDCG@10 {mnd:.4f}   IC95% [{lnd:.4f} · {hnd:.4f}]")
        print(f"  MRR     {mmr:.4f}   IC95% [{lmr:.4f} · {hmr:.4f}]")
        print(f"  cobertura del pool (media)  {sum(cob)/len(cob):.1%}")
        print(f"  mejora minima detectable    {mejora_minima_detectable(nd):.4f} (nDCG)")

        # aviso de interpretabilidad
        cob_media = sum(cob) / len(cob)
        if cob_media < 0.7:
            print(f"\n  !! AVISO: cobertura {cob_media:.0%} < 70 %. La metrica no es")
            print(f"     plenamente interpretable: hay documentos sin juicio que ocupan")
            print(f"     puesto y desplazan a relevantes. La Fase B lo corrige.")

        resultados[nombre] = {
            "n_consultas": len(filas),
            "precision_at_5": {"media": mp5, "ic95": [lp5, hp5]},
            "ndcg_at_10": {"media": mnd, "ic95": [lnd, hnd]},
            "mrr": {"media": mmr, "ic95": [lmr, hmr]},
            "cobertura_media": round(cob_media, 4),
            "juzgados_por_consulta": round(sum(col("n_juzgados")) / len(filas), 1),
            "sin_juicio_por_consulta": round(sum(col("n_sin_juicio")) / len(filas), 1),
            "mejora_minima_detectable": mejora_minima_detectable(nd),
            "detalle": filas,
        }

    # comparacion entre sistemas
    if len(resultados) > 1:
        print("\n" + "=" * 74)
        print("COMPARACION ENTRE SISTEMAS (nDCG@10)")
        print("=" * 74)
        orden = sorted(resultados.items(),
                       key=lambda kv: -kv[1]["ndcg_at_10"]["media"])
        for nom, r in orden:
            print(f"  {nom:24} {r['ndcg_at_10']['media']:.4f}  "
                  f"IC95% [{r['ndcg_at_10']['ic95'][0]:.4f} · "
                  f"{r['ndcg_at_10']['ic95'][1]:.4f}]  "
                  f"cob {r['cobertura_media']:.0%}")
        print(f"\n  (un sistema solo se distingue de otro si sus intervalos NO se solapan)")

    if args.salida:
        out = Path(args.salida)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "meta": {
                "fase": "A",
                "criterio": "juicio del LLM por dataset_id (no patrones)",
                "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "n_etiquetas": len(gt),
                "top_k": args.top_k,
                "nota": ("Los documentos sin juicio se EXCLUYEN del calculo y se "
                         "contabilizan en la cobertura. Los no juzgados ocupan "
                         "puesto, asi que penalizan."),
            },
            "resultados": resultados,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n  guardado: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
