#!/usr/bin/env python3
"""
BATERÍA DE PRUEBAS EXTENDIDA - Buscador Semántico de Datasets
Cubre 40+ casos de prueba en múltiples dominios y escenarios.

Ejecutar:
    python3 test_bateria_extendida.py
"""

import requests
import json
import time
from datetime import datetime
from collections import defaultdict

API_URL = "http://localhost:8000"

# ============================================================================
# TESTS ORIGINALES (12) - Mejorados
# ============================================================================

TESTS_BASE = [
    {
        "query": "despoblación",
        "description": "Concepto específico: despoblación rural",
        "category": "demografia",
        "min_results": 2,
        "must_contain_any": ["despobl", "poblaci", "rural", "municipio", "habitante", "riesgo", "antidespoblamiento"],
        "must_not_contain": ["desviación", "accidente", "tráfico"],
        "territory_expected": True,
    },
    {
        "query": "paro juvenil",
        "description": "Empleo: desempleo en jóvenes",
        "category": "empleo",
        "min_results": 3,
        "must_contain_any": ["paro", "desempleo", "juvenil", "joven", "empleo", "desemplead", "garantia", "inscripcion", "abandono", "prematuro", "educativo"],
        "must_not_contain": ["universidad", "universitario", "máster", "grado universitario", "master", "egresados en estudios de grado"],
        "territory_expected": True,
    },
    {
        "query": "calidad del aire",
        "description": "Medio ambiente: contaminación atmosférica",
        "category": "medio_ambiente",
        "min_results": 3,
        "must_contain_any": ["aire", "calidad", "contaminación", "emisiones", "atmosférica", "NO2", "ozono"],
        "must_not_contain": ["agua", "suelo", "ruido"],
        "territory_expected": True,
    },
    {
        "query": "matriculaciones coches eléctricos",
        "description": "Movilidad: vehículos eléctricos",
        "category": "transporte",
        "min_results": 2,
        "must_contain_any": ["matriculación", "vehículo", "eléctrico", "coche", "automóvil", "turismo"],
        "must_not_contain": ["gas natural", "gasolina", "diesel", "carbón", "petróleo", "combustible fósil"],
        "territory_expected": True,
    },
    {
        "query": "gasto sanitario por habitante",
        "description": "Sanidad: financiación salud",
        "category": "sanidad",
        "min_results": 2,
        "must_contain_any": ["sanidad", "sanitario", "gasto", "salud", "hospital", "médico"],
        "must_not_contain": ["educación", "defensa"],
        "territory_expected": True,
    },
    {
        "query": "precio vivienda",
        "description": "Vivienda: mercado inmobiliario",
        "category": "vivienda",
        "min_results": 3,
        "must_contain_any": ["vivienda", "precio", "inmobiliario", "casa", "alquiler", "hipoteca", "m2"],
        "must_not_contain": ["vehículo", "coche"],
        "territory_expected": True,
    },
    {
        "query": "tasa de natalidad",
        "description": "Demografía: nacimientos",
        "category": "demografia",
        "min_results": 3,
        "must_contain_any": ["natalidad", "nacimiento", "fertilidad", "fecundidad", "demográfico", "población"],
        "must_not_contain": ["mortalidad", "defunción"],
        "territory_expected": True,
    },
    {
        "query": "energía solar fotovoltaica",
        "description": "Energías renovables",
        "category": "energia",
        "min_results": 2,
        "must_contain_any": ["solar", "fotovoltaica", "renovable", "energía", "panel"],
        "must_not_contain": ["nuclear", "carbón", "gas natural", "gasolina", "diesel", "petróleo"],
        "territory_expected": True,
    },
    {
        "query": "delitos por municipio",
        "description": "Seguridad: criminalidad",
        "category": "seguridad",
        "min_results": 2,
        "must_contain_any": ["delito", "criminalidad", "seguridad", "policía", "delincuencia"],
        "must_not_contain": ["accidente", "tráfico"],
        "territory_expected": True,
    },
    {
        "query": "rendimiento académico escolar",
        "description": "Educación: resultados escolares",
        "category": "educacion",
        "min_results": 2,
        "must_contain_any": ["educación", "escolar", "académico", "rendimiento", "nota", "evaluación", "alumno", "alumnado", "estudios", "enseñanza", "bachillerato", "eso", "primaria", "secundaria"],
        "must_not_contain": ["universidad", "formación profesional"],
        "territory_expected": True,
    },
    {
        "query": "Turismo en Canarias",
        "description": "Turismo: territorio específico",
        "category": "turismo",
        "min_results": 2,
        "must_contain_any": ["turismo", "turista", "alojamiento", "viaje"],
        "must_not_contain": [],
        "territory_expected": True,
        "territory_filter": "Canarias",
    },
    {
        "query": "Agua potable",
        "description": "Recursos hídricos básico",
        "category": "medio_ambiente",
        "min_results": 2,
        "must_contain_any": ["agua", "potable", "abastecimiento", "hídrico"],
        "must_not_contain": ["desagüe", "aguas residuales"],
        "territory_expected": True,
    },
]

# ============================================================================
# TESTS ADICIONALES - Transporte y Movilidad
# ============================================================================

TESTS_TRANSPORTE = [
    {
        "query": "accidentes de tráfico",
        "description": "Seguridad vial: accidentes",
        "category": "transporte",
        "min_results": 3,
        "must_contain_any": ["accidente", "tráfico", "circulación", "vial", "carretera", "vehículo"],
        "must_not_contain": ["delito", "criminalidad"],
        "territory_expected": True,
    },
    {
        "query": "bicicleta carril bici",
        "description": "Movilidad sostenible: infraestructura ciclista",
        "category": "transporte",
        "min_results": 1,
        "must_contain_any": ["bicicleta", "carril bici", "ciclista", "movilidad", "sostenible"],
        "must_not_contain": ["motor", "gasolina"],
        "territory_expected": True,
    },
    {
        "query": "transporte público autobús",
        "description": "Transporte público: autobuses",
        "category": "transporte",
        "min_results": 2,
        "must_contain_any": ["autobús", "bus", "transporte público", "movilidad", "pasajero"],
        "must_not_contain": [],
        "territory_expected": True,
    },
]

# ============================================================================
# TESTS ADICIONALES - Medio Ambiente y Cambio Climático
# ============================================================================

TESTS_MEDIO_AMBIENTE = [
    {
        "query": "cambio climático temperatura",
        "description": "Cambio climático: datos meteorológicos",
        "category": "medio_ambiente",
        "min_results": 2,
        "must_contain_any": ["clima", "temperatura", "meteorológico", "meteorología", "climático"],
        "must_not_contain": ["política", "económico"],
        "territory_expected": True,
    },
    {
        "query": "residuos reciclaje",
        "description": "Gestión de residuos y reciclaje",
        "category": "medio_ambiente",
        "min_results": 2,
        "must_contain_any": ["residuo", "reciclaje", "basura", "reciclar", "contenedor"],
        "must_not_contain": ["nuclear", "tóxico"],
        "territory_expected": True,
    },
    {
        "query": "espacios verdes parques",
        "description": "Espacios naturales urbanos",
        "category": "medio_ambiente",
        "min_results": 1,
        "must_contain_any": ["parque", "verde", "natural", "jardín", "espacio verde"],
        "must_not_contain": [],
        "territory_expected": True,
    },
]

# ============================================================================
# TESTS ADICIONALES - Economía y Empleo
# ============================================================================

TESTS_ECONOMIA = [
    {
        "query": "PIB producto interior bruto",
        "description": "Economía: indicador macroeconómico",
        "category": "economia",
        "min_results": 2,
        "must_contain_any": ["PIB", "producto interior bruto", "economía", "renta"],
        "must_not_contain": ["paro", "desempleo"],
        "territory_expected": True,
    },
    {
        "query": "pensiones jubilación",
        "description": "Seguridad social: pensiones",
        "category": "economia",
        "min_results": 2,
        "must_contain_any": ["pensión", "jubilación", "jubilado", "seguridad social"],
        "must_not_contain": ["paro", "desempleo"],
        "territory_expected": True,
    },
    {
        "query": "subvenciones ayudas",
        "description": "Financiación pública: subvenciones",
        "category": "economia",
        "min_results": 2,
        "must_contain_any": ["subvención", "ayuda", "financiación", "beca", "fondo"],
        "must_not_contain": [],
        "territory_expected": True,
    },
]

# ============================================================================
# TESTS ADICIONALES - Cultura y Patrimonio
# ============================================================================

TESTS_CULTURA = [
    {
        "query": "museos exposiciones",
        "description": "Cultura: instituciones museísticas",
        "category": "cultura",
        "min_results": 2,
        "must_contain_any": ["museo", "exposición", "cultural", "patrimonio", "arte"],
        "must_not_contain": ["deporte", "comercial"],
        "territory_expected": True,
    },
    {
        "query": "bibliotecas lectura",
        "description": "Cultura: bibliotecas y fomento de lectura",
        "category": "cultura",
        "min_results": 1,
        "must_contain_any": ["biblioteca", "lectura", "libro", "cultural"],
        "must_not_contain": [],
        "territory_expected": True,
    },
    {
        "query": "festivales música",
        "description": "Ocio cultural: festivales",
        "category": "cultura",
        "min_results": 1,
        "must_contain_any": ["festival", "música", "cultural", "evento"],
        "must_not_contain": ["deporte"],
        "territory_expected": True,
    },
]

# ============================================================================
# TESTS ADICIONALES - Deportes
# ============================================================================

TESTS_DEPORTE = [
    {
        "query": "instalaciones deportivas",
        "description": "Deporte: infraestructuras",
        "category": "deporte",
        "min_results": 2,
        "must_contain_any": ["deporte", "instalación", "piscina", "gimnasio", "polideportivo"],
        "must_not_contain": ["cultural", "museo"],
        "territory_expected": True,
    },
    {
        "query": "fútbol equipos",
        "description": "Deporte: fútbol",
        "category": "deporte",
        "min_results": 1,
        "must_contain_any": ["fútbol", "futbol", "equipo", "deporte"],
        "must_not_contain": ["baloncesto", "tenis"],
        "territory_expected": True,
    },
]

# ============================================================================
# TESTS ADICIONALES - Infraestructuras y Urbanismo
# ============================================================================

TESTS_INFRAESTRUCTURAS = [
    {
        "query": "obra pública construcción",
        "description": "Urbanismo: obras públicas",
        "category": "infraestructuras",
        "min_results": 2,
        "must_contain_any": ["obra", "construcción", "edificación", "urbanismo", "infraestructura"],
        "must_not_contain": ["privada"],
        "territory_expected": True,
    },
    {
        "query": "carreteras carretera",
        "description": "Infraestructuras: red viaria",
        "category": "infraestructuras",
        "min_results": 2,
        "must_contain_any": ["carretera", "vial", "infraestructura", "tráfico"],
        "must_not_contain": [],
        "territory_expected": True,
    },
]

# ============================================================================
# TESTS ADICIONALES - Agricultura y Pesca
# ============================================================================

TESTS_AGRICULTURA = [
    {
        "query": "agricultura cultivos",
        "description": "Agricultura: producción agrícola",
        "category": "agricultura",
        "min_results": 2,
        "must_contain_any": ["agricultura", "cultivo", "agrario", "rural", "explotación"],
        "must_not_contain": ["industrial", "urbano"],
        "territory_expected": True,
    },
    {
        "query": "pesca flota pesquera",
        "description": "Pesca: sector pesquero",
        "category": "agricultura",
        "min_results": 1,
        "must_contain_any": ["pesca", "pesquero", "flota", "mar", "acuicultura"],
        "must_not_contain": ["caza"],
        "territory_expected": True,
    },
]

# ============================================================================
# TESTS ADICIONALES - Tecnología e Innovación
# ============================================================================

TESTS_TECNOLOGIA = [
    {
        "query": "banda ancha internet",
        "description": "Tecnología: conectividad",
        "category": "tecnologia",
        "min_results": 1,
        "must_contain_any": ["banda ancha", "internet", "conectividad", "telecomunicación", "digital"],
        "must_not_contain": [],
        "territory_expected": True,
    },
    {
        "query": "innovación I+D investigación",
        "description": "Innovación: I+D+i",
        "category": "tecnologia",
        "min_results": 1,
        "must_contain_any": ["innovación", "investigación", "I+D", "desarrollo", "tecnología"],
        "must_not_contain": ["educación"],
        "territory_expected": True,
    },
]

# ============================================================================
# TESTS DE CASOS LÍMITE Y ESPECIALES
# ============================================================================

TESTS_ESPECIALES = [
    {
        "query": "COVID-19 coronavirus pandemia",
        "description": "Caso especial: término técnico moderno",
        "category": "especial",
        "min_results": 1,
        "must_contain_any": ["covid", "coronavirus", "pandemia", "sanitario", "salud"],
        "must_not_contain": [],
        "territory_expected": True,
    },
    {
        "query": "igualdad género mujer",
        "description": "Caso especial: términos sociales",
        "category": "especial",
        "min_results": 1,
        "must_contain_any": ["igualdad", "género", "mujer", "femenino"],
        "must_not_contain": [],
        "territory_expected": True,
    },
    {
        "query": "discapacidad accesibilidad",
        "description": "Caso especial: términos de inclusión",
        "category": "especial",
        "min_results": 1,
        "must_contain_any": ["discapacidad", "accesibilidad", "inclusión", "minusvalía"],
        "must_not_contain": [],
        "territory_expected": True,
    },
    {
        "query": "inmigración extranjero",
        "description": "Caso sensible: inmigración",
        "category": "especial",
        "min_results": 1,
        "must_contain_any": ["inmigración", "extranjero", "migración", "extranjera"],
        "must_not_contain": [],
        "territory_expected": True,
    },
]

# ============================================================================
# TESTS DE FILTROS TERRITORIALES
# ============================================================================

TESTS_TERRITORIALES = [
    {
        "query": "turismo",
        "description": "Filtro territorial: Andalucía",
        "category": "territorial",
        "min_results": 2,
        "must_contain_any": ["turismo", "turista"],
        "must_not_contain": [],
        "territory_expected": True,
        "territory_filter": "Andalucía",
    },
    {
        "query": "padrón habitantes",
        "description": "Filtro territorial: Madrid",
        "category": "territorial",
        "min_results": 2,
        "must_contain_any": ["padrón", "habitante", "población"],
        "must_not_contain": [],
        "territory_expected": True,
        "territory_filter": "Madrid",
    },
    {
        "query": "playas costa",
        "description": "Filtro territorial: Cataluña",
        "category": "territorial",
        "min_results": 1,
        "must_contain_any": ["playa", "costa", "litoral"],
        "must_not_contain": [],
        "territory_expected": True,
        "territory_filter": "Cataluña",
    },
]

# ============================================================================
# TESTS DE UMBRALES DE CALIDAD
# ============================================================================

TESTS_UMBRALES = [
    {
        "query": "hospitales",
        "description": "Umbral bajo: término simple",
        "category": "umbrales",
        "min_results": 3,
        "must_contain_any": ["hospital", "sanitario", "salud"],
        "must_not_contain": [],
        "territory_expected": True,
        "min_score": 0.10,
    },
    {
        "query": "hospitales",
        "description": "Umbral alto: término simple",
        "category": "umbrales",
        "min_results": 1,
        "must_contain_any": ["hospital", "sanitario", "salud"],
        "must_not_contain": [],
        "territory_expected": True,
        "min_score": 0.50,
    },
]

# ============================================================================
# COMBINAR TODOS LOS TESTS
# ============================================================================

ALL_TESTS = (
    TESTS_BASE +
    TESTS_TRANSPORTE +
    TESTS_MEDIO_AMBIENTE +
    TESTS_ECONOMIA +
    TESTS_CULTURA +
    TESTS_DEPORTE +
    TESTS_INFRAESTRUCTURAS +
    TESTS_AGRICULTURA +
    TESTS_TECNOLOGIA +
    TESTS_ESPECIALES +
    TESTS_TERRITORIALES +
    TESTS_UMBRALES
)


# ============================================================================
# FUNCIONES DE EVALUACIÓN
# ============================================================================

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
            issues.append(f"  ❌ Resultado #{i+1} no contiene términos esperados (score: {score:.4f})")
            issues.append(f"     Título: {result.get('title', 'N/A')[:80]}...")
        
        # Verificar must_not_contain
        for bad_term in test.get("must_not_contain", []):
            if bad_term.lower() in content:
                issues.append(f"  ⚠️ Resultado #{i+1} contiene '{bad_term}' (score: {score:.4f})")
                issues.append(f"     Título: {result.get('title', 'N/A')[:80]}...")
    
    return issues


def run_test(test):
    """Ejecuta una búsqueda y evalúa resultados."""
    payload = {
        "query": test["query"],
        "top_k": 10,
        "semantic_weight": 0.7,
        "lexical_weight": 0.3,
        "min_score": test.get("min_score", 0.20),
        "require_lexical_match": True,
        "explain": True,
    }
    
    # Añadir filtro de territorio si está definido
    if test.get("territory_filter"):
        payload["territorio"] = test["territory_filter"]
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_URL}/search",
            json=payload,
            timeout=30
        )
        elapsed = (time.time() - start_time) * 1000
        
        if response.status_code != 200:
            return {
                "query": test["query"],
                "status": "ERROR",
                "error": f"HTTP {response.status_code}",
                "issues": [f"Error de API: {response.status_code}"],
                "category": test.get("category", "general"),
            }
        
        data = response.json()
        results = data.get("results", [])
        
        issues = check_results(results, test)
        
        return {
            "query": test["query"],
            "status": "PASS" if not issues else "FAIL",
            "description": test["description"],
            "category": test.get("category", "general"),
            "results_count": len(results),
            "search_time_ms": data.get("search_time_ms", 0),
            "response_time_ms": elapsed,
            "issues": issues,
            "top_result": results[0] if results else None,
        }
        
    except requests.exceptions.ConnectionError:
        return {
            "query": test["query"],
            "status": "ERROR",
            "error": "No se pudo conectar a la API",
            "issues": ["Verifica que la API esté corriendo en http://localhost:8000"],
            "category": test.get("category", "general"),
        }
    except Exception as e:
        return {
            "query": test["query"],
            "status": "ERROR",
            "error": str(e),
            "issues": [str(e)],
            "category": test.get("category", "general"),
        }


def print_result(result):
    """Imprime resultado formateado."""
    status_icon = "✅" if result["status"] == "PASS" else ("❌" if result["status"] == "FAIL" else "💥")
    
    print(f"\n{'='*80}")
    print(f"{status_icon} {result['query']}")
    print(f"   [{result.get('category', 'general').upper()}] {result['description']}")
    print(f"   Resultados: {result['results_count']} | Tiempo API: {result.get('search_time_ms', 'N/A')}ms | Tiempo total: {result.get('response_time_ms', 'N/A'):.1f}ms")
    
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
        print(f"\n   🥇 Top resultado (score: {top['score']:.4f}):")
        print(f"      Título: {top['title'][:100]}")
        print(f"      Publisher: {top.get('publisher', 'N/A')}")
        print(f"      Territorio: {top.get('territorio', 'N/A')}")


def print_category_summary(results):
    """Imprime resumen por categoría."""
    print(f"\n{'='*80}")
    print("📊 RESUMEN POR CATEGORÍA")
    print("="*80)
    
    categories = defaultdict(lambda: {"passed": 0, "failed": 0, "errors": 0, "total": 0})
    
    for r in results:
        cat = r.get("category", "general")
        categories[cat]["total"] += 1
        if r["status"] == "PASS":
            categories[cat]["passed"] += 1
        elif r["status"] == "FAIL":
            categories[cat]["failed"] += 1
        else:
            categories[cat]["errors"] += 1
    
    for cat, stats in sorted(categories.items()):
        accuracy = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"\n{cat.upper()}:")
        print(f"   ✅ {stats['passed']}/{stats['total']} | ❌ {stats['failed']}/{stats['total']} | 💥 {stats['errors']}/{stats['total']}")
        print(f"   📈 Precisión: {accuracy:.1f}%")


def main():
    print("="*80)
    print("🔍 BATERÍA DE TESTS EXTENDIDA - Buscador Semántico de Datasets")
    print("="*80)
    print(f"\nAPI: {API_URL}")
    print(f"Tests: {len(ALL_TESTS)}")
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
    for i, test in enumerate(ALL_TESTS, 1):
        print(f"\n[{i}/{len(ALL_TESTS)}] ", end="", flush=True)
        result = run_test(test)
        results.append(result)
        print_result(result)
    
    # Resumen general
    print(f"\n{'='*80}")
    print("📊 RESUMEN GENERAL")
    print("="*80)
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    
    print(f"✅ Pasados: {passed}/{len(ALL_TESTS)}")
    print(f"❌ Fallidos: {failed}/{len(ALL_TESTS)}")
    print(f"💥 Errores: {errors}/{len(ALL_TESTS)}")
    print(f"📈 Precisión global: {passed/len(ALL_TESTS)*100:.1f}%")
    
    # Resumen por categoría
    print_category_summary(results)
    
    # Detalle de fallos
    if failed > 0:
        print(f"\n🔴 Tests fallidos:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"   - [{r.get('category', 'general')}] {r['query']}: {r['description']}")
                for issue in r["issues"][:2]:  # Mostrar solo primeros 2 issues
                    print(f"     {issue}")
    
    if errors > 0:
        print(f"\n💥 Tests con error:")
        for r in results:
            if r["status"] == "ERROR":
                print(f"   - [{r.get('category', 'general')}] {r['query']}: {r.get('error', 'Error desconocido')}")
    
    # Guardar reporte
    report = {
        "fecha": datetime.now().isoformat(),
        "api_url": API_URL,
        "total_tests": len(ALL_TESTS),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "accuracy": passed/len(ALL_TESTS)*100,
        "results": results,
    }
    
    output_file = "test_report_extendido.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Reporte detallado guardado en: {output_file}")


if __name__ == "__main__":
    main()
