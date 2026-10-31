#!/usr/bin/env python3
"""
Actualiza los campos de la tabla datasets desde raw_metadata.
Los datos originales tienen title_es/description_es pero la tabla espera title/description.
"""
import psycopg2
from tqdm import tqdm
import time

# Configuración
DB_CONFIG = {
    'host': '172.17.0.1',
    'port': 5432,
    'database': 'buscador',
    'user': 'postgres',
    'password': 'postgres'
}

BATCH_SIZE = 1000

def update_metadata():
    """Actualiza los campos de la tabla datasets desde raw_metadata."""
    
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()
    
    print("🔍 Verificando estructura actual...")
    
    # Verificar cuántos registros necesitan actualización
    cur.execute("""
        SELECT COUNT(*) FROM datasets 
        WHERE title = '' OR title IS NULL;
    """)
    total_to_update = cur.fetchone()[0]
    print(f"📊 Registros con título vacío: {total_to_update}")
    
    if total_to_update == 0:
        print("✅ Todos los registros tienen título. No se necesita actualización.")
        return
    
    # Obtener todos los IDs que necesitan actualización
    cur.execute("""
        SELECT id FROM datasets 
        WHERE title = '' OR title IS NULL;
    """)
    ids_to_update = [row[0] for row in cur.fetchall()]
    
    print(f"📝 Actualizando {len(ids_to_update)} registros...")
    
    # Actualizar en batches
    updated = 0
    errors = 0
    start_time = time.time()
    
    for i in tqdm(range(0, len(ids_to_update), BATCH_SIZE), desc="Actualizando"):
        batch_ids = ids_to_update[i:i+BATCH_SIZE]
        
        try:
            # Actualizar usando raw_metadata
            for dataset_id in batch_ids:
                cur.execute("""
                    UPDATE datasets 
                    SET 
                        title = COALESCE(NULLIF(raw_metadata->>'title_es', ''), 
                                        NULLIF(raw_metadata->>'title_en', ''), 
                                        'Sin título'),
                        description = COALESCE(NULLIF(raw_metadata->>'description_es', ''), 
                                               NULLIF(raw_metadata->>'description_en', ''), 
                                               ''),
                        theme = COALESCE(NULLIF(raw_metadata->>'themes', ''), ''),
                        theme_label = COALESCE(NULLIF(raw_metadata->>'theme_labels', ''), ''),
                        territory = COALESCE(NULLIF(raw_metadata->>'spatial_name', ''), ''),
                        territory_label = COALESCE(NULLIF(raw_metadata->>'spatial_name_original', ''), ''),
                        publisher = COALESCE(NULLIF(raw_metadata->>'publisher_name', ''), ''),
                        publisher_id = COALESCE(NULLIF(raw_metadata->>'publisher_uri', ''), ''),
                        format = COALESCE(NULLIF(raw_metadata->>'formats', ''), ''),
                        language = COALESCE(NULLIF(raw_metadata->>'language', ''), 'es'),
                        license = COALESCE(NULLIF(raw_metadata->>'license_name', ''), ''),
                        frequency = COALESCE(NULLIF(raw_metadata->>'accrual_periodicity', ''), ''),
                        temporal_coverage = COALESCE(NULLIF(raw_metadata->>'temporal_coverage', ''), ''),
                        url = COALESCE(NULLIF(raw_metadata->>'primary_url', ''), 
                                      NULLIF(raw_metadata->>'source_url', ''), '')
                    WHERE id = %s;
                """, (dataset_id,))
            
            conn.commit()
            updated += len(batch_ids)
            
        except Exception as e:
            conn.rollback()
            errors += len(batch_ids)
            print(f"\n❌ Error en batch: {e}")
            continue
    
    elapsed = time.time() - start_time
    print(f"\n✅ Actualización completada:")
    print(f"   - Registros actualizados: {updated}")
    print(f"   - Errores: {errors}")
    print(f"   - Tiempo: {elapsed:.1f}s ({updated/elapsed:.1f} registros/s)")
    
    # Verificar resultado
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE title = '' OR title IS NULL) as empty_titles,
            COUNT(*) FILTER (WHERE title != '' AND title IS NOT NULL) as filled_titles
        FROM datasets;
    """)
    row = cur.fetchone()
    print(f"\n📊 Verificación:")
    print(f"   - Títulos vacíos: {row[0]}")
    print(f"   - Títulos llenos: {row[1]}")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    update_metadata()
