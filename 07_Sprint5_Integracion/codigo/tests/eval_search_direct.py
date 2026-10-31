#!/usr/bin/env python3
"""
Evaluación directa de calidad del buscador.
Se conecta directamente a PostgreSQL sin depender de la API HTTP.
"""

import psycopg2
import json
import time
import ast
from datetime import datetime

# Configuración PostgreSQL
DB_CONFIG = {
    "host": "host.docker.internal",
    "port": 5432,
    "database": "buscador",
    "user": "postgres",
    "password": "postgres",
}

# Queries de prueba
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


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def search_lexical(conn, query, top_k=5):
    """Búsqueda léxica con TSVECTOR."""
    with conn.cursor() as cur:
        # Usar plainto_tsquery para AND lógico
        cur.execute("""
            SELECT 
                dataset_id, title, description, publisher, theme, territory, format,
                ts_rank_cd(search_vector, plainto_tsquery('spanish', %s)) as rank
            FROM datasets
            WHERE search_vector @@ plainto_tsquery('spanish', %s)
            ORDER BY ts_rank_cd(search_vector, plainto_tsquery('spanish', %s)) DESC
            LIMIT %s
        """, (query, query, query, top_k))
        
        results = []
        for row in cur.fetchall():
            results.append({
                "id": row[0],
                "title": row[1] or "Sin título",
                "description": (row[2] or "")[:200],
                "publisher": row[3] or "",
                "theme": row[4] or "",
                "territory": row[5] or "",
                "format": row[6] or "",
                "score": float(row[7]),
                "type": "lexical"
            })
        return results


def search_semantic_dummy(conn, query, top_k=5):
    """Búsqueda semántica simulada (porque no tenemos el modelo en este entorno)."""
    # Simplemente buscar palabras similares
    words = query.lower().split()
    
    with conn.cursor() as cur:
        # Buscar datasets que contengan palabras similares
        conditions = []
        params = []
        for word in words:
            conditions.append("(title ILIKE %s OR description ILIKE %s)")
            params.extend([f"%{word}%", f"%{word}%"])
        
        where_clause = " OR ".join(conditions)
        
        cur.execute(f"""
            SELECT 
                dataset_id, title, description, publisher, theme, territory, format,
                0.5 as similarity
            FROM datasets
            WHERE {where_clause}
            LIMIT %s
        """, params + [top_k])
        
        results = []
        for row in cur.fetchall():
            results.append({
                "id": row[0],
                "title": row[1] or "Sin título",
                "description": (row[2] or "")[:200],
                "publisher": row[3] or "",
                "theme": row[4] or "",
                "territory": row[5] or "",
                "format": row[6] or "",
                "score": float(row[7]),
                "type": "semantic"
            })
        return results


def evaluate_query(conn, query_info):
    """Evalúa una query y calcula precisión."""
    query = query_info["query"]
    start = time.time()
    
    # Realizar búsqueda léxica
    results = search_lexical(conn, query, top_k=10)
    
    elapsed = (time.time() - start) * 1000
    
    if not results:
        return {
            "query": query,
            "status": "no_results",
            "total_results": 0,
            "precision": 0.0,
            "time_ms": elapsed,
            "results": []
        }
    
    # Evaluar relevancia
    relevant_count = 0
    expected_theme = query_info.get("expected_theme", "")
    expected_territory = query_info.get("expected_territory", "")
    
    evaluated_results = []
    for result in results[:5]:  # Evaluar top 5
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
        
        # Verificar palabras clave
        title = result.get("title", "").lower()
        desc = result.get("description", "").lower()
        query_words = query.lower().split()
        matching_words = sum(1 for w in query_words if w in title or w in desc)
        if matching_words >= len(query_words) * 0.5:
            is_relevant = True
            reasons.append("keywords")
        
        if is_relevant:
            relevant_count += 1
        
        evaluated_results.append({
            "title": result["title"][:60],
            "theme": result["theme"],
            "territory": result["territory"],
            "score": result["score"],
            "relevant": is_relevant,
            "reasons": reasons
        })
    
    precision = relevant_count / len(evaluated_results) if evaluated_results else 0
    
    return {
        "query": query,
        "status": "ok",
        "total_results": len(results),
        "precision": round(precision, 2),
        "relevant_count": relevant_count,
        "time_ms": round(elapsed, 2),
        "results": evaluated_results
    }


def run_evaluation():
    print("=" * 80)
    print("🧪 EVALUACIÓN DE CALIDAD DEL BUSCADOR (Directa a PostgreSQL)")
    print("=" * 80)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🗄️  Base de datos: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"📊 Queries de prueba: {len(TEST_QUERIES)}")
    print()
    
    conn = get_db_connection()
    
    # Verificar conexión
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM datasets")
        count = cur.fetchone()[0]
        print(f"✅ Conectado. Total datasets: {count}")
        
        # Verificar pgvector
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        has_pgvector = cur.fetchone() is not None
        print(f"{'✅' if has_pgvector else '❌'} pgvector: {'disponible' if has_pgvector else 'no disponible'}")
        
        # Verificar embeddings
        cur.execute("SELECT COUNT(*) FROM datasets WHERE embedding IS NOT NULL")
        with_emb = cur.fetchone()[0]
        print(f"📊 Datasets con embedding: {with_emb} ({with_emb/count*100:.1f}%)")
    
    print()
    
    # Ejecutar pruebas
    results = []
    total_time = 0
    
    for i, query_info in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/{len(TEST_QUERIES)}] Probando: '{query_info['query']}'")
        result = evaluate_query(conn, query_info)
        results.append(result)
        total_time += result.get("time_ms", 0)
        
        if result["status"] == "ok":
            print(f"   ✅ {result['total_results']} resultados en {result['time_ms']:.0f}ms")
            print(f"   🎯 Precisión@5: {result['precision']:.0%} ({result['relevant_count']}/5)")
            for r in result["results"][:2]:
                marker = "✅" if r['relevant'] else "❌"
                print(f"      {marker} {r['title']}")
        else:
            print(f"   ❌ Sin resultados")
    
    conn.close()
    
    # Generar resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 80)
    
    successful = [r for r in results if r["status"] == "ok"]
    no_results = [r for r in results if r["status"] == "no_results"]
    
    total_queries = len(TEST_QUERIES)
    success_rate = len(successful) / total_queries if total_queries > 0 else 0
    avg_precision = sum(r.get("precision", 0) for r in successful) / len(successful) if successful else 0
    avg_time = total_time / total_queries if total_queries > 0 else 0
    
    print(f"\n📈 Métricas Generales:")
    print(f"   ✅ Queries con resultados: {len(successful)}/{total_queries} ({success_rate:.0%})")
    print(f"   ⚠️  Queries sin resultados: {len(no_results)}/{total_queries}")
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
    output_file = f"eval_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "database": DB_CONFIG,
            "total_queries": total_queries,
            "successful_queries": len(successful),
            "no_results_queries": len(no_results),
            "avg_precision": round(avg_precision, 4),
            "avg_time_ms": round(avg_time, 2),
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Resultados guardados en: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation()