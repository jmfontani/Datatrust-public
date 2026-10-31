# Validador DCAT-AP-ES

Script de validación de datasets contra el perfil DCAT-AP-ES para documentación de cumplimiento.

## Características

- ✅ **Sin impacto en flujo actual**: Solo documenta, NO filtra datasets
- ✅ **Validación completa**: Campos obligatorios y recomendados
- ✅ **Reporte detallado**: Estadísticas de cumplimiento por campo
- ✅ **Identificación de problemas**: Datasets no conformes documentados
- ✅ **Integración continua**: Puede ejecutarse en CI/CD sin romper builds

## Uso

### Validación completa

```bash
cd 03_Sprint1_Ingesta/codigo/validacion

# Validar todos los datasets
python validate_dcat_ap_es.py \
    --input ../../datos/processed/datasets_clean.jsonl \
    --output reporte_dcat_completo.json
```

### Validación de muestra (para pruebas)

```bash
# Validar solo 1000 datasets
python validate_dcat_ap_es.py \
    --input ../../datos/processed/datasets_clean.jsonl \
    --output reporte_dcat_sample.json \
    --sample 1000
```

### Con salida verbose

```bash
python validate_dcat_ap_es.py \
    --input ../../datos/processed/datasets_clean.jsonl \
    --verbose
```

## Salida

El script genera:

1. **Reporte JSON** (`dcat_validation_report.json`) con:
   - Información de la validación (timestamp, estándar, etc.)
   - Estadísticas de cumplimiento
   - Distribución de estados
   - Cumplimiento por campo
   - Ejemplos de datasets no conformes

2. **Resumen en consola** con:
   - Total de datasets analizados
   - Porcentaje de cumplimiento obligatorio
   - Porcentaje de cumplimiento recomendado
   - Tabla de cumplimiento por campo

## Campos Validados

### Obligatorios (MUST)

| Campo | Descripción | Implementado |
|-------|-------------|--------------|
| `dct:title` | Título en español | ✅ Sí |
| `dct:description` | Descripción en español | ✅ Sí |
| `dct:publisher` | Organismo publicador | ✅ Sí |
| `dcat:theme` | Temas del dataset | ✅ Sí |

### Recomendados (SHOULD)

| Campo | Descripción | Implementado |
|-------|-------------|--------------|
| `dcat:keyword` | Palabras clave | ✅ Sí |
| `dct:spatial` | Cobertura geográfica | ✅ Sí |
| `dct:temporal` | Cobertura temporal | ✅ Sí |
| `dcat:distribution` | Distribuciones | ✅ Sí |
| `dct:license` | Licencia | ✅ Sí |
| `dct:issued` | Fecha publicación | ✅ Sí |
| `dct:modified` | Fecha modificación | ✅ Sí |
| `dcat:contactPoint` | Punto de contacto | ❌ No (HVD) |
| `dcatap:applicableLegislation` | Legislación aplicable | ❌ No (HVD) |

## Interpretación de Resultados

### Estados de un dataset

- **PASS**: Cumple todos los campos obligatorios y recomendados
- **FAIL_RECOMMENDED**: Cumple obligatorios, falta algún recomendado
- **FAIL_MANDATORY**: No cumple algún campo obligatorio

### Métricas Clave

1. **Mandatory Compliance**: % de datasets que cumplen campos obligatorios
2. **Recommended Compliance**: % de datasets que cumplen campos recomendados
3. **Field Compliance**: % de datasets que cumplen cada campo específico

### Ejemplo de Reporte

```json
{
  "validation_info": {
    "timestamp": "2026-05-27T10:00:00",
    "standard": "DCAT-AP-ES",
    "specification_url": "https://datosgobes.github.io/DCAT-AP-ES/",
    "total_rules_validated": 13
  },
  "summary": {
    "total_datasets": 87677,
    "mandatory_compliance": {
      "pass_count": 87677,
      "pass_percentage": 100.0
    },
    "recommended_compliance": {
      "pass_count": 82345,
      "pass_percentage": 93.9
    }
  }
}
```

## Integración en Pipeline

El script está diseñado para:

- ✅ **NO fallar** si hay datasets no conformes (exit code 0 siempre)
- ✅ Generar reportes para análisis posterior
- ✅ Permitir decidir si filtrar datasets más adelante

### Ejemplo de integración en script de ingesta

```bash
# Después de limpieza
python clean_datasets.py

# Validación DCAT-AP-ES (documentación solamente)
python validacion/validate_dcat_ap_es.py \
    --input datos/processed/datasets_clean.jsonl \
    --output datos/processed/dcat_validation_report.json

# Pipeline continúa sin interrupción
python build_indices.py
```

## Decisiones sobre Datos No Conformes

El reporte permite decidir posteriormente:

1. **Filtrar datasets obligatorios**: Descartar `FAIL_MANDATORY`
2. **Advertir recomendados**: Marcar `FAIL_RECOMMENDED` pero mantener
3. **Mantener todo**: Usar todos los datasets independientemente del estado

**Nota**: El proyecto actual **mantiene todos los datasets** sin filtrar, documentando el estado de cumplimiento.

## Referencias

- **DCAT-AP-ES**: https://datosgobes.github.io/DCAT-AP-ES/
- **Linked Data API**: http://purl.org/linked-data/api/vocab
- **DCAT-AP (EU)**: https://joinup.ec.europa.eu/collection/semantic-interoperability-community-solution/dcat-ap
