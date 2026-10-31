#!/usr/bin/env python3
"""
Tests del motor de búsqueda híbrida.

Uso:
  python test_search.py
"""
import json
import sys
import time
from pathlib import Path

# Añadir motor al path
sys.path.insert(0, str(Path(__file__).parent.parent / "motor"))

from search_engine import HybridSearchEngine


def test_basic_search():
    """Test básico de búsqueda."""
    print("=" * 80)
    print("TEST 1: Búsqueda básica")
    print("=" * 80)
    
    engine = HybridSearchEngine()
    result = engine.search("educación", top_k=5)
    
    assert result["returned_results"] > 0, "No hay resultados"
    assert all("score" in r for r in result["results"]), "Falta score"
    assert all("title" in r for r in result["results"]), "Falta título"
    
    print(f"✅ Búsqueda básica OK ({result['returned_results']} resultados)")
    return True


def test_semantic_only():
    """Test búsqueda semántica pura."""
    print("\n" + "=" * 80)
    print("TEST 2: Búsqueda semántica pura")
    print("=" * 80)
    
    engine = HybridSearchEngine()
    result = engine.search(
        "datos sobre estudiantes universitarios",
        semantic_weight=1.0,
        lexical_weight=0.0,
        top_k=5,
    )
    
    assert result["returned_results"] > 0
    print(f"✅ Semántica pura OK ({result['returned_results']} resultados)")
    return True


def test_lexical_only():
    """Test búsqueda léxica pura."""
    print("\n" + "=" * 80)
    print("TEST 3: Búsqueda léxica pura")
    print("=" * 80)
    
    engine = HybridSearchEngine()
    result = engine.search(
        "población Madrid",
        semantic_weight=0.0,
        lexical_weight=1.0,
        top_k=5,
    )
    
    assert result["returned_results"] > 0
    print(f"✅ Léxica pura OK ({result['returned_results']} resultados)")
    return True


def test_facet_filter():
    """Test filtros facetados."""
    print("\n" + "=" * 80)
    print("TEST 4: Filtros facetados")
    print("=" * 80)
    
    engine = HybridSearchEngine()
    
    # Sin filtro
    result_all = engine.search("tráfico", top_k=20)
    
    # Con filtro
    result_filtered = engine.search(
        "tráfico",
        territorio="Comunidad de Madrid",
        top_k=20,
    )
    
    assert len(result_filtered["results"]) <= len(result_all["results"])
    assert all(
        "Comunidad de Madrid" in r.get("territorio", [])
        for r in result_filtered["results"]
    ), "Filtro territorial no funciona"
    
    print(f"✅ Filtros OK (sin filtro: {len(result_all['results'])}, con filtro: {len(result_filtered['results'])})")
    return True


def test_explanations():
    """Test explicaciones de relevancia."""
    print("\n" + "=" * 80)
    print("TEST 5: Explicaciones de relevancia")
    print("=" * 80)
    
    engine = HybridSearchEngine()
    result = engine.search("educación primaria", top_k=3, explain=True)
    
    assert all("explanation" in r for r in result["results"]), "Faltan explicaciones"
    print("✅ Explicaciones OK")
    for r in result["results"][:3]:
        print(f"   {r['title']}: {r['explanation']}")
    return True


def test_performance():
    """Test rendimiento."""
    print("\n" + "=" * 80)
    print("TEST 6: Rendimiento")
    print("=" * 80)
    
    engine = HybridSearchEngine()
    
    queries = [
        "educación",
        "tráfico Madrid",
        "población",
        "presupuestos",
        "energía solar",
    ]
    
    times = []
    for q in queries:
        start = time.perf_counter()
        engine.search(q, top_k=10)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        print(f"   '{q}': {elapsed:.1f}ms")
    
    avg_time = sum(times) / len(times)
    print(f"\n   Tiempo medio: {avg_time:.1f}ms")
    assert avg_time < 5000, f"Demasiado lento: {avg_time:.1f}ms"
    print("✅ Rendimiento OK")
    return True


def run_all_tests():
    """Ejecuta todos los tests."""
    tests = [
        test_basic_search,
        test_semantic_only,
        test_lexical_only,
        test_facet_filter,
        test_explanations,
        test_performance,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ FAIL: {test.__name__}: {e}")
    
    print("\n" + "=" * 80)
    print(f"RESULTADOS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
