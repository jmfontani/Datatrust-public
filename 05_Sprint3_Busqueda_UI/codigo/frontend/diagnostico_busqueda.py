#!/usr/bin/env python3
"""
Diagnóstico de búsqueda para entender por qué no encuentra resultados.
Ejecutar: python3 diagnostico_busqueda.py
"""
import sys
import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "http://localhost:8000"

def test_search(query, **kwargs):
    """Prueba una búsqueda y muestra resultados detallados."""
    print(f"\n{'='*80}")
    print(f"🔍 Buscando: '{query}'")
    if kwargs:
        print(f"   Filtros: {kwargs}")
    print(f"{'='*80}")
    
    try:
        response = requests.post(
            f"{API_URL}/search",
            json={"query": query, "top_k": 10, **kwargs},
            timeout=30,
            verify=False
        )
        
        if response.status_code != 200:
            print(f"❌ Error HTTP {response.status_code}")
            print(f"Respuesta: {response.text[:500]}")
            return
        
        data = response.json()
        
        print(f"\n📊 ESTADÍSTICAS:")
        print(f"   Query: {data['query']}")
        print(f"   Total resultados: {data['total_results']}")
        print(f"   Resultados devueltos: {data['returned_results']}")
        print(f"   Tiempo: {data['search_time_ms']}ms")
        print(f"   Pesos: Semántico={data['semantic_weight']:.0%}, Léxico={data['lexical_weight']:.0%}")
        
        results = data.get("results", [])
        if not results:
            print(f"\n⚠️  SIN RESULTADOS")
            print(f"\n💡 POSIBLES CAUSAS:")
            print(f"   1. La palabra no existe en los datasets")
            print(f"   2. Los embeddings no capturan el concepto")
            print(f"   3. El umbral de score es muy alto")
            print(f"   4. No hay coincidencias léxicas (BM25)")
            return
        
        print(f"\n📋 RESULTADOS (top {len(results)}):")
        for i, r in enumerate(results, 1):
            print(f"\n{i}. [{r['score']:.3f}] {r['title']}")
            print(f"   🏛️  {r.get('publisher', 'N/A')}")
            print(f"   🌍 {', '.join(r.get('territorio', [])[:3])}")
            print(f"   🏷️  {', '.join(r.get('tema', [])[:3])}")
            if 'explanation' in r:
                print(f"   💡 {r['explanation']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_facet_values():
    """Muestra valores de facetas para entender qué datos hay."""
    print(f"\n{'='*80}")
    print("📚 VALORES DE FACETAS (muestra)")
    print(f"{'='*80}")
    
    facets = ["tema", "territorio", "formato"]
    for facet in facets:
        try:
            response = requests.get(
                f"{API_URL}/facets/{facet}",
                params={"limit": 10},
                timeout=10,
                verify=False
            )
            if response.status_code == 200:
                data = response.json()
                values = data.get("values", [])
                print(f"\n{facet.upper()} ({len(values)} total):")
                for v in values[:5]:
                    print(f"   - {v}")
            else:
                print(f"\n❌ Error en {facet}: HTTP {response.status_code}")
        except Exception as e:
            print(f"\n❌ Error en {facet}: {e}")


def test_variations():
    """Prueba variaciones de la query para ver qué funciona."""
    queries = [
        "despoblación",
        "despoblacion",
        "población",
        "poblacion",
        "demografía",
        "censo",
        "habitantes",
        "municipios",
        "rural",
        "pueblos",
    ]
    
    print(f"\n{'='*80}")
    print("🧪 TEST DE VARIACIONES DE QUERY")
    print(f"{'='*80}")
    
    for q in queries:
        try:
            response = requests.post(
                f"{API_URL}/search",
                json={"query": q, "top_k": 3},
                timeout=30,
                verify=False
            )
            if response.status_code == 200:
                data = response.json()
                count = data.get("total_results", 0)
                print(f"   '{q}' → {count} resultados")
            else:
                print(f"   '{q}' → Error HTTP {response.status_code}")
        except Exception as e:
            print(f"   '{q}' → Error: {e}")


if __name__ == "__main__":
    print("🔧 DIAGNÓSTICO DE BÚSQUEDA")
    print("API URL:", API_URL)
    
    # Verificar que API está corriendo
    try:
        health = requests.get(f"{API_URL}/health", timeout=5, verify=False)
        if health.status_code == 200:
            print("✅ API conectada")
            data = health.json()
            print(f"   Datasets cargados: {data.get('datasets_count', 'N/A')}")
        else:
            print(f"⚠️  API responde con status {health.status_code}")
    except Exception as e:
        print(f"❌ No se puede conectar a la API: {e}")
        sys.exit(1)
    
    # Tests
    test_search("despoblación")
    test_search("despoblación", semantic_weight=1.0, lexical_weight=0.0)
    test_search("despoblación", semantic_weight=0.0, lexical_weight=1.0)
    test_variations()
    test_facet_values()
    
    print(f"\n{'='*80}")
    print("✅ FIN DEL DIAGNÓSTICO")
    print(f"{'='*80}")
