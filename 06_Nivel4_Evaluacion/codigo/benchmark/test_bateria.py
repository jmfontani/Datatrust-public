#!/usr/bin/env python3
"""
Batería de tests para evaluar la calidad del buscador semántico.

Ejecutar:
    python3 test_bateria.py
"""

import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000"

# Batería de tests: consulta -> criterios de evaluación
TESTS = [
    {
        "query": "despoblación",
        "description": "Concepto específico: despoblación rural",
        "min_results": 2,
        "must_contain_any": ["despobl", "poblaci", "rural", "municipio", "habitante", "riesgo", "antidespoblamiento"],
        "must_not_contain": ["desviación", "accidente", "tráfico"],
        "territory_expected": True,
    },
    {
        "query": "paro juvenil",
        "description": "Empleo: desempleo en jóvenes",
        "min_results": 3,
        "must_contain_any": ["paro", "desempleo", "juvenil", "joven", "empleo", "desemplead", "garantia", "inscripcion", "abandono", "prematuro", "educativo"],
        "must_not_contain": ["universidad", "universitario", "máster", "grado universitario", "master", "egresados en estudios de grado"],
        "territory_expected": True,
    },
    {
        "query": "calidad del aire",
        "description": "Medio ambiente: contaminación atmosférica",
        "min_results": 3,
        "must_contain_any": ["aire", "calidad", "contaminación", "emisiones", "atmosférica", "NO2", "ozono"],
        "must_not_contain": ["agua", "suelo", "ruido"],
        "territory_expected": True,
    },
    {
        "query": "matriculaciones coches eléctricos",
        "description": "Movilidad: vehículos eléctricos",
        "min_results": 2,
        "must_contain_any": ["matriculación", "vehículo", "eléctrico", "coche", "automóvil", "turismo"],
        "must_not_contain": ["gas natural", "gasolina", "diesel", "carbón", "petróleo", "combustible fósil"],
        "territory_expected": True,
    },
    {
        "query": "gasto sanitario por habitante",
        "description": "Sanidad: financiación salud",
        "min_results": 2,
        "must_contain_any": ["sanidad", "sanitario", "gasto", "salud", "hospital", "médico"],
        "must_not_contain": ["educación", "defensa"],
        "territory_expected": True,
    },
    {
        "query": "precio vivienda",
        "description": "Vivienda: mercado inmobiliario",
        "min_results": 3,
        "must_contain_any": ["vivienda", "precio", "inmobiliario", "casa", "alquiler", "hipoteca", "m2"],
        "must_not_contain": ["vehículo", "coche"],
        "territory_expected": True,
    },
    {
        "query": "tasa de natalidad",
        "description": "Demografía: nacimientos",
        "min_results": 3,
        "must_contain_any": ["natalidad", "nacimiento", "fertilidad", "fecundidad", "demográfico", "población"],
        "must_not_contain": ["mortalidad", "defunción"],
        "territory_expected": True,
    },
    {
        "query": "energía solar fotovoltaica",
        "description": "Energías renovables",
        "min_results": 2,
        "must_contain_any": ["solar", "fotovoltaica", "renovable", "energía", "panel"],
        "must_not_contain": ["nuclear", "carbón", "gas"],
        "territory_expected": True,
    },
    {
        "query": "delitos por municipio",
        "description": "Seguridad: criminalidad",
        "min_results": 2,
        "must_contain_any": ["delito", "criminalidad", "seguridad", "policía", "delincuencia"],
        "must_not_contain": ["accidente", "tráfico"],
        "territory_expected": True,
    },
    {
        "query": "rendimiento académico escolar",
        "description": "Educación: resultados escolares",
        "min_results": 2,
        "must_contain_any": ["educación", "escolar", "académico", "rendimiento", "nota", "evaluación", "alumno", "alumnado", "estudios", "enseñanza", "bachillerato", "eso", "primaria", "secundaria"],
        "must_not_contain": ["universidad", "formación profesional"],
        "territory_expected": True,
    },
    {
        "query": "Turismo en Canarias",
        "description": "Turismo: territorio específico",
        "min_results": 2,
        "must_contain_any": ["turismo", "turista", "alojamiento", "viaje"],
        "must_not_contain": [],
        "territory_expected": True,
        "territory_filter": "Canarias",
    },
    {
        "query": "Agua potable",
        "description": "Recursos hídricos básico",
        "min_results": 2,
        "must_contain_any": ["agua", "potable", "abastecimiento", "hídrico"],
        "must_not_contain": ["desagüe", "aguas residuales"],
        "territory_expected": True,
    },
]


def check_results(results, test):
    """Evalúa si los resultados cumplen los criterios."""
    issues = []
    
    # Verificar número mínimo de resultados
    if len(results) < test["min_results"]:
        issues.append(f"⚠️ Solo {len(results)} resultados (mínimo esperado: {test['min_results']})")
    
    for i, result in enumerate(results):
        title = result.get("title", "").lower()
        desc = result.get("description", "").lower()
        content = title + " " + desc
        score = result.get("score", 0)
        
        # Verificar must_contain_any
        has_required = any(term.lower() in content for term in test["must_contain_any"])
        if not has_required:
            issues.append(f"  ❌ Resultado #{i+1} no contiene términos esperados (score: {score})")
            issues.append(f"     Título: {result.get('title', 'N/A')[:80]}...")
        
        # Verificar must_not_contain
        for bad_term in test.get("must_not_contain", []):
            if bad_term.lower() in content:
                issues.append(f"  ⚠️ Resultado #{i+1} contiene '{bad_term}' (score: {score})")
                issues.append(f"     Título: {result.get('title', 'N/A')[:80]}...")
    
    return issues


def run_test(test):
    """Ejecuta una búsqueda y evalúa resultados."""
    payload = {
        "query": test["query"],
        "top_k": 10,
        "semantic_weight": 0.7,
        "lexical_weight": 0.3,
        "min_score": 0.20,
        "require_lexical_match": True,
        "explain": True,
    }
    
    # Añadir filtro de territorio si está definido
    if test.get("territory_filter"):
        payload["territorio"] = test["territory_filter"]
    
    try:
        response = requests.post(
            f"{API_URL}/search",
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            return {
                "query": test["query"],
                "status": "ERROR",
                "error": f"HTTP {response.status_code}",
                "issues": [f"Error de API: {response.status_code}"],
            }
        
        data = response.json()
        results = data.get("results", [])
        
        issues = check_results(results, test)
        
        return {
            "query": test["query"],
            "status": "PASS" if not issues else "FAIL",
            "description": test["description"],
            "results_count": len(results),
            "search_time_ms": data.get("search_time_ms", 0),
            "issues": issues,
            "top_result": results[0] if results else None,
        }
        
    except requests.exceptions.ConnectionError:
        return {
            "query": test["query"],
            "status": "ERROR",
            "error": "No se pudo conectar a la API",
            "issues": ["Verifica que la API esté corriendo en http://localhost:8000"],
        }
    except Exception as e:
        return {
            "query": test["query"],
            "status": "ERROR",
            "error": str(e),
            "issues": [str(e)],
        }


def print_result(result):
    """Imprime resultado formateado."""
    status_icon = "✅" if result["status"] == "PASS" else ("❌" if result["status"] == "FAIL" else "💥")
    
    print(f"\n{'='*80}")
    print(f"{status_icon} {result['query']}")
    print(f"   {result['description']}")
    print(f"   Resultados: {result['results_count']} | Tiempo: {result.get('search_time_ms', 'N/A')}ms")
    
    if result["status"] == "ERROR":
        print(f"   ERROR: {result.get('error', 'Desconocido')}")
        return
    
    if result["issues"]:
        print(f"   ⚠️ Problemas encontrados:")
        for issue in result["issues"]:
            print(f"      {issue}")
    else:
        print(f"   ✅ Todos los criterios cumplidos")
    
    # Mostrar top resultado
    if result.get("top_result"):
        top = result["top_result"]
        print(f"\n   🥇 Top resultado (score: {top['score']}):")
        print(f"      Título: {top['title'][:100]}")
        print(f"      Publisher: {top.get('publisher', 'N/A')}")
        print(f"      Territorio: {top.get('territorio', 'N/A')}")
        if top.get("explanation"):
            print(f"      Explicación: {top['explanation'][:120]}")


def main():
    print("="*80)
    print("🔍 BATERÍA DE TESTS - Buscador Semántico de Datasets")
    print("="*80)
    print(f"\nAPI: {API_URL}")
    print(f"Tests: {len(TESTS)}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar API primero
    try:
        health = requests.get(f"{API_URL}/health", timeout=5).json()
        print(f"✅ API OK - Datasets cargados: {health.get('datasets_count', 'N/A')}")
    except:
        print("❌ API no disponible. Verifica que esté corriendo.")
        return
    
    # Ejecutar tests
    results = []
    for test in TESTS:
        result = run_test(test)
        results.append(result)
        print_result(result)
    
    # Resumen
    print(f"\n{'='*80}")
    print("📊 RESUMEN")
    print("="*80)
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    
    print(f"✅ Pasados: {passed}/{len(TESTS)}")
    print(f"❌ Fallidos: {failed}/{len(TESTS)}")
    print(f"💥 Errores: {errors}/{len(TESTS)}")
    print(f"📈 Precisión: {passed/len(TESTS)*100:.1f}%")
    
    # Detalle de fallos
    if failed > 0:
        print(f"\n🔴 Tests fallidos:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"   - {r['query']}: {r['description']}")
    
    if errors > 0:
        print(f"\n💥 Tests con error:")
        for r in results:
            if r["status"] == "ERROR":
                print(f"   - {r['query']}: {r.get('error', 'Error desconocido')}")
    
    # Guardar reporte
    report = {
        "fecha": datetime.now().isoformat(),
        "api_url": API_URL,
        "total_tests": len(TESTS),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "accuracy": passed/len(TESTS)*100,
        "results": results,
    }
    
    output_file = "test_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Reporte guardado en: {output_file}")


if __name__ == "__main__":
    main()
