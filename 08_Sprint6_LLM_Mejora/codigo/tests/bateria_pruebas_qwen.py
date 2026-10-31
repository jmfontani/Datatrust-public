#!/usr/bin/env python3
"""
Batería de Pruebas - Evaluación con Modelo Qwen2.5:7b (LOCAL)
===============================================================

Versión de la batería que usa el modelo qwen2.5:7b en lugar de deepseek-v4.1-flash.
Este modelo corre en local y permite comparar resultados.

Uso:
    source ~/datos/PFM/Datatrust/venv/bin/activate
    python3 bateria_pruebas_qwen.py

Salida:
    - resultados/bateria_qwen_YYYY-MM-DD_HHMMSS_para_evaluar.csv

Comparar con:
    - bateria_mini_2026-05-31_205027_para_evaluar.csv (deepseek-v4.1-flash)
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

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "http://localhost:8000"
RESULTS_DIR = Path(__file__).parent / "resultados"

# Forzar uso de modelo qwen2.5:7b
os.environ["LLM_RERANKER_MODEL"] = "qwen2.5:7b"

from llm_reranker import LLMReranker

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


def buscar_con_qwen(query: str, limit: int = 3) -> dict:
    """Ejecuta búsqueda con LLM usando modelo qwen2.5:7b."""
    try:
        resp = requests.post(
            f"{API_URL}/llm/search/rerank",
            json={
                "query": query,
                "limit": limit,
                "rerank_top_n": 10,
                "use_llm": True
            },
            timeout=180,  # Más timeout para modelo local
            verify=False
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"   ❌ Error en búsqueda: {e}")
        return None


def main():
    print("=" * 80)
    print("🔬 BATERÍA CON QWEN2.5:7B (LOCAL)")
    print("=" * 80)
    print("\nModelo: qwen2.5:7b (ejecutándose en local)")
    print("Comparación: vs deepseek-v4.1-flash:cloud (cloud)")
    print("=" * 80)

    resultados = []
    timestamp = datetime.now()

    for caso in CASOS_PRUEBA:
        print(f"\n🔍 Caso {caso['id']}: {caso['query']}")
        print(f"   Categoría: {caso['categoria']}")
        print("   ⏳ Consultando API con qwen2.5:7b...")

        try:
            inicio = time.time()
            data = buscar_con_qwen(caso['query'])
            tiempo = time.time() - inicio

            if not data:
                print("   ⚠️  Sin resultados")
                continue

            print(f"   ✅ {len(data['results'])} resultados en {tiempo:.1f}s")
            print(f"   Modelo usado: {data.get('metadata', {}).get('model', 'desconocido')}")

            for i, r in enumerate(data['results'], 1):
                resultado = {
                    "caso_id": caso['id'],
                    "categoria": caso['categoria'],
                    "query": caso['query'],
                    "posicion": i,
                    "dataset_titulo": r['title'],
                    "dataset_publisher": r.get('publisher', 'N/A'),
                    "score_llm": r.get('llm_relevance_score', 0),
                    "explicacion": r.get('explanation', 'No disponible'),
                    "tiempo": round(tiempo, 1),
                    "modelo": data.get('metadata', {}).get('model', 'unknown')
                }
                resultados.append(resultado)
        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Guardar CSV
    fecha = timestamp.strftime("%Y-%m-%d_%H%M%S")
    csv_file = RESULTS_DIR / f"bateria_qwen_{fecha}_para_evaluar.csv"

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

    print("\n" + "=" * 80)
    print("✅ Batería completada!")
    print("=" * 80)
    print("\n📋 PARA COMPARAR:")
    print("1. Abre el CSV generado")
    print("2. Compara con: bateria_mini_2026-05-31_205027_para_evaluar.csv (deepseek)")
    print("3. Evalúa diferencias en calidad de explicaciones y calibración de scores")


if __name__ == "__main__":
    main()
