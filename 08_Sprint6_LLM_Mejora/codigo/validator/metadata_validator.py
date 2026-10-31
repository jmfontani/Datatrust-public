#!/usr/bin/env python3
"""
Validador General de Metadatos de Datasets
Detecta inconsistencias, anomalías y errores de calidad en metadatos.

Diseño extensible mediante:
1. Reglas configurables (patrones entre campos)
2. Validación cruzada (coherencia entre campos)
3. Detección de anomalías estadísticas
4. Validación semántica (embeddings)

Uso:
    from metadata_validator import MetadataValidator, ValidationRule

    validator = MetadataValidator()
    validator.add_rule(ValidationRule.cross_field_pattern(
        source_field="title",
        target_field="publisher",
        description="El título debe coincidir con el publisher"
    ))

    issues = validator.validate_dataset(dataset)
"""

from typing import List, Dict, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import re
import json
from collections import defaultdict


class Severity(Enum):
    """Nivel de severidad del problema detectado."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Problema detectado en la validación."""
    rule_id: str
    severity: Severity
    field: str
    message: str
    suggestion: Optional[str] = None
    dataset_id: Optional[str] = None
    context: Dict = field(default_factory=dict)


@dataclass
class ValidationRule:
    """
    Regla de validación configurable.

    Una regla puede ser:
    - De campo único: revisa un campo específico
    - De campos cruzados: revisa consistencia entre campos
    - De anomalía: detecta outliers estadísticos
    - Semántica: usa embeddings/NLP para validar coherencia
    """
    rule_id: str
    name: str
    description: str
    severity: Severity
    check_function: Callable[[Dict], Optional[ValidationIssue]]
    applies_to: Optional[List[str]] = None  # Campos a los que aplica (None = todos)
    enabled: bool = True

    @classmethod
    def required_field(cls, field_name: str, severity: Severity = Severity.ERROR) -> 'ValidationRule':
        """Regla: campo obligatorio no puede estar vacío."""
        def check(dataset: Dict) -> Optional[ValidationIssue]:
            value = dataset.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                return ValidationIssue(
                    rule_id=f"required_{field_name}",
                    severity=severity,
                    field=field_name,
                    message=f"El campo '{field_name}' está vacío o ausente",
                    suggestion=f"Proporcionar un valor para '{field_name}'"
                )
            return None

        return cls(
            rule_id=f"required_{field_name}",
            name=f"Campo obligatorio: {field_name}",
            description=f"Verifica que {field_name} no esté vacío",
            severity=severity,
            check_function=check,
            applies_to=[field_name]
        )

    @classmethod
    def cross_field_pattern(
        cls,
        source_field: str,
        target_field: str,
        extract_keywords: Optional[Callable[[str], Set[str]]] = None,
        severity: Severity = Severity.WARNING
    ) -> 'ValidationRule':
        """
        Regla: campos cruzados deben ser consistentes.

        Ejemplo: Si title contiene "UEx", publisher debería contener "Extremadura"
        """
        def check(dataset: Dict) -> Optional[ValidationIssue]:
            source_value = str(dataset.get(source_field, ""))
            target_value = str(dataset.get(target_field, ""))

            if not source_value or not target_value:
                return None

            # Extraer keywords del campo fuente
            if extract_keywords:
                keywords = extract_keywords(source_value)
            else:
                keywords = set()

            if not keywords:
                return None

            # Debug (comentar en producción)
            # print(f"DEBUG: Keywords extraídos de '{source_field}': {keywords}")

            # Verificar si alguna keyword del source aparece en target
            target_lower = target_value.lower()
            missing = []

            for kw in keywords:
                # Mapeo de abreviaturas comunes
                expanded = _expand_abbreviation(kw)
                # print(f"DEBUG: '{kw}' -> '{expanded}'")

                if expanded:
                    expanded_lower = expanded.lower()
                    kw_lower = kw.lower()

                    # Verificar si la expansión o la abreviatura original está en target
                    if expanded_lower not in target_lower and kw_lower not in target_lower:
                        missing.append(kw)
                        # print(f"DEBUG: '{expanded}' no encontrado en '{target_value}'")

            if missing:
                return ValidationIssue(
                    rule_id=f"cross_pattern_{source_field}_{target_field}",
                    severity=severity,
                    field=target_field,
                    message=f"Inconsistencia: '{source_field}' menciona {missing} pero '{target_field}' no lo refleja",
                    suggestion=f"Verificar que {target_field} corresponda al contenido de {source_field}",
                    context={
                        "source_field": source_field,
                        "target_field": target_field,
                        "keywords_found": list(keywords),
                        "expected_in_target": missing
                    }
                )
            return None

        return cls(
            rule_id=f"cross_pattern_{source_field}_{target_field}",
            name=f"Consistencia {source_field} ↔ {target_field}",
            description=f"Verifica que {target_field} sea consistente con {source_field}",
            severity=severity,
            check_function=check,
            applies_to=[source_field, target_field]
        )

    @classmethod
    def field_format(cls, field_name: str, pattern: str, description: str) -> 'ValidationRule':
        """Regla: campo debe coincidir con patrón regex."""
        regex = re.compile(pattern)

        def check(dataset: Dict) -> Optional[ValidationIssue]:
            value = str(dataset.get(field_name, ""))
            if value and not regex.match(value):
                return ValidationIssue(
                    rule_id=f"format_{field_name}",
                    severity=Severity.WARNING,
                    field=field_name,
                    message=f"El campo '{field_name}' no cumple el formato esperado: {description}",
                    suggestion=f"Revisar formato de '{field_name}'",
                    context={"value": value, "expected_pattern": pattern}
                )
            return None

        return cls(
            rule_id=f"format_{field_name}",
            name=f"Formato {field_name}",
            description=description,
            severity=Severity.WARNING,
            check_function=check,
            applies_to=[field_name]
        )

    @classmethod
    def statistical_anomaly(
        cls,
        field_name: str,
        reference_values: List[str],
        threshold: float = 0.3
    ) -> 'ValidationRule':
        """
        Regla: detectar valores atípicos basados en referencia.

        Ejemplo: Si un publisher suele tener temas ["educacion", "investigacion"],
        detectar si aparece con "medio_ambiente" (podría ser un error)
        """
        reference_set = set(reference_values)

        def check(dataset: Dict) -> Optional[ValidationIssue]:
            value = dataset.get(field_name)
            if not value:
                return None

            # Si el valor no está en el conjunto de referencia y hay referencias
            if reference_set and value not in reference_set:
                # Sugerir valores similares
                similar = _find_similar(value, reference_set)
                if similar:
                    return ValidationIssue(
                        rule_id=f"anomaly_{field_name}",
                        severity=Severity.WARNING,
                        field=field_name,
                        message=f"Valor inusual en '{field_name}': '{value}'",
                        suggestion=f"¿Quizás quisiste decir: {similar}?",
                        context={"value": value, "similar_values": similar}
                    )
            return None

        return cls(
            rule_id=f"anomaly_{field_name}",
            name=f"Anomalía {field_name}",
            description=f"Detecta valores atípicos en {field_name}",
            severity=Severity.WARNING,
            check_function=check,
            applies_to=[field_name]
        )


class MetadataValidator:
    """
    Validador general de metadatos.

    Permite registrar múltiples reglas y aplicarlas a datasets.
    """

    def __init__(self):
        self.rules: List[ValidationRule] = []
        self._statistics: Dict[str, Dict] = defaultdict(lambda: defaultdict(int))

    def add_rule(self, rule: ValidationRule) -> 'MetadataValidator':
        """Añadir una regla al validador."""
        self.rules.append(rule)
        return self

    def add_default_rules(self) -> 'MetadataValidator':
        """Añadir reglas por defecto para datasets estándar."""
        # Campos obligatorios
        self.add_rule(ValidationRule.required_field("title"))
        self.add_rule(ValidationRule.required_field("publisher"))
        self.add_rule(ValidationRule.required_field("theme"))

        # Consistencia entre campos
        self.add_rule(ValidationRule.cross_field_pattern(
            source_field="title",
            target_field="publisher",
            extract_keywords=_extract_org_abbreviations
        ))

        self.add_rule(ValidationRule.cross_field_pattern(
            source_field="title",
            target_field="territory",
            extract_keywords=_extract_territory_keywords
        ))

        # Formato de campos
        self.add_rule(ValidationRule.field_format(
            "format",
            r"^(CSV|JSON|XML|RDF|XLS|PDF|GeoJSON|TTL|NT)$",
            "Formato estándar de archivo"
        ))

        return self

    def validate_dataset(self, dataset: Dict) -> List[ValidationIssue]:
        """
        Validar un dataset contra todas las reglas activas.

        Args:
            dataset: Diccionario con metadatos del dataset

        Returns:
            Lista de problemas detectados
        """
        issues = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            try:
                issue = rule.check_function(dataset)
                if issue:
                    issue.dataset_id = dataset.get("dataset_id") or dataset.get("id")
                    issues.append(issue)
            except Exception as e:
                # Error en la regla, no debería parar la validación
                issues.append(ValidationIssue(
                    rule_id=f"{rule.rule_id}_error",
                    severity=Severity.ERROR,
                    field="system",
                    message=f"Error ejecutando regla {rule.rule_id}: {str(e)}"
                ))

        return issues

    def validate_batch(self, datasets: List[Dict]) -> Dict[str, List[ValidationIssue]]:
        """
        Validar un lote de datasets.

        Returns:
            Dict {dataset_id: [issues]}
        """
        results = {}
        for dataset in datasets:
            dataset_id = dataset.get("dataset_id") or dataset.get("id", "unknown")
            results[dataset_id] = self.validate_dataset(dataset)
        return results

    def generate_report(self, issues: List[ValidationIssue]) -> str:
        """Generar reporte legible de problemas."""
        if not issues:
            return "✅ No se detectaron problemas en los metadatos"

        lines = ["📋 Reporte de Validación de Metadatos", "=" * 50]

        # Agrupar por severidad
        by_severity = defaultdict(list)
        for issue in issues:
            by_severity[issue.severity].append(issue)

        for severity in [Severity.CRITICAL, Severity.ERROR, Severity.WARNING, Severity.INFO]:
            if severity in by_severity:
                lines.append(f"\n🔴 {severity.value.upper()} ({len(by_severity[severity])})")
                for issue in by_severity[severity]:
                    lines.append(f"  • [{issue.rule_id}] {issue.field}: {issue.message}")
                    if issue.suggestion:
                        lines.append(f"    💡 {issue.suggestion}")

        return "\n".join(lines)


# Funciones auxiliares

def _expand_abbreviation(abbr: str) -> Optional[str]:
    """Expandir abreviaturas comunes de universidades/organizaciones."""
    expansions = {
        "UEX": "Universidad de Extremadura",
        "UB": "Universidad de Barcelona",
        "UAB": "Universidad Autónoma de Barcelona",
        "UCM": "Universidad Complutense de Madrid",
        "UPC": "Universidad Politécnica de Cataluña",
        "UPF": "Universidad Pompeu Fabra",
        "US": "Universidad de Sevilla",
        "UGR": "Universidad de Granada",
        "UVA": "Universidad de Valladolid",
        "UNED": "Universidad Nacional de Educación a Distancia",
        "CSIC": "Consejo Superior de Investigaciones Científicas",
        "INE": "Instituto Nacional de Estadística",
        "MITECO": "Ministerio para la Transición Ecológica",
        "MAPFRE": "Mutua Madrileña Automovilista",
        "CCAA": "Comunidad Autónoma",
        "AYTO": "Ayuntamiento",
        "DIP": "Diputación",
        "CAB": "Cabildo",
    }
    # Buscar case-insensitive
    abbr_upper = abbr.upper()
    return expansions.get(abbr_upper)


def _extract_org_abbreviations(text: str) -> Set[str]:
    """Extraer posibles abreviaturas de organizaciones del texto."""
    keywords = set()

    if not text:
        return keywords

    text_str = str(text)

    # Buscar patrones específicos: UEx, UAB, CSIC, etc. (mezcla de mayúsculas/minúsculas permitida)
    # Buscar palabras que parezcan abreviaturas de universidades
    abbreviations = re.findall(r'\b[Uu][A-Za-z]{1,4}\b', text_str)
    for abbr in abbreviations:
        keywords.add(abbr)

    # Buscar específicamente "Universidad de ..."
    universities = re.findall(r'Universidad de [\w\s]+?(?=\s|$|,|\.|\()', text_str)
    for uni in universities:
        keywords.add(uni.strip())

    # Comunidades autónomas (case insensitive)
    ccaa_list = [
        'Extremadura', 'Cataluña', 'Madrid', 'Andalucía',
        'Valencia', 'País Vasco', 'Galicia', 'Castilla y León',
        'Castilla-La Mancha', 'Aragón', 'Asturias', 'Cantabria',
        'La Rioja', 'Murcia', 'Navarra', 'Baleares', 'Canarias'
    ]
    for ccaa in ccaa_list:
        if re.search(ccaa, text_str, re.IGNORECASE):
            keywords.add(ccaa)

    return keywords


def _extract_territory_keywords(text: str) -> Set[str]:
    """Extraer referencias territoriales del texto."""
    keywords = set()

    # Comunidades autónomas
    ccaa = [
        "Extremadura", "Cataluña", "Madrid", "Andalucía", "Valencia",
        "País Vasco", "Galicia", "Castilla y León", "Castilla-La Mancha",
        "Aragón", "Asturias", "Cantabria", "La Rioja", "Murcia",
        "Navarra", "Baleares", "Canarias"
    ]

    for region in ccaa:
        if re.search(region, text, re.IGNORECASE):
            keywords.add(region)

    # Provincias españolas comunes
    provinces = [
        "Barcelona", "Madrid", "Sevilla", "Valencia", "Granada",
        "Badajoz", "Cáceres", "Mérida", "Salamanca", "Valladolid"
    ]

    for prov in provinces:
        if re.search(rf'\b{prov}\b', text, re.IGNORECASE):
            keywords.add(prov)

    return keywords


def _find_similar(value: str, candidates: Set[str], max_suggestions: int = 3) -> List[str]:
    """Encontrar valores similares usando distancia de edición simple."""
    from difflib import get_close_matches
    return get_close_matches(value, candidates, n=max_suggestions, cutoff=0.6)


# Tests
if __name__ == "__main__":
    print("Test del Validador de Metadatos")
    print("=" * 60)

    # Crear validador con reglas por defecto
    validator = MetadataValidator().add_default_rules()

    # Test 1: Dataset con inconsistencia UEx/Barcelona
    print("\n1. Test: Inconsistencia UEx ↔ Barcelona")
    dataset_problematic = {
        "dataset_id": "test-001",
        "title": "Proyectos Investigación UEx - Portal de Investigación",
        "description": "Proyectos de investigación de la Universidad de Extremadura",
        "publisher": "Universidad de Barcelona",
        "territory": "Cataluña",  # Inconsistente con UEx
        "theme": "investigacion",
        "format": "CSV"
    }

    issues = validator.validate_dataset(dataset_problematic)
    print(validator.generate_report(issues))

    # Test 2: Dataset correcto
    print("\n2. Test: Dataset correcto")
    dataset_correct = {
        "dataset_id": "test-002",
        "title": "Proyectos de Investigación",
        "description": "Proyectos activos",
        "publisher": "Universidad de Extremadura",
        "territory": "Extremadura",
        "theme": "ciencia",
        "format": "JSON"
    }

    issues = validator.validate_dataset(dataset_correct)
    print(validator.generate_report(issues))

    # Test 3: Dataset con campos vacíos
    print("\n3. Test: Campos vacíos")
    dataset_empty = {
        "dataset_id": "test-003",
        "title": "",
        "publisher": "   ",
        "theme": None
    }

    issues = validator.validate_dataset(dataset_empty)
    print(validator.generate_report(issues))

    # Test 4: Batch validation
    print("\n4. Test: Validación en batch")
    batch_results = validator.validate_batch([dataset_problematic, dataset_correct, dataset_empty])
    for ds_id, ds_issues in batch_results.items():
        print(f"  {ds_id}: {len(ds_issues)} problemas")

    print("\n" + "=" * 60)
    print("Tests completados")
