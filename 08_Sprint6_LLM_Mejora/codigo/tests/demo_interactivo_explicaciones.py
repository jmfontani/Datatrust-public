#!/usr/bin/env python3
"""
Demo Interactivo - Evaluación de Explicaciones LLM
==================================================

Script interactivo para evaluar las explicaciones del LLM en tiempo real.

Uso:
    # 1. Activar entorno virtual (OBLIGATORIO)
    source ~/datos/PFM/Datatrust/venv/bin/activate

    # 2. Ejecutar
    python3 demo_interactivo_explicaciones.py

Requiere:
    - Entorno virtual activado
    - API corriendo en localhost:8000
    - Ollama disponible

Funciona en terminal interactiva (no en modo script).
"""

import os
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings()

API_URL = "http://localhost:8000"


def main():
    print("\n" + "="*80)
    print("🎮 DEMO INTERACTIVO - EVALUACIÓN DE EXPLICACIONES LLM")
    print("="*80)

    # Queries de ejemplo
    queries = [
        ("paro juvenil desempleo jóvenes", "sinonimia"),
        ("sostenibilidad urbana", "conceptual"),
        ("renta ingresos salarios", "sinonimia"),
        ("contaminación calidad aire", "sinonimia"),
        ("turismo Canarias 2023", "territorial"),
        ("emisiones CO2", "conceptual"),
    ]

    evaluaciones = []

    while True:
        print("\n📋 Queries disponibles:")
        for i, (q, cat) in enumerate(queries, 1):
            print(f"  {i}. [{cat}] {q}")
        print("  q. Salir")

        sel = input("\n🔢 Selecciona query (1-6) o 'q': ").strip().lower()

        if sel == 'q':
            break

        try:
            idx = int(sel) - 1
            if not (0 <= idx < len(queries)):
                print("❌ Número inválido")
                continue
            query, categoria = queries[idx]
        except ValueError:
            print("❌ Introduce un número válido")
            continue

        print(f"\n🔍 Query: \"{query}\"")
        print("⏳ Consultando API (puede tardar 60-90s)...")
        print("-"*80)

        try:
            resp = requests.post(
                f"{API_URL}/llm/search/rerank",
                json={
                    'query': query,
                    'limit': 3,
                    'rerank_top_n': 10,
                    'use_llm': True
                },
                timeout=120,
                verify=False
            )
            resp.raise_for_status()
            data = resp.json()

            print(f"✅ Resultados obtenidos en {data['metadata'].get('total_time_ms', 0)/1000:.1f}s")
            print(f"   Modelo: {data['metadata']['model']}")
            print("\n" + "="*80)

            for i, r in enumerate(data['results'], 1):
                print(f"\n📊 RESULTADO #{i}")
                print("-"*80)
                print(f"📄 Título: {r['title'][:70]}")
                print(f"🏛️  Publisher: {r.get('publisher', 'N/A')[:50]}")
                print(f"📈 Score LLM: {r['llm_relevance_score']}/10")

                delta = r['original_rank'] - r['new_rank']
                if delta > 0:
                    change = f"🟢 Subió {delta} posiciones"
                elif delta < 0:
                    change = f"🔴 Bajó {abs(delta)} posiciones"
                else:
                    change = "⚪ Sin cambio"
                print(f"🔄 Rank: #{r['original_rank']} → #{r['new_rank']} ({change})")

                print(f"\n💬 EXPLICACIÓN DEL LLM:")
                print(f'   \"{r["explanation"]}\"')

                # Evaluación
                print("\n📝 EVALÚA ESTA EXPLICACIÓN:")
                print("   [1] Muy mala - Irrelevante o incorrecta")
                print("   [2] Mala - Poco relevante")
                print("   [3] Aceptable - Genérica pero correcta")
                print("   [4] Buena - Específica y útil")
                print("   [5] Excelente - Muy específica y valiosa")

                ev = input("\n   Tu puntuación (1-5, Enter=saltar): ").strip()

                if ev in ['1', '2', '3', '4', '5']:
                    evaluaciones.append({
                        'timestamp': datetime.now().isoformat(),
                        'query': query,
                        'categoria': categoria,
                        'dataset': r['title'][:60],
                        'explicacion': r['explanation'],
                        'puntuacion': int(ev)
                    })
                    print(f"   ✅ Guardado: {ev}/5")

                cont = input("   Continuar con siguiente resultado? (s/n): ").strip().lower()
                if cont == 'n':
                    break

            print("\n" + "="*80)

        except Exception as e:
            print(f"\n❌ Error: {e}")
            continue

    # Resumen
    if evaluaciones:
        print("\n" + "="*80)
        print("📊 RESUMEN DE TUS EVALUACIONES")
        print("="*80)

        scores = [e['puntuacion'] for e in evaluaciones]
        media = sum(scores) / len(scores)

        print(f"\nTotal evaluaciones: {len(evaluaciones)}")
        print(f"Score medio: {media:.2f}/5.0")

        print("\nPuntuaciones:")
        for e in evaluaciones:
            print(f"  {e['puntuacion']}/5 - \"{e['explicacion'][:50]}...\"")

        # Guardar
        guardar = input("\n💾 Guardar evaluaciones? (s/n): ").strip().lower()
        if guardar == 's':
            import json
            from pathlib import Path

            fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo = Path(__file__).parent / f"resultados/mi_evaluacion_{fecha}.json"

            with open(archivo, 'w', encoding='utf-8') as f:
                json.dump(evaluaciones, f, indent=2, ensure_ascii=False)

            print(f"✅ Guardado en: {archivo}")

    print("\n👋 Demo terminado. ¡Gracias!")
    print("="*80)


if __name__ == "__main__":
    main()
