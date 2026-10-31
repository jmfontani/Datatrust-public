#!/usr/bin/env python3
"""
Batería Mini - Evaluación de Explicaciones LLM (Versión Rápida)
================================================================

Versión reducida con 3 casos para demostración rápida.
Para batería completa (10 casos), usar: bateria_pruebas_explicaciones.py

Uso:
    source ~/datos/PFM/Datatrust/venv/bin/activate
    python3 bateria_pruebas_mini.py --auto

Salida:
    - resultados/bateria_mini_YYYY-MM-DD_HHMMSS_para_evaluar.csv
"""

import json
import csv
import sys
import os
from datetime import datetime
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "http://localhost:8000"
RESULTS_DIR = Path(__file__).parent / "resultados"

# Solo 3 casos para demo rápida
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


def buscar_con_llm(query: str) -> dict:
    """Ejecuta búsqueda con LLM."""
    resp = requests.post(
        f"{API_URL}/llm/search/rerank",
        json={"query": query, "limit": 3, "rerank_top_n": 10, "use_llm": True},
        timeout=120,
        verify=False
    )
    resp.raise_for_status()
    return resp.json()


def main():
    print("=" * 80)
    print("🔬 BATERÍA MINI (3 casos) - EXPLICACIONES LLM")
    print("=" * 80)
    print("\n⏳ Ejecutando 3 casos de prueba (~3-5 minutos)...\n")

    resultados = []
    timestamp = datetime.now()

    for caso in CASOS_PRUEBA:
        print(f"🔍 Caso {caso['id']}: {caso['query']}")
        print(f"   Categoría: {caso['categoria']}")

        try:
            inicio = time.time()
            data = buscar_con_llm(caso['query'])
            tiempo = time.time() - inicio

            print(f"   ✅ {len(data['results'])} resultados en {tiempo:.1f}s")

            for i, r in enumerate(data['results'], 1):
                resultados.append({
                    "caso_id": caso['id'],
                    "categoria": caso['categoria'],
                    "query": caso['query'],
                    "posicion": i,
                    "dataset_titulo": r['title'],
                    "dataset_publisher": r.get('publisher', 'N/A'),
                    "score_llm": r.get('llm_relevance_score', 0),
                    "explicacion": r.get('explanation', 'No disponible'),
                    "tiempo": round(tiempo, 1)
                })
        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Guardar CSV para evaluación
    fecha = timestamp.strftime("%Y-%m-%d_%H%M%S")
    csv_file = RESULTS_DIR / f"bateria_mini_{fecha}_para_evaluar.csv"

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            "id_fila", "caso_id", "categoria", "query", "posicion",
            "dataset_titulo", "dataset_publisher", "score_llm",
            "explicacion", "puntuacion_1_5", "comentario"
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
                "puntuacion_1_5": "",
                "comentario": ""
            })

    # Mostrar resumen
    print("\n" + "=" * 80)
    print("📊 RESULTADOS")
    print("=" * 80)
    print(f"\nTotal: {len(resultados)} explicaciones generadas")
    print("\nArchivo generado:")
    print(f"   {csv_file}")

    print("\n" + "=" * 80)
    print("📋 PARA EVALUAR:")
    print("=" * 80)
    print("""
1. Abre el archivo CSV con Excel/LibreOffice/VSCode
2. Completa las columnas:
   - puntuacion_1_5: Tu puntuación (1=muy mala, 5=excelente)
   - comentario: Tu feedback opcional

3. Guarda como: bateria_mini_EVALUADO.csv
4. Envíame el archivo para generar el informe

💡 Criterios:
   1 = Incorrecta o irrelevante
   2 = Poco relevante/genérica
   3 = Aceptable, correcta
   4 = Buena, específica
   5 = Excelente, muy valiosa
    """)
    print("=" * 80)

    # Mostrar muestras
    print("\n📝 MUESTRAS DE EXPLICACIONES:")
    print("-" * 80)
    for r in resultados[:3]:
        print(f"\n[{r['caso_id']}] {r['query']}")
        print(f"   Dataset: {r['dataset_titulo'][:60]}...")
        print(f"   Explicación: \"{r['explicacion'][:120]}...\"")
        print(f"   Score LLM: {r['score_llm']}/10")

    print("\n" + "=" * 80)
    print("✅ Batería completada!")
    print("=" * 80)


if __name__ == "__main__":
    main()
