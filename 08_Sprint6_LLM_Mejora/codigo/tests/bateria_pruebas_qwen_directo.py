#!/usr/bin/env python3
"""
Batería de Pruebas - Evaluación con Modelo Qwen2.5:7b (LOCAL) - VERSIÓN DIRECTA
================================================================================

Esta versión usa el LLMReranker directamente en lugar de llamar a la API HTTP.
Esto permite probar el modelo qwen2.5:7b sin necesidad de reiniciar la API.

Uso:
    source ~/datos/PFM/Datatrust/venv/bin/activate
    python3 bateria_pruebas_qwen_directo.py

Salida:
    - resultados/bateria_qwen_directo_YYYY-MM-DD_HHMMSS_para_evaluar.csv
"""

import json
import csv
import sys
import os
from datetime import datetime
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "motor"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "07_Sprint5_Integracion" / "codigo" / "motor"))

# Importar reranker qwen
from llm_reranker_qwen import LLMReranker, SearchResult

RESULTS_DIR = Path(__file__).parent / "resultados"

# Casos de prueba
CASOS_PRUEBA = [
    {
        "id": "S1",
        "categoria": "sinonimia",
        "query": "paro juvenil desempleo jóvenes",
        "descripcion": "Query con sinónimos (paro/desempleo, juvenil/jóvenes)"
    },
    {
        "id": "C1",
        "categoria": "conceptual",
        "query": "vulnerabilidad económica juventud",
        "descripcion": "Concepto abstracto que requiere interpretación"
    },
    {
        "id": "T1",
        "categoria": "territorial",
        "query": "turismo Canarias 2023",
        "descripcion": "Query con ubicación y temporalidad"
    }
]


def crear_resultados_mock(query: str, limit: int = 3) -> list:
    """Crea resultados mock simulando el motor híbrido."""

    resultados_mock = {
        "paro juvenil desempleo jóvenes": [
            SearchResult(
                dataset_id="l01080193-ld-aj-16",
                title="Población parada (EPA) según sexo, grupo quinquenal de edad y nivel de formación",
                description="Población parada según datos de la Encuesta de Población Activa (EPA), desagregada por sexo, grupos de edad quinquenales y nivel de formación.",
                publisher="Ayuntamiento de Barcelona",
                theme="Empleo",
                territory="Barcelona",
                format="CSV",
                score_semantic=0.92,
                score_lexical=0.88,
                score_final=0.90
            ),
            SearchResult(
                dataset_id="l01080193-ld-aj-15",
                title="Población parada (EPA) según sexo, grupo quinquenal de edad y nacionalidad",
                description="Población parada según la EPA desagregada por sexo, grupos de edad y nacionalidad.",
                publisher="Ayuntamiento de Barcelona",
                theme="Empleo",
                territory="Barcelona",
                format="CSV",
                score_semantic=0.85,
                score_lexical=0.90,
                score_final=0.87
            ),
            SearchResult(
                dataset_id="l01080193-ld-aj-14",
                title="Población parada (EPA) según sexo, grupo quinquenal de edad y duración del paro",
                description="Población parada según duración del desempleo, desagregada por sexo y edad.",
                publisher="Ayuntamiento de Barcelona",
                theme="Empleo",
                territory="Barcelona",
                format="CSV",
                score_semantic=0.80,
                score_lexical=0.85,
                score_final=0.82
            )
        ],
        "vulnerabilidad económica juventud": [
            SearchResult(
                dataset_id="eus-0024",
                title="Tasas de riesgo de pobreza o exclusión social (AROPE) por grupos de edad",
                description="Indicador AROPE (At Risk of Poverty or Social Exclusion) que mide el riesgo de pobreza y exclusión social por grupos de edad.",
                publisher="Eustat",
                theme="Economía",
                territory="País Vasco",
                format="JSON",
                score_semantic=0.88,
                score_lexical=0.82,
                score_final=0.85
            ),
            SearchResult(
                dataset_id="eus-0025",
                title="Población en riesgo de pobreza según comunidad autónoma",
                description="Porcentaje de población que vive con ingresos por debajo del umbral de pobreza relativa.",
                publisher="Eustat",
                theme="Economía",
                territory="España",
                format="CSV",
                score_semantic=0.82,
                score_lexical=0.78,
                score_final=0.80
            ),
            SearchResult(
                dataset_id="eus-0026",
                title="Indicadores de calidad de vida - Desigualdad económica",
                description="Indicadores sobre brechas económicas y desigualdad de ingresos en la población.",
                publisher="Eustat",
                theme="Economía",
                territory="País Vasco",
                format="JSON",
                score_semantic=0.75,
                score_lexical=0.72,
                score_final=0.73
            )
        ],
        "turismo Canarias 2023": [
            SearchResult(
                dataset_id="can-0015",
                title="Movimientos turísticos en Canarias - Estadística de flujos turísticos 2023",
                description="Estadísticas de llegadas y pernoctaciones de turistas en las Islas Canarias durante el año 2023.",
                publisher="ISTAC",
                theme="Turismo",
                territory="Canarias",
                format="CSV",
                score_semantic=0.95,
                score_lexical=0.92,
                score_final=0.93
            ),
            SearchResult(
                dataset_id="can-0016",
                title="Establecimientos y plazas turísticas en Canarias",
                description="Número de establecimientos turísticos y plazas disponibles por isla en Canarias.",
                publisher="ISTAC",
                theme="Turismo",
                territory="Canarias",
                format="CSV",
                score_semantic=0.88,
                score_lexical=0.85,
                score_final=0.86
            ),
            SearchResult(
                dataset_id="can-0017",
                title="Gasto turístico en Canarias - Encuesta de gasto turístico",
                description="Datos sobre gasto medio diario y total de los turistas que visitan Canarias.",
                publisher="ISTAC",
                theme="Turismo",
                territory="Canarias",
                format="JSON",
                score_semantic=0.82,
                score_lexical=0.88,
                score_final=0.85
            )
        ]
    }

    return resultados_mock.get(query, [])[:limit]


def main():
    print("=" * 80)
    print("🔬 BATERÍA CON QWEN2.5:7B (LOCAL) - VERSIÓN DIRECTA")
    print("=" * 80)
    print("\nModelo: qwen2.5:7b (ejecutándose en local)")
    print("Método: LLMReranker directo (sin API HTTP)")
    print("Timeout: 300 segundos (5 minutos)")
    print("=" * 80)

    # Inicializar reranker con qwen
    print("\n🔄 Inicializando LLMReranker con modelo qwen2.5:7b...")
    reranker = LLMReranker(verbose=True)
    print(f"✅ Modelo configurado: {reranker.llm.model}")
    print(f"✅ Timeout: {reranker.llm.timeout}s")

    resultados = []
    timestamp = datetime.now()

    for caso in CASOS_PRUEBA:
        print(f"\n{'='*80}")
        print(f"🔍 Caso {caso['id']}: {caso['query']}")
        print(f"   Categoría: {caso['categoria']}")
        print("   ⏳ Procesando con qwen2.5:7b (puede tardar varios minutos)...")

        try:
            # Obtener resultados mock
            mock_results = crear_resultados_mock(caso['query'])

            if not mock_results:
                print(f"   ⚠️  No hay resultados mock para este query")
                continue

            # Ejecutar re-ranking
            inicio = time.time()
            reranked_results, metadata = reranker.rerank(
                query=caso['query'],
                results=mock_results,
                top_n=3
            )
            tiempo = time.time() - inicio

            print(f"   ✅ {len(reranked_results)} resultados re-rankeados en {tiempo:.1f}s")
            print(f"   Modelo usado: {metadata.get('model', 'desconocido')}")

            for i, r in enumerate(reranked_results, 1):
                resultado = {
                    "caso_id": caso['id'],
                    "categoria": caso['categoria'],
                    "query": caso['query'],
                    "posicion": i,
                    "dataset_titulo": r.title,
                    "dataset_publisher": r.publisher,
                    "score_llm": r.llm_relevance_score,
                    "explicacion": r.explanation,
                    "tiempo": round(tiempo, 1),
                    "modelo": metadata.get('model', 'unknown')
                }
                resultados.append(resultado)

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

    # Guardar CSV
    RESULTS_DIR.mkdir(exist_ok=True)
    fecha = timestamp.strftime("%Y-%m-%d_%H%M%S")
    csv_file = RESULTS_DIR / f"bateria_qwen_directo_{fecha}_para_evaluar.csv"

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            "id_fila", "caso_id", "categoria", "query", "posicion",
            "dataset_titulo", "dataset_publisher", "score_llm",
            "explicacion", "modelo", "tiempo",
            "puntuacion_1_5", "comentario"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, r in enumerate(resultados, 1):
            writer.writerow({
                "id_fila": i,
                "caso_id": r['caso_id'],
                "categoria": r['categoria'],
                "query": r['query'],
                "posicion": r['posicion'],
                "dataset_titulo": r['dataset_titulo'][:80],
                "dataset_publisher": r['dataset_publisher'][:50],
                "score_llm": r['score_llm'],
                "explicacion": r['explicacion'],
                "modelo": r['modelo'],
                "tiempo": r['tiempo'],
                "puntuacion_1_5": "",
                "comentario": ""
            })

    # Mostrar resumen
    print("\n" + "=" * 80)
    print("📊 RESULTADOS CON QWEN2.5:7B")
    print("=" * 80)
    print(f"\nTotal: {len(resultados)} explicaciones generadas")
    print(f"Archivo: {csv_file}")

    print("\n📝 MUESTRAS:")
    print("-" * 80)
    for r in resultados[:3]:
        print(f"\n[{r['caso_id']}] {r['query']}")
        print(f"   Dataset: {r['dataset_titulo'][:60]}...")
        print(f"   Score: {r['score_llm']}/10")
        print(f"   Explicación: \"{r['explicacion'][:100]}...\"")
        print(f"   Modelo: {r['modelo']}")
        print(f"   Tiempo: {r['tiempo']}s")

    print("\n" + "=" * 80)
    print("✅ Batería completada!")
    print("=" * 80)


if __name__ == "__main__":
    main()
