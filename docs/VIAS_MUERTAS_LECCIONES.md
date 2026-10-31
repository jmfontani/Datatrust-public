# Vías Muertas y Lecciones Aprendidas

> **Fecha:** 2026-06-08  
> **Autor:** TFM - Buscador Semántico de Open Data  
> **Propósito:** Documentar experimentos fallidos y lecciones extraídas para la memoria del TFM

---

## 📊 Resumen Ejecutivo

| Experimento | Duración | Resultado | Lección Principal |
|-------------|----------|-----------|-------------------|
| Normalización Conceptual (#8) | 2 días | ❌ 0% mejora | Diccionarios manuales no escalan |
| Búsqueda Semántica Pura | 1 día | ❌ Fallback necesario | Descripciones cortas → embeddings pobres |
| LLM-only Ranking | 1 día | ❌ 42s/query | Inviable en tiempo real |
| Conceptual Search API | 1 día | ❌ 100% "desconocido" | Mismatch terminológico |

**Total tiempo invertido:** ~5 días  
**Valor para la memoria:** Alto (justifica decisiones de diseño)

---

## 🪦 Experimento #1: Normalización Conceptual (Caso #8)

### Ficha Técnica

| Campo | Valor |
|-------|-------|
| **Sprint** | #6 (LLM - Mejora) |
| **Fecha** | 2026-06-05 → 2026-06-06 |
| **Archivado** | 2026-06-06 |
| **Rama Git** | `experiment/conceptual-normalization` |
| **Estado** | ⚰️ Archivado (NO incorporar) |

### Objetivo

Crear una capa de normalización conceptual que mapeara términos coloquiales a conceptos administrativos:

```
"paro juvenil" → desempleo_juvenil → [datasets equivalentes]
```

### Implementación

**Archivos creados:**
| Archivo | Líneas | Estado |
|---------|--------|--------|
| `conceptos_semanticos.yml` | 2,857 | ⚰️ Archivado |
| `concept_normalizer.py` | 592 | ⚰️ Archivado |
| `test_concept_normalizer.py` | 378 | ⚰️ Archivado |

**Diccionario creado:**
- 105 conceptos
- 521 triggers (términos de activación)
- 11 dominios temáticos

### Evaluación

| Métrica | Target | Resultado | Estado |
|---------|--------|-----------|--------|
| Mejora P@5 | +5-10% | **0%** | ❌ |
| Mejora NDCG@10 | Apreciable | **0%** | ❌ |
| Clasificaciones útiles | >50% | **0%** | ❌ |

**Distribución de 100 resultados clasificados:**
```
├─ Equivalente: 0
├─ Relacionado: 0
├─ Complementario: 0
├─ No equivalente: 0
└─ Desconocido: 100 ← 100%
```

### Causa Raíz del Fracaso

**Mismatch terminológico:** Los títulos reales de datasets usan lenguaje administrativo técnico que no coincide con el diccionario coloquial.

| Nuestro Diccionario | Títulos Reales en BD |
|---------------------|---------------------|
| "paro juvenil" | "Paro registrado: 2005-2023. Evolución" |
| "desempleo" | "Tasa de desempleo de personas 16-74 años" |
| "vivienda" | "Tablas estadísticas de Edificación y Vivienda" |
| "educación" | "Alumnado matriculado por edad y sexo" |
| "hospitales" | "Población de 16 y más años según hospitalización" |

**Ejemplo concreto:**
```
Query: "paro juvenil"
Concepto detectado: ✅ desempleo_juvenil

Resultado: "Paro registrado: 2005-2023. Evolución"
Términos en diccionario: ["paro juvenil", "desempleo juvenil", "jóvenes parados"]
Matching: ❌ NINGUNO coincide

Clasificación: "desconocido"
```

### Lección Aprendida

> **Los diccionarios manuales de conceptos no son sostenibles para datos abiertos.**

**Razones:**
1. Variación terminológica infinita — cada organismo usa su nomenclatura
2. Lenguaje administrativo — los títulos reales son técnicos, no coloquiales
3. Mantenimiento exponencial — cada concepto requiere 20-50 términos adicionales
4. Falso positivo garantizado — siempre habrá títulos no previstos

### ¿Qué SÍ funciona?

| Enfoque | Por qué funciona |
|---------|------------------|
| Búsqueda semántica con embeddings | Captura similitud sin diccionario |
| Expansión de sinónimos simple | Bajo coste, buen recall |
| Query Preprocessor (#3, #4, #12) | 44 datasets únicos, sin clasificación rígida |

### Referencias

- **Archivos:** `08_Sprint6_LLM_Mejora/codigo/motor/concept_normalizer.py` (archivado)
- **Documentación:** `08_Sprint6_LLM_Mejora/docs/EXPERIMENTO_NORMALIZACION_CONCEPTUAL.md`
- **Rama Git:** `experiment/conceptual-normalization`

---

## 🪦 Experimento #2: Búsqueda Semántica Pura

### Ficha Técnica

| Campo | Valor |
|-------|-------|
| **Sprint** | #2 |
| **Fecha** | 2026-05-18 → 2026-05-19 |
| **Estado** | ❌ Descartado |
| **Rama Git** | `experiment/pure-semantic` (eliminada) |

### Objetivo

Implementar búsqueda usando **exclusivamente** similitud de embeddings (pgvector), sin fallback léxico.

### Implementación

```python
# Pseudo-código del experimento
results = semantic_search(query)  # Solo pgvector
return results
```

### Evaluación

**Queries problemáticas:**

| Query | Problema |
|-------|----------|
| "BOE-A-2023-12345" | Embedding no captura IDs exactos |
| "EPA" | Embedding no prioriza acrónimos |
| "paro juvenil Canarias 2023" | Embedding ignora filtros temporales/territoriales |

**Resultado:** Precisión <30% en queries específicas.

### Causa Raíz del Fracaso

**Hallazgo posterior del análisis de metadatos:** 72.5% de descripciones tienen <50 palabras.

**Consecuencia:** Embeddings de texto corto son poco discriminativos → muchos falsos positivos/negativos.

### Lección Aprendida

> **La búsqueda semántica pura falla con descripciones cortas.**

**Justificación del híbrido:**
- FTS (léxica): exacto para términos específicos
- pgvector (semántica): conceptual, sinónimos
- LLM (re-ranking): contextual

### ¿Qué SÍ funciona?

**Arquitectura híbrida actual:**
```
Query → FTS + pgvector → Merge → LLM re-ranking (opcional) → Resultados
```

---

## 🪦 Experimento #3: LLM-only Ranking

### Ficha Técnica

| Campo | Valor |
|-------|-------|
| **Sprint** | #6 |
| **Fecha** | 2026-05-22 → 2026-05-23 |
| **Estado** | ❌ Descartado |
| **Rama Git** | `experiment/llm-only` (eliminada) |

### Objetivo

Usar LLM (Ollama) para **todo** el ranking de resultados, sin FTS ni pgvector.

### Implementación

```python
# Pseudo-código del experimento
all_datasets = get_all_datasets()  # 87.676 datasets
ranked = llm_rank(query, all_datasets)  # LLM rank completo
return ranked[:10]
```

### Evaluación

| Métrica | Valor | Estado |
|---------|-------|--------|
| Tiempo por query | **42s** | ❌ Inviable |
| Tokens consumidos | ~5000/query | ❌ Coste alto |
| Precisión | Similar a híbrido | ⚠️ Sin mejora |

**Comparación con baseline:**

| Método | P@5 | Tiempo |
|--------|-----|--------|
| Híbrido (baseline) | 0.279 | 0.8s |
| LLM-only | 0.225 | 42s |

### Causa Raíz del Fracaso

**Latencia prohibitiva:** 42 segundos por query vs 0.8s del híbrido.

**Token cost:** ~5000 tokens/query × 48 queries RAGAS = 240k tokens (solo evaluación).

### Lección Aprendida

> **LLM es útil para tareas específicas, no para procesamiento completo.**

**Uso adecuado del LLM:**
- Query preprocessing (interpretación, expansión)
- Re-ranking de top-10 resultados
- Explicación de resultados

**Uso inadecuado:**
- Ranking de corpus completo (87k datasets)
- Tiempo real con latencia <1s

---

## 🪦 Experimento #4: Conceptual Search API

### Ficha Técnica

| Campo | Valor |
|-------|-------|
| **Sprint** | #6 |
| **Fecha** | 2026-06-05 |
| **Estado** | ⚰️ Archivado con Caso #8 |

### Objetivo

Endpoints dedicados para búsqueda conceptual:
- `POST /experimental/concept-normalize`
- `POST /experimental/conceptual-search`

### Evaluación

**Resultados:**
- 100% de clasificaciones = "desconocido"
- 0% de mejora en precisión
- -29ms de overhead (tiempo perdido)

### Lección Aprendida

> **No añadir complejidad sin beneficio medible.**

---

## 📈 Patrón de Fracaso Común

### Análisis Transversal

Todos los experimentos fallidos comparten un patrón:

| Patrón | Manifestación |
|--------|---------------|
| **Complejidad innecesaria** | Diccionarios manuales, LLM-only |
| **Ignorar características de datos** | Descripciones cortas, lenguaje administrativo |
| **Sin validación temprana** | Evaluación posterior al desarrollo |

### Anti-patrones Identificados

1. **Diccionario infinito** — Intentar mapear todo el vocabulario coloquial al administrativo
2. **LLM como solución mágica** — Usar LLM donde no aporta valor diferencial
3. **Pureza arquitectónica** — "Solo semántico", "solo LLM" vs pragmático/híbrido
4. **Validación tardía** — Evaluar después de implementar, no antes

---

## ✅ Lo que SÍ Funcionó

### Decisiones Correctas

| Decisión | Resultado |
|----------|-----------|
| **Híbrido FTS + pgvector** | P@5 = 0.279, 0.8s/query |
| **Fallback léxico** | Queries exactas funcionan |
| **LLM para preprocessing** | 44 datasets únicos encontrados |
| **Query expansion simple** | Sinónimos de bajo coste |
| **Análisis de metadatos antes de diseñar** | Evitó diseño incorrecto |

### Factores de Éxito

1. **Validación continua** — RAGAS después de cada sprint LLM
2. **Ground truth compartido** — 48 queries como referencia común
3. **Pragmatismo sobre pureza** — Híbrido > "solo X"
4. **Documentar vías muertas** — Lecciones para la memoria

---

## 📋 Conexión con Decisiones de Diseño

### Tabla Resumen

| Experimento Fallido | Decisión de Diseño Resultante | Sprint |
|---------------------|------------------------------|--------|
| Normalización Conceptual | Query Preprocessor flexible (#3, #4, #12) | #6 |
| Búsqueda Semántica Pura | Fallback léxico obligatorio | #4 |
| LLM-only Ranking | LLM solo para top-10 re-ranking | #6 |
| Conceptual Search API | Endpoints simples, sin complejidad | #6 |

### Justificación de Arquitectura Final

```
┌─────────────────────────────────────────────────────────┐
│                    QUERY DEL USUARIO                     │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ PostgreSQL FTS  │     │   pgvector      │
│ (léxica, rápido)│     │ (semántica)     │
│ ✅ Funciona     │     │ ✅ Funciona     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌─────────────────────┐
         │   LLM Re-ranking    │
         │ (top-10, opcional)  │
         │ ✅ Funciona         │
         └─────────────────────┘
```

**Cada componente está justificado por un experimento fallido:**
- FTS ← Búsqueda semántica pura falló
- pgvector ← Fallback necesario para sinonimia
- LLM limitado ← LLM-only fue inviable (42s)

---

## 🎓 Lecciones para la Memoria del TFM

### Capítulo Sugerido

```
CAPÍTULO X: Vías Muertas y Lecciones Aprendidas

X.1 Introducción
    - Por qué documentar fracasos
    - Metodología de experimentación

X.2 Normalización Conceptual (Caso #8)
    - Objetivo y motivación
    - Implementación (2,857 líneas de conceptos)
    - Evaluación (0% mejora)
    - Causa raíz: mismatch terminológico
    - Lección: diccionarios manuales no escalan

X.3 Búsqueda Semántica Pura
    - Hipótesis inicial
    - Problema: descripciones cortas (72.5% <50 palabras)
    - Solución: híbrido FTS + pgvector

X.4 LLM-only Ranking
    - Promesa del LLM
    - Realidad: 42s/query
    - Solución: LLM solo para preprocessing y top-10

X.5 Síntesis: Arquitectura Híbrida
    - Cada componente justificado por un fracaso
    - Pragmatismo sobre pureza

X.6 Recomendaciones para Futuros Investigadores
    - Validar temprano
    - Medir antes de asumir
    - Documentar vías muertas
```

---

## 🔗 Referencias Cruzadas

| Documento | Ruta | Propósito |
|-----------|------|-----------|
| Experimento Normalización | `08_Sprint6_LLM_Mejora/docs/EXPERIMENTO_NORMALIZACION_CONCEPTUAL.md` | Post-mortem detallado |
| Análisis de Metadatos | `docs/ANALISIS_METADATOS.md` | Justifica diseño híbrido |
| Narrativa TFM | `docs/NARRATIVA_TFM.md` | Camino seguido completo |
| Estrategia Git | `docs/ESTRATEGIA_GIT.md` | Ramas de experimentos |

---

*Documento generado como parte del TFM - Buscador Semántico de Open Data*
