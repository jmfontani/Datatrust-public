#!/usr/bin/env python3
"""
Script de evaluación de calidad del buscador.
Compara resultados entre la versión antigua y nueva.

Ejecutar:
    python3 test_search_quality.py
"""

import requests
import json
import time
from datetime import datetime

API_URL = "http://localhost:8000"

# Queries de prueba representativas
TEST_QUERIES = [
    # Transporte / Tráfico
    {"query": "trafico madrid", "expected_theme": "transporte", "expected_territory": "Comunidad de Madrid"},
    {"query": "accidentes de tráfico", "expected_theme": "transporte"},
    {"query": "transporte público", "expected_theme": "transporte"},
    
    # Educación
    {"query": "educación", "expected_theme": "educacion"},
    {"query": "universidades", "expected_theme": "educacion"},
    {"query": "estudiantes", "expected_theme": "educacion"},
    
    # Salud
    {"query": "hospitales", "expected_theme": "salud"},
    {"query": "covid", "expected_theme": "salud"},
    {"query": "sanidad", "expected_theme": "salud"},
    
    # Economía / Empleo
    {"query": "paro", "expected_theme": "empleo"},
    {"query": "pib", "expected_theme": "economia"},
    {"query": "empresas", "expected_theme": "economia"},
    
    # Medio Ambiente
    {"query": "calidad del aire", "expected_theme": "medio ambiente"},
    {"query": "contaminación", "expected_theme": "medio ambiente"},
    {"query": "energía renovable", "expected_theme": "energia"},
    
    # Turismo
    {"query": "turismo", "expected_theme": "turismo"},
    {"query": "hoteles", "expected_theme": "turismo"},
    {"query": "viajeros", "expected_theme": "turismo"},
    
    # Cultura
    {"query": "museos", "expected_theme": "cultura ocio"},
    {"query": "bibliotecas", "expected_theme": "cultura ocio"},
    
    # Seguridad
    {"query": "delitos", "expected_theme": "seguridad"},
    {"query": "policía", "expected_theme": "seguridad"},
    
    # Demografía
    {"query": "censo", "expected_theme": "demografia"},
    {"query": "población", "expected_theme": "demografia"},
    
    # Urbanismo
    {"query": "vivienda", "expected_theme": "urbanismo infraestructuras"},
    {"query": "edificios", "expected_theme": "urbanismo infraestructuras"},
]


def test_search(query_info):
    """Ejecuta una búsqueda y evalúa los resultados."""
    query = query_info["query"]
    
    try:
        response = requests.post(
            f"{API_URL}/search",
            json={
                "query": query,
                "top_k": 5,
                "semantic_weight": 0.7,
                "lexical_weight": 0.3,
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return {
                "query": query,
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "results": []
            }
        
        data = response.json()
        results = data.get("results", [])
        
        # Evaluar relevancia
        relevant_count = 0
        expected_theme = query_info.get("expected_theme", "")
        expected_territory = query_info.get("expected_territory", "")
        
        for result in results:
            is_relevant = False
            
            # Verificar tema
            if expected_theme:
                themes = result.get("tema", [])
                if isinstance(themes, str):
                    themes = [themes]
                for theme in themes:
                    if expected_theme.lower() in theme.lower():
                        is_relevant = True
                        break
            
            # Verificar territorio
            if expected_territory and not is_relevant:
                territories = result.get("territorio", [])
                if isinstance(territories, str):
                    territories = [territories]
                for territory in territories:
                    if expected_territory.lower() in territory.lower():
                        is_relevant = True
                        break
            
            # Verificar palabras clave en título/descripción
            if not is_relevant:
                title = result.get("title", "").lower()
                desc = result.get("description", "").lower()
                query_words = query.lower().split()
                matching_words = sum(1 for w in query_words if w in title or w in desc)
                if matching_words >= len(query_words) * 0.5:
                    is_relevant = True
            
            if is_relevant:
                relevant_count += 1
        
        # Calcular precision@k
        precision = relevant_count / len(results) if results else 0
        
        return {
            "query": query,
            "status": "ok",
            "total_results": data.get("total_results", 0),
            "returned_results": data.get("returned_results", 0),
            "search_time_ms": data.get("search_time_ms", 0),
            "precision": round(precision, 2),
            "relevant_count": relevant_count,
            "results": [
                {
                    "title": r.get("title", "")[:60],
                    "tema": r.get("tema", []),
                    "territorio": r.get("territorio", []),
                    "score": r.get("score", 0),
                    "explanation": r.get("explanation", "")
                }
                for r in results[:3]  # Solo primeros 3 para no saturar
            ]
        }
        
    except Exception as e:
        return {
            "query": query,
            "status": "error",
            "error": str(e),
            "results": []
        }


def run_evaluation():
    """Ejecuta todas las pruebas y genera reporte."""
    print("=" * 80)
    print("🧪 EVALUACIÓN DE CALIDAD DEL BUSCADOR")
    print("=" * 80)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 API: {API_URL}")
    print(f"📊 Queries de prueba: {len(TEST_QUERIES)}")
    print()
    
    # Verificar API disponible
    try:
        health = requests.get(f"{API_URL}/health", timeout=5)
        if health.status_code == 200:
            data = health.json()
            print(f"✅ API disponible")
            print(f"   📦 Datasets: {data.get('datasets_count', 'N/A')}")
            print(f"   🧠 Modelo: {data.get('embedding_model', 'N/A')}")
            print(f"   🗄️  PostgreSQL: {data.get('pg_version', 'N/A')}")
            print()
        else:
            print(f"❌ API no disponible (HTTP {health.status_code})")
            return
    except Exception as e:
        print(f"❌ Error conectando a API: {e}")
        return
    
    # Ejecutar pruebas
    results = []
    total_time = 0
    
    for i, query_info in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/{len(TEST_QUERIES)}] Probando: '{query_info['query']}'")
        result = test_search(query_info)
        results.append(result)
        total_time += result.get("search_time_ms", 0)
        
        if result["status"] == "ok":
            print(f"   ✅ {result['returned_results']} resultados en {result['search_time_ms']:.0f}ms")
            print(f"   🎯 Precisión@5: {result['precision']:.0%} ({result['relevant_count']}/{result['returned_results']})")
            for r in result["results"][:2]:
                print(f"      📄 {r['title']}")
        else:
            print(f"   ❌ Error: {result.get('error', 'Unknown')}")
    
    # Generar resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 80)
    
    successful = [r for r in results if r["status"] == "ok"]
    errors = [r for r in results if r["status"] == "error"]
    
    # Métricas generales
    total_queries = len(TEST_QUERIES)
    success_rate = len(successful) / total_queries if total_queries > 0 else 0
    avg_precision = sum(r.get("precision", 0) for r in successful) / len(successful) if successful else 0
    avg_time = total_time / total_queries if total_queries > 0 else 0
    
    print(f"\n📈 Métricas Generales:")
    print(f"   ✅ Queries exitosas: {len(successful)}/{total_queries} ({success_rate:.0%})")
    print(f"   ❌ Queries con error: {len(errors)}/{total_queries}")
    print(f"   🎯 Precisión promedio@5: {avg_precision:.1%}")
    print(f"   ⏱️  Tiempo promedio: {avg_time:.0f}ms")
    
    # Precisión por categoría
    print(f"\n📊 Precisión por Categoría:")
    categories = {}
    for query_info, result in zip(TEST_QUERIES, results):
        if result["status"] == "ok":
            theme = query_info.get("expected_theme", "otros")
            if theme not in categories:
                categories[theme] = []
            categories[theme].append(result["precision"])
    
    for theme, precisions in sorted(categories.items()):
        avg = sum(precisions) / len(precisions)
        print(f"   🏷️  {theme:30s}: {avg:.0%} ({len(precisions)} queries)")
    
    # Calificación final
    print(f"\n🏆 CALIFICACIÓN FINAL:")
    if avg_precision >= 0.8:
        grade = "EXCELENTE 🌟"
    elif avg_precision >= 0.6:
        grade = "BUENO ✅"
    elif avg_precision >= 0.4:
        grade = "ACEPTABLE ⚠️"
    else:
        grade = "NECESITA MEJORAS ❌"
    
    print(f"   {grade}")
    print(f"   Precisión global: {avg_precision:.1%}")
    
    # Guardar resultados
    output_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "api_url": API_URL,
            "total_queries": total_queries,
            "successful_queries": len(successful),
            "error_queries": len(errors),
            "avg_precision": round(avg_precision, 4),
            "avg_time_ms": round(avg_time, 2),
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Resultados guardados en: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation()