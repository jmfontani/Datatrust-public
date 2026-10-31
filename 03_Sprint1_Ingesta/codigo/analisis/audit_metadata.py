#!/usr/bin/env python3
"""
Metadata Audit Script - Análisis Exploratorio del Catálogo de Datos Abiertos
=============================================================================

Extrae conocimiento de los metadatos de los datasets para:
1. Entender el corpus (87.676 datasets)
2. Justificar decisiones de diseño del buscador
3. Aportar valor original: diagnóstico del estado de datos.gob.es

Dimensiones analizadas:
- Formato (CSV, JSON, XML, API, etc.)
- Publisher (quién publica más, por tipo institucional)
- Calidad de metadatos (campos completados, longitud descripción)
- Cobertura territorial (nacional, autonómico, municipal)
- Cobertura temporal (años cubiertos, actualización)
- Tamaño estimado por formato

Uso:
    python audit_metadata.py --output ../entregables/analisis_metadatos/metadata_audit.csv

Autor: TFM - Buscador Semántico de Open Data
Fecha: 2026-06-08
"""

import argparse
import json
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "dbname": "buscador",
    "user": "postgres",
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "host": os.getenv("POSTGRES_HOST", "host.docker.internal"),
    "port": "5432",
}

# Mapeo de tipos de publishers
PUBLISHER_TYPES = {
    # Nacional
    "Instituto Nacional de Estadística": "institucional_nacional",
    "INE": "institucional_nacional",
    "Ministerio": "institucional_nacional",
    "Secretaría de Estado": "institucional_nacional",
    "Agencia Estatal": "institucional_nacional",
    # Autonómico
    "Comunidad de": "institucional_autonomico",
    "Gobierno de": "institucional_autonomico",
    "Generalitat": "institucional_autonomico",
    "Junta de": "institucional_autonomico",
    "Principado de": "institucional_autonomico",
    # Municipal
    "Ayuntamiento": "institucional_municipal",
    "Diputación": "institucional_provincial",
    # Otros
    "Unión Europea": "internacional",
    "Eurostat": "internacional",
}

# Mapeo de territorios
TERRITORY_LEVELS = {
    "nacional": ["España", "Nacional", "Estado", "INE", "Ministerio"],
    "autonomico": [
        "Andalucía",
        "Aragón",
        "Asturias",
        "Baleares",
        "Canarias",
        "Cantabria",
        "Castilla-La Mancha",
        "Castilla y León",
        "Cataluña",
        "Comunidad Valenciana",
        "Extremadura",
        "Galicia",
        "La Rioja",
        "Madrid",
        "Murcia",
        "Navarra",
        "País Vasco",
    ],
    "municipal": [
        "Madrid",
        "Barcelona",
        "Valencia",
        "Sevilla",
        "Zaragoza",
        "Málaga",
        "Bilbao",
        "Ayuntamiento",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE EXTRACCIÓN
# ═══════════════════════════════════════════════════════════════════════════════


def get_db_connection():
    """Establecer conexión con PostgreSQL."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Conectado a PostgreSQL (buscador)")
        return conn
    except Exception as e:
        logger.error(f"Error conectando a PostgreSQL: {e}")
        sys.exit(1)


def infer_publisher_type(publisher: str) -> str:
    """Inferir tipo de publisher basándose en el nombre."""
    if not publisher:
        return "desconocido"

    publisher_lower = publisher.lower()

    # Buscar patrones
    for pattern, ptype in PUBLISHER_TYPES.items():
        if pattern.lower() in publisher_lower:
            return ptype

    # Detectar autonómico por nombre de comunidad
    for comunidad in TERRITORY_LEVELS["autonomico"]:
        if comunidad.lower() in publisher_lower:
            return "institucional_autonomico"

    # Detectar municipal
    if "ayuntamiento" in publisher_lower or "municipal" in publisher_lower:
        return "institucional_municipal"

    return "otro"


def infer_territory_level(
    territory: str, publisher: str, municipality: str
) -> str:
    """Inferir nivel territorial."""
    if municipality:
        return "municipal"

    if territory:
        territory_lower = territory.lower()
        for level, keywords in TERRITORY_LEVELS.items():
            for keyword in keywords:
                if keyword.lower() in territory_lower:
                    return level

    # Inferir de publisher
    if publisher:
        return infer_publisher_type(publisher).replace("institucional_", "")

    return "desconocido"


def parse_format(raw_format: str) -> List[str]:
    """Parsear campo format que puede venir en varios formatos."""
    if not raw_format:
        return ["desconocido"]

    raw_format = raw_format.strip()

    if not raw_format or raw_format in ["[]", "", "null", "None"]:
        return ["desconocido"]

    # Limpiar corchetes y comillas
    raw_format = raw_format.strip("[]").strip()
    if not raw_format:
        return ["desconocido"]

    # Caso: "CSV", "JSON" -> puede tener comillas
    raw_format = raw_format.replace('"', '').replace("'", "")

    # Caso: CSV, JSON -> string separado por comas
    if "," in raw_format:
        formats = [f.strip().upper() for f in raw_format.split(",") if f.strip()]
        return formats if formats else ["desconocido"]

    # Caso simple: "CSV"
    return [raw_format.upper()]


def get_primary_format(raw_format: str) -> str:
    """Obtener formato primario (el primero de la lista)."""
    formats = parse_format(raw_format)
    return formats[0] if formats else "desconocido"


def calculate_description_quality(description: str) -> Tuple[int, str]:
    """Calificar calidad de descripción por longitud."""
    if not description:
        return 0, "muy_corta"

    length = len(description.split())

    if length < 50:
        return length, "corta"
    elif length < 100:
        return length, "media"
    elif length < 200:
        return length, "buena"
    else:
        return length, "excelente"


def calculate_fields_completeness(row: Dict) -> float:
    """Calcular porcentaje de campos completados."""
    required_fields = [
        "title",
        "description",
        "publisher",
        "theme",
        "format",
        "license",
        "territory",
        "temporal_coverage",
    ]

    filled = 0
    for field in required_fields:
        value = row.get(field)
        if value and value not in ["", "[]", "null", "None"]:
            filled += 1

    return filled / len(required_fields)


def extract_temporal_years(temporal_coverage: str) -> Optional[int]:
    """Extraer rango temporal en años."""
    if not temporal_coverage:
        return None

    # Buscar patrones de año (1990-2020, 2015, etc.)
    years = re.findall(r"\b(19|20)\d{2}\b", temporal_coverage)
    if len(years) >= 2:
        return int(years[-1]) - int(years[0])
    elif len(years) == 1:
        return 1

    return None


def extract_metadata_from_db(conn) -> List[Dict]:
    """Extraer metadatos de todos los datasets."""
    logger.info("Extrayendo metadatos de la base de datos...")

    query = """
    SELECT
        id, dataset_id, title, description, publisher, publisher_id,
        format, license, theme, subtheme,
        territory, territory_label, municipality, spatial_coverage,
        temporal_coverage, issued_date, modified_date,
        keywords, tags, url, download_url
    FROM datasets
    """

    with conn.cursor() as cur:
        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        # Convertir a dict manualmente
        datasets = [dict(zip(columns, row)) for row in rows]
        logger.info(f"Extraídos {len(datasets)} datasets")
        return datasets


def audit_datasets(datasets: List[Dict]) -> List[Dict]:
    """Procesar datasets y extraer métricas de auditoría."""
    logger.info("Procesando datasets...")

    audited = []

    for i, row in enumerate(datasets):
        if (i + 1) % 10000 == 0:
            logger.info(f"  Procesado {i + 1}/{len(datasets)}")

        # Formatos
        formats = parse_format(row.get("format", ""))
        primary_format = formats[0] if formats else "desconocido"
        multi_format = len(formats) > 1

        # Publisher
        publisher = row.get("publisher", "") or ""
        publisher_type = infer_publisher_type(publisher)

        # Territorio
        territory_level = infer_territory_level(
            row.get("territory", ""),
            publisher,
            row.get("municipality", ""),
        )

        # Calidad de descripción
        desc_length, desc_quality = calculate_description_quality(
            row.get("description", "")
        )

        # Completitud de campos
        fields_completeness = calculate_fields_completeness(row)

        # Cobertura temporal
        temporal_years = extract_temporal_years(row.get("temporal_coverage", ""))
        has_temporal = temporal_years is not None

        # Fecha de emisión
        issued_date = row.get("issued_date")
        issued_year = issued_date.year if issued_date else None

        # Fecha de modificación
        modified_date = row.get("modified_date")
        days_since_update = None
        if modified_date:
            days_since_update = (datetime.now() - modified_date).days

        audited.append(
            {
                "dataset_id": row.get("dataset_id", ""),
                "title": (row.get("title", "") or "")[:200],
                "format_primary": primary_format,
                "formats_all": "|".join(formats),
                "is_multi_format": multi_format,
                "publisher": publisher,
                "publisher_type": publisher_type,
                "territory_level": territory_level,
                "territory_raw": row.get("territory", ""),
                "municipality": row.get("municipality", ""),
                "theme": row.get("theme", ""),
                "subtheme": row.get("subtheme", ""),
                "description_length_words": desc_length,
                "description_quality": desc_quality,
                "fields_completeness": round(fields_completeness, 2),
                "has_temporal_coverage": has_temporal,
                "temporal_range_years": temporal_years,
                "temporal_coverage_raw": row.get("temporal_coverage", ""),
                "issued_year": issued_year,
                "days_since_update": days_since_update,
                "license": row.get("license", ""),
                "keywords_count": len(row.get("keywords", []) or []),
                "tags_count": len(row.get("tags", []) or []),
                "has_url": bool(row.get("url")),
                "has_download_url": bool(row.get("download_url")),
            }
        )

    return audited


def save_to_csv(audited: List[Dict], output_path: str):
    """Guardar resultados en CSV."""
    import csv

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(audited[0].keys())

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audited)

    logger.info(f"Guardado {len(audited)} registros en {output_path}")


def save_to_postgres(conn, audited: List[Dict]):
    """Guardar resultados en PostgreSQL."""
    logger.info("Guardando resultados en PostgreSQL...")

    create_table = """
    CREATE TABLE IF NOT EXISTS metadata_audit (
        dataset_id TEXT PRIMARY KEY,
        title TEXT,
        format_primary TEXT,
        formats_all TEXT,
        is_multi_format BOOLEAN,
        publisher TEXT,
        publisher_type TEXT,
        territory_level TEXT,
        territory_raw TEXT,
        municipality TEXT,
        theme TEXT,
        subtheme TEXT,
        description_length_words INTEGER,
        description_quality TEXT,
        fields_completeness FLOAT,
        has_temporal_coverage BOOLEAN,
        temporal_range_years INTEGER,
        temporal_coverage_raw TEXT,
        issued_year INTEGER,
        days_since_update INTEGER,
        license TEXT,
        keywords_count INTEGER,
        tags_count INTEGER,
        has_url BOOLEAN,
        has_download_url BOOLEAN,
        extracted_at TIMESTAMP DEFAULT NOW()
    );
    """

    with conn.cursor() as cur:
        cur.execute(create_table)

        insert_query = """
        INSERT INTO metadata_audit (
            dataset_id, title, format_primary, formats_all, is_multi_format,
            publisher, publisher_type, territory_level, territory_raw, municipality,
            theme, subtheme, description_length_words, description_quality,
            fields_completeness, has_temporal_coverage, temporal_range_years,
            temporal_coverage_raw, issued_year, days_since_update, license,
            keywords_count, tags_count, has_url, has_download_url
        ) VALUES (
            %(dataset_id)s, %(title)s, %(format_primary)s, %(formats_all)s, %(is_multi_format)s,
            %(publisher)s, %(publisher_type)s, %(territory_level)s, %(territory_raw)s, %(municipality)s,
            %(theme)s, %(subtheme)s, %(description_length_words)s, %(description_quality)s,
            %(fields_completeness)s, %(has_temporal_coverage)s, %(temporal_range_years)s,
            %(temporal_coverage_raw)s, %(issued_year)s, %(days_since_update)s, %(license)s,
            %(keywords_count)s, %(tags_count)s, %(has_url)s, %(has_download_url)s
        ) ON CONFLICT (dataset_id) DO UPDATE SET
            format_primary = EXCLUDED.format_primary,
            publisher_type = EXCLUDED.publisher_type,
            territory_level = EXCLUDED.territory_level,
            description_quality = EXCLUDED.description_quality,
            fields_completeness = EXCLUDED.fields_completeness,
            extracted_at = NOW()
        """

        for i, row in enumerate(audited):
            cur.execute(insert_query, row)
            if (i + 1) % 10000 == 0:
                logger.info(f"  Insertados {i + 1}/{len(audited)}")

    conn.commit()
    logger.info("Guardado en PostgreSQL completado")


def generate_summary(audited: List[Dict]) -> Dict:
    """Generar resumen estadístico."""
    from collections import Counter

    logger.info("Generando resumen estadístico...")

    summary = {
        "total_datasets": len(audited),
        "extracted_at": datetime.now().isoformat(),
        "formatos": dict(Counter(r["format_primary"] for r in audited)),
        "publisher_types": dict(Counter(r["publisher_type"] for r in audited)),
        "territory_levels": dict(Counter(r["territory_level"] for r in audited)),
        "description_quality": dict(Counter(r["description_quality"] for r in audited)),
        "temporal_coverage": {
            "with_coverage": sum(1 for r in audited if r["has_temporal_coverage"]),
            "without_coverage": sum(
                1 for r in audited if not r["has_temporal_coverage"]
            ),
        },
        "fields_completeness": {
            "mean": sum(r["fields_completeness"] for r in audited) / len(audited),
            "complete_100": sum(1 for r in audited if r["fields_completeness"] == 1.0),
            "partial_50_99": sum(
                1 for r in audited if 0.5 <= r["fields_completeness"] < 1.0
            ),
            "low_below_50": sum(
                1 for r in audited if r["fields_completeness"] < 0.5
            ),
        },
    }

    # Top publishers
    publisher_counts = Counter(r["publisher"] for r in audited if r["publisher"])
    summary["top_publishers"] = dict(publisher_counts.most_common(20))

    # Años de emisión
    issued_years = [r["issued_year"] for r in audited if r["issued_year"]]
    if issued_years:
        summary["issued_years"] = dict(Counter(issued_years).most_common())

    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Auditoría de metadatos del catálogo de datos abiertos"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="../entregables/analisis_metadatos/metadata_audit.csv",
        help="Ruta de salida para CSV",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Saltar guardado en PostgreSQL",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Solo generar resumen (sin CSV completo)",
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("AUDITORÍA DE METADATOS - Catálogo de Datos Abiertos")
    logger.info("=" * 70)

    # Conectar a BD
    conn = get_db_connection()

    try:
        # Extraer metadatos
        datasets = extract_metadata_from_db(conn)

        # Auditar datasets
        audited = audit_datasets(datasets)

        if not args.summary_only:
            # Guardar en CSV
            save_to_csv(audited, args.output)

            # Guardar en PostgreSQL
            if not args.skip_db:
                save_to_postgres(conn, audited)

        # Generar resumen
        summary = generate_summary(audited)

        # Guardar resumen JSON
        summary_path = Path(args.output).parent / "resumen_ejecutivo.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info(f"Resumen guardado en {summary_path}")

        # Imprimir resumen rápido
        logger.info("")
        logger.info("=" * 70)
        logger.info("RESUMEN RÁPIDO")
        logger.info("=" * 70)
        logger.info(f"Total datasets: {summary['total_datasets']:,}")
        logger.info("")
        logger.info("Formatos principales:")
        for fmt, count in sorted(
            summary["formatos"].items(), key=lambda x: x[1], reverse=True
        )[:10]:
            pct = count / summary["total_datasets"] * 100
            logger.info(f"  {fmt}: {count:,} ({pct:.1f}%)")
        logger.info("")
        logger.info("Calidad de descripciones:")
        for quality, count in summary["description_quality"].items():
            pct = count / summary["total_datasets"] * 100
            logger.info(f"  {quality}: {count:,} ({pct:.1f}%)")
        logger.info("")
        logger.info("Cobertura territorial:")
        for level, count in summary["territory_levels"].items():
            pct = count / summary["total_datasets"] * 100
            logger.info(f"  {level}: {count:,} ({pct:.1f}%)")

    finally:
        conn.close()
        logger.info("Conexión cerrada")


if __name__ == "__main__":
    main()
