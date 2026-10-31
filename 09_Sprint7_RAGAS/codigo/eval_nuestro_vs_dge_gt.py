#!/usr/bin/env python3
"""
Evalúa nuestro buscador (API local localhost:8000) con el GROUND TRUTH DEL
JUEZ (GT v5), aplicado al subconjunto de consultas derivadas de datos.gob.es.

ACTUALIZADO (01-oct-2026): la relevancia la decide el JUICIO del GT v5
(`entregables/gt_etiquetas_v5.json`: 10.653 etiquetas, 214 consultas, escala
0/1/2, clave (query_id, dataset_id)). ANTES usaba coincidencia de patrones de
texto en el título — criterio retirado (ver utils/gt_metrics.py).

Solo evalúa las consultas del fichero de entrada que TIENEN etiquetas en el
GT v5; las demás se excluyen y se contabilizan (no cuentan como "0 relevantes").

Uso:
    python eval_nuestro_vs_dge_gt.py \
        --ground-truth ../entregables/ground_truth_datosgobes.jsonl \
        --output ../entregables/ragas_scores_nuestro_vs_dge_gt.json
"""

import json
import argparse
import sys
import time
from pathlib import Path
from datetime import datetime

import requests

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "utils"))

from utils.ragas_metrics import evaluar_query_individual, cargar_gt_v5
from utils.gt_metrics import intervalo_confianza


API_URL = "http://localhost:8000"


def check_api_health() -> bool:
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def buscar_datasets_api(query: str, top_k: int = 10) -> list[dict]:
    try:
        r = requests.post(
            f"{API_URL}/search",
            json={"query": query, "top_k": top_k},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if "results" in data:
            return data["results"]
        elif isinstance(data, list):
            return data
        return []
    except Exception as e:
        print(f"❌ Error en búsqueda: {e}")
        return []


def cargar_jsonl(path: Path) -> list[dict]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ground-truth", "-g", type=str, default="../entregables/ground_truth_datosgobes.jsonl")
    parser.add_argument("--output", "-o", type=str, default="../entregables/ragas_scores_nuestro_vs_dge_gt.json")
    args = parser.parse_args()

    gt_path = Path(args.ground_truth)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not check_api_health():
        print(f"❌ API no disponible en {API_URL}")
        sys.exit(1)

    gt = cargar_gt_v5()
    ground_truths = cargar_jsonl(gt_path)

    # solo consultas con juicio en el GT v5
    prefixos_et = {k.rsplit("|", 1)[0] for k in gt._et}
    con_juicio = [q for q in ground_truths if q.get("id") in prefixos_et]
    sin_juicio = len(ground_truths) - len(con_juicio)
    print(f"🔍 Evaluando nuestro buscador con el GT del juez: {len(con_juicio)} queries"
          f" ({sin_juicio} del fichero sin etiquetas se EXCLUYEN)")

    metricas_agregadas = {
        "precision_at_5": [],
        "precision_at_10": [],
        "ndcg_at_10": [],
        "recall": [],
        "cobertura_top10": [],
    }
    resultados_por_query = []

    start_time = time.time()

    for i, gtq in enumerate(con_juicio, 1):
        qid = gtq["id"]
        query = gtq["query"]
        print(f"   [{i}/{len(con_juicio)}] {qid}: {query[:50]}...", end=" ", flush=True)

        search_start = time.time()
        resultados = buscar_datasets_api(query, top_k=10)
        search_time = time.time() - search_start

        eval_result = evaluar_query_individual(qid, query, resultados, gt)
        eval_result["search_time_sec"] = round(search_time, 3)
        eval_result["source"] = "nuestro_buscador_vs_dge_gt"

        resultados_por_query.append(eval_result)
        metricas_agregadas["precision_at_5"].append(eval_result["precision_at_5"])
        metricas_agregadas["precision_at_10"].append(eval_result["precision_at_10"])
        metricas_agregadas["ndcg_at_10"].append(eval_result["ndcg_at_10"])
        metricas_agregadas["recall"].append(eval_result["recall"])
        metricas_agregadas["cobertura_top10"].append(eval_result["cobertura_top10"])

        status = "✅" if eval_result["ndcg_at_10"] >= 0.5 else "⚠️" if eval_result["ndcg_at_10"] > 0 else "❌"
        print(f"{status} nDCG={eval_result['ndcg_at_10']:.2f} cob={eval_result['cobertura_top10']:.2f} ({search_time:.2f}s)")

    total_time = time.time() - start_time

    def avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    _, ic_lo, ic_hi = intervalo_confianza(metricas_agregadas["ndcg_at_10"])

    resumen = {
        "metricas": {
            "precision_at_5": round(avg(metricas_agregadas["precision_at_5"]), 4),
            "precision_at_10": round(avg(metricas_agregadas["precision_at_10"]), 4),
            "ndcg_at_10": round(avg(metricas_agregadas["ndcg_at_10"]), 4),
            "ndcg_at_10_ic95": [ic_lo, ic_hi],
            "recall": round(avg(metricas_agregadas["recall"]), 4),
            "cobertura_top10": round(avg(metricas_agregadas["cobertura_top10"]), 4),
        },
        "n_queries": len(con_juicio),
        "n_excluidas_sin_juicio": sin_juicio,
        "source": "nuestro_buscador_vs_dge_gt",
        "instrumento": "gt_v5_juez (escala 0/1/2; relevancia por dataset_id)",
        "tiempo_total_seg": round(total_time, 2),
    }

    output_data = {
        "resumen": resumen,
        "resultados_por_query": resultados_por_query,
        "timestamp": datetime.now().isoformat(),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"📊 NUESTRO BUSCADOR (GT del juez, consultas datos.gob.es)")
    print(f"{'='*60}")
    print(f"   Queries evaluadas: {resumen['n_queries']} (+{resumen['n_excluidas_sin_juicio']} sin juicio, excluidas)")
    print(f"   Precision@5:  {resumen['metricas']['precision_at_5']:.4f}")
    print(f"   Precision@10: {resumen['metricas']['precision_at_10']:.4f}")
    print(f"   NDCG@10:      {resumen['metricas']['ndcg_at_10']:.4f}  IC95 [{ic_lo} · {ic_hi}]")
    print(f"   Recall:       {resumen['metricas']['recall']:.4f}")
    print(f"   Cobertura:    {resumen['metricas']['cobertura_top10']:.4f}")
    print(f"\n✅ Resultados guardados en: {output_path}")


if __name__ == "__main__":
    main()