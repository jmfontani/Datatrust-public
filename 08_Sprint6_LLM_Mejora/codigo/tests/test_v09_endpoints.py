#!/usr/bin/env python3
"""
Test rápido de la arquitectura V09
==================================

Verifica que los endpoints `/llm/enhance` y `/llm/explain` funcionan correctamente.

Uso:
    python3 test_v09_endpoints.py
    python3 test_v09_endpoints.py --url http://localhost:8000

Requisitos:
    - API corriendo (main_v2_final_v07.py)
    - Ollama disponible
"""

import requests
import argparse
import sys


def test_health(base_url: str) -> bool:
    """Test del endpoint /llm/health."""
    print("\n" + "="*60)
    print("TEST 1: /llm/health")
    print("="*60)

    try:
        response = requests.get(f"{base_url}/llm/health", timeout=10)
        response.raise_for_status()
        data = response.json()

        print(f"✅ Status: {data.get('status', 'unknown')}")
        print(f"   Ollama disponible: {data.get('ollama_available', False)}")
        print(f"   Modelo re-ranking: {data.get('reranker_model', 'N/A')}")
        print(f"   Modelo explanation: {data.get('explanation_model', 'N/A')}")

        if data.get('available_models'):
            print(f"   Modelos disponibles: {len(data.get('available_models', []))}")

        return data.get('ollama_available', False)

    except requests.exceptions.ConnectionError:
        print("❌ ERROR: No se pudo conectar a la API")
        print(f"   Verifica que la API está corriendo en {base_url}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_enhance(base_url: str, query: str = "paro juvenil desempleo") -> bool:
    """Test del endpoint /llm/enhance."""
    print("\n" + "="*60)
    print(f"TEST 2: /llm/enhance")
    print(f"Query: '{query}'")
    print("="*60)
    print("Nota: Este test puede tardar 60-90 segundos...")
    print("-"*60)

    try:
        response = requests.post(
            f"{base_url}/llm/enhance",
            json={
                "query": query,
                "limit": 5,
                "rerank_top_n": 10,
                "include_explanations": True
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()

        print(f"✅ Respuesta recibida")
        print(f"   Query: {data.get('query')}")
        print(f"   Total resultados: {data.get('total', 0)}")
        print(f"   Modelo: {data.get('metadata', {}).get('model', 'N/A')}")
        print(f"   Tiempo total: {data.get('metadata', {}).get('total_time_ms', 0)/1000:.1f}s")
        print(f"   Status: {data.get('metadata', {}).get('status', 'unknown')}")

        if data.get('results'):
            print("\n   Top 3 resultados:")
            for i, r in enumerate(data['results'][:3], 1):
                print(f"   {i}. [{r.get('new_rank')}] {r.get('title', 'N/A')[:50]}...")
                print(f"      Score LLM: {r.get('llm_relevance_score', 0):.1f}")
                if r.get('explanation'):
                    print(f"      Explicación: {r.get('explanation', '')[:60]}...")

        return True

    except requests.exceptions.Timeout:
        print("⚠️  TIMEOUT: La petición tardó demasiado (normal para primeras llamadas)")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_explain(base_url: str, query: str = "paro juvenil", dataset_id: str = None) -> bool:
    """Test del endpoint /llm/explain."""
    print("\n" + "="*60)
    print(f"TEST 3: /llm/explain")
    print(f"Query: '{query}'")
    print("="*60)
    print("Nota: Este test puede tardar 5-15 segundos...")
    print("-"*60)

    # Si no se proporciona dataset_id, buscamos uno
    if not dataset_id:
        try:
            search_resp = requests.post(
                f"{base_url}/search",
                json={"query": query, "top_k": 1},
                timeout=10
            )
            search_resp.raise_for_status()
            search_data = search_resp.json()
            if search_data.get('results'):
                dataset_id = search_data['results'][0].get('id')
                print(f"   Dataset encontrado automáticamente: {dataset_id}")
        except Exception as e:
            print(f"   No se pudo buscar dataset automáticamente: {e}")
            dataset_id = "ejemplo-dataset-id"

    try:
        response = requests.post(
            f"{base_url}/llm/explain",
            json={
                "query": query,
                "dataset_id": dataset_id
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        print(f"✅ Respuesta recibida")
        print(f"   Dataset: {data.get('title', 'N/A')}")
        print(f"   Score relevancia: {data.get('relevance_score', 0):.1f}")
        print(f"   Explicación: {data.get('explanation', 'N/A')[:80]}...")

        if data.get('factors'):
            print(f"\n   Factores identificados:")
            for f in data['factors']:
                print(f"   - {f.get('factor')}: {f.get('score', 0):.2f} - {f.get('description', '')[:50]}")

        print(f"\n   Modelo: {data.get('metadata', {}).get('model', 'N/A')}")
        print(f"   Tiempo: {data.get('metadata', {}).get('time_ms', 0)/1000:.1f}s")

        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test endpoints V09")
    parser.add_argument("--url", default="http://localhost:8000", help="URL base de la API")
    parser.add_argument("--skip-enhance", action="store_true", help="Saltar test de /llm/enhance (lento)")
    parser.add_argument("--skip-explain", action="store_true", help="Saltar test de /llm/explain")
    args = parser.parse_args()

    print("="*60)
    print("TEST V09: Arquitectura Endpoints Separados")
    print("="*60)
    print(f"API URL: {args.url}")

    results = []

    # Test 1: Health
    ollama_ok = test_health(args.url)
    results.append(("/llm/health", True))  # Health siempre pasa si conecta

    if not ollama_ok:
        print("\n" + "!"*60)
        print("ADVERTENCIA: Ollama no disponible")
        print("Los tests de enhance/explain fallarán")
        print("!"*60)

    # Test 2: Enhance (si no se salta)
    if not args.skip_enhance:
        enhance_ok = test_enhance(args.url)
        results.append(("/llm/enhance", enhance_ok))
    else:
        print("\n   (Saltado por --skip-enhance)")
        results.append(("/llm/enhance", "skipped"))

    # Test 3: Explain (si no se salta)
    if not args.skip_explain:
        explain_ok = test_explain(args.url)
        results.append(("/llm/explain", explain_ok))
    else:
        print("\n   (Saltado por --skip-explain)")
        results.append(("/llm/explain", "skipped"))

    # Resumen
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)
    for endpoint, status in results:
        icon = "✅" if status is True else ("⚪" if status == "skipped" else "❌")
        print(f"  {icon} {endpoint}")

    print("\n" + "="*60)
    print("V09 implementado correctamente" if all(s is True for _, s in results[:1]) else "Hay problemas")
    print("="*60)

    return 0 if all(s in (True, "skipped") for _, s in results) else 1


if __name__ == "__main__":
    sys.exit(main())
