#!/usr/bin/env python3
"""
Inferir Formato desde URL - Complemento a Auditoría de Metadatos
=================================================================

Script para inferir el formato real de los datasets analizando las URLs
de descarga, ya que el campo `format` en metadatos está vacío el 98.5%.

Mejoras v2:
- Detección de URLs ambiguas (dashboards, servicios, visores)
- Manejo de múltiples formatos por dataset
- Clasificación por tipo de acceso (directo, bajo demanda, servicio)

Uso:
    python infer_format_from_url.py --output ../entregables/analisis_metadatos/formatos_inferidos.csv

Autor: TFM - Buscador Semántico de Open Data
Fecha: 2026-06-10
"""

import argparse
import logging
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

# Mapeo de extensiones a formatos normalizados
FORMAT_MAPPING = {
    # CSV y derivados
    ".csv": "CSV",
    ".csv.zip": "CSV (ZIP)",
    ".csv.gz": "CSV (GZIP)",
    ".tsv": "TSV",
    # Excel
    ".xls": "XLS",
    ".xlsx": "XLSX",
    ".xlsm": "XLSM",
    ".xlsb": "XLSB",
    ".ods": "ODS",
    # JSON
    ".json": "JSON",
    ".jsonl": "JSONL",
    ".geojson": "GeoJSON",
    # XML
    ".xml": "XML",
    ".gml": "GML",
    ".kml": "KML",
    ".kmz": "KMZ",
    ".rss": "RSS",
    ".rdf": "RDF",
    # PDF
    ".pdf": "PDF",
    # Texto
    ".txt": "TXT",
    ".rtf": "RTF",
    # HTML
    ".html": "HTML",
    ".htm": "HTML",
    # Archivos comprimidos
    ".zip": "ZIP",
    ".tar": "TAR",
    ".tar.gz": "TAR.GZ",
    ".7z": "7Z",
    ".rar": "RAR",
    # GIS
    ".shp": "SHP",
    ".shx": "SHX",
    ".dbf": "DBF",
    ".prj": "PRJ",
    ".geojson": "GeoJSON",
    ".gpx": "GPX",
    # Datos estadísticos
    ".px": "PX (PC-Axis)",
    ".sdmx": "SDMX",
    # API/Servicios
    "wms": "WMS",
    "wfs": "WFS",
    "wmts": "WMTS",
    "wcs": "WCS",
    "rest": "REST API",
    "soap": "SOAP API",
    # Otros
    ".doc": "DOC",
    ".docx": "DOCX",
    ".ppt": "PPT",
    ".pptx": "PPTX",
}

# Patrones de URLs ambiguas (no son archivos descargables directamente)
AMBIGUOUS_PATTERNS = [
    # Dashboards BI
    (r"saw\.dll", "Dashboard BI (Oracle/Siebel)"),
    (r"analytics_pub", "Dashboard BI"),
    # Visores estadísticos
    (r"jaxi/tabla\.do", "Visor estadístico (JAXI)"),
    (r"typeDownload", "Visor con descarga bajo demanda"),
    # Servicios OGC
    (r"service=WMS", "Servicio WMS"),
    (r"service=WFS", "Servicio WFS"),
    (r"service=WCS", "Servicio WCS"),
    (r"service=WMTS", "Servicio WMTS"),
    (r"geoserver/ows", "GeoServer OWS"),
    # Portales de catálogo
    (r"/dataset/", "Portal de catálogo"),
    (r"/data/dataset/", "Portal de datos"),
    # Geoserver
    (r"geoserver", "GeoServer"),
    # Carto
    (r"carto\.com", "CartoDB"),
]

# Prioridad de formatos (para seleccionar el mejor cuando hay múltiples)
FORMAT_PRIORITY = {
    "CSV": 1,
    "JSON": 2,
    "XML": 3,
    "GEOJSON": 4,
    "TSV": 5,
    "XLSX": 6,
    "XLS": 7,
    "ODS": 8,
    "PDF": 9,
    "HTML": 10,
    "ZIP": 11,
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


def detect_ambiguous_url(url: str) -> Optional[str]:
    """Detectar si una URL es ambigua (no archivo directo)."""
    url_lower = url.lower()
    for pattern, label in AMBIGUOUS_PATTERNS:
        if re.search(pattern, url_lower):
            return label
    return None


def extract_extensions_from_url(url: str) -> List[str]:
    """Extraer todas las extensiones posibles de una URL."""
    if not url:
        return []

    url_lower = url.lower()
    extensions = []

    # Quitar query strings para análisis principal
    url_clean = url_lower.split("?")[0]

    # Casos especiales: servicios
    if "service=wms" in url_lower:
        return ["wms"]
    if "service=wfs" in url_lower:
        return ["wfs"]
    if "service=wcs" in url_lower:
        return ["wcs"]
    if "service=wmts" in url_lower:
        return ["wmts"]

    # Caso especial: visor JAXI con typeDownload
    if "jaxi/tabla.do" in url_lower and "typeDownload=" in url_lower:
        # Extraer tipo de descarga
        type_match = re.search(r"typeDownload=(\d+)", url_lower)
        if type_match:
            type_code = type_match.group(1)
            # 0 = HTML, 6 = CSV, 7 = XLS, 8 = XML (típico en JAXI)
            type_mapping = {"6": ".csv", "7": ".xls", "8": ".xml"}
            if type_code in type_mapping:
                return [type_mapping[type_code]]
        return [".html"]  # Por defecto es visor HTML

    # Buscar todas las extensiones conocidas en la URL
    for ext in sorted(FORMAT_MAPPING.keys(), key=len, reverse=True):
        if url_clean.endswith(ext):
            extensions.append(ext)

    # Si no se encontró nada, intentar patrón genérico
    if not extensions:
        matches = re.findall(r"\.([a-z0-9]+)(?:[?&]|$)", url_clean)
        for match in matches:
            ext = "." + match
            if ext in FORMAT_MAPPING:
                extensions.append(ext)

    return extensions


def infer_formats_from_metadata(format_metadata: str) -> List[str]:
    """Extraer lista de formatos desde el campo format del metadato."""
    if not format_metadata or format_metadata in ["", "[]", "null"]:
        return []

    # Limpiar
    fmt_clean = format_metadata.strip("[]").replace('"', "").strip()

    # Si hay comas, es múltiple
    if "," in fmt_clean:
        return [f.strip().upper() for f in fmt_clean.split(",") if f.strip()]

    return [fmt_clean.upper()]


def select_best_format(formats: List[str]) -> Optional[str]:
    """Seleccionar el mejor formato de una lista según prioridad."""
    if not formats:
        return None

    # Ordenar por prioridad
    sorted_formats = sorted(
        formats,
        key=lambda f: FORMAT_PRIORITY.get(f, 999)
    )

    return sorted_formats[0]


def classify_url_type(url: str, formats: List[str]) -> str:
    """Clasificar el tipo de URL."""
    # Es un servicio?
    if any(f in ["WMS", "WFS", "WCS", "WMTS", "REST API"] for f in formats):
        return "servicio"

    # Es dashboard/visor?
    ambiguous = detect_ambiguous_url(url)
    if ambiguous:
        return "ambiguo"

    # Tiene formato claro?
    if formats:
        return "directo"

    return "desconocido"


def analyze_formats(conn) -> Dict:
    """Analizar formatos inferidos desde URLs."""
    logger.info("Analizando formatos desde URLs...")

    query = """
    SELECT
        dataset_id,
        title,
        url,
        format as format_metadata
    FROM datasets
    WHERE url IS NOT NULL AND url != ''
    """

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    results = {
        "total": len(rows),
        "inferred_formats": defaultdict(int),
        "inferred_formats_primary": defaultdict(int),
        "extensions": defaultdict(int),
        "url_types": defaultdict(int),
        "ambiguous_types": defaultdict(int),
        "multiple_formats": 0,
        "metadata_vs_inferred": {
            "both_empty": 0,
            "metadata_only": 0,
            "inferred_only": 0,
            "both_match": 0,
            "mismatch": 0,
            "multiple_in_metadata": 0,
        },
        "examples": {
            "ambiguous": [],
            "multiple": [],
        },
    }

    for dataset_id, title, url, format_metadata in rows:
        # Extraer extensiones de URL
        extensions = extract_extensions_from_url(url)
        formats = [FORMAT_MAPPING.get(ext, ext.upper().strip(".")) for ext in extensions]

        # Formatos del metadato
        metadata_formats = infer_formats_from_metadata(format_metadata)

        # Clasificar tipo de URL
        url_type = classify_url_type(url, formats)
        results["url_types"][url_type] += 1

        # Detectar URLs ambiguas
        ambiguous_type = detect_ambiguous_url(url)
        if ambiguous_type:
            results["ambiguous_types"][ambiguous_type] += 1
            if len(results["examples"]["ambiguous"]) < 10:
                results["examples"]["ambiguous"].append({
                    "dataset_id": dataset_id,
                    "title": title[:100],
                    "url": url,
                    "type": ambiguous_type,
                })

        # Contar múltiples formatos
        if len(formats) > 1 or len(metadata_formats) > 1:
            results["multiple_formats"] += 1
            if len(results["examples"]["multiple"]) < 10:
                results["examples"]["multiple"].append({
                    "dataset_id": dataset_id,
                    "title": title[:100],
                    "url": url,
                    "formats_url": formats,
                    "formats_metadata": metadata_formats,
                })

        # Contar extensiones
        for ext in extensions:
            results["extensions"][ext] += 1

        # Contar formatos inferidos (todos)
        for fmt in formats:
            results["inferred_formats"][fmt] += 1

        # Formato primario (el mejor)
        best_format = select_best_format(formats)
        if best_format:
            results["inferred_formats_primary"][best_format] += 1

        # Comparar metadato vs inferido
        if not metadata_formats and not formats:
            results["metadata_vs_inferred"]["both_empty"] += 1
        elif metadata_formats and not formats:
            results["metadata_vs_inferred"]["metadata_only"] += 1
        elif formats and not metadata_formats:
            results["metadata_vs_inferred"]["inferred_only"] += 1
        elif metadata_formats and formats:
            # Normalizar para comparación
            metadata_primary = metadata_formats[0] if metadata_formats else None
            inferred_primary = best_format

            if len(metadata_formats) > 1:
                results["metadata_vs_inferred"]["multiple_in_metadata"] += 1

            if metadata_primary == inferred_primary:
                results["metadata_vs_inferred"]["both_match"] += 1
            else:
                results["metadata_vs_inferred"]["mismatch"] += 1

    return results


def save_results(results: Dict, output_path: str):
    """Guardar resultados en CSV."""
    import csv

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["métrica", "valor", "porcentaje"])

        total = results["total"]

        # Tipos de URL
        writer.writerow([])
        writer.writerow(["TIPOS DE URL"])
        for url_type, count in sorted(results["url_types"].items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100
            writer.writerow([f"url_type:{url_type}", count, f"{pct:.2f}%"])

        # URLs ambiguas
        writer.writerow([])
        writer.writerow(["URLS AMBIGUAS"])
        for amb_type, count in sorted(results["ambiguous_types"].items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100
            writer.writerow([f"ambiguous:{amb_type}", count, f"{pct:.2f}%"])

        # Extensiones top
        writer.writerow([])
        writer.writerow(["EXTENSIONES DETECTADAS"])
        for ext, count in sorted(results["extensions"].items(), key=lambda x: x[1], reverse=True)[:20]:
            pct = count / total * 100
            writer.writerow([f"ext:{ext}", count, f"{pct:.2f}%"])

        # Formatos inferidos (primarios)
        writer.writerow([])
        writer.writerow(["FORMATOS INFERIDOS (PRIMARIO)"])
        for fmt, count in sorted(results["inferred_formats_primary"].items(), key=lambda x: x[1], reverse=True)[:20]:
            pct = count / total * 100
            writer.writerow([f"format:{fmt}", count, f"{pct:.2f}%"])

        # Comparación metadato vs inferido
        writer.writerow([])
        writer.writerow(["COMPARACIÓN METADATO VS INFERIDO"])
        for category, count in results["metadata_vs_inferred"].items():
            pct = count / total * 100
            writer.writerow([category, count, f"{pct:.2f}%"])

    logger.info(f"Resultados guardados en {output_path}")


def generate_summary(results: Dict) -> str:
    """Generar resumen en texto."""
    total = results["total"]

    summary = []
    summary.append("=" * 70)
    summary.append("RESUMEN: FORMATOS INFERIDOS DESDE URL (v2)")
    summary.append("=" * 70)
    summary.append(f"Total datasets con URL: {total:,}")
    summary.append("")

    summary.append("TIPOS DE URL:")
    for url_type, count in sorted(results["url_types"].items(), key=lambda x: x[1], reverse=True):
        pct = count / total * 100
        summary.append(f"  {url_type}: {count:,} ({pct:.1f}%)")

    summary.append("")
    summary.append("URLS AMBIGUAS (top 10):")
    for amb_type, count in sorted(results["ambiguous_types"].items(), key=lambda x: x[1], reverse=True)[:10]:
        pct = count / total * 100
        summary.append(f"  {amb_type}: {count:,} ({pct:.1f}%)")

    summary.append("")
    summary.append("FORMATOS INFERIDOS (PRIMARIO, TOP 15):")
    for fmt, count in sorted(results["inferred_formats_primary"].items(), key=lambda x: x[1], reverse=True)[:15]:
        pct = count / total * 100
        summary.append(f"  {fmt}: {count:,} ({pct:.1f}%)")

    summary.append("")
    summary.append("COMPARACIÓN METADATO VS INFERIDO:")
    for category, count in results["metadata_vs_inferred"].items():
        pct = count / total * 100
        summary.append(f"  {category}: {count:,} ({pct:.1f}%)")

    summary.append("")
    summary.append(f"Múltiples formatos detectados: {results['multiple_formats']:,} ({results['multiple_formats']/total*100:.1f}%)")

    # Ejemplos
    if results["examples"]["ambiguous"]:
        summary.append("")
        summary.append("EJEMPLOS DE URLS AMBIGUAS:")
        for ex in results["examples"]["ambiguous"][:5]:
            summary.append(f"  - {ex['type']}: {ex['title'][:60]}...")

    if results["examples"]["multiple"]:
        summary.append("")
        summary.append("EJEMPLOS DE MÚLTIPLES FORMATOS:")
        for ex in results["examples"]["multiple"][:5]:
            formats_str = ", ".join(ex["formats_url"]) if ex["formats_url"] else "N/A"
            summary.append(f"  - {ex['title'][:50]}... [{formats_str}]")

    return "\n".join(summary)


def main():
    parser = argparse.ArgumentParser(
        description="Inferir formatos de datasets desde URLs (v2)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="../entregables/analisis_metadatos/formatos_inferidos.csv",
        help="Ruta de salida para CSV",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostrar ejemplos detallados",
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("INFERENCIA DE FORMATOS DESDE URLs (v2)")
    logger.info("=" * 70)

    conn = get_db_connection()

    try:
        results = analyze_formats(conn)
        save_results(results, args.output)

        # Imprimir resumen
        print(generate_summary(results))

        if args.verbose:
            logger.info("")
            logger.info("EJEMPLOS DETALLADOS:")
            for ex in results["examples"]["ambiguous"][:3]:
                logger.info(f"  Ambiguo: {ex['type']}")
                logger.info(f"    URL: {ex['url']}")
            for ex in results["examples"]["multiple"][:3]:
                logger.info(f"  Múltiple: {ex['formats_url']}")
                logger.info(f"    URL: {ex['url']}")

    finally:
        conn.close()
        logger.info("Conexión cerrada")


if __name__ == "__main__":
    main()
