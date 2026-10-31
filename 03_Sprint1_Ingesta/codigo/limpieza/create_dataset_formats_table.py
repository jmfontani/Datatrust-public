#!/usr/bin/env python3
"""
Crear tabla dataset_formats para formatos múltiples
====================================================

Crea una tabla separada para almacenar los formatos de cada dataset,
permitiendo relaciones 1:N (un dataset puede tener múltiples formatos).

Esto facilita queries como:
- SELECT * FROM datasets JOIN dataset_formats USING (dataset_id) WHERE format = 'CSV'
- SELECT format, COUNT(DISTINCT dataset_id) FROM dataset_formats GROUP BY format

Uso:
    python create_dataset_formats_table.py --commit

Autor: TFM - Buscador Semántico de Open Data
Fecha: 2026-06-10
"""

import argparse
import logging
import os
from typing import Dict, List, Optional

import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "dbname": "buscador",
    "user": "postgres",
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "host": os.getenv("POSTGRES_HOST", "host.docker.internal"),
    "port": "5432",
}

# Extensiones comunes
EXTENSION_TO_FORMAT = {
    ".csv": "CSV",
    ".xlsx": "XLSX",
    ".xls": "XLS",
    ".json": "JSON",
    ".xml": "XML",
    ".pdf": "PDF",
    ".zip": "ZIP",
    ".geojson": "GEOJSON",
    ".shp": "SHP",
    ".kml": "KML",
    ".kmz": "KMZ",
    ".gml": "GML",
    ".rdf": "RDF",
    ".turtle": "TURTLE",
    ".html": "HTML",
    ".htm": "HTML",
    ".txt": "TXT",
    ".tsv": "TSV",
    ".ods": "ODS",
    ".px": "PX",
    ".sdmx": "SDMX",
    ".gpx": "GPX",
    ".dbf": "DBF",
    ".prj": "PRJ",
    ".shx": "SHX",
}


def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Conectado a PostgreSQL")
        return conn
    except Exception as e:
        logger.error(f"Error conectando: {e}")
        raise


def extract_formats_from_url(url: str) -> List[str]:
    """Extraer todos los formatos detectables desde una URL."""
    if not url:
        return []

    formats = []
    url_lower = url.lower()

    # Servicios OGC
    if "service=wms" in url_lower:
        formats.append("WMS")
    if "service=wfs" in url_lower:
        formats.append("WFS")
    if "service=wcs" in url_lower:
        formats.append("WCS")
    if "service=wmts" in url_lower:
        formats.append("WMTS")

    # Buscar extensiones (puede haber múltiples en URLs complejas)
    for ext, fmt in EXTENSION_TO_FORMAT.items():
        if ext in url_lower:
            formats.append(fmt)

    # Eliminar duplicados manteniendo orden
    seen = set()
    unique_formats = []
    for f in formats:
        if f not in seen:
            seen.add(f)
            unique_formats.append(f)

    return unique_formats


def create_table(conn):
    """Crear tabla dataset_formats."""
    logger.info("Creando tabla dataset_formats...")

    create_query = """
    CREATE TABLE IF NOT EXISTS dataset_formats (
        id SERIAL PRIMARY KEY,
        dataset_id TEXT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
        format TEXT NOT NULL,
        format_source TEXT NOT NULL DEFAULT 'inferred',
        confidence FLOAT DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(dataset_id, format)
    );

    CREATE INDEX IF NOT EXISTS idx_dataset_formats_format
    ON dataset_formats(format);

    CREATE INDEX IF NOT EXISTS idx_dataset_formats_dataset_id
    ON dataset_formats(dataset_id);

    COMMENT ON TABLE dataset_formats IS 'Formatos disponibles para cada dataset (1:N)';
    COMMENT ON COLUMN dataset_formats.format_source IS 'inferred (URL), metadata (distributions.format), manual';
    COMMENT ON COLUMN dataset_formats.confidence IS '1.0 = seguro, 0.5 = posible, 0.1 = incierto';
    """

    with conn.cursor() as cur:
        cur.execute(create_query)
    conn.commit()
    logger.info("Tabla dataset_formats creada")


def populate_formats(conn, dry_run: bool = True, batch_size: int = 10000):
    """
    Poblar tabla dataset_formats extrayendo formatos de:
    1. distributions[].format (si no está vacío)
    2. distributions[].access_url (inferir desde URL)
    3. distributions[].download_url (inferir desde URL)
    """
    logger.info("Poblando tabla dataset_formats...")

    query = """
    SELECT
        dataset_id,
        raw_metadata->'distributions' as distributions
    FROM datasets
    WHERE raw_metadata->'distributions' IS NOT NULL
      AND jsonb_array_length(raw_metadata->'distributions') > 0
    """

    insert_query = """
    INSERT INTO dataset_formats (dataset_id, format, format_source, confidence)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (dataset_id, format) DO NOTHING
    """

    with conn.cursor() as fetch_cursor:
        fetch_cursor.execute(query)
        rows = fetch_cursor.fetchall()

    total_datasets = len(rows)
    total_formats = 0
    datasets_with_multiple = 0
    batch = []

    with conn.cursor() as insert_cursor:
        for dataset_id, distributions in rows:
            formats_found = []

            if distributions:
                for dist in distributions:
                    fmt_uri = dist.get("format", "")
                    if fmt_uri and fmt_uri.strip():
                        if "publications.europa.eu" in fmt_uri:
                            fmt = fmt_uri.rstrip("/").split("/")[-1]
                            formats_found.append((fmt, "metadata", 1.0))
                        else:
                            formats_found.append((fmt_uri.upper(), "metadata", 1.0))

                    access_url = dist.get("access_url", "")
                    if access_url:
                        inferred = extract_formats_from_url(access_url)
                        for fmt in inferred:
                            formats_found.append((fmt, "inferred_url", 0.9))

                    download_url = dist.get("download_url", "")
                    if download_url:
                        inferred = extract_formats_from_url(download_url)
                        for fmt in inferred:
                            formats_found.append((fmt, "inferred_url", 0.9))

            unique_formats = {}
            for fmt, source, confidence in formats_found:
                if fmt not in unique_formats:
                    unique_formats[fmt] = (source, confidence)

            if len(unique_formats) > 1:
                datasets_with_multiple += 1

            for fmt, (source, confidence) in unique_formats.items():
                if dry_run:
                    total_formats += 1
                else:
                    batch.append((dataset_id, fmt, source, confidence))
                    if len(batch) >= batch_size:
                        insert_cursor.executemany(insert_query, batch)
                        conn.commit()
                        total_formats += len(batch)
                        batch = []

        if not dry_run and batch:
            insert_cursor.executemany(insert_query, batch)
            conn.commit()
            total_formats += len(batch)

    logger.info(f"  Datasets procesados: {total_datasets:,}")
    logger.info(f"  Datasets con múltiples formatos: {datasets_with_multiple:,} ({datasets_with_multiple/total_datasets*100:.1f}%)")
    logger.info(f"  Total formatos insertados: {total_formats:,}")


def get_summary(conn) -> Dict:
    """Obtener resumen de la tabla dataset_formats."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT format, COUNT(DISTINCT dataset_id) as datasets, COUNT(*) as entries
            FROM dataset_formats
            GROUP BY format
            ORDER BY datasets DESC
        """)
        by_format = cur.fetchall()

        cur.execute("""
            SELECT
                CASE
                    WHEN num_formats = 1 THEN '1 formato'
                    WHEN num_formats = 2 THEN '2 formatos'
                    ELSE '3+ formatos'
                END as categoria,
                COUNT(*) as datasets
            FROM (
                SELECT dataset_id, COUNT(*) as num_formats
                FROM dataset_formats
                GROUP BY dataset_id
            ) t
            GROUP BY categoria
            ORDER BY categoria
        """)
        by_count = cur.fetchall()

        cur.execute("""
            SELECT COUNT(DISTINCT dataset_id) FROM dataset_formats
        """)
        total_with_formats = cur.fetchone()[0]

    return {
        "by_format": by_format,
        "by_count": by_count,
        "total_with_formats": total_with_formats,
    }


def main():
    parser = argparse.ArgumentParser(description="Crear y poblar dataset_formats")
    parser.add_argument("--commit", action="store_true", help="Ejecutar creación e inserción")
    parser.add_argument("--batch-size", type=int, default=10000, help="Tamaño de batch para inserts")
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("CREAR TABLA DATASET_FORMATS")
    logger.info("=" * 70)

    conn = get_db_connection()

    try:
        if args.commit:
            create_table(conn)

            logger.info("")
            logger.info("POBLANDO TABLA...")
            populate_formats(conn, dry_run=False, batch_size=args.batch_size)

            logger.info("")
            logger.info("RESUMEN:")
            summary = get_summary(conn)
            logger.info(f"  Total datasets con formatos: {summary['total_with_formats']:,}")
            logger.info("")
            logger.info("  Datasets por número de formatos:")
            for categoria, count in summary["by_count"]:
                logger.info(f"    {categoria}: {count:,}")
            logger.info("")
            logger.info("  Formatos detectados (top 15):")
            for fmt, datasets, entries in summary["by_format"][:15]:
                pct = datasets / 87676 * 100
                logger.info(f"    {fmt}: {datasets:,} datasets ({pct:.1f}%), {entries:,} entries")

        else:
            logger.info("")
            logger.info("DRY-RUN: usar --commit para crear y poblar")
            logger.info("")
            logger.info("ESTIMACIÓN (sin crear tabla):")
            populate_formats(conn, dry_run=True)

    finally:
        conn.close()
        logger.info("Conexión cerrada")


if __name__ == "__main__":
    main()
