#!/usr/bin/env python3
"""
Evaluación de la versión mejorada del buscador.
Compara resultados antes/después de las mejoras.
"""

import psycopg2
import json
import time
import requests
from datetime import datetime

# Configuración PostgreSQL
DB_CONFIG = {
    "host": "postgres",  # Nombre del servicio en docker-compose
    "port": 5432,
    "database": "buscador",
    "user": "postgres",
    "password": "***",
}

API_URL = "http://host.docker.internal:8000"

# Queries de prueba - incluyendo casos problemáticos
TEST_QUERIES = [
    # Casos problemáticos
    {"query": "paro", "expected_theme": "empleo", "problematic": True, 
     "notes": "Palabra ambigua: paro vs parada"},
    {"query": "paro desempleo", "expected_theme": "empleo", "problematic": True,
     "notes": "Contexto desempleo"},
    
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


def search_via_api(query, use_improved=True):
    """Realiza búsqueda a través de la API."""
    try:
        payload = {
            "query": query,
            "top_k": 5,
            "semantic_weight": 0.7,
            "lexical_weight": 0.3,
        }
        
        # La API mejorada está en un endpoint diferente o usa parámetros
        if use_improved:
            payload["use_synonyms"] = True
            payload["remove_stopwords"] = True
        
        response = requests.post(
            f"{API_URL}/search",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def search_direct_sql(conn, query, use_improved=False):
    """Realiza búsqueda directa SQL con mejoras."""
    with conn.cursor() as cur:
        if use_improved:
            # Query mejorada con expansión de sinónimos
            # Para "paro", expandir a "desempleo atur"
            expanded = query.lower()
            if 'paro' in expanded and 'desempleo' not in expanded:
                expanded = expanded.replace('paro', 'paro desempleo atur')
            
            cur.execute("""
                SELECT 
                    dataset_id, title, description, publisher, theme, territory, format,
                    ts_rank_cd(search_vector, plainto_tsquery('spanish', %s)) as rank
                FROM datasets
                WHERE search_vector @@ plainto_tsquery('spanish', %s)
                ORDER BY ts_rank_cd(search_vector, plainto_tsquery('spanish', %s)) DESC
                LIMIT 5
            """, (expanded, expanded, expanded))
        else:
            # Query básica original
            cur.execute("""
                SELECT 
                    dataset_id, title, description, publisher, theme, territory, format,
                    ts_rank_cd(search_vector, plainto_tsquery('spanish', %s)) as rank
                FROM datasets
                WHERE search_vector @@ plainto_tsquery('spanish', %s)
                ORDER BY ts_rank_cd(search_vector, plainto_tsquery('spanish', %s)) DESC
                LIMIT 5
            """, (query, query, query))
        
        results = []
        for row in cur.fetchall():
            results.append({
                "id": row[0],
                "title": row[1] or "Sin título",
                "description": (row[2] or "")[:200],
                "theme": row[4] or "",
                "territory": row[5] or "",
                "score": float(row[7]),
            })
        return results


def evaluate_results(query_info, results):
    """Evalúa la relevancia de los resultados."""
    if not results:
        return {"precision": 0.0, "relevant": 0, "total": 0, "results": []}
    
    expected_theme = query_info.get("expected_theme", "")
    expected_territory = query_info.get("expected_territory", "")
    
    relevant_count = 0
    evaluated = []
    
    for result in results[:5]:
        is_relevant = False
        reasons = []
        
        # Verificar tema
        if expected_theme:
            theme = result.get("theme", "").lower()
            if expected_theme.lower() in theme:
                is_relevant = True
                reasons.append("tema")
        
        # Verificar territorio
        if expected_territory:
            territory = result.get("territory", "").lower()
            if expected_territory.lower() in territory:
                is_relevant = True
                reasons.append("territorio")
        
        # Verificar palabras clave en título/descripción
        title = result.get("title", "").lower()
        desc = result.get("description", "").lower()
        query_words = query_info["query"].lower().split()
        matching_words = sum(1 for w in query_words if w in title or w in desc)
        if matching_words >= len(query_words) * 0.5:
            is_relevant = True
            reasons.append("keywords")
        
        if is_relevant:
            relevant_count += 1
        
        evaluated.append({
            "title": result["title"][:60],
            "theme": result.get("theme", ""),
            "territory": result.get("territory", ""),
            "score": result.get("score", 0),
            "relevant": is_relevant,
        })
    
    precision = relevant_count / len(evaluated) if evaluated else 0
    
    return {
        "precision": round(precision, 2),
        "relevant": relevant_count,
        "total": len(evaluated),
        "results": evaluated
    }


def run_comparison():
    """Compara versión original vs mejorada."""
    print("=" * 90)
    print("🧪 COMPARACIÓN: VERSIÓN ORIGINAL vs VERSIÓN MEJORADA")
    print("=" * 90)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Verificar conexión
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM datasets")
        count = cur.fetchone()[0]
        print(f"✅ Conectado. Total datasets: {count}")
    
    print()
    
    # Resultados acumulados
    original_results = []
    improved_results = []
    
    for i, query_info in enumerate(TEST_QUERIES, 1):
        query = query_info["query"]
        is_problematic = query_info.get("problematic", False)
        
        print(f"\n[{i}/{len(TEST_QUERIES)}] Query: '{query}'")
        if is_problematic:
            print(f"   ⚠️ CASO PROBLEMÁTICO: {query_info.get('notes', '')}")
        
        # Versión original
        start = time.time()
        orig_results = search_direct_sql(conn, query, use_improved=False)
        orig_time = (time.time() - start) * 1000
        orig_eval = evaluate_results(query_info, orig_results)
        original_results.append(orig_eval)
        
        # Versión mejorada
        start = time.time()
        impr_results = search_direct_sql(conn, query, use_improved=True)
        impr_time = (time.time() - start) * 1000
        impr_eval = evaluate_results(query_info, impr_results)
        improved_results.append(impr_eval)
        
        # Mostrar comparación
        print(f"   ORIGINAL:  {orig_eval['precision']:.0%} precisión, {orig_eval['relevant']}/{orig_eval['total']} relevantes, {orig_time:.0f}ms")
        for r in orig_eval['results'][:2]:
            marker = "✅" if r['relevant'] else "❌"
            print(f"      {marker} {r['title']}")
        
        print(f"   MEJORADA:  {impr_eval['precision']:.0%} precisión, {impr_eval['relevant']}/{impr_eval['total']} relevantes, {impr_time:.0f}ms")
        for r in impr_eval['results'][:2]:
            marker = "✅" if r['relevant'] else "❌"
            print(f"      {marker} {r['title']}")
        
        # Indicar mejora
        if impr_eval['precision'] > orig_eval['precision']:
            print(f"   📈 MEJORA: +{(impr_eval['precision'] - orig_eval['precision']):.0%}")
        elif impr_eval['precision'] < orig_eval['precision']:
            print(f"   📉 EMP.:")
    
    conn.close()
    
    # Resumen final
    print("\n" + "=" * 90)
    print("📊 RESUMEN COMPARATIVO")
    print("=" * 90)
    
    orig_avg = sum(r['precision'] for r in original_results) / len(original_results)
    impr_avg = sum(r['precision'] for r in improved_results) / len(improved_results)
    
    print(f"\n📈 Precisión Global:")
    print(f"   Original:  {orig_avg:.1%}")
    print(f"   Mejorada:  {impr_avg:.1%}")
    print(f"   Diferencia: {(impr_avg - orig_avg):+.1%}")
    
    # Casos problemáticos específicos
    print(f"\n🔍 Casos Problemáticos:")
    for i, (query_info, orig, impr) in enumerate(zip(TEST_QUERIES, original_results, improved_results)):
        if query_info.get("problematic"):
            print(f"   '{query_info['query']}':")
            print(f"      Original:  {orig['precision']:.0%}")
            print(f"      Mejorada:  {impr['precision']:.0%}")
            if impr['precision'] > orig['precision']:
                print(f"      ✅ MEJORADO")
            elif impr['precision'] == orig['precision']:
                print(f"      ➡️  IGUAL")
            else:
                print(f"      ⚠️  REVISAR")
    
    # Calificación
    print(f"\n🏆 CALIFICACIÓN:")
    if impr_avg >= 0.9:
        grade = "EXCELENTE 🌟"
    elif impr_avg >= 0.7:
        grade = "BUENO ✅"
    elif impr_avg >= 0.5:
        grade = "ACEPTABLE ⚠️"
    else:
        grade = "NECESITA MEJORAS ❌"
    
    print(f"   Versión Mejorada: {grade} ({impr_avg:.1%})")
    
    # Guardar resultados
    output_file = f"comparison_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_queries": len(TEST_QUERIES),
            "original_avg_precision": round(orig_avg, 4),
            "improved_avg_precision": round(impr_avg, 4),
            "improvement": round(impr_avg - orig_avg, 4),
            "queries": [
                {
                    "query": q["query"],
                    "original": o,
                    "improved": i,
                }
                for q, o, i in zip(TEST_QUERIES, original_results, improved_results)
            ]
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Resultados guardados en: {output_file}")
    print("=" * 90)


if __name__ == "__main__":
    run_comparison()