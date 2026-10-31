#!/usr/bin/env python3
"""
Generador de Visualizaciones - Análisis de Metadatos
=====================================================

Genera gráficos estáticos para la memoria del TFM basándose en los
resultados de la auditoría de metadatos.

Gráficos generados:
1. Distribución por formato (pie chart)
2. Top 20 publishers (bar chart)
3. Calidad de descripciones (pie chart)
4. Cobertura territorial (pie chart)
5. Tipos de publishers (bar chart)
6. Completitud de campos (bar chart)
7. Cobertura temporal (bar chart)
8. Evolución temporal de publicación (line chart)

Uso:
    python generate_charts.py --input ../entregables/analisis_metadatos/metadata_audit.csv
    python generate_charts.py --input ../entregables/analisis_metadatos/metadata_audit.csv --output ../entregables/analisis_metadatos/figuras/

Autor: TFM - Buscador Semántico de Open Data
Fecha: 2026-06-08
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Colores para gráficos (paleta accesible)
COLORS = {
    "primary": "#2E86AB",
    "secondary": "#A23B72",
    "tertiary": "#F18F01",
    "quaternary": "#C73E1D",
    "palette": ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#6A994E", "#577A8C", "#8B5CF6", "#EC4899"],
}


def load_summary(summary_path: str) -> Dict:
    """Cargar resumen ejecutivo desde JSON."""
    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_format_distribution(summary: Dict, output_dir: str):
    """Gráfico 1: Distribución por formato."""
    import matplotlib.pyplot as plt

    formatos = summary["formatos"]

    # Agrupar formatos menores
    total = sum(formatos.values())
    main_formats = {k: v for k, v in formatos.items() if v / total > 0.01}  # >1%
    other = sum(v for k, v in formatos.items() if v / total <= 0.01)

    labels = list(main_formats.keys()) + ["Otros"]
    sizes = list(main_formats.values()) + [other]

    # Ordenar descendente
    sorted_idx = sorted(range(len(sizes)), key=lambda i: sizes[i], reverse=True)
    labels = [labels[i] for i in sorted_idx]
    sizes = [sizes[i] for i in sorted_idx]

    plt.figure(figsize=(12, 10))
    wedges, texts, autotexts = plt.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        colors=COLORS["palette"][: len(labels)],
        startangle=90,
        pctdistance=0.85,
    )

    # Estilizar texto
    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_color("white")

    plt.title(
        "Distribución de Formatos en el Catálogo (n=87,676 datasets)",
        fontsize=14,
        fontweight="bold",
    )

    # Círculo central para efecto donut
    circle = plt.Circle((0, 0), 0.6, color="white")
    plt.gca().add_patch(circle)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "01_formatos.png"), dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Gráfico 1 guardado: {output_dir}/01_formatos.png")


def plot_top_publishers(summary: Dict, output_dir: str):
    """Gráfico 2: Top 20 publishers."""
    import matplotlib.pyplot as plt
    import numpy as np

    publishers = summary["top_publishers"]

    # Ordenar y tomar top 20
    sorted_pubs = sorted(publishers.items(), key=lambda x: x[1], reverse=True)[:20]
    labels = [p[0] for p in sorted_pubs]
    values = [p[1] for p in sorted_pubs]

    plt.figure(figsize=(14, 10))

    # Barras horizontales
    y_pos = np.arange(len(labels))
    bars = plt.barh(y_pos, values, color=COLORS["primary"])

    # Invertir para que el mayor esté arriba
    plt.gca().invert_yaxis()

    # Etiquetas
    plt.xlabel("Número de datasets", fontsize=11)
    plt.title(
        "Top 20 Publishers - Quiénes más datos publican",
        fontsize=14,
        fontweight="bold",
    )
    plt.yticks(y_pos, labels, fontsize=9)

    # Añadir valores en las barras
    for bar, val in zip(bars, values):
        plt.text(
            bar.get_width() + 100,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}",
            va="center",
            fontsize=9,
        )

    plt.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "02_publishers.png"), dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Gráfico 2 guardado: {output_dir}/02_publishers.png")


def plot_description_quality(summary: Dict, output_dir: str):
    """Gráfico 3: Calidad de descripciones."""
    import matplotlib.pyplot as plt

    quality = summary["description_quality"]

    # Ordenar por calidad
    order = ["excelente", "buena", "media", "corta"]
    labels = [
        f"Excelente\n(>200 palabras)",
        f"Buena\n(100-200 palabras)",
        f"Media\n(50-100 palabras)",
        f"Corta\n(<50 palabras)",
    ]
    sizes = [quality.get(q, 0) for q in order]

    plt.figure(figsize=(10, 8))

    wedges, texts, autotexts = plt.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        colors=[COLORS["palette"][2], COLORS["palette"][0], COLORS["palette"][5], COLORS["palette"][3]],
        startangle=90,
    )

    for autotext in autotexts:
        autotext.set_fontsize(11)
        autotext.set_color("white")

    plt.title(
        "Calidad de Descripciones - Longitud del texto descriptivo",
        fontsize=14,
        fontweight="bold",
    )

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "03_calidad_descripciones.png"), dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Gráfico 3 guardado: {output_dir}/03_calidad_descripciones.png")


def plot_territory_levels(summary: Dict, output_dir: str):
    """Gráfico 4: Cobertura territorial."""
    import matplotlib.pyplot as plt

    territory = summary["territory_levels"]

    labels = ["Nacional", "Autonómico", "Municipal", "Otro"]
    sizes = [
        territory.get("nacional", 0),
        territory.get("autonomico", 0),
        territory.get("municipal", 0),
        territory.get("otro", 0),
    ]

    plt.figure(figsize=(10, 8))

    wedges, texts, autotexts = plt.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        colors=[COLORS["palette"][0], COLORS["palette"][1], COLORS["palette"][4], COLORS["palette"][5]],
        startangle=90,
    )

    for autotext in autotexts:
        autotext.set_fontsize(12)
        autotext.set_color("white")

    plt.title(
        "Cobertura Territorial de los Datasets",
        fontsize=14,
        fontweight="bold",
    )

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "04_territorio.png"), dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Gráfico 4 guardado: {output_dir}/04_territorio.png")


def plot_publisher_types(summary: Dict, output_dir: str):
    """Gráfico 5: Tipos de publishers."""
    import matplotlib.pyplot as plt
    import numpy as np

    types = summary["publisher_types"]

    labels_map = {
        "institucional_nacional": "Nacional",
        "institucional_autonomico": "Autonómico",
        "institucional_municipal": "Municipal",
        "institucional_provincial": "Provincial",
        "internacional": "Internacional",
        "otro": "Otro",
    }

    ordered_types = [
        "institucional_nacional",
        "institucional_autonomico",
        "institucional_municipal",
        "institucional_provincial",
        "otro",
    ]

    labels = [labels_map.get(t, t) for t in ordered_types]
    sizes = [types.get(t, 0) for t in ordered_types]

    plt.figure(figsize=(12, 6))

    bars = plt.bar(labels, sizes, color=[COLORS["palette"][0], COLORS["palette"][1], COLORS["palette"][4], COLORS["palette"][5], COLORS["palette"][3]])

    plt.ylabel("Número de datasets", fontsize=11)
    plt.title("Tipos de Publishers - Clasificación institucional", fontsize=14, fontweight="bold")
    plt.xticks(rotation=15)

    # Añadir valores
    for bar, val in zip(bars, sizes):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 200,
            f"{val:,}",
            ha="center",
            fontsize=10,
        )

    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "05_tipos_publishers.png"), dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Gráfico 5 guardado: {output_dir}/05_tipos_publishers.png")


def plot_fields_completeness(summary: Dict, output_dir: str):
    """Gráfico 6: Completitud de campos."""
    import matplotlib.pyplot as plt

    completeness = summary["fields_completeness"]

    labels = ["100% completo", "50-99% completo", "<50% completo"]
    sizes = [
        completeness["complete_100"],
        completeness["partial_50_99"],
        completeness["low_below_50"],
    ]

    plt.figure(figsize=(10, 8))

    wedges, texts, autotexts = plt.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        colors=[COLORS["palette"][4], COLORS["palette"][2], COLORS["palette"][3]],
        startangle=90,
    )

    for autotext in autotexts:
        autotext.set_fontsize(12)
        autotext.set_color("white")

    plt.title(
        f"Completitud de Campos DCAT-AP-ES (media: {completeness['mean']:.1%})",
        fontsize=14,
        fontweight="bold",
    )

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "06_completitud_campos.png"), dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Gráfico 6 guardado: {output_dir}/06_completitud_campos.png")


def plot_temporal_coverage(summary: Dict, output_dir: str):
    """Gráfico 7: Cobertura temporal."""
    import matplotlib.pyplot as plt

    temporal = summary["temporal_coverage"]

    labels = ["Con cobertura temporal", "Sin cobertura temporal"]
    sizes = [temporal["with_coverage"], temporal["without_coverage"]]

    plt.figure(figsize=(10, 8))

    wedges, texts, autotexts = plt.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        colors=[COLORS["palette"][4], COLORS["palette"][5]],
        startangle=90,
    )

    for autotext in autotexts:
        autotext.set_fontsize(12)
        autotext.set_color("white")

    plt.title(
        "Cobertura Temporal Declarada en los Datasets",
        fontsize=14,
        fontweight="bold",
    )

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "07_cobertura_temporal.png"), dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Gráfico 7 guardado: {output_dir}/07_cobertura_temporal.png")


def plot_issued_years(summary: Dict, output_dir: str):
    """Gráfico 8: Evolución de publicación por año."""
    import matplotlib.pyplot as plt

    issued = summary.get("issued_years", {})
    if not issued:
        logger.warning("No hay datos de issued_years")
        return

    # Filtrar años razonables
    years_data = [(int(y), c) for y, c in issued.items() if y.isdigit() and 2000 <= int(y) <= 2030]
    years_data.sort(key=lambda x: x[0])

    if not years_data:
        logger.warning("No hay años válidos")
        return

    years = [str(y[0]) for y in years_data]
    counts = [y[1] for y in years_data]

    plt.figure(figsize=(14, 6))

    plt.plot(years, counts, marker="o", linewidth=2, color=COLORS["primary"], markersize=6)
    plt.fill_between(range(len(years)), counts, alpha=0.3, color=COLORS["primary"])

    plt.xlabel("Año de publicación", fontsize=11)
    plt.ylabel("Número de datasets", fontsize=11)
    plt.title("Evolución de Publicación de Datasets en el Catálogo", fontsize=14, fontweight="bold")
    plt.xticks(rotation=45)
    plt.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "08_evolucion_publicacion.png"), dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Gráfico 8 guardado: {output_dir}/08_evolucion_publicacion.png")


def main():
    parser = argparse.ArgumentParser(description="Generar visualizaciones del análisis de metadatos")
    parser.add_argument(
        "--input",
        type=str,
        default="../entregables/analisis_metadatos/resumen_ejecutivo.json",
        help="Ruta al resumen ejecutivo JSON",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="../entregables/analisis_metadatos/figuras/",
        help="Directorio de salida para las figuras",
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("GENERADOR DE VISUALIZACIONES - Análisis de Metadatos")
    logger.info("=" * 70)

    # Crear directorio de salida
    Path(args.output).mkdir(parents=True, exist_ok=True)

    # Cargar resumen
    logger.info(f"Cargando resumen desde {args.input}...")
    summary = load_summary(args.input)

    # Generar todos los gráficos
    logger.info(f"Total datasets analizados: {summary['total_datasets']:,}")
    logger.info("")

    plot_format_distribution(summary, args.output)
    plot_top_publishers(summary, args.output)
    plot_description_quality(summary, args.output)
    plot_territory_levels(summary, args.output)
    plot_publisher_types(summary, args.output)
    plot_fields_completeness(summary, args.output)
    plot_temporal_coverage(summary, args.output)
    plot_issued_years(summary, args.output)

    logger.info("")
    logger.info("=" * 70)
    logger.info("VISUALIZACIONES GENERADAS")
    logger.info("=" * 70)

    for i, name in enumerate(
        [
            "01_formatos.png",
            "02_publishers.png",
            "03_calidad_descripciones.png",
            "04_territorio.png",
            "05_tipos_publishers.png",
            "06_completitud_campos.png",
            "07_cobertura_temporal.png",
            "08_evolucion_publicacion.png",
        ],
        1,
    ):
        logger.info(f"  {i}. {name}")


if __name__ == "__main__":
    main()
