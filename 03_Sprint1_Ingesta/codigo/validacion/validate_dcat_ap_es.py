#!/usr/bin/env python3
"""
Validador DCAT-AP-ES - Documentación de Cumplimiento
=====================================================

Script para validar datasets contra el perfil DCAT-AP-ES sin afectar
el flujo de procesamiento. Genera reportes de cumplimiento para
documentación y análisis posterior.

Características:
- Valida campos obligatorios y recomendados de DCAT-AP-ES
- NO filtra datasets (solo documenta)
- Genera estadísticas de cumplimiento
- Identifica datasets con problemas y sus motivos
- Guarda reporte detallado en JSON

Uso:
    python validate_dcat_ap_es.py --input ../../datos/processed/datasets_clean.jsonl
    python validate_dcat_ap_es.py --input ../../datos/processed/datasets_clean.jsonl --output reporte_dcat.json
    python validate_dcat_ap_es.py --input ../../datos/processed/datasets_clean.jsonl --sample 1000

Salida:
    - Reporte JSON con estadísticas de cumplimiento
    - Lista de datasets no conformes (sin filtrar)
    - Porcentaje de cumplimiento por campo

Referencia:
    Especificación DCAT-AP-ES: https://datosgobes.github.io/DCAT-AP-ES/
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# REGLAS DCAT-AP-ES
# ═══════════════════════════════════════════════════════════════════════════════

class DCATRule:
    """Representa una regla de validación DCAT-AP-ES."""

    def __init__(self, field: str, path: str, required: bool, description: str, validator=None):
        self.field = field
        self.path = path  # Path en el dataset (puede ser nested)
        self.required = required
        self.description = description
        self.validator = validator or self._default_validator

    def _default_validator(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validador por defecto: campo existe y no está vacío."""
        if value is None:
            return False, "Campo nulo"
        if isinstance(value, str) and not value.strip():
            return False, "Campo vacío"
        if isinstance(value, list) and len(value) == 0:
            return False, "Lista vacía"
        if isinstance(value, dict) and len(value) == 0:
            return False, "Diccionario vacío"
        return True, None

    def validate(self, dataset: Dict) -> Tuple[bool, Optional[str]]:
        """Valida un dataset contra esta regla."""
        value = self._get_value(dataset, self.path)
        return self.validator(value)

    def _get_value(self, dataset: Dict, path: str) -> Any:
        """Obtiene valor de un path (soporta anidación simple)."""
        if "." in path:
            parts = path.split(".")
            current = dataset
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
            return current
        return dataset.get(path)


# Definición de reglas DCAT-AP-ES
DCAT_RULES = [
    # Campos OBLIGATORIOS (MUST)
    DCATRule("dct:title", "title_es", True,
             "Título en español (obligatorio según DCAT-AP-ES)"),
    DCATRule("dct:description", "description_es", True,
             "Descripción en español (obligatorio según DCAT-AP-ES)"),
    DCATRule("dct:publisher", "publisher_uri", True,
             "URI del publicador (obligatorio según DCAT-AP-ES)"),
    DCATRule("dcat:theme", "themes", True,
             "Temas del dataset (obligatorio según DCAT-AP-ES)",
             validator=lambda x: (isinstance(x, list) and len(x) > 0, "Lista vacía o nula") if x else (False, "Campo nulo")),

    # Campos RECOMENDADOS (SHOULD)
    DCATRule("dcat:keyword", "keywords", False,
             "Palabras clave (recomendado)"),
    DCATRule("dct:spatial", "spatial_uri", False,
             "Cobertura geográfica (recomendado)"),
    DCATRule("dct:temporal", "temporal_coverage", False,
             "Cobertura temporal (recomendado)"),
    DCATRule("dcat:distribution", "distributions", False,
             "Distribuciones/formatos (recomendado)",
             validator=lambda x: (isinstance(x, list), "No es una lista") if x is not None else (True, None)),
    DCATRule("dct:license", "license_uri", False,
             "Licencia (recomendado)"),
    DCATRule("dct:issued", "issued", False,
             "Fecha de publicación (recomendado)"),
    DCATRule("dct:modified", "modified", False,
             "Fecha de modificación (recomendado)"),
    DCATRule("dcat:contactPoint", "contact_point", False,
             "Punto de contacto (recomendado, obligatorio para HVD)",
             validator=lambda x: (False, "No implementado en este proyecto")),
    DCATRule("dcatap:applicableLegislation", "applicable_legislation", False,
             "Legislación aplicable (recomendado, obligatorio para HVD)",
             validator=lambda x: (False, "No implementado en este proyecto")),

    # Campos OPCIONALES (MAY)
    DCATRule("foaf:page", "landing_page", False,
             "Página web del dataset (opcional)",
             validator=lambda x: (True, None)),  # source_url podría servir
]


def categorize_rules() -> Tuple[List[DCATRule], List[DCATRule], List[DCATRule]]:
    """Separa reglas en obligatorias, recomendadas y opcionales."""
    mandatory = [r for r in DCAT_RULES if r.required and r.field.startswith("dct:") or r.field.startswith("dcat:theme")]
    recommended = [r for r in DCAT_RULES if not r.required and not r.field.startswith("dcatap:")]
    hvd_specific = [r for r in DCAT_RULES if "applicableLegislation" in r.field or "contactPoint" in r.field]

    # Recategorizar correctamente
    mandatory = [r for r in DCAT_RULES if r.required]
    recommended = [r for r in DCAT_RULES if not r.required and not r.validator.__name__ == "<lambda>"]
    optional = [r for r in DCAT_RULES if not r.required]

    return mandatory, recommended, optional


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE VALIDACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def validate_dataset(dataset: Dict, rules: List[DCATRule]) -> Dict:
    """
    Valida un dataset contra todas las reglas DCAT-AP-ES.

    Returns:
        Dict con resultado de validación por campo
    """
    results = {
        "dataset_id": dataset.get("identifier", "unknown"),
        "title_preview": dataset.get("title_es", "")[:50],
        "validations": {},
        "mandatory_pass": True,
        "recommended_pass": True,
        "failed_mandatory": [],
        "failed_recommended": [],
        "overall_status": "PASS"
    }

    for rule in rules:
        is_valid, error_msg = rule.validate(dataset)

        results["validations"][rule.field] = {
            "valid": is_valid,
            "required": rule.required,
            "error": error_msg,
            "description": rule.description
        }

        if not is_valid:
            if rule.required:
                results["mandatory_pass"] = False
                results["failed_mandatory"].append({
                    "field": rule.field,
                    "error": error_msg,
                    "description": rule.description
                })
            else:
                results["recommended_pass"] = False
                results["failed_recommended"].append({
                    "field": rule.field,
                    "error": error_msg,
                    "description": rule.description
                })

    # Determinar estado general
    if not results["mandatory_pass"]:
        results["overall_status"] = "FAIL_MANDATORY"
    elif not results["recommended_pass"]:
        results["overall_status"] = "FAIL_RECOMMENDED"

    return results


def calculate_statistics(all_results: List[Dict]) -> Dict:
    """Calcula estadísticas globales de cumplimiento."""
    total = len(all_results)

    if total == 0:
        return {}

    # Conteo por estado
    status_counts = defaultdict(int)
    mandatory_pass = 0
    recommended_pass = 0

    # Conteo por campo
    field_stats = defaultdict(lambda: {"valid": 0, "invalid": 0, "required": False})

    for result in all_results:
        status_counts[result["overall_status"]] += 1

        if result["mandatory_pass"]:
            mandatory_pass += 1
        if result["recommended_pass"]:
            recommended_pass += 1

        for field, validation in result["validations"].items():
            if validation["required"]:
                field_stats[field]["required"] = True
            if validation["valid"]:
                field_stats[field]["valid"] += 1
            else:
                field_stats[field]["invalid"] += 1

    # Calcular porcentajes por campo
    field_percentages = {}
    for field, stats in field_stats.items():
        total_validations = stats["valid"] + stats["invalid"]
        if total_validations > 0:
            field_percentages[field] = {
                "compliance_rate": round(stats["valid"] / total_validations * 100, 2),
                "valid_count": stats["valid"],
                "invalid_count": stats["invalid"],
                "required": stats["required"]
            }

    return {
        "total_datasets": total,
        "status_distribution": dict(status_counts),
        "mandatory_compliance": {
            "pass_count": mandatory_pass,
            "pass_percentage": round(mandatory_pass / total * 100, 2),
            "fail_count": total - mandatory_pass
        },
        "recommended_compliance": {
            "pass_count": recommended_pass,
            "pass_percentage": round(recommended_pass / total * 100, 2),
            "fail_count": total - recommended_pass
        },
        "field_compliance": field_percentages
    }


def generate_report(all_results: List[Dict], stats: Dict, output_path: Path):
    """Genera reporte JSON de validación."""

    # Separar datasets por estado
    fail_mandatory = [r for r in all_results if r["overall_status"] == "FAIL_MANDATORY"]
    fail_recommended = [r for r in all_results if r["overall_status"] == "FAIL_RECOMMENDED"]
    pass_all = [r for r in all_results if r["overall_status"] == "PASS"]

    report = {
        "validation_info": {
            "timestamp": datetime.utcnow().isoformat(),
            "standard": "DCAT-AP-ES",
            "specification_url": "https://datosgobes.github.io/DCAT-AP-ES/",
            "total_rules_validated": len(DCAT_RULES),
            "mandatory_rules": len([r for r in DCAT_RULES if r.required]),
            "recommended_rules": len([r for r in DCAT_RULES if not r.required])
        },
        "summary": stats,
        "non_compliant_datasets": {
            "mandatory_failures": {
                "count": len(fail_mandatory),
                "percentage": round(len(fail_mandatory) / len(all_results) * 100, 2) if all_results else 0,
                "examples": fail_mandatory[:10]  # Primeros 10 ejemplos
            },
            "recommended_failures": {
                "count": len(fail_recommended),
                "percentage": round(len(fail_recommended) / len(all_results) * 100, 2) if all_results else 0,
                "examples": fail_recommended[:10]
            }
        },
        "compliant_datasets": {
            "count": len(pass_all),
            "percentage": round(len(pass_all) / len(all_results) * 100, 2) if all_results else 0
        },
        "validation_rules": [
            {
                "field": r.field,
                "path": r.path,
                "required": r.required,
                "description": r.description
            }
            for r in DCAT_RULES
        ]
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def print_summary(stats: Dict, non_compliant: Dict):
    """Imprime resumen en consola."""
    print("\n" + "=" * 80)
    print("REPORTE DE VALIDACIÓN DCAT-AP-ES")
    print("=" * 80)

    print(f"\n📊 Total de datasets analizados: {stats['total_datasets']:,}")

    print("\n📋 Distribución por estado:")
    for status, count in stats['status_distribution'].items():
        percentage = count / stats['total_datasets'] * 100
        print(f"   {status:25} {count:6,} ({percentage:5.1f}%)")

    print("\n✅ Cumplimiento campos OBLIGATORIOS:")
    m = stats['mandatory_compliance']
    print(f"   Cumplen: {m['pass_count']:,} / {stats['total_datasets']:,} ({m['pass_percentage']:.1f}%)")
    print(f"   No cumplen: {m['fail_count']:,}")

    print("\n⚪ Cumplimiento campos RECOMENDADOS:")
    r = stats['recommended_compliance']
    print(f"   Cumplen: {r['pass_count']:,} / {stats['total_datasets']:,} ({r['pass_percentage']:.1f}%)")
    print(f"   No cumplen: {r['fail_count']:,}")

    print("\n📊 Cumplimiento por campo:")
    print("   " + "-" * 70)
    print(f"   {'Campo':<35} {'Tipo':<12} {'Cumple':>8} {'No Cumple':>10} {'%':>6}")
    print("   " + "-" * 70)

    # Ordenar por tipo (obligatorios primero)
    sorted_fields = sorted(
        stats['field_compliance'].items(),
        key=lambda x: (not x[1]['required'], x[0])
    )

    for field, data in sorted_fields:
        field_type = "OBL" if data['required'] else "REC"
        valid = data['valid_count']
        invalid = data['invalid_count']
        pct = data['compliance_rate']
        print(f"   {field:<35} {field_type:<12} {valid:>8,} {invalid:>10,} {pct:>6.1f}%")

    print("\n❌ Resumen de no conformidades:")
    print(f"   Datasets con fallos obligatorios: {non_compliant['mandatory_failures']['count']:,}")
    print(f"   Datasets con fallos recomendados: {non_compliant['recommended_failures']['count']:,}")

    print("\n" + "=" * 80)
    print("Nota: Este reporte es solo informativo. NO se han filtrado datasets.")
    print("=" * 80 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Validador DCAT-AP-ES - Documentación de cumplimiento"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Ruta al archivo JSONL con datasets (ej: datasets_clean.jsonl)"
    )
    parser.add_argument(
        "--output", "-o",
        default="dcat_validation_report.json",
        help="Ruta del reporte JSON (default: dcat_validation_report.json)"
    )
    parser.add_argument(
        "--sample", "-s",
        type=int,
        default=None,
        help="Validar solo N datasets (para pruebas)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar progreso detallado"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        logger.error(f"Archivo no encontrado: {input_path}")
        sys.exit(1)

    logger.info(f"Iniciando validación DCAT-AP-ES")
    logger.info(f"Input: {input_path}")
    logger.info(f"Output: {output_path}")
    logger.info(f"Total de reglas a validar: {len(DCAT_RULES)}")

    # Cargar datasets
    datasets = []
    logger.info("Cargando datasets...")
    with open(input_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if args.sample and i >= args.sample:
                break
            try:
                datasets.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"Línea {i+1}: JSON inválido, ignorando")

    logger.info(f"Datasets cargados: {len(datasets):,}")

    # Validar cada dataset
    logger.info("Validando datasets contra DCAT-AP-ES...")
    all_results = []

    for i, dataset in enumerate(datasets):
        if args.verbose and (i + 1) % 1000 == 0:
            logger.info(f"  Progreso: {i + 1:,} / {len(datasets):,}")

        result = validate_dataset(dataset, DCAT_RULES)
        all_results.append(result)

    # Calcular estadísticas
    logger.info("Calculando estadísticas...")
    stats = calculate_statistics(all_results)

    # Generar reporte
    logger.info(f"Generando reporte: {output_path}")
    report = generate_report(all_results, stats, output_path)

    # Imprimir resumen
    print_summary(stats, report["non_compliant_datasets"])

    logger.info("Validación completada.")
    logger.info(f"Reporte guardado en: {output_path.absolute()}")

    # Retornar código de salida 0 (éxito) - no fallamos aunque haya datasets no conformes
    sys.exit(0)


if __name__ == "__main__":
    main()
