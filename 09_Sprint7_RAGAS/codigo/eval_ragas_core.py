#!/usr/bin/env python3
"""
Evaluación del Buscador Semántico con el GROUND TRUTH DEL JUEZ (GT v5).

ACTUALIZADO (01-oct-2026): la relevancia la decide el JUICIO del GT v5
(`entregables/gt_etiquetas_v5.json`: 10.653 etiquetas del juez LLM sobre
214 consultas, escala 0/1/2, clave (query_id, dataset_id)). ANTES usaba
coincidencia de patrones de texto en el título — criterio retirado del
instrumento canónico (marcaba como relevante el 41 % de lo que el juicio
rechaza; ver utils/gt_metrics.py).

Cobre con el instrumento canonico del proyecto; el marco "RAGAS" real
(context precision/recall, faithfulness con LLM) sigue disponible en
utils/ragas_metrics.evaluar_con_ragas().

Uso:
    # contra el instrumento canonico (recomendado)
    python eval_ragas_core.py --mode basic --output ../entregables/ragas_scores_basic.json

    # limitado (testing)
    python eval_ragas_core.py --mode basic --limit 5

Requiere: API del buscador en localhost:8000 y gt_etiquetas_v5.json.
"""

import json
import argparse
import sys
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

# Imports locales
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "utils"))

try:
    import requests
except ImportError:
    print("❌ Instalando requests: pip install requests")
    sys.exit(1)

from utils.ragas_metrics import evaluar_query_individual, cargar_gt_v5
from utils.gt_metrics import intervalo_confianza

# Configuración de la API
API_URL = "http://localhost:8000"


def check_api_health() -> bool:
    """Verifica que la API esté disponible."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def buscar_datasets(
    query: str,
    top_k: int = 10
) -> list[dict]:
    """
    Busca datasets usando la API del buscador (pesos de producción 0,7/0,3
    implícitos en el endpoint; no se envían pesos explícitos).
    """
    try:
        response = requests.post(
            f"{API_URL}/search",
            json={"query": query, "top_k": top_k},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if "results" in data:
            return data["results"]
        elif isinstance(data, list):
            return data
        print(f"⚠️  Respuesta inesperada: {str(data)[:120]}")
        return []
    except requests.RequestException as e:
        print(f"❌ Error en búsqueda: {e}")
        return []


def cargar_ground_truth(input_path: Path) -> list[dict]:
    """Carga queries de evaluación desde archivo JSONL."""
    items = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def evaluar_con_ground_truth(
    ground_truths: list[dict],
    gt=None,
    limit: Optional[int] = None
) -> dict:
    """
    Evalúa el buscador contra el GT del juez (GT v5).

    Solo evalúa las consultas que TIENEN etiquetas en el GT v5: una consulta
    sin juicios no produce métrica (el nDCG ideal sería indefinido).
    """
    if limit:
        ground_truths = ground_truths[:limit]

    gt = gt or cargar_gt_v5()

    # filtrar a las consultas con etiquetas
    prefixos_et = {k.rsplit("|", 1)[0] for k in gt._et}
    con_juicio = [q for q in ground_truths if q.get("id") in prefixos_et]
    sin_juicio = len(ground_truths) - len(con_juicio)
    print(f"🔍 Evaluando {len(con_juicio)} queries con juicio en el GT v5"
          f" ({sin_juicio} sin etiquetas se EXCLUYEN)")
    if sin_juicio:
        print("   (las excluidas no forman parte del instrumento canonico)")

    resultados_por_query = []
    metricas_agregadas = {
        "precision_at_5": [],
        "precision_at_10": [],
        "ndcg_at_10": [],
        "recall": [],
        "cobertura_top10": [],
    }

    start_time = time.time()

    for i, gtq in enumerate(con_juicio, 1):
        query = gtq["query"]
        query_id = gtq["id"]

        print(f"   [{i}/{len(con_juicio)}] {query_id}: {query[:50]}...", end=" ", flush=True)

        search_start = time.time()
        resultados = buscar_datasets(query, top_k=10)
        search_time = time.time() - search_start

        # Evaluar con el JUICIO (GT v5, por dataset_id)
        eval_result = evaluar_query_individual(query_id, query, resultados, gt)
        eval_result["search_time_sec"] = round(search_time, 3)

        resultados_por_query.append(eval_result)

        # Agregar métricas
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

    # IC95 pareado por consulta (obligatorio al reportar en este proyecto)
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
        "instrumento": "gt_v5_juez (escala 0/1/2; relevancia por dataset_id)",
        "tiempo_total_seg": round(total_time, 2),
        "tiempo_medio_por_query_seg": round(total_time / len(con_juicio), 2) if con_juicio else 0,
    }

    # Análisis por categoría
    categorias = {}
    for gtq, resultado in zip(con_juicio, resultados_por_query):
        cat = gtq.get("categoria", "unknown")
        if cat not in categorias:
            categorias[cat] = {"precision_at_5": [], "ndcg_at_10": []}
        categorias[cat]["precision_at_5"].append(resultado["precision_at_5"])
        categorias[cat]["ndcg_at_10"].append(resultado["ndcg_at_10"])

    resumen["por_categoria"] = {
        cat: {
            "precision_at_5": round(avg(metrics["precision_at_5"]), 4),
            "ndcg_at_10": round(avg(metrics["ndcg_at_10"]), 4),
            "n_queries": len(metrics["precision_at_5"]),
        }
        for cat, metrics in categorias.items()
    }

    # Análisis por dificultad
    dificultades = {}
    for gtq, resultado in zip(con_juicio, resultados_por_query):
        dif = gtq.get("dificultad", "unknown")
        if dif not in dificultades:
            dificultades[dif] = {"precision_at_5": [], "ndcg_at_10": []}
        dificultades[dif]["precision_at_5"].append(resultado["precision_at_5"])
        dificultades[dif]["ndcg_at_10"].append(resultado["ndcg_at_10"])

    resumen["por_dificultad"] = {
        dif: {
            "precision_at_5": round(avg(metrics["precision_at_5"]), 4),
            "ndcg_at_10": round(avg(metrics["ndcg_at_10"]), 4),
            "n_queries": len(metrics["precision_at_5"]),
        }
        for dif, metrics in dificultades.items()
    }

    return {
        "resumen": resumen,
        "resultados_por_query": resultados_por_query,
        "timestamp": datetime.now().isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluación con GT del juez (GT v5)")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["basic"],
        default="basic",
        help="Modo de evaluación (el modo 'llm' del rerank clásico se retiró: usar 146/147)"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="../entregables/ground_truth.jsonl",
        help="Archivo de entrada con las consultas (ids deben existir en el GT v5)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="../entregables/ragas_scores.json",
        help="Archivo de salida con resultados"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Límite de queries a evaluar (para testing)"
    )
    args = parser.parse_args()

    # Verificar API
    print(f"🔌 Verificando API en {API_URL}...")
    if not check_api_health():
        print("❌ API no disponible en localhost:8000")
        sys.exit(1)
    print("   ✅ API disponible")

    # Cargar queries
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Archivo no encontrado: {input_path}")
        sys.exit(1)

    print(f"📖 Cargando queries desde {input_path}...")
    ground_truths = cargar_ground_truth(input_path)

    # GT del juez
    gt = cargar_gt_v5()
    print(f"   GT del juez: {len(gt)} etiquetas (meta: {gt.meta.get('fase','?')}, juez {gt.meta.get('juez','?')})")

    # Evaluar
    resultados = evaluar_con_ground_truth(ground_truths, gt=gt, limit=args.limit)

    # Guardar resultados
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    # Imprimir resumen
    resumen = resultados["resumen"]
    print(f"\n{'='*60}")
    print(f"📊 RESULTADOS DE EVALUACIÓN (instrumento: {resumen['instrumento']})")
    print(f"{'='*60}")
    print(f"   Queries evaluadas: {resumen['n_queries']} (+{resumen['n_excluidas_sin_juicio']} sin juicio, excluidas)")
    print(f"   Tiempo total: {resumen['tiempo_total_seg']:.1f}s ({resumen['tiempo_medio_por_query_seg']:.2f}s/query)")
    print(f"\n   MÉTRICAS GLOBALES:")
    print(f"      Precision@5:  {resumen['metricas']['precision_at_5']:.4f}")
    print(f"      Precision@10: {resumen['metricas']['precision_at_10']:.4f}")
    print(f"      NDCG@10:      {resumen['metricas']['ndcg_at_10']:.4f}  IC95 [{resumen['metricas']['ndcg_at_10_ic95'][0]} · {resumen['metricas']['ndcg_at_10_ic95'][1]}]")
    print(f"      Recall:       {resumen['metricas']['recall']:.4f}")
    print(f"      Cobertura:    {resumen['metricas']['cobertura_top10']:.4f}")

    print(f"\n   POR CATEGORÍA:")
    for cat, metrics in sorted(resumen["por_categoria"].items()):
        print(f"      {cat:15} P@5={metrics['precision_at_5']:.3f} NDCG={metrics['ndcg_at_10']:.3f} (n={metrics['n_queries']})")

    print(f"\n   POR DIFICULTAD:")
    for dif, metrics in sorted(resumen["por_dificultad"].items()):
        print(f"      {dif:15} P@5={metrics['precision_at_5']:.3f} NDCG={metrics['ndcg_at_10']:.3f} (n={metrics['n_queries']})")

    print(f"\n✅ Resultados guardados en: {output_path}")


if __name__ == "__main__":
    main()