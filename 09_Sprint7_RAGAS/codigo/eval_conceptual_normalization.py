#!/usr/bin/env python3
"""
Evaluación de Normalización Conceptual - EXPERIMENTAL

Compara 3 modos de búsqueda:
1. Búsqueda básica (actual)
2. conceptual_normalization=True, adjust_scores=False (anotación)
3. conceptual_normalization=True, adjust_scores=True (ranking ajustado)

Métricas:
- P@5, P@10, NDCG@10
- Tiempo medio/query
- Distribución de clasificaciones conceptuales

Uso:
    python eval_conceptual_normalization.py

Autor: Fonta
Fecha: 2026-06-05
"""

import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

try:
    import requests
except ImportError:
    print("❌ Instalando requests: pip install requests")
    import sys
    sys.exit(1)


# ============================================
# CONFIGURACIÓN
# ============================================

API_URL = "http://localhost:8000"

# Queries de prueba enfocadas en conceptos ambiguos
TEST_QUERIES = [
    # Empleo
    {"query": "paro juvenil", "categoria": "empleo", "dificultad": "fácil"},
    {"query": "desempleo municipal", "categoria": "empleo", "dificultad": "media"},
    {"query": "tasa de paro por comunidades", "categoria": "empleo", "dificultad": "fácil"},

    # Vivienda
    {"query": "alquiler vivienda", "categoria": "vivienda", "dificultad": "fácil"},
    {"query": "precio vivienda", "categoria": "vivienda", "dificultad": "fácil"},
    {"query": "mercado inmobiliario", "categoria": "vivienda", "dificultad": "media"},

    # Sanidad
    {"query": "gasto sanitario", "categoria": "sanidad", "dificultad": "fácil"},
    {"query": "hospitales públicos", "categoria": "sanidad", "dificultad": "media"},

    # Educación
    {"query": "abandono escolar", "categoria": "educacion", "dificultad": "fácil"},
    {"query": "fracaso educativo", "categoria": "educacion", "dificultad": "media"},

    # Demografía
    {"query": "población envejecida", "categoria": "demografia", "dificultad": "media"},
    {"query": "personas mayores", "categoria": "demografia", "dificultad": "fácil"},

    # Transporte
    {"query": "transporte público", "categoria": "transporte", "dificultad": "fácil"},
    {"query": "movilidad urbana", "categoria": "transporte", "dificultad": "media"},

    # Medio Ambiente
    {"query": "calidad del aire", "categoria": "medio_ambiente", "dificultad": "fácil"},
    {"query": "contaminación atmosférica", "categoria": "medio_ambiente", "dificultad": "media"},
]

# Ground truth mínimo para evaluación
# Formato: {query_pattern: [patrones de títulos esperados]}
GROUND_TRUTH = {
    "paro juvenil": ["paro juvenil", "desempleo juvenil", "jóvenes parados", "tasa de paro juvenil"],
    "desempleo municipal": ["paro", "desempleo", "desocupados"],
    "tasa de paro": ["paro", "desempleo", "tasa de paro"],
    "alquiler vivienda": ["alquiler", "arrendamiento", "renta alquiler"],
    "precio vivienda": ["compraventa", "precio vivienda", "transmisiones"],
    "mercado inmobiliario": ["vivienda", "inmobiliario", "catastro"],
    "gasto sanitario": ["gasto sanitario", "presupuesto sanitario", "salud"],
    "hospitales": ["hospital", "centro sanitario", "centro de salud"],
    "abandono escolar": ["abandono escolar", "abandono educativo", "fracaso escolar"],
    "fracaso educativo": ["fracaso escolar", "abandono", "rendimiento"],
    "población envejecida": ["envejecimiento", "mayores", "tercera edad"],
    "personas mayores": ["mayores", "tercera edad", "ancianos"],
    "transporte público": ["transporte público", "transporte urbano", "autobús"],
    "movilidad urbana": ["movilidad", "transporte urbano", "tráfico"],
    "calidad del aire": ["calidad del aire", "contaminación", "emisiones"],
    "contaminación atmosférica": ["contaminación", "calidad del aire", "emisiones"],
}


# ============================================
# FUNCIONES DE EVALUACIÓN
# ============================================

def check_api_health() -> bool:
    """Verifica que la API esté disponible."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def search_basic(query: str, top_k: int = 10) -> tuple:
    """Búsqueda básica sin normalización conceptual."""
    payload = {
        "query": query,
        "top_k": top_k,
        "conceptual_normalization": False,
    }

    start = time.perf_counter()
    response = requests.post(f"{API_URL}/search", json=payload, timeout=30)
    elapsed = time.perf_counter() - start

    if response.status_code == 200:
        data = response.json()
        return data.get("results", []), elapsed
    return [], elapsed


def search_conceptual_annotated(query: str, top_k: int = 10) -> tuple:
    """Búsqueda con anotación conceptual (sin ajustar ranking)."""
    payload = {
        "query": query,
        "top_k": top_k,
        "conceptual_normalization": True,
        "conceptual_adjust_scores": False,
    }

    start = time.perf_counter()
    response = requests.post(f"{API_URL}/search", json=payload, timeout=30)
    elapsed = time.perf_counter() - start

    if response.status_code == 200:
        data = response.json()
        return data.get("results", []), elapsed, data.get("detected_concept")
    return [], elapsed, None


def search_conceptual_adjusted(query: str, top_k: int = 10) -> tuple:
    """Búsqueda con ranking ajustado conceptualmente."""
    payload = {
        "query": query,
        "top_k": top_k,
        "conceptual_normalization": True,
        "conceptual_adjust_scores": True,
    }

    start = time.perf_counter()
    response = requests.post(f"{API_URL}/search", json=payload, timeout=30)
    elapsed = time.perf_counter() - start

    if response.status_code == 200:
        data = response.json()
        return data.get("results", []), elapsed, data.get("detected_concept")
    return [], elapsed, None


def calculate_precision_at_k(results: List[Dict], ground_truth_patterns: List[str], k: int) -> float:
    """Calcula Precision@K."""
    if not results:
        return 0.0

    top_k = results[:k]
    relevant = 0

    for result in top_k:
        title = (result.get("title", "") or "").lower()
        # Verificar si el título coincide con algún patrón del ground truth
        for pattern in ground_truth_patterns:
            if pattern.lower() in title:
                relevant += 1
                break

    return relevant / len(top_k) if top_k else 0.0


def calculate_ndcg_at_k(results: List[Dict], ground_truth_patterns: List[str], k: int) -> float:
    """Calcula NDCG@K (simplificado)."""
    if not results:
        return 0.0

    top_k = results[:k]
    dcg = 0.0
    idcg = 0.0

    for i, result in enumerate(top_k):
        title = (result.get("title", "") or "").lower()
        # Relevancia binaria: 1 si coincide, 0 si no
        rel = 0
        for pattern in ground_truth_patterns:
            if pattern.lower() in title:
                rel = 1
                break

        dcg += rel / (i + 2)  # log2(i+2)
        idcg += 1 / (i + 2)

    return dcg / idcg if idcg > 0 else 0.0


def analyze_conceptual_distribution(results: List[Dict]) -> Dict[str, int]:
    """Analiza distribución de clasificaciones conceptuales."""
    distribution = {
        "equivalente": 0,
        "relacionado": 0,
        "complementario": 0,
        "no_equivalente": 0,
        "desconocido": 0,
    }

    for result in results:
        relation = result.get("conceptual_relation", "desconocido")
        if relation in distribution:
            distribution[relation] += 1

    return distribution


# ============================================
# EVALUACIÓN PRINCIPAL
# ============================================

def evaluate_all_queries(limit: Optional[int] = None) -> Dict:
    """
    Evalúa todas las queries en los 3 modos.

    Returns:
        Dict con resultados completos de evaluación
    """
    queries = TEST_QUERIES[:limit] if limit else TEST_QUERIES

    print(f"\n{'='*70}")
    print(f"EVALUACIÓN DE NORMALIZACIÓN CONCEPTUAL")
    print(f"{'='*70}")
    print(f"Queries a evaluar: {len(queries)}")
    print(f"API: {API_URL}")
    print(f"{'='*70}\n")

    # Verificar API
    print("🔌 Verificando API...")
    if not check_api_health():
        print(f"❌ API no disponible en {API_URL}")
        print("   Asegúrate de ejecutar: uvicorn main_v2_final_v07:app --port 8000")
        return {}
    print("   ✅ API disponible\n")

    # Resultados por modo
    resultados = {
        "basico": [],
        "conceptual_annotated": [],
        "conceptual_adjusted": [],
    }

    # Métricas agregadas
    metricas = {
        "basico": {"p5": [], "p10": [], "ndcg10": [], "tiempos": []},
        "conceptual_annotated": {"p5": [], "p10": [], "ndcg10": [], "tiempos": [], "conceptos_detectados": 0},
        "conceptual_adjusted": {"p5": [], "p10": [], "ndcg10": [], "tiempos": [], "conceptos_detectados": 0},
    }

    # Distribución conceptual
    distribucion = {
        "conceptual_annotated": {"equivalente": 0, "relacionado": 0, "complementario": 0, "no_equivalente": 0, "desconocido": 0},
        "conceptual_adjusted": {"equivalente": 0, "relacionado": 0, "complementario": 0, "no_equivalente": 0, "desconocido": 0},
    }

    # Evaluar cada query
    for i, q in enumerate(queries, 1):
        query = q["query"]
        categoria = q.get("categoria", "unknown")

        # Obtener ground truth para esta query
        gt_patterns = []
        for gt_query, patterns in GROUND_TRUTH.items():
            if gt_query in query.lower():
                gt_patterns.extend(patterns)

        if not gt_patterns:
            gt_patterns = [query.split()[0]]  # Fallback: primera palabra

        print(f"[{i}/{len(queries)}] {query} ({categoria})")

        # Modo 1: Básico
        results_basic, time_basic = search_basic(query)
        p5_basic = calculate_precision_at_k(results_basic, gt_patterns, 5)
        p10_basic = calculate_precision_at_k(results_basic, gt_patterns, 10)
        ndcg10_basic = calculate_ndcg_at_k(results_basic, gt_patterns, 10)

        resultados["basico"].append({
            "query": query,
            "categoria": categoria,
            "results": results_basic,
            "p5": p5_basic,
            "p10": p10_basic,
            "ndcg10": ndcg10_basic,
            "tiempo": time_basic,
        })
        metricas["basico"]["p5"].append(p5_basic)
        metricas["basico"]["p10"].append(p10_basic)
        metricas["basico"]["ndcg10"].append(ndcg10_basic)
        metricas["basico"]["tiempos"].append(time_basic)

        print(f"   Básico:    P@5={p5_basic:.3f} P@10={p10_basic:.3f} NDCG@10={ndcg10_basic:.3f} ({time_basic*1000:.0f}ms)")

        # Modo 2: Conceptual anotado
        results_annotated, time_annotated, concept_annotated = search_conceptual_annotated(query)
        p5_annotated = calculate_precision_at_k(results_annotated, gt_patterns, 5)
        p10_annotated = calculate_precision_at_k(results_annotated, gt_patterns, 10)
        ndcg10_annotated = calculate_ndcg_at_k(results_annotated, gt_patterns, 10)

        if concept_annotated:
            metricas["conceptual_annotated"]["conceptos_detectados"] += 1

        # Analizar distribución conceptual
        dist_annotated = analyze_conceptual_distribution(results_annotated)
        for k, v in dist_annotated.items():
            distribucion["conceptual_annotated"][k] += v

        resultados["conceptual_annotated"].append({
            "query": query,
            "categoria": categoria,
            "results": results_annotated,
            "detected_concept": concept_annotated,
            "p5": p5_annotated,
            "p10": p10_annotated,
            "ndcg10": ndcg10_annotated,
            "tiempo": time_annotated,
        })
        metricas["conceptual_annotated"]["p5"].append(p5_annotated)
        metricas["conceptual_annotated"]["p10"].append(p10_annotated)
        metricas["conceptual_annotated"]["ndcg10"].append(ndcg10_annotated)
        metricas["conceptual_annotated"]["tiempos"].append(time_annotated)

        print(f"   Anotado:   P@5={p5_annotated:.3f} P@10={p10_annotated:.3f} NDCG@10={ndcg10_annotated:.3f} ({time_annotated*1000:.0f}ms)")

        # Modo 3: Conceptual ajustado
        results_adjusted, time_adjusted, concept_adjusted = search_conceptual_adjusted(query)
        p5_adjusted = calculate_precision_at_k(results_adjusted, gt_patterns, 5)
        p10_adjusted = calculate_precision_at_k(results_adjusted, gt_patterns, 10)
        ndcg10_adjusted = calculate_ndcg_at_k(results_adjusted, gt_patterns, 10)

        if concept_adjusted:
            metricas["conceptual_adjusted"]["conceptos_detectados"] += 1

        # Analizar distribución conceptual
        dist_adjusted = analyze_conceptual_distribution(results_adjusted)
        for k, v in dist_adjusted.items():
            distribucion["conceptual_adjusted"][k] += v

        resultados["conceptual_adjusted"].append({
            "query": query,
            "categoria": categoria,
            "results": results_adjusted,
            "detected_concept": concept_adjusted,
            "p5": p5_adjusted,
            "p10": p10_adjusted,
            "ndcg10": ndcg10_adjusted,
            "tiempo": time_adjusted,
        })
        metricas["conceptual_adjusted"]["p5"].append(p5_adjusted)
        metricas["conceptual_adjusted"]["p10"].append(p10_adjusted)
        metricas["conceptual_adjusted"]["ndcg10"].append(ndcg10_adjusted)
        metricas["conceptual_adjusted"]["tiempos"].append(time_adjusted)

        print(f"   Ajustado:  P@5={p5_adjusted:.3f} P@10={p10_adjusted:.3f} NDCG@10={ndcg10_adjusted:.3f} ({time_adjusted*1000:.0f}ms)")
        print()

    # Calcular promedios
    def avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    resumen = {
        "basico": {
            "p5": avg(metricas["basico"]["p5"]),
            "p10": avg(metricas["basico"]["p10"]),
            "ndcg10": avg(metricas["basico"]["ndcg10"]),
            "tiempo_medio_ms": avg(metricas["basico"]["tiempos"]) * 1000,
            "n_queries": len(queries),
        },
        "conceptual_annotated": {
            "p5": avg(metricas["conceptual_annotated"]["p5"]),
            "p10": avg(metricas["conceptual_annotated"]["p10"]),
            "ndcg10": avg(metricas["conceptual_annotated"]["ndcg10"]),
            "tiempo_medio_ms": avg(metricas["conceptual_annotated"]["tiempos"]) * 1000,
            "conceptos_detectados": metricas["conceptual_annotated"]["conceptos_detectados"],
            "n_queries": len(queries),
        },
        "conceptual_adjusted": {
            "p5": avg(metricas["conceptual_adjusted"]["p5"]),
            "p10": avg(metricas["conceptual_adjusted"]["p10"]),
            "ndcg10": avg(metricas["conceptual_adjusted"]["ndcg10"]),
            "tiempo_medio_ms": avg(metricas["conceptual_adjusted"]["tiempos"]) * 1000,
            "conceptos_detectados": metricas["conceptual_adjusted"]["conceptos_detectados"],
            "n_queries": len(queries),
        },
    }

    # Calcular mejoras
    resumen["mejora_annotated_vs_basico"] = {
        "p5": resumen["conceptual_annotated"]["p5"] - resumen["basico"]["p5"],
        "p10": resumen["conceptual_annotated"]["p10"] - resumen["basico"]["p10"],
        "ndcg10": resumen["conceptual_annotated"]["ndcg10"] - resumen["basico"]["ndcg10"],
    }

    resumen["mejora_adjusted_vs_basico"] = {
        "p5": resumen["conceptual_adjusted"]["p5"] - resumen["basico"]["p5"],
        "p10": resumen["conceptual_adjusted"]["p10"] - resumen["basico"]["p10"],
        "ndcg10": resumen["conceptual_adjusted"]["ndcg10"] - resumen["basico"]["ndcg10"],
    }

    return {
        "resumen": resumen,
        "distribucion_conceptual": distribucion,
        "resultados_por_query": {
            "basico": resultados["basico"],
            "conceptual_annotated": resultados["conceptual_annotated"],
            "conceptual_adjusted": resultados["conceptual_adjusted"],
        },
        "timestamp": datetime.now().isoformat(),
        "config": {
            "api_url": API_URL,
            "n_queries": len(queries),
        }
    }


def generar_reporte_md(resultados: Dict, output_path: str):
    """Genera reporte Markdown."""
    resumen = resultados.get("resumen", {})
    distribucion = resultados.get("distribucion_conceptual", {})

    md = f"""# 📊 Evaluación de Normalización Conceptual - Experimental

**Fecha**: {resultados.get('timestamp', 'N/A')}
**Queries evaluadas**: {resumen.get('basico', {}).get('n_queries', 0)}
**API**: {resultados.get('config', {}).get('api_url', 'N/A')}

---

## 📈 Resumen Comparativo

### Precision@5

| Modo | P@5 | vs Básico |
|------|-----|-----------|
| **Básico** | {resumen.get('basico', {}).get('p5', 0):.4f} | - |
| **Anotado** | {resumen.get('conceptual_annotated', {}).get('p5', 0):.4f} | {resumen.get('mejora_annotated_vs_basico', {}).get('p5', 0):+.4f} |
| **Ajustado** | {resumen.get('conceptual_adjusted', {}).get('p5', 0):.4f} | {resumen.get('mejora_adjusted_vs_basico', {}).get('p5', 0):+.4f} |

### Precision@10

| Modo | P@10 | vs Básico |
|------|------|-----------|
| **Básico** | {resumen.get('basico', {}).get('p10', 0):.4f} | - |
| **Anotado** | {resumen.get('conceptual_annotated', {}).get('p10', 0):.4f} | {resumen.get('mejora_annotated_vs_basico', {}).get('p10', 0):+.4f} |
| **Ajustado** | {resumen.get('conceptual_adjusted', {}).get('p10', 0):.4f} | {resumen.get('mejora_adjusted_vs_basico', {}).get('p10', 0):+.4f} |

### NDCG@10

| Modo | NDCG@10 | vs Básico |
|------|---------|-----------|
| **Básico** | {resumen.get('basico', {}).get('ndcg10', 0):.4f} | - |
| **Anotado** | {resumen.get('conceptual_annotated', {}).get('ndcg10', 0):.4f} | {resumen.get('mejora_annotated_vs_basico', {}).get('ndcg10', 0):+.4f} |
| **Ajustado** | {resumen.get('conceptual_adjusted', {}).get('ndcg10', 0):.4f} | {resumen.get('mejora_adjusted_vs_basico', {}).get('ndcg10', 0):+.4f} |

### Tiempo Medio por Query

| Modo | Tiempo (ms) | Overhead |
|------|-------------|----------|
| **Básico** | {resumen.get('basico', {}).get('tiempo_medio_ms', 0):.1f}ms | - |
| **Anotado** | {resumen.get('conceptual_annotated', {}).get('tiempo_medio_ms', 0):.1f}ms | +{resumen.get('conceptual_annotated', {}).get('tiempo_medio_ms', 0) - resumen.get('basico', {}).get('tiempo_medio_ms', 0):.1f}ms |
| **Ajustado** | {resumen.get('conceptual_adjusted', {}).get('tiempo_medio_ms', 0):.1f}ms | +{resumen.get('conceptual_adjusted', {}).get('tiempo_medio_ms', 0) - resumen.get('basico', {}).get('tiempo_medio_ms', 0):.1f}ms |

---

## 📊 Distribución de Clasificaciones Conceptuales

### Modo Anotado
| Clasificación | Count |
|---------------|-------|
| Equivalente | {distribucion.get('conceptual_annotated', {}).get('equivalente', 0)} |
| Relacionado | {distribucion.get('conceptual_annotated', {}).get('relacionado', 0)} |
| Complementario | {distribucion.get('conceptual_annotated', {}).get('complementario', 0)} |
| No equivalente | {distribucion.get('conceptual_annotated', {}).get('no_equivalente', 0)} |
| Desconocido | {distribucion.get('conceptual_annotated', {}).get('desconocido', 0)} |

### Modo Ajustado
| Clasificación | Count |
|---------------|-------|
| Equivalente | {distribucion.get('conceptual_adjusted', {}).get('equivalente', 0)} |
| Relacionado | {distribucion.get('conceptual_adjusted', {}).get('relacionado', 0)} |
| Complementario | {distribucion.get('conceptual_adjusted', {}).get('complementario', 0)} |
| No equivalente | {distribucion.get('conceptual_adjusted', {}).get('no_equivalente', 0)} |
| Desconocido | {distribucion.get('conceptual_adjusted', {}).get('desconocido', 0)} |

---

## 🎯 Criterios de Éxito

| Criterio | Target | Resultado | Estado |
|----------|--------|-----------|--------|
| Mejora P@5 | +5-10% | {resumen.get('mejora_adjusted_vs_basico', {}).get('p5', 0)*100:+.1f}% | {'✅' if resumen.get('mejora_adjusted_vs_basico', {}).get('p5', 0) >= 0.05 else '⚠️'} |
| Mejora NDCG@10 | Apreciable | {resumen.get('mejora_adjusted_vs_basico', {}).get('ndcg10', 0)*100:+.1f}% | {'✅' if resumen.get('mejora_adjusted_vs_basico', {}).get('ndcg10', 0) > 0 else '⚠️'} |
| Overhead latencia | <20ms | +{resumen.get('conceptual_adjusted', {}).get('tiempo_medio_ms', 0) - resumen.get('basico', {}).get('tiempo_medio_ms', 0):.1f}ms | {'✅' if (resumen.get('conceptual_adjusted', {}).get('tiempo_medio_ms', 0) - resumen.get('basico', {}).get('tiempo_medio_ms', 0)) < 20 else '⚠️'} |

---

## 📝 Conclusiones

{'✅ La normalización conceptual MEJORA la calidad de búsqueda.' if resumen.get('mejora_adjusted_vs_basico', {}).get('p5', 0) > 0.05 else '⚠️ La normalización conceptual NO muestra mejora significativa.'}

{'✅ El overhead de latencia es aceptable (<20ms).' if (resumen.get('conceptual_adjusted', {}).get('tiempo_medio_ms', 0) - resumen.get('basico', {}).get('tiempo_medio_ms', 0)) < 20 else '⚠️ El overhead de latencia es elevado.'}

### Recomendación

{'**INCORPORAR** la normalización conceptual al flujo principal.' if resumen.get('mejora_adjusted_vs_basico', {}).get('p5', 0) > 0.05 else '**NO INCORPORAR** la normalización conceptual en su estado actual. Se recomienda:'}
{'- Ampliar el diccionario de conceptos' if resumen.get('mejora_adjusted_vs_basico', {}).get('p5', 0) <= 0.05 else ''}
{'- Ajustar los multiplicadores de score' if resumen.get('mejora_adjusted_vs_basico', {}).get('p5', 0) <= 0.05 else ''}
{'- Refinar las reglas de clasificación' if resumen.get('mejora_adjusted_vs_basico', {}).get('p5', 0) <= 0.05 else ''}

---

*Reporte generado automáticamente por `eval_conceptual_normalization.py` - Experimental*
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"📄 Reporte guardado en: {output_path}")


# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description="Evaluación de Normalización Conceptual")
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Límite de queries a evaluar (para testing rápido)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="../entregables/conceptual_normalization_report.json",
        help="Archivo de salida con resultados JSON"
    )
    parser.add_argument(
        "--report", "-r",
        type=str,
        default="../entregables/conceptual_normalization_report.md",
        help="Archivo de reporte Markdown"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="URL de la API (default: http://localhost:8000)"
    )

    args = parser.parse_args()

    # Update API URL globally for evaluation
    API_URL = args.api_url

    # Evaluar
    resultados = evaluate_all_queries(limit=args.limit)

    if not resultados:
        print("\n❌ Evaluación fallida - API no disponible")
        return 1

    # Guardar resultados JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Resultados guardados en: {output_path}")

    # Generar reporte Markdown
    generar_reporte_md(resultados, args.report)

    # Imprimir resumen
    resumen = resultados.get("resumen", {})
    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)

    print(f"\n{'Métrica':<15} {'Básico':>10} {'Anotado':>12} {'Ajustado':>12}")
    print("-"*50)
    print(f"{'P@5':<15} {resumen.get('basico', {}).get('p5', 0):>10.4f} {resumen.get('conceptual_annotated', {}).get('p5', 0):>12.4f} {resumen.get('conceptual_adjusted', {}).get('p5', 0):>12.4f}")
    print(f"{'P@10':<15} {resumen.get('basico', {}).get('p10', 0):>10.4f} {resumen.get('conceptual_annotated', {}).get('p10', 0):>12.4f} {resumen.get('conceptual_adjusted', {}).get('p10', 0):>12.4f}")
    print(f"{'NDCG@10':<15} {resumen.get('basico', {}).get('ndcg10', 0):>10.4f} {resumen.get('conceptual_annotated', {}).get('ndcg10', 0):>12.4f} {resumen.get('conceptual_adjusted', {}).get('ndcg10', 0):>12.4f}")
    print(f"{'Tiempo (ms)':<15} {resumen.get('basico', {}).get('tiempo_medio_ms', 0):>10.1f} {resumen.get('conceptual_annotated', {}).get('tiempo_medio_ms', 0):>12.1f} {resumen.get('conceptual_adjusted', {}).get('tiempo_medio_ms', 0):>12.1f}")

    print("\n" + "="*70)
    print("✅ Evaluación completada")
    print("="*70)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
