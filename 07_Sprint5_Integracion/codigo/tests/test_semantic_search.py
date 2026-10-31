"""
Test de búsqueda semántica usando pgvector y embeddings pre-calculados
"""
import psycopg2
import psycopg2.extras
import numpy as np
import time
import sys

# Conexión a la base de datos
DB_CONFIG = {
    'host': '172.17.0.1',
    'port': '5432',
    'database': 'buscador',
    'user': 'postgres',
    'password': 'postgres'
}

def get_connection():
    """Establecer conexión con la base de datos."""
    return psycopg2.connect(**DB_CONFIG)

def normalize_vector(v):
    """Normalizar vector a longitud unitaria."""
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm

def generate_random_query_embedding():
    """Generar un embedding aleatorio normalizado (384 dimensiones)."""
    vec = np.random.randn(384).astype(np.float32)
    return normalize_vector(vec)

def test_cosine_similarity():
    """Probar búsqueda por similitud coseno usando pgvector."""
    print("=" * 60)
    print("TEST: Búsqueda Semántica - Similitud Coseno (pgvector)")
    print("=" * 60)
    
    query_vec = generate_random_query_embedding()
    print(f"\nVector de consulta generado: 384 dimensiones")
    print(f"Primera dimensión: {query_vec[0]:.6f}")
    print(f"Norma del vector: {np.linalg.norm(query_vec):.6f}")
    
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Test 1: Buscar datasets similares
        print("\n--- Test 1: Búsqueda por similitud coseno ---")
        start_time = time.time()
        
        cur.execute("""
            SELECT 
                dataset_id,
                title,
                description,
                theme,
                territory,
                publisher,
                embedding <=> %s::vector AS distance,
                1 - (embedding <=> %s::vector) AS similarity
            FROM datasets
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT 10
        """, (query_vec.tolist(), query_vec.tolist(), query_vec.tolist()))
        
        results = cur.fetchall()
        elapsed = time.time() - start_time
        
        print(f"\n⏱️  Tiempo de respuesta: {elapsed:.3f}s")
        print(f"📊 Resultados encontrados: {len(results)}")
        
        print(f"\n{'='*60}")
        print("TOP 10 RESULTADOS (con embedding aleatorio):")
        print(f"{'='*60}")
        
        for i, row in enumerate(results, 1):
            print(f"\n{i}. [{row['dataset_id']}]")
            print(f"   Título: {row['title'][:80] if row['title'] else 'N/A'}")
            print(f"   Distancia coseno: {row['distance']:.4f}")
            print(f"   Similitud: {row['similarity']:.4f}")
            print(f"   Tema: {row['theme'][:50] if row['theme'] else 'N/A'}")
            print(f"   Territorio: {row['territory'][:40] if row['territory'] else 'N/A'}")
        
        # Test 2: Verificar plan de ejecución
        print(f"\n{'='*60}")
        print("--- Test 2: Verificar plan de ejecución (EXPLAIN) ---")
        print(f"{'='*60}")
        
        cur.execute("""
            EXPLAIN (ANALYZE, BUFFERS)
            SELECT dataset_id, title
            FROM datasets
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT 10
        """, (query_vec.tolist(),))
        
        plan = cur.fetchall()
        print("\nPlan de ejecución:")
        for line in plan:
            print(f"   {line['QUERY PLAN']}")
        
        # Test 3: Verificar índice HNSW
        print(f"\n{'='*60}")
        print("--- Test 3: Verificar índice HNSW ---")
        print(f"{'='*60}")
        
        cur.execute("""
            SELECT 
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = 'datasets' 
            AND indexname LIKE '%hnsw%'
        """)
        
        indexes = cur.fetchall()
        if indexes:
            print(f"\n✅ Índice HNSW encontrado:")
            for idx in indexes:
                print(f"   Nombre: {idx['indexname']}")
                print(f"   Definición: {idx['indexdef'][:80]}...")
        else:
            print(f"\n⚠️ No se encontró índice HNSW")
        
        # Test 4: Performance con diferentes límites
        print(f"\n{'='*60}")
        print("--- Test 4: Performance con diferentes tamaños ---")
        print(f"{'='*60}")
        
        for limit in [5, 10, 50, 100]:
            start = time.time()
            cur.execute("""
                SELECT dataset_id, title, embedding <=> %s::vector AS distance
                FROM datasets
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_vec.tolist(), query_vec.tolist(), limit))
            
            cur.fetchall()
            elapsed = time.time() - start
            print(f"   Top {limit:3d}: {elapsed:.4f}s")
        
        print(f"\n{'='*60}")
        print("✅ TESTS DE BÚSQUEDA SEMÁNTICA COMPLETADOS")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    test_cosine_similarity()
