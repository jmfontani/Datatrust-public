#!/usr/bin/env python3
"""
Evalúa el buscador de datos.gob.es con el GROUND TRUTH DEL JUEZ (GT v5).

ACTUALIZADO (01-oct-2026): la relevancia la decide el JUICIO del GT v5
(`entregables/gt_etiquetas_v5.json`, escala 0/1/2, clave (query_id,
dataset_id)). ANTES usaba coincidencia de patrones de texto en el título.

RESTRICCIÓN IMPORTANTÍSIMA del portal publico de datos.gob.es: sus SERPs solo
traen TÍTULOS, sin dataset_id estable, por lo que el cruce por (query_id,
dataset_id) del GT v5 NO ES POSIBLE contra ese portal. Este script evalúa:
    1) el solape del portal con los titles del GT v5 (informativa, cobre BAJA:
       los títulos no son identificadores);
    2) NO produce nDCG comparable con el instrumento canónico — lo deja a None
       y lo dice en el output. Las comparaciones de calidad se hacen con la
       SERP del buscador propio (eval_ragas_core.py / eval_nuestro_vs_dge_gt.py).

Uso:
    python eval_datosgobes_core.py \
        --results ../entregables/datosgobes_search_results.jsonl \
        --ground-truth ../entregables/gt_etiquetas_v5.json \
        --output ../entregables/ragas_scores_datosgobes.json
"""

import json
import argparse
import sys
import time
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "utils"))

from utils.ragas_metrics import cargar_gt_v5

def cargar_jsonl(path: Path) -> list[dict]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def _norm(s: str) -> str:
    """Normalización ligera para cruce de títulos (informativa)."""
    return " ".join(s.lower().split())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", "-r", type=str, default="../entregables/datosgobes_search_results.jsonl")
    parser.add_argument("--ground-truth", "-g", type=str, default="../entregables/gt_etiquetas_v5.json")
    parser.add_argument("--output", "-o", type=str, default="../entregables/ragas_scores_datosgobes.json")
    args = parser.parse_args()

    results_path = Path(args.results)
    gt_path = Path(args.ground_truth)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    resultados_raw = cargar_jsonl(results_path)

    metricas = {
        "n_queries": 0,
        "n_con_titles": 0,
        "solape_titles_medio": None,
    }
    resultados_por_query = []
    start_time = time.time()

    for i, res in enumerate(resultados_raw, 1):
        qid = res["id"]
        query = res["query"]
        print(f"   [{i}/{len(resultados_raw)}] {qid}: {query[:50]}...", end=" ", flush=True)

        # El GT del juez no cruza por título: el portal público no da dataset_id.
        # Salida honesta: marcamos la métrica como NO PRODUCTIBLE.
        out = {
            "query_id": qid,
            "query": query,
            "n_titles_portal": len(res.get("titles", [])),
            "precision_at_5": None,
            "precision_at_10": None,
            "ndcg_at_10": None,
            "recall": None,
            "nota": (
                "datos.gob.es solo devuelve títulos (sin dataset_id estable): "
                "el GT v5 del juez cruza por (query_id, dataset_id) y NO es "
                "aplicable al portal. Métricas NO comparables; se mantienen a "
                "None para que ningún reporte las mezcle con las canónicas."
            ),
            "source": "datos.gob.es",
        }
        resultados_por_query.append(out)
        print("⚠️  no comparable (title-only SERP)")

    total_time = time.time() - start_time

    resumen = {
        "n_queries": len(resultados_raw),
        "metricas": {
            "precision_at_5": None,
            "precision_at_10": None,
            "ndcg_at_10": None,
            "recall": None,
            "motivo": "SERP title-only: no hay dataset_id para cruzar con el GT del juez",
        },
        "instrumento": "NO APLICABLE (documentado; ver nota por query)",
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
    print(f"📊 RESULTADOS DATOS.GOB.ES (no comparables)")
    print(f"{'='*60}")
    print(f"   Queries: {resumen['n_queries']}")
    print(f"   nDCG/P/recall: None — el portal no da dataset_id; el GT del juez cruza por id")
    print(f"   Para comparar contra el buscador propio: eval_nuestro_vs_dge_gt.py")
    print(f"\n✅ Resultados guardados en: {output_path}")


if __name__ == "__main__":
    main()