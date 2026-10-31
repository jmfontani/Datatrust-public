#!/usr/bin/env python3
"""
Actualizar campo `format` desde distributions (access_url)
===========================================================

El formato está en raw_metadata->distributions[].format pero está vacío
para el 98.5% de datasets. Sin embargo, distributions[].access_url contiene
la URL de descarga que podemos usar para inferir el formato.

Uso:
    python update_format_from_access_url.py --commit   # Actualizar BD

Autor: TFM - Buscador Semántico de Open Data
Fecha: 2026-06-10
"""

import argparse
import logging
import os
import re
from typing import Optional

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
    ".wms": "WMS",
    ".wfs": "WFS",
}


def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Conectado a PostgreSQL")
        return conn
    except Exception as e:
        logger.error(f"Error conectando: {e}")
        raise


def extract_format_from_url(url: str) -> Optional[str]:
    """Extraer formato desde URL de descarga."""
    if not url:
        return None

    url_lower = url.lower().split("?")[0]

    # Servicios OGC
    if "service=wms" in url_lower:
        return "WMS"
    if "service=wfs" in url_lower:
        return "WFS"
    if "service=wcs" in url_lower:
        return "WCS"

    # Buscar extensiones
    for ext, fmt in sorted(EXTENSION_TO_FORMAT.items(), key=lambda x: len(x[0]), reverse=True):
        if url_lower.endswith(ext):
            return fmt

    return None


def main():
    parser = argparse.ArgumentParser(description="Actualizar format desde access_url")
    parser.add_argument("--commit", action="store_true", help="Ejecutar actualización")
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("ACTUALIZAR FORMAT DESDE ACCESS_URL")
    logger.info("=" * 70)

    conn = get_db_connection()

    try:
        # Estado inicial
        logger.info("")
        logger.info("ESTADO INICIAL:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM datasets
                WHERE format IS NULL OR format = '' OR format = '[]'
            """)
            sin_formato = cur.fetchone()[0]
            logger.info(f"  Sin formato: {sin_formato:,}")

        # Análisis de access_url
        logger.info("")
        logger.info("ANÁLISIS DE ACCESS_URL:")

        with conn.cursor() as cur:
            # URLs con extensiones detectables
            cur.execute("""
                SELECT
                    COUNT(CASE WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.csv' THEN 1 END) as csv,
                    COUNT(CASE WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.xlsx' THEN 1 END) as xlsx,
                    COUNT(CASE WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.xls' THEN 1 END) as xls,
                    COUNT(CASE WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.json' THEN 1 END) as json,
                    COUNT(CASE WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.xml' THEN 1 END) as xml,
                    COUNT(CASE WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.pdf' THEN 1 END) as pdf,
                    COUNT(CASE WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.zip' THEN 1 END) as zip,
                    COUNT(CASE WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.geojson' THEN 1 END) as geojson,
                    COUNT(CASE WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%service=wms%' THEN 1 END) as wms,
                    COUNT(CASE WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%service=wfs%' THEN 1 END) as wfs
                FROM datasets
                WHERE format IS NULL OR format = '' OR format = '[]'
            """)
            row = cur.fetchone()
            logger.info(f"  CSV: {row[0]:,}")
            logger.info(f"  XLSX: {row[1]:,}")
            logger.info(f"  XLS: {row[2]:,}")
            logger.info(f"  JSON: {row[3]:,}")
            logger.info(f"  XML: {row[4]:,}")
            logger.info(f"  PDF: {row[5]:,}")
            logger.info(f"  ZIP: {row[6]:,}")
            logger.info(f"  GeoJSON: {row[7]:,}")
            logger.info(f"  WMS: {row[8]:,}")
            logger.info(f"  WFS: {row[9]:,}")

            total_detectable = sum([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9]])
            logger.info(f"  TOTAL detectable: ~{total_detectable:,}")

        if args.commit:
            logger.info("")
            logger.info("EJECUTANDO ACTUALIZACIÓN...")

            # Actualizar usando access_url del primer distribution
            update_query = """
            UPDATE datasets
            SET format = CASE
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.csv%' THEN 'CSV'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.xlsx%' THEN 'XLSX'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.xls%' THEN 'XLS'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.json%' THEN 'JSON'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.xml%' THEN 'XML'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.pdf%' THEN 'PDF'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.zip%' THEN 'ZIP'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.geojson%' THEN 'GEOJSON'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%service=wms%' THEN 'WMS'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%service=wfs%' THEN 'WFS'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.shp%' THEN 'SHP'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.kml%' THEN 'KML'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.txt%' THEN 'TXT'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.tsv%' THEN 'TSV'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.ods%' THEN 'ODS'
                WHEN raw_metadata->'distributions'->0->>'access_url' LIKE '%.px%' THEN 'PX'
                ELSE format
            END
            WHERE format IS NULL OR format = '' OR format = '[]'
              AND raw_metadata->'distributions' IS NOT NULL
              AND jsonb_array_length(raw_metadata->'distributions') > 0
            """

            with conn.cursor() as cur:
                cur.execute(update_query)
                updated = cur.rowcount

            conn.commit()
            logger.info(f"  Actualizados: {updated:,} datasets")

            # Estado final
            logger.info("")
            logger.info("ESTADO FINAL:")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN format IS NOT NULL AND format != '' AND format != '[]' THEN 1 END) as con_formato
                    FROM datasets
                """)
                row = cur.fetchone()
                logger.info(f"  Total: {row[0]:,}")
                logger.info(f"  Con formato: {row[1]:,} ({row[1]/row[0]*100:.1f}%)")

            # Distribución final
            logger.info("")
            logger.info("DISTRIBUCIÓN FINAL (top 15):")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT format, COUNT(*) as count
                    FROM datasets
                    WHERE format IS NOT NULL AND format != '' AND format != '[]'
                    GROUP BY format
                    ORDER BY count DESC
                    LIMIT 15
                """)
                for row in cur.fetchall():
                    fmt = row[0]
                    count = row[1]
                    pct = count / 87676 * 100
                    logger.info(f"  {fmt}: {count:,} ({pct:.1f}%)")

        else:
            logger.info("")
            logger.info("DRY-RUN: usar --commit para ejecutar")

    finally:
        conn.close()
        logger.info("Conexión cerrada")


if __name__ == "__main__":
    main()
