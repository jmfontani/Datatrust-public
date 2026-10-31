# Sistema General de Validación de Metadatos

## Propósito

Detectar **inconsistencias, anomalías y errores de calidad** en metadatos de datasets de forma automática y configurable, sin depender de casos específicos hardcodeados.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    MetadataValidator                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Colección de Reglas                      │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐  │  │
│  │  │   Reglas    │ │   Reglas    │ │     Reglas      │  │  │
│  │  │   Campo     │ │  Cruzadas   │ │   Anomalías     │  │  │
│  │  │  Único      │ │             │ │                 │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Dataset (dict)                           │  │
│  │  {                                                    │  │
│  │    "title": "Proyectos UEx...",                      │  │
│  │    "publisher": "Universidad de Barcelona",          │  │
│  │    "territory": "Cataluña",                           │  │
│  │    ...                                                │  │
│  │  }                                                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           Lista de ValidationIssue                    │  │
│  │  [                                                    │  │
│  │    {                                                  │  │
│  │      severity: WARNING,                               │  │
│  │      field: "publisher",                              │  │
│  │      message: "Inconsistencia..."                     │  │
│  │    }                                                  │  │
│  │  ]                                                    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Tipos de Reglas

### 1. Reglas de Campo Único

Validan un campo específico de forma aislada.

```python
ValidationRule.required_field("title", severity=Severity.ERROR)
ValidationRule.field_format("format", r"^(CSV|JSON|XML)$", "Formato estándar")
```

**Casos de uso:**
- Campos obligatorios no vacíos
- Formatos consistentes (fechas, emails, etc.)
- Rangos de valores numéricos

### 2. Reglas de Campos Cruzados

Validan consistencia entre múltiples campos.

```python
ValidationRule.cross_field_pattern(
    source_field="title",
    target_field="publisher",
    extract_keywords=_extract_org_abbreviations
)
```

**Casos de uso:**
- Si `title` menciona "UEx", `publisher` debería ser "Universidad de Extremadura"
- Si `title` menciona "Barcelona", `territory` debería ser "Cataluña"
- El `theme` debería ser consistente con palabras clave del `description`

### 3. Reglas de Anomalías Estadísticas

Detectan valores atípicos basados en referencias históricas.

```python
ValidationRule.statistical_anomaly(
    field_name="theme",
    reference_values=["economia", "empleo", "demografia"],
    threshold=0.3
)
```

**Casos de uso:**
- Un publisher que normalmente publica "educación" aparece con "agricultura"
- Temas inesperados para ciertos territorios
- Formatos de archivo inusuales

## Extensibilidad

### Crear una Regla Personalizada

```python
def my_custom_check(dataset: Dict) -> Optional[ValidationIssue]:
    """Verificar condición específica."""
    if dataset.get("title") == dataset.get("description"):
        return ValidationIssue(
            rule_id="duplicate_title_description",
            severity=Severity.WARNING,
            field="description",
            message="Título y descripción son idénticos",
            suggestion="Hacer la descripción más detallada que el título"
        )
    return None

rule = ValidationRule(
    rule_id="no_duplicate_content",
    name="Sin contenido duplicado",
    description="Verifica que título y descripción sean distintos",
    severity=Severity.WARNING,
    check_function=my_custom_check
)

validator = MetadataValidator()
validator.add_rule(rule)
```

### Agregar Nuevas Abreviaturas

```python
def _expand_abbreviation(abbr: str) -> Optional[str]:
    expansions = {
        "UEx": "Universidad de Extremadura",
        "UB": "Universidad de Barcelona",
        "UC3M": "Universidad Carlos III de Madrid",  # Nueva
        "UPNA": "Universidad Pública de Navarra",     # Nueva
        # ...
    }
    return expansions.get(abbr.upper())
```

## Uso

### Validación Básica

```python
from metadata_validator import MetadataValidator

validator = MetadataValidator().add_default_rules()

# Validar un dataset
dataset = {
    "title": "Proyectos Investigación UEx",
    "publisher": "Universidad de Barcelona",  # ¡Inconsistente!
    "territory": "Cataluña",
    "theme": "investigacion",
    "format": "CSV"
}

issues = validator.validate_dataset(dataset)

for issue in issues:
    print(f"[{issue.severity}] {issue.field}: {issue.message}")
    if issue.suggestion:
        print(f"  💡 {issue.suggestion}")
```

### Validación en Batch

```python
datasets = [...]  # Lista de datasets

results = validator.validate_batch(datasets)

for dataset_id, issues in results.items():
    if issues:
        print(f"{dataset_id}: {len(issues)} problemas")
```

### Generar Reporte

```python
report = validator.generate_report(issues)
print(report)
```

Salida:
```
📋 Reporte de Validación de Metadatos
==================================================

🔴 WARNING (1)
  • [cross_pattern_title_publisher] publisher: Inconsistencia: 'title' menciona ['UEx'] pero 'publisher' no lo refleja
    💡 Verificar que publisher corresponda al contenido de title
```

## Integración con el Pipeline de Ingesta

### Uso Recomendado

```python
# En el script de ingesta de datos
from metadata_validator import MetadataValidator

validator = MetadataValidator().add_default_rules()

def process_dataset(raw_dataset):
    """Procesar dataset con validación."""
    # Validar antes de insertar
    issues = validator.validate_dataset(raw_dataset)

    # Separar por severidad
    critical = [i for i in issues if i.severity == Severity.CRITICAL]
    warnings = [i for i in issues if i.severity == Severity.WARNING]

    if critical:
        # Log error y descartar/marcar para revisión
        log.error(f"Dataset {raw_dataset['id']} tiene errores críticos")
        return None, issues

    if warnings:
        # Log warning pero permitir ingesta
        log.warning(f"Dataset {raw_dataset['id']} tiene advertencias")

    return clean_dataset, issues
```

## Reglas por Defecto Incluidas

| Regla | Tipo | Descripción |
|-------|------|-------------|
| `required_title` | Campo | Título no puede estar vacío |
| `required_publisher` | Campo | Publisher obligatorio |
| `required_theme` | Campo | Tema obligatorio |
| `cross_pattern_title_publisher` | Cruzada | Título debe coincidir con publisher |
| `cross_pattern_title_territory` | Cruzada | Título debe coincidir con territorio |
| `format_standard` | Campo | Formato debe ser estándar |

## Caso Real: UEx vs Barcelona

```python
dataset = {
    "title": "Proyectos Investigación UEx - Portal de Investigación",
    "publisher": "Universidad de Barcelona",  # ⚠️ Error!
    "territory": "Cataluña",
}

# El validador detecta:
# 1. Extrae "UEx" del título
# 2. Expande a "Universidad de Extremadura"
# 3. Verifica si está en publisher: "Universidad de Barcelona"
# 4. ❌ No está → Genera WARNING
```

## Futuras Mejoras

### Validación Semántica con Embeddings

```python
# Verificar coherencia semántica entre campos
def semantic_coherence_check(dataset: Dict) -> Optional[ValidationIssue]:
    title_embedding = embed(dataset["title"])
    description_embedding = embed(dataset["description"])

    similarity = cosine_similarity(title_embedding, description_embedding)

    if similarity < 0.5:
        return ValidationIssue(
            severity=Severity.WARNING,
            field="description",
            message="Descripción no parece relacionarse con el título",
            # Usar LLM para sugerir mejora
            suggestion=llm_suggest_better_description(dataset)
        )
```

### Aprendizaje de Patrones

```python
# Aprender patrones normales de publishers
publisher_themes = defaultdict(lambda: defaultdict(int))

# Entrenamiento con datos históricos
for dataset in training_data:
    publisher_themes[dataset["publisher"]][dataset["theme"]] += 1

# Detectar anomalías
if dataset["theme"] not in publisher_themes[dataset["publisher"]]:
    return ValidationIssue(
        severity=Severity.WARNING,
        message=f"'{dataset['publisher']}' normalmente publica temas diferentes"
    )
```

## Tests

Ejecutar tests:

```bash
cd 08_Sprint6_LLM_Mejora/codigo/validator
python metadata_validator.py
```

## Referencias

- `metadata_validator.py` - Implementación principal
- `SISTEMA_VALIDACION.md` - Este documento
