# ⚰️ Experimento Archivado: Normalización Conceptual

**Fecha creación**: 2026-06-05  
**Fecha archivo**: 2026-06-06  
**Estado**: **VÍA MUERTA - NO INCORPORAR**  
**Autor**: Fonta

---

## 🚫 DECISIÓN: NO INCORPORAR

Este experimento ha sido **archivado como vía muerta** tras evaluar que no hay mejora medible en la calidad de búsqueda.

---

## 📊 Resumen Post-Mortem

### Objetivo Original

Crear una capa de normalización conceptual que:
1. Detectara conceptos en queries (ej: "paro juvenil" → `desempleo_juvenil`)
2. Clasificara resultados como equivalente/relacionado/complementario/no_equivalente
3. Ajustara scores según clasificación

### Resultado Final

| Métrica | Target | Resultado | Estado |
|---------|--------|-----------|--------|
| Mejora P@5 | +5-10% | **0%** | ❌ |
| Mejora NDCG@10 | Apreciable | **0%** | ❌ |
| Clasificaciones útiles | >50% | **0%** | ❌ |
| Overhead latencia | <20ms | **-29ms** | ✅ |

### Datos de Evaluación Final

- **Diccionario**: 105 conceptos, 521 triggers, 11 dominios
- **Queries evaluadas**: 10
- **Resultados clasificados**: 100
- **Clasificaciones útiles**: 0 (100% "desconocido")

```
Distribución Conceptual (100 resultados):
├─ Equivalente: 0
├─ Relacionado: 0
├─ Complementario: 0
├─ No equivalente: 0
└─ Desconocido: 100 ← 100%
```

---

## 🔍 Causa Raíz del Fracaso

### Mismatch Terminológico

Los **títulos reales de datasets** usan lenguaje administrativo técnico que no coincide con los términos del diccionario:

| Nuestro Diccionario | Títulos Reales en BD |
|---------------------|---------------------|
| "paro juvenil" | "Paro registrado: 2005-2023. Evolución" |
| "desempleo" | "Tasa de desempleo de personas 16-74 años" |
| "vivienda" | "Tablas estadísticas de Edificación y Vivienda" |
| "educación" | "Alumnado matriculado por edad y sexo" |
| "hospitales" | "Población de 16 y más años según hospitalización" |

### Ejemplo Concreto

```
Query: "paro juvenil"
Concepto detectado: ✅ desempleo_juvenil

Resultado: "Paro registrado: 2005-2023. Evolución"
Términos en diccionario: ["paro juvenil", "desempleo juvenil", "jóvenes parados"]
Matching: ❌ NINGUNO coincide

Clasificación: "desconocido"
```

### Problema Fundamental

El enfoque de **diccionario manual** es insostenible para datos abiertos porque:

1. **Variación terminológica infinita**: Cada organismo usa su propia nomenclatura
2. **Lenguaje administrativo**: "Población de 16 y más años según..." vs "paro juvenil"
3. **Mantenimiento exponencial**: Cada nuevo concepto requiere 20-50 términos adicionales
4. **Falso positivo garantizado**: Siempre habrá títulos que no coincidan

---

## 📁 Archivos del Experimento

### Creados (Archivados)

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `config/conceptos_semanticos.yml` | Diccionario 105 conceptos | ⚰️ Archivado |
| `motor/concept_normalizer.py` | Módulo de normalización | ⚰️ Archivado |
| `tests/test_concept_normalizer.py` | 20 tests unitarios | ⚰️ Archivado |
| `docs/EXPERIMENTO_NORMALIZACION_CONCEPTUAL.md` | Esta documentación | ✅ Post-mortem |
| `entregables/conceptual_normalization_report.md` | Reporte evaluación | ⚰️ Archivado |

### Endpoints (No usar)

- `POST /experimental/concept-normalize` - ⚰️ No usar
- `POST /experimental/conceptual-search` - ⚰️ No usar
- Parámetros `conceptual_normalization`, `conceptual_adjust_scores` - ⚰️ Ignorar

---

## 🧠 Learnings

### Lo que NO funciona

| Enfoque | Por qué falla |
|---------|---------------|
| Diccionario manual de conceptos | Terminología administrativa infinita |
| Matching exacto de triggers | Títulos reales usan variaciones no previstas |
| Clasificación basada en keywords | Falsos negativos masivos |

### Lo que SÍ funciona (ya implementado)

| Enfoque | Por qué funciona |
|---------|------------------|
| **Búsqueda semántica con embeddings** | Captura similitud conceptual sin diccionario |
| **Expansión de sinónimos simple** (`sinonimos.json`) | Bajo coste, buen recall para queries cortas |
| **Query Preprocessor (#3,#4,#12)** | 44 datasets únicos encontrados, sin clasificación rígida |

---

## 📋 Recomendaciones Futuras

### NO hacer

- ❌ Ampliar el diccionario de conceptos
- ❌ Intentar matching fuzzy o regex
- ❌ Usar LLM para clasificación en tiempo real (latencia +10s)

### SÍ considerar

- ✅ Mantener búsqueda semántica como principal
- ✅ Mejorar `sinonimos.json` con términos administrativos reales
- ✅ Explorar fine-tuning de embeddings para dominio específico

---

## 🔗 Referencias

### Archivos Relacionados

- `motor/sinonimos.json` - Diccionario de sinónimos (SÍ usar)
- `motor/query_preprocessor.py` - Query Preprocessor #3,#4,#12 (SÍ usar)
- `motor/lexical_expander.py` - Expansión léxica fallback (SÍ usar)

### Evaluación

- `09_Sprint7_RAGAS/entregables/conceptual_normalization_report.json` - Resultados JSON
- `09_Sprint7_RAGAS/entregables/conceptual_normalization_report.md` - Reporte Markdown

---

*Documento de archivo - Experimento cerrado 2026-06-06*  
*No incorporar al flujo principal*  
*No reabrir sin evidencia de mejora medible*
