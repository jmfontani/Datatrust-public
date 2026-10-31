#!/usr/bin/env python3
"""
Actualizar campo `format` desde `distributions` en raw_metadata
================================================================

El formato está disponible en raw_metadata->distributions[].format para
el 100% de los datasets, pero el campo directo `format` solo tiene valor
para 1.5% de datasets.

Este script extrae el formato de distributions y actualiza el campo directo.

Uso:
    python update_format_from_distributions.py --dry-run  # Solo ver estadísticas
    python update_format_from_distributions.py --commit   # Actualizar BD

Autor: TFM - Buscador Semántico de Open Data
Fecha: 2026-06-10
"""

import argparse
import logging
import os
import re
from typing import Dict, Optional, Tuple

import psycopg2

# Configuración de logging
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

# Mapeo de URIs de formato a valores simplificados
FORMAT_URI_MAPPING = {
    "http://publications.europa.eu/resource/authority/file-type/CSV": "CSV",
    "http://publications.europa.eu/resource/authority/file-type/XLSX": "XLSX",
    "http://publications.europa.eu/resource/authority/file-type/XLS": "XLS",
    "http://publications.europa.eu/resource/authority/file-type/JSON": "JSON",
    "http://publications.europa.eu/resource/authority/file-type/XML": "XML",
    "http://publications.europa.eu/resource/authority/file-type/PDF": "PDF",
    "http://publications.europa.eu/resource/authority/file-type/HTML": "HTML",
    "http://publications.europa.eu/resource/authority/file-type/ZIP": "ZIP",
    "http://publications.europa.eu/resource/authority/file-type/GEOJSON": "GeoJSON",
    "http://publications.europa.eu/resource/authority/file-type/SHP": "SHP",
    "http://publications.europa.eu/resource/authority/file-type/KML": "KML",
    "http://publications.europa.eu/resource/authority/file-type/GML": "GML",
    "http://publications.europa.eu/resource/authority/file-type/RDF": "RDF",
    "http://publications.europa.eu/resource/authority/file-type/TURTLE": "TURTLE",
    "http://publications.europa.eu/resource/authority/file-type/WMS": "WMS",
    "http://publications.europa.eu/resource/authority/file-type/WFS": "WFS",
    "http://publications.europa.eu/resource/authority/file-type/ODS": "ODS",
    "http://publications.europa.eu/resource/authority/file-type/TSV": "TSV",
}


def get_db_connection():
    """Establecer conexión con PostgreSQL."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Conectado a PostgreSQL (buscador)")
        return conn
    except Exception as e:
        logger.error(f"Error conectando a PostgreSQL: {e}")
        raise


def extract_format_from_uri(uri: str) -> str:
    """Extraer formato simplificado desde URI."""
    if not uri:
        return ""

    # Si es URI de Europa Publications
    if "publications.europa.eu" in uri:
        # Extraer último segmento (ej: CSV, XLSX, JSON)
        format_code = uri.rstrip("/").split("/")[-1]
        return format_code

    # Si ya es un formato simple
    return uri.upper()


def analyze_distributions(conn) -> Dict:
    """Analizar el estado actual de distributions y format."""
    logger.info("Analizando distributions...")

    query = """
    SELECT
        dataset_id,
        title,
        format as format_directo,
        raw_metadata->'distributions' as distributions,
        raw_metadata->'formats' as formats_array
    FROM datasets
    LIMIT 100
    """

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    stats = {
        "total_analyzed": len(rows),
        "format_distribution": {},
        "uri_patterns": {},
    }

    for dataset_id, title, format_directo, distributions, formats_array in rows:
        if distributions:
            for dist in distributions:
                fmt_uri = dist.get("format", "")
                if fmt_uri:
                    fmt_simple = extract_format_from_uri(fmt_uri)
                    stats["format_distribution"][fmt_simple] = stats["format_distribution"].get(fmt_simple, 0) + 1

                    # Contar patrones de URI
                    if "publications.europa.eu" in fmt_uri:
                        stats["uri_patterns"]["europa_uri"] = stats["uri_patterns"].get("europa_uri", 0) + 1
                    else:
                        stats["uri_patterns"]["other"] = stats["uri_patterns"].get("other", 0) + 1

    return stats


def update_formats(conn, dry_run: bool = True) -> Tuple[int, int]:
    """
    Actualizar campo format desde distributions.

    Returns: (updated_count, unchanged_count)
    """
    logger.info("Actualizando campo format desde distributions...")

    # Query para extraer formato del primer distribution
    update_query = """
    UPDATE datasets
    SET format = CASE
        WHEN raw_metadata->'distributions' IS NOT NULL
             AND jsonb_array_length(raw_metadata->'distributions') > 0
             AND raw_metadata->'distributions'->0->>'format' IS NOT NULL
        THEN UPPER(
            REPLACE(
                REPLACE(
                    raw_metadata->'distributions'->0->>'format',
                    'http://publications.europa.eu/resource/authority/file-type/',
                    ''
                ),
                '/', ''
            )
        )
        ELSE format
    END
    WHERE format IS NULL OR format = '' OR format = '[]'
    """

    if dry_run:
        # Contar cuántos se actualizarían
        count_query = """
        SELECT COUNT(*) FROM datasets
        WHERE (format IS NULL OR format = '' OR format = '[]')
          AND raw_metadata->'distributions' IS NOT NULL
          AND jsonb_array_length(raw_metadata->'distributions') > 0
          AND raw_metadata->'distributions'->0->>'format' IS NOT NULL
        """
        with conn.cursor() as cur:
            cur.execute(count_query)
            count = cur.fetchone()[0]

        logger.info(f"[DRY-RUN] Se actualizarían {count} datasets")
        return count, 0

    else:
        with conn.cursor() as cur:
            cur.execute(update_query)
            updated = cur.rowcount

        conn.commit()
        logger.info(f"Actualizados {updated} datasets")
        return updated, 0


def verify_update(conn) -> Dict:
    """Verificar el estado después de la actualización."""
    logger.info("Verificando actualización...")

    query = """
    SELECT
        COUNT(*) as total,
        COUNT(CASE WHEN format IS NOT NULL AND format != '' AND format != '[]' THEN 1 END) as con_formato,
        COUNT(CASE WHEN format IS NULL OR format = '' OR format = '[]' THEN 1 END) as sin_formato,
        ROUND(COUNT(CASE WHEN format IS NOT NULL AND format != '' AND format != '[]' THEN 1 END)::numeric / COUNT(*)::numeric * 100, 2) as pct_con_formato
    FROM datasets
    """

    with conn.cursor() as cur:
        cur.execute(query)
        row = cur.fetchone()

    return {
        "total": row[0],
        "con_formato": row[1],
        "sin_formato": row[2],
        "pct_con_formato": row[3],
    }


def get_format_distribution(conn) -> Dict:
    """Obtener distribución de formatos después de la actualización."""
    query = """
    SELECT format, COUNT(*) as count
    FROM datasets
    WHERE format IS NOT NULL AND format != '' AND format != '[]'
    GROUP BY format
    ORDER BY count DESC
    LIMIT 20
    """

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    return {row[0]: row[1] for row in rows}


def main():
    parser = argparse.ArgumentParser(
        description="Actualizar campo format desde distributions"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Ejecutar actualización (sin esto es solo dry-run)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostrar detalles de ejemplos",
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("ACTUALIZAR FORMAT DESDE DISTRIBUTIONS")
    logger.info("=" * 70)

    conn = get_db_connection()

    try:
        # Estado inicial
        logger.info("")
        logger.info("ESTADO INICIAL:")
        initial = verify_update(conn)
        logger.info(f"  Total datasets: {initial['total']:,}")
        logger.info(f"  Con formato: {initial['con_formato']:,} ({initial['pct_con_formato']}%)")
        logger.info(f"  Sin formato: {initial['sin_formato']:,}")

        # Análisis de distributions
        logger.info("")
        logger.info("ANÁLISIS DE DISTRIBUTIONS (muestra 100 datasets):")
        stats = analyze_distributions(conn)
        logger.info("  Formatos encontrados en distributions:")
        for fmt, count in sorted(stats["format_distribution"].items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"    {fmt}: {count}")

        # Actualización
        logger.info("")
        if args.commit:
            logger.info("EJECUTANDO ACTUALIZACIÓN...")
            updated, unchanged = update_formats(conn, dry_run=False)
            logger.info(f"  Actualizados: {updated:,}")
        else:
            logger.info("DRY-RUN (usar --commit para ejecutar):")
            updated, unchanged = update_formats(conn, dry_run=True)

        # Verificación
        if args.commit:
            logger.info("")
            logger.info("ESTADO FINAL:")
            final = verify_update(conn)
            logger.info(f"  Total datasets: {final['total']:,}")
            logger.info(f"  Con formato: {final['con_formato']:,} ({final['pct_con_formato']}%)")
            logger.info(f"  Sin formato: {final['sin_formato']:,}")

            logger.info("")
            logger.info("DISTRIBUCIÓN DE FORMATOS (top 15):")
            dist = get_format_distribution(conn)
            for fmt, count in list(dist.items())[:15]:
                pct = count / final['total'] * 100
                logger.info(f"  {fmt}: {count:,} ({pct:.1f}%)")

    finally:
        conn.close()
        logger.info("Conexión cerrada")


if __name__ == "__main__":
    main()
