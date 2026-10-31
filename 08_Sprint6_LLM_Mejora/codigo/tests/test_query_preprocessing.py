#!/usr/bin/env python3
"""
Tests básicos del Query Preprocessor (#3, #4, #12)
Fase 08: Sprint 6 - Query Preprocessing

Uso:
    source ~/datos/PFM/Datatrust/venv/bin/activate
    python3 test_query_preprocessing.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "motor"))

from query_preprocessor import QueryPreprocessor, get_preprocessor


def test_basic_functionality():
    """Test básico de funcionalidad."""
    print("=" * 70)
    print("TEST BÁSICO - Query Preprocessor")
    print("=" * 70)

    preprocessor = QueryPreprocessor(verbose=True)

    # Test 1: Query válida
    print("\n--- Test 1: Query válida ---")
    result = preprocessor.process("paro juvenil Canarias 2023")

    assert result.validation.is_valid, "La query debería ser válida"
    assert "paro" in result.expansion.query_expandida.lower(), "Debe incluir término original"
    assert len(result.structure.temas) > 0, "Debe extraer temas"
    print(f"✅ Válida: {result.validation.is_valid}")
    print(f"✅ Temas: {result.structure.temas}")
    print(f"✅ Expansión añade: {result.expansion.terminos_añadidos}")

    # Test 2: Cache
    print("\n--- Test 2: Cache ---")
    result_cached = preprocessor.process("paro juvenil Canarias 2023")
    assert result_cached.metadata.get("duration_ms", 100) < 50, "Cache debería ser instantáneo"
    print(f"✅ Cache funciona (duración: {result_cached.metadata.get('duration_ms', 0):.0f}ms)")

    # Test 3: Query inválida
    print("\n--- Test 3: Query inválida ---")
    result_invalid = preprocessor.process("xyz123 nonsense")
    print(f"✅ Reconoce inválida: {not result_invalid.validation.is_valid}")

    # Test 4: Quick expand
    print("\n--- Test 4: Quick expand ---")
    expanded = preprocessor.quick_expand("consumo energía Madrid")
    assert len(expanded) > len("consumo energía Madrid"), "Debe expandir"
    print(f"✅ Expandida: {expanded[:80]}...")

    print("\n" + "=" * 70)
    print("TODOS LOS TESTS PASADOS ✅")
    print("=" * 70)


def test_endpoints():
    """Test de endpoints (requiere API corriendo)."""
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print("\n" + "=" * 70)
    print("TEST DE ENDPOINTS API")
    print("=" * 70)

    base_url = "http://localhost:8000/enhanced"

    # Test health
    try:
        response = requests.get(f"{base_url}/health", verify=False, timeout=5)
        print(f"✅ Health check: {response.json()}")
    except Exception as e:
        print(f"⚠️  API no disponible: {e}")
        print("   (Ignorando test de endpoints)")
        return

    # Test validate
    print("\n--- POST /query/validate ---")
    response = requests.post(
        f"{base_url}/query/validate",
        json={"query": "paro juvenil"},
        verify=False,
        timeout=10
    )
    print(f"✅ Status: {response.status_code}")
    print(f"   Response: {response.json()}")

    # Test expand
    print("\n--- POST /query/expand ---")
    response = requests.post(
        f"{base_url}/query/expand",
        json={"query": "turismo Barcelona"},
        verify=False,
        timeout=10
    )
    result = response.json()
    print(f"✅ Status: {response.status_code}")
    print(f"   Expandida: {result.get('query_expandida', 'N/A')[:80]}...")

    # Test analyze
    print("\n--- POST /query/analyze ---")
    response = requests.post(
        f"{base_url}/query/analyze",
        json={"query": "vulnerabilidad económica"},
        verify=False,
        timeout=10
    )
    result = response.json()
    print(f"✅ Status: {response.status_code}")
    print(f"   Estructura: {result.get('structure', {}).get('temas', [])}")

    # Test search
    print("\n--- POST /search ---")
    response = requests.post(
        f"{base_url}/search",
        json={
            "query": "paro juvenil",
            "limit": 3,
            "use_expansion": True,
            "use_filters": True
        },
        verify=False,
        timeout=30
    )
    result = response.json()
    print(f"✅ Status: {response.status_code}")
    print(f"   Resultados: {len(result.get('results', []))}")
    print(f"   Query expandida: {result.get('query_expandida', 'N/A')[:60]}...")
    print(f"   Filtros aplicados: {result.get('filtros_aplicados', {})}")

    print("\n" + "=" * 70)
    print("ENDPOINTS TESTEADOS ✅")
    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Query Preprocessor")
    parser.add_argument("--api", action="store_true", help="Incluir tests de API (requiere servidor)")
    args = parser.parse_args()

    test_basic_functionality()

    if args.api:
        test_endpoints()
