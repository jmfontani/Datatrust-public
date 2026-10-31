#!/usr/bin/env python3
"""Test rápido de la API buscando vía HTTP al backend."""
import requests, json, time

API_BASE = "http://localhost:8000"

def test_search(query, **kwargs):
    url = f"{API_BASE}/search"
    payload = {"query": query, "top_k": 5, **kwargs}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"\n🔍 Query: '{query}'")
            print(f"   ⏱️  {data['search_time_ms']:.1f}ms | pesos S:{data['semantic_weight']:.2f} L:{data['lexical_weight']:.2f}")
            for i, res in enumerate(data['results'][:3], 1):
                print(f"   {i}. {res['title'][:55]:55} (score:{res['score']:.3f} sem:{res.get('semantic_score',0):.3f} lex:{res.get('lexical_score',0):.3f})")
            return data
        else:
            print(f"❌ Error {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None

print("="*70)
print("TEST DE BÚSQUEDA EN API V2 (PostgreSQL)")
print("="*70)

# Health check
try:
    r = requests.get(f"{API_BASE}/health", timeout=5)
    if r.status_code == 200:
        h = r.json()
        print(f"✅ Health: {h.get('datasets_count',0)} datasets, pgvector: {h.get('pgvector',False)}")
    else:
        print(f"⚠️  Health status: {r.status_code}")
except Exception as e:
    print(f"❌ No se puede conectar a {API_BASE}: {e}")
    print("   Asegúrate de que el backend está corriendo: ./launch_all_v2.sh")
    exit(1)

# Tests
test_search("paro", semantic_weight=0.7, lexical_weight=0.3)
test_search("paro desempleo", semantic_weight=0.7, lexical_weight=0.3)
test_search("trafico madrid", semantic_weight=0.7, lexical_weight=0.3)
test_search("transporte público", semantic_weight=0.7, lexical_weight=0.3)
test_search("hospitales", semantic_weight=0.7, lexical_weight=0.3)
test_search("covid", semantic_weight=0.7, lexical_weight=0.3)
test_search("educación", semantic_weight=0.7, lexical_weight=0.3)

print("\n" + "="*70)
