#!/usr/bin/env python3
"""
Script de prueba rápida de la API Linked Data de datos.gob.es
Sin dependencias externas - usa solo urllib.

Uso:
    python3 test_api.py
"""

import json
import sys
import urllib.request
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urljoin

BASE_URL = "https://datos.gob.es/apidata/catalog/dataset"


def api_get_json(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """GET HTTP y devuelve JSON."""
    if params:
        url = f"{url}?{urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "PFM-Test/1.0",
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def explore_dataset(dataset: Dict):
    """Explora la estructura de un dataset."""
    title_raw = dataset.get('title', [])
    title_es = ""
    if isinstance(title_raw, list) and title_raw:
        title_es = title_raw[0].get('_value', 'N/A')
    elif isinstance(title_raw, dict):
        title_es = title_raw.get('_value', 'N/A')
    
    print(f"\n📊 Dataset ID: {dataset.get('identifier', 'N/A')}")
    print(f"   URL: {dataset.get('_about', 'N/A')}")
    print(f"   Título (ES): {title_es[:100]}...")
    
    print(f"\n   Claves principales: {list(dataset.keys())}")
    
    important = ["title", "description", "theme", "publisher", "spatial", 
                 "license", "temporal", "accrualPeriodicity", "distribution",
                 "keyword", "identifier", "issued", "modified"]
    
    for field in important:
        value = dataset.get(field)
        if value is None:
            print(f"   {field}: ❌ No presente")
        else:
            print(f"   {field}: {type(value).__name__}")
            if isinstance(value, list) and value:
                print(f"      → Lista con {len(value)} elementos")
                if isinstance(value[0], dict):
                    print(f"      → Keys: {list(value[0].keys())}")
                    print(f"      → Muestra: {json.dumps(value[0], ensure_ascii=False)[:300]}...")
                else:
                    print(f"      → Ejemplo: {value[0]}")
            elif isinstance(value, dict):
                print(f"      → Keys: {list(value.keys())}")
                print(f"      → Muestra: {json.dumps(value, ensure_ascii=False)[:300]}...")
            else:
                print(f"      → Valor: {str(value)[:200]}")


def main():
    print("🔍 Test de conectividad - datos.gob.es Linked Data API")
    print(f"   URL Base: {BASE_URL}")
    
    # 1. Test conexión básica
    print_section("1. CONEXIÓN BÁSICA")
    data = api_get_json(f"{BASE_URL}.json", {"_page": 0, "_pageSize": 3})
    
    if not data:
        print("❌ No se pudo conectar. Abortando.")
        sys.exit(1)
    
    result = data.get("result", {})
    items = result.get("items", [])
    
    print(f"✅ Conectado. Datasets en página: {len(items)}")
    
    # Mostrar metadata de paginación
    print(f"\n   Metadata de paginación:")
    for key in ["_about", "first", "next", "isPartOf"]:
        if key in result:
            print(f"      {key}: {result[key]}")
    
    # 2. Explorar primer dataset
    if items:
        print_section("2. ESTRUCTURA DE DATASET (primer elemento)")
        explore_dataset(items[0])
        
        # 3. Frecuencia de campos
        print_section("3. FRECUENCIA DE CAMPOS (muestra de página)")
        fields_count = {}
        for ds in items:
            for key in ds.keys():
                fields_count[key] = fields_count.get(key, 0) + 1
        
        total = len(items)
        for field, cnt in sorted(fields_count.items(), key=lambda x: -x[1]):
            print(f"   {field:25s}: {cnt:2d}/{total} ({(cnt/total)*100:5.0f}%)")
    
    # 4. Total estimado
    print_section("4. ESTIMACIÓN TOTAL")
    data_large = api_get_json(f"{BASE_URL}.json", {"_page": 0, "_pageSize": 1})
    if data_large:
        result_large = data_large.get("result", {})
        # Intentar obtener el total desde la URL de isPartOf o calcular
        print(f"   ✓ API responde correctamente")
        print(f"   → Para obtener total completo, iterar por páginas")
    
    print_section("✅ TEST COMPLETADO")
    print("La API Linked Data responde correctamente.")
    print(f"\nComando sugerido (100 datasets para empezar):")
    print(f"   python3 src/ingestion/ingest_datos_gob.py --limit 100 --output data/raw/")


if __name__ == "__main__":
    main()
