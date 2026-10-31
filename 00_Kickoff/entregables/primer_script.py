#!/usr/bin/env python3
"""
Primer Script - Prueba de Conexión a datos.gob.es

Este script sirve como punto de partida para:
1. Verificar que la API de datos.gob.es es accesible
2. Entender la estructura de los datos
3. Obtener una muestra inicial para análisis

Equipo: Buscador Semántico de Datasets Públicos
Fecha: 2026-05-20

NOTA: La API de datos.gob.es usa parámetros de paginación:
  - _pageSize: Número de resultados por página (máx 50)
  - _page: Número de página (empezando en 0)
"""

import requests
import json
from datetime import datetime

# Configuración
API_BASE_URL = "https://datos.gob.es/apidata/catalog"
DATASET_ENDPOINT = f"{API_BASE_URL}/dataset"

def test_api_connection():
    """
    Prueba básica de conexión a la API de datos.gob.es.
    Obtiene los primeros 5 datasets.
    """
    print("=" * 60)
    print("PRUEBA 1: Conexión a API datos.gob.es")
    print("=" * 60)
    
    try:
        # Parámetros de paginación de la API
        params = {
            "_pageSize": 5,  # Máximo 50
            "_page": 0       # Primera página
        }
        
        print(f"\nConsultando: {DATASET_ENDPOINT}")
        print(f"Parámetros: {params}")
        
        response = requests.get(
            DATASET_ENDPOINT,
            params=params,
            headers={"Accept": "application/json"},
            timeout=15
        )
        
        print(f"Código de estado: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
        
        if response.status_code == 200:
            try:
                data = response.json()
            except json.JSONDecodeError:
                print(f"\n⚠️ Respuesta no es JSON. Primeros 200 caracteres:")
                print(response.text[:200])
                return False
            
            print("\n✅ CONEXIÓN EXITOSA")
            
            # Inspeccionar estructura
            if 'result' in data:
                result = data['result']
                if isinstance(result, dict) and 'items' in result:
                    items = result['items']
                    total = result.get('total', 'N/A')
                elif isinstance(result, list):
                    items = result
                    total = len(items)
                else:
                    items = []
                    total = 0
            elif 'items' in data:
                items = data['items']
                total = data.get('total', len(items))
            else:
                # La respuesta podría ser directamente la lista
                items = data if isinstance(data, list) else []
                total = len(items)
            
            print(f"\nTotal de datasets: {total}")
            print(f"Datasets en esta página: {len(items)}")
            
            if items:
                print(f"\nMostrando primeros {min(3, len(items))} datasets:")
                print("-" * 60)
                
                for i, dataset in enumerate(items[:3], 1):
                    if isinstance(dataset, dict):
                        title = dataset.get('title', dataset.get('name', 'Sin título'))
                        description = dataset.get('description', dataset.get('notes', ''))[:150]
                        organization = dataset.get('organization', 'Sin organización')
                        if isinstance(organization, dict):
                            organization = organization.get('title', organization.get('name', 'Sin organización'))
                        
                        print(f"\n{i}. {title}")
                        print(f"   Organización: {organization}")
                        print(f"   Descripción: {description}...")
                    else:
                        print(f"\n{i}. {str(dataset)[:100]}")
            
            return True
            
        else:
            print(f"\n❌ Error: Código de estado {response.status_code}")
            print(f"Respuesta: {response.text[:500]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error de conexión: {e}")
        return False


def analyze_response_structure():
    """
    Analiza en detalle la estructura de la respuesta JSON.
    """
    print("\n" + "=" * 60)
    print("PRUEBA 2: Análisis de Estructura de Respuesta")
    print("=" * 60)
    
    try:
        params = {"_pageSize": 1, "_page": 0}
        response = requests.get(
            DATASET_ENDPOINT,
            params=params,
            headers={"Accept": "application/json"},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n📊 Estructura de la respuesta:")
            print("-" * 60)
            
            def print_structure(obj, indent=0):
                """Recursivamente imprime la estructura del JSON"""
                prefix = "  " * indent
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, (dict, list)):
                            print(f"{prefix}• {key} ({type(value).__name__})")
                            if len(str(value)) < 200:
                                print(f"{prefix}  → {value}")
                            print_structure(value, indent + 1)
                        else:
                            value_str = str(value)[:80]
                            print(f"{prefix}• {key}: {value_str}")
                elif isinstance(obj, list):
                    print(f"{prefix}[Lista con {len(obj)} elementos]")
                    if obj:
                        print(f"{prefix}Primer elemento:")
                        print_structure(obj[0], indent + 1)
            
            print_structure(data)
            
            # Guardar estructura para análisis offline
            with open("estructura_respuesta.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print("\n✅ Estructura guardada en: estructura_respuesta.json")
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_sample_datasets():
    """
    Guarda una muestra de 10 datasets para análisis offline.
    """
    print("\n" + "=" * 60)
    print("PRUEBA 3: Guardado de Muestra")
    print("=" * 60)
    
    try:
        params = {"_pageSize": 10, "_page": 0}
        response = requests.get(
            DATASET_ENDPOINT,
            params=params,
            headers={"Accept": "application/json"},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Guardar respuesta completa
            filename = "muestra_completa.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"\n✅ Respuesta completa guardada en: {filename}")
            
            # Extraer datasets para análisis más simple
            if 'result' in data and isinstance(data['result'], dict) and 'items' in data['result']:
                datasets = data['result']['items']
            elif 'items' in data:
                datasets = data['items']
            elif isinstance(data, list):
                datasets = data
            else:
                datasets = []
            
            simplified = []
            for ds in datasets:
                if isinstance(ds, dict):
                    simplified.append({
                        "title": ds.get("title", ds.get("name", "Sin título")),
                        "description": ds.get("description", ds.get("notes", ""))[:300],
                        "organization": ds.get("organization", "N/A") if isinstance(ds.get("organization"), str) else ds.get("organization", {}).get("title", "N/A"),
                        "tags": ds.get("tags", []),
                        "theme": ds.get("theme", []),
                        "publisher": ds.get("publisher", {}),
                        "contactPoint": ds.get("contactPoint", {}),
                        "identifier": ds.get("identifier", "N/A"),
                        "license": ds.get("license", "N/A"),
                        "spatial": ds.get("spatial", "N/A"),
                        "temporal": ds.get("temporal", "N/A"),
                        "accrualPeriodicity": ds.get("accrualPeriodicity", "N/A"),
                        "distribution": ds.get("distribution", []),
                    })
            
            filename_simple = "muestra_simplificada.json"
            with open(filename_simple, "w", encoding="utf-8") as f:
                json.dump(simplified, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Versión simplificada guardada en: {filename_simple}")
            print(f"   Total de datasets en muestra: {len(simplified)}")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_different_formats():
    """
    Prueba diferentes formatos de respuesta de la API.
    """
    print("\n" + "=" * 60)
    print("PRUEBA 4: Formatos de Respuesta")
    print("=" * 60)
    
    formats = [
        ("json", "application/json"),
        ("xml", "application/xml"),
        ("rdf", "application/rdf+xml"),
    ]
    
    params = {"_pageSize": 1, "_page": 0}
    
    for ext, content_type in formats:
        try:
            url = f"{DATASET_ENDPOINT}.{ext}"
            response = requests.get(
                url,
                params=params,
                headers={"Accept": content_type},
                timeout=15
            )
            
            status = "✅ OK" if response.status_code == 200 else f"❌ {response.status_code}"
            print(f"  {ext.upper():6} ({content_type}): {status}")
            
            if response.status_code == 200 and ext == "json":
                content_length = len(response.text)
                print(f"         Tamaño: {content_length} caracteres")
                
        except Exception as e:
            print(f"  {ext.upper():6}: ❌ Error - {e}")


def main():
    """
    Ejecuta todas las pruebas.
    """
    print("\n" + "=" * 60)
    print("PRIMER SCRIPT - PRUEBA DE CONEXIÓN A DATOS.GOB.ES")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")
    
    # Ejecutar pruebas
    results = {
        "API datos.gob.es": test_api_connection(),
        "Estructura": analyze_response_structure(),
        "Guardado": save_sample_datasets(),
    }
    
    # Probar formatos
    test_with_different_formats()
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ OK" if result else "❌ FALLIDO"
        print(f"  {test_name}: {status}")
    
    all_ok = all(results.values())
    
    if all_ok:
        print("\n🎉 Todas las pruebas principales pasaron!")
        print("\nArchivos generados:")
        print("  • estructura_respuesta.json - Estructura detallada")
        print("  • muestra_completa.json - Respuesta completa")
        print("  • muestra_simplificada.json - Versión simplificada")
        print("\nSiguientes pasos:")
        print("  1. Revisar muestra_simplificada.json")
        print("  2. Identificar campos relevantes para embeddings")
        print("  3. Diseñar schema de PostgreSQL")
        print("  4. Planificar pipeline de ingestión")
    else:
        print("\n⚠️ Algunas pruebas fallaron. Revisar errores arriba.")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
