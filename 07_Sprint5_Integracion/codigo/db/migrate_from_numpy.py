#!/usr/bin/env python3
"""
Migración de datos desde NumPy/JSONL a PostgreSQL + pgvector
Fase 07: Sprint 5 - Integración y Despliegue

Uso:
    python migrate_from_numpy.py --verify-only    # Solo verificar conexión
    python migrate_from_numpy.py --dry-run        # Simular sin escribir
    python migrate_from_numpy.py                # Migración completa
"""

import psycopg2
import psycopg2.extras
import numpy as np
import json
import sys
import time
import argparse
from pathlib import Path

# Configuración de rutas (ajustar según estructura del proyecto)
BASE_DIR = Path(__file__).parent.parent.parent.parent  # Hasta raíz del proyecto
DATA_DIR = BASE_DIR / "03_Sprint1_Ingesta" / "datos" / "processed"
EMBEDDINGS_DIR = BASE_DIR / "04_Sprint2_Embeddings" / "datos" / "processed"
INDICES_DIR = BASE_DIR / "04_Sprint2_Embeddings" / "datos" / "indices"

# Configuración de PostgreSQL
DB_CONFIG = {
    'host': '172.17.0.1',  # O 'localhost' si es local
    'port': '5432',
    'database': 'buscador',
    'user': 'postgres',
    'password': 'postgres'
}

BATCH_SIZE = 1000  # Registros por batch para evitar timeouts


def get_db_connection():
    """Establecer conexión con PostgreSQL."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(f"✅ Conectado a PostgreSQL en {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        return conn
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        sys.exit(1)


def check_data_files():
    """Verificar que existen los archivos de datos necesarios."""
    required_files = {
        'datasets_clean.jsonl': DATA_DIR / "datasets_clean.jsonl",
        'embeddings.npy': EMBEDDINGS_DIR / "embeddings.npy",
        'id_position_map.json': INDICES_DIR / "id_position_map.json",
    }
    
    print("\n📁 Verificando archivos de datos...")
    missing = []
    for name, path in required_files.items():
        if path.exists():
            size = path.stat().st_size / (1024*1024)  # MB
            print(f"   ✅ {name}: {size:.1f} MB")
        else:
            print(f"   ❌ {name}: NO ENCONTRADO")
            missing.append(name)
    
    if missing:
        print(f"\n❌ Faltan archivos: {', '.join(missing)}")
        print(f"   Buscando en: {DATA_DIR}")
        # Listar archivos disponibles
        if DATA_DIR.exists():
            print(f"   Archivos en {DATA_DIR}:")
            for f in DATA_DIR.iterdir():
                print(f"      - {f.name}")
        sys.exit(1)
    
    return required_files


def load_embeddings():
    """Cargar embeddings de NumPy."""
    print("\n🔄 Cargando embeddings...")
    start = time.time()
    embeddings = np.load(EMBEDDINGS_DIR / "embeddings.npy")
    elapsed = time.time() - start
    print(f"   ✅ Embeddings cargados: {embeddings.shape} en {elapsed:.2f}s")
    return embeddings


def load_id_mapping():
    """Cargar mapeo de ID a posición."""
    print("\n🔄 Cargando mapeo de IDs...")
    with open(INDICES_DIR / "id_position_map.json", 'r', encoding='utf-8') as f:
        id_position_map = json.load(f)
    print(f"   ✅ Mapeo cargado: {len(id_position_map)} datasets")
    return id_position_map


def load_datasets_jsonl():
    """Cargar datasets desde JSONL."""
    print("\n🔄 Cargando datasets desde JSONL...")
    datasets = []
    jsonl_path = DATA_DIR / "datasets_clean.jsonl"
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                datasets.append(json.loads(line))
    
    print(f"   ✅ Datasets cargados: {len(datasets)}")
    return datasets


def get_field_value(dataset, field, max_length=None):
    """Extraer valor de campo con manejo seguro de tipos y longitudes."""
    value = dataset.get(field)
    if value is None:
        return None
    
    # Convertir lista a string si es necesario
    if isinstance(value, list):
        value = ', '.join(str(v) for v in value)
    else:
        value = str(value)
    
    # Truncar si excede longitud máxima
    if max_length and len(value) > max_length:
        value = value[:max_length]
    
    return value


def migrate_batch(conn, datasets_batch, embeddings, id_position_map, dry_run=False):
    """Migrar un batch de datasets a PostgreSQL."""
    cursor = conn.cursor()
    
    inserted = 0
    errors = 0
    
    for dataset in datasets_batch:
        try:
            dataset_id = dataset.get('id') or dataset.get('dataset_id')
            if not dataset_id:
                errors += 1
                continue
            
            # Obtener embedding correspondiente
            position = id_position_map.get(dataset_id)
            if position is None or position >= len(embeddings):
                errors += 1
                continue
            
            embedding = embeddings[position].tolist()
            
            # Extraer campos con manejo seguro
            title = get_field_value(dataset, 'title_es', 1000) or get_field_value(dataset, 'title_en', 1000)
            description = get_field_value(dataset, 'description_es', 5000) or get_field_value(dataset, 'description_en', 5000)
            themes = get_field_value(dataset, 'themes', 255)
            territory = get_field_value(dataset, 'spatial_name', 255)
            formats = get_field_value(dataset, 'formats', 50)
            
            if dry_run:
                inserted += 1
                continue
            
            # Insertar en PostgreSQL
            cursor.execute("""
                INSERT INTO datasets (
                    dataset_id, title, description, publisher, 
                    theme, territory, format, language, license,
                    embedding, raw_metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s)
                ON CONFLICT (dataset_id) DO NOTHING
            """, (
                dataset_id,
                title,
                description,
                get_field_value(dataset, 'publisher_name', 500),
                themes,
                territory,
                formats,
                get_field_value(dataset, 'language', 10),
                get_field_value(dataset, 'license_name', 255),
                embedding,
                json.dumps(dataset)
            ))
            
            inserted += 1
            
        except Exception as e:
            errors += 1
            print(f"   ⚠️ Error en dataset {dataset_id}: {e}")
    
    if not dry_run:
        conn.commit()
    
    cursor.close()
    return inserted, errors


def update_search_vectors(conn):
    """Actualizar search_vector (TSVECTOR) para búsqueda léxica."""
    print("\n🔄 Actualizando índices de búsqueda léxica...")
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE datasets 
            SET search_vector = 
                setweight(to_tsvector('spanish', COALESCE(title, '')), 'A') ||
                setweight(to_tsvector('spanish', COALESCE(description, '')), 'B')
            WHERE search_vector IS NULL
        """)
        conn.commit()
        print(f"   ✅ {cursor.rowcount} registros actualizados con TSVECTOR")
    except Exception as e:
        print(f"   ❌ Error actualizando TSVECTOR: {e}")
    finally:
        cursor.close()


def verify_migration(conn):
    """Verificar que la migración se completó correctamente."""
    print("\n🔍 Verificando migración...")
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    checks = [
        ("SELECT COUNT(*) as count FROM datasets", "Total datasets"),
        ("SELECT COUNT(*) as count FROM datasets WHERE embedding IS NOT NULL", "Con embeddings"),
        ("SELECT COUNT(*) as count FROM datasets WHERE title IS NOT NULL AND title != ''", "Con título"),
        ("SELECT COUNT(*) as count FROM datasets WHERE search_vector IS NOT NULL", "Con search_vector"),
    ]
    
    for query, label in checks:
        cursor.execute(query)
        result = cursor.fetchone()
        print(f"   {label}: {result['count']:,}")
    
    # Verificar tamaño de la tabla
    cursor.execute("""
        SELECT pg_size_pretty(pg_total_relation_size('datasets')) as size
    """)
    size = cursor.fetchone()
    print(f"   Tamaño tabla: {size['size']}")
    
    cursor.close()


def main():
    parser = argparse.ArgumentParser(description='Migrar datos de NumPy a PostgreSQL')
    parser.add_argument('--verify-only', action='store_true', help='Solo verificar conexión')
    parser.add_argument('--dry-run', action='store_true', help='Simular sin escribir')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE, help='Tamaño del batch')
    args = parser.parse_args()
    
    print("=" * 60)
    print("MIGRACIÓN: NumPy → PostgreSQL + pgvector")
    print("=" * 60)
    
    # Conectar a PostgreSQL
    conn = get_db_connection()
    
    if args.verify_only:
        print("\n✅ Conexión verificada correctamente")
        conn.close()
        return
    
    # Verificar archivos
    check_data_files()
    
    # Cargar datos
    embeddings = load_embeddings()
    id_position_map = load_id_mapping()
    datasets = load_datasets_jsonl()
    
    # Verificar consistencia
    print(f"\n📊 Consistencia de datos:")
    print(f"   Datasets en JSONL: {len(datasets)}")
    print(f"   Embeddings: {len(embeddings)}")
    print(f"   IDs en mapeo: {len(id_position_map)}")
    
    if len(datasets) != len(embeddings):
        print("⚠️ ADVERTENCIA: Número de datasets != embeddings")
    
    # Migración por batches
    mode = "SIMULACIÓN" if args.dry_run else "MIGRACIÓN REAL"
    print(f"\n🚀 Iniciando {mode}...")
    
    total_inserted = 0
    total_errors = 0
    start_time = time.time()
    
    for i in range(0, len(datasets), args.batch_size):
        batch = datasets[i:i + args.batch_size]
        batch_num = i // args.batch_size + 1
        
        inserted, errors = migrate_batch(conn, batch, embeddings, id_position_map, args.dry_run)
        total_inserted += inserted
        total_errors += errors
        
        if batch_num % 10 == 0 or batch_num == 1:
            elapsed = time.time() - start_time
            rate = total_inserted / elapsed if elapsed > 0 else 0
            print(f"   Batch {batch_num}: {total_inserted:,} insertados, {total_errors} errores ({rate:.0f} reg/s)")
    
    total_time = time.time() - start_time
    print(f"\n✅ Migración completada:")
    print(f"   Insertados: {total_inserted:,}")
    print(f"   Errores: {total_errors}")
    print(f"   Tiempo: {total_time:.1f}s")
    print(f"   Velocidad: {total_inserted/total_time:.0f} registros/s")
    
    if not args.dry_run:
        # Actualizar search vectors
        update_search_vectors(conn)
        
        # Verificar migración
        verify_migration(conn)
    
    conn.close()
    print("\n🏁 Proceso finalizado")


if __name__ == "__main__":
    main()
