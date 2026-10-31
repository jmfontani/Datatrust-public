#!/usr/bin/env python3
"""
Script de diagnóstico para verificar conectividad con la API.
Ejecutar: python3 diagnostico.py
"""
import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# URLs a probar
URLS = [
    "http://localhost:8000",
    "http://localhost:8000/",
    "http://localhost:8000/health",
    "http://localhost:8000/facets/territorio",
    "https://servidor1.local:8443",
    "https://servidor1.local:8443/",
    "https://servidor1.local:8443/health",
    "https://servidor1.local:8443/facets/territorio",
]

print("="*80)
print("DIAGNÓSTICO DE CONECTIVIDAD API")
print("="*80)
print()

for url in URLS:
    print(f"Probando: {url}")
    try:
        response = requests.get(url, timeout=10, verify=False)
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('content-type', 'N/A')}")
        print(f"  Tamaño respuesta: {len(response.text)} bytes")
        
        # Intentar parsear JSON
        try:
            data = response.json()
            print(f"  ✅ JSON válido: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
        except Exception as e:
            print(f"  ❌ No es JSON: {e}")
            print(f"  Primeros 300 chars:")
            print(f"  {response.text[:300]}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()

print("="*80)
print("FIN DEL DIAGNÓSTICO")
print("="*80)
