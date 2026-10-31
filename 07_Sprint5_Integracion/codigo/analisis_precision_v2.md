# Análisis de Precisión - Buscador Semántico V2 (PostgreSQL)

## Fecha: 2026-05-25
## Entorno: PostgreSQL 15.4 + pgvector (87,676 datasets)
## Comparativa: NumPy (91.85%) vs PostgreSQL (88.5%)

---

## Resumen Ejecutivo

La migración a PostgreSQL/pgvector mantiene una precisión del **88.5%** frente al **91.85%** de NumPy, con una degradación de **~3.3 puntos porcentuales**. Los casos problemáticos identificados son:

| Query | Precisión PostgreSQL | Problema Raíz |
|-------|---------------------|---------------|
| censo | 0% | Embedding semántico asocia "censo" a "cotización/estadísticas tributarias" en lugar de "demografía/población" |
| delitos | 40% | Resultados mixtos: datasets de "sector público" con menciones tangenciales |
| bibliotecas | 60% | Datasets con múltiples temas genéricos desplazan resultados específicos |
| hoteles | 80% | Un resultado de "sector público" (estadísticas) mezcla con turismo |
| paro | 20% | Con sinónimos funciona bien (3/5 relevantes), sin sinónimos falla |

---

## Diagnóstico Detallado

### 1. Problema: "censo" → 0% precisión

**Análisis:**
- El embedding semántico asocia "censo" con "cotización, estadística tributaria, IRPF" (tema: economía/hacienda)
- La búsqueda léxica encuentra "censo electoral", "censo de locales", "censo agrario" pero con scores bajos
- **No existe** un dataset titulado exactamente "Censo de Población" con `theme='demografia'` en los top results

**Verificación en BD:**
```sql
-- Datasets con 'censo' en título + demografía existen:
-- "Censo Anual de Población" (theme: demografia)
-- "Censo de Población y Viviendas" (theme: demografia)
-- Pero el embedding no los posiciona en top-5
```

**Causa raíz:** El modelo `paraphrase-multilingual-MiniLM-L12-v2` fue entrenado con datos generales. En el contexto de datos.gob.es, "censo" aparece más frecuentemente en contextos de "censo electoral", "censo de locales comerciales" que en "censo de población", sesgando el embedding.

### 2. Problema: "delitos" → 40% precisión

**Análisis:**
- Resultado #1: "Delitos" (theme: legislacion justicia) ✅
- Resultado #2: "Hechos conocidos de infracciones penales" (theme: sector publico) ⚠️
- Resultado #3: "Clasificación de tipos de infracciones penales" (theme: sector publico) ⚠️

**Causa raíz:** Los datasets del ISTAC (Canarias) clasifican temas como "sector publico" en lugar de "legislacion justicia", aunque el contenido sea sobre delitos. La clasificación temática de la fuente original es inconsistente.

### 3. Problema: "bibliotecas" → 60% precisión

**Análisis:**
- Resultado #3: Dataset con tema genérico que incluye 20+ categorías ("ciencia tecnologia, comercio, cultura ocio, demografia, deporte, economia, educacion, empleo, energia, hacienda, industria, legislacion justicia, medio ambiente, medio rural pesca, salud, sector publico, seguridad, sociedad bienestar, transporte, turismo")
- Este dataset es un "esquema de conceptos" genérico, no específico de bibliotecas

**Causa raíz:** Metadatos de baja calidad en la fuente original. Datasets esquema/catalogo reciben clasificaciones temáticas exhaustivas que no reflejan su contenido real.

### 4. Problema: "hoteles" → 80% precisión

**Análisis:**
- Resultado #1: "Número de establecimientos hoteleros por tipo" (theme: sector publico) ⚠️
- Este dataset es estadístico/turístico pero clasificado como "sector publico"

**Causa raíz:** Inconsistencia en la clasificación temática de la fuente. Estadísticas de turismo a veces se clasifican como "sector publico".

---

## Factores de Degradación (PostgreSQL vs NumPy)

### Factor 1: Diferencias en la fórmula de score

**NumPy (original):**
- Score = 0.6 * cosine_similarity + 0.4 * lexical_score
- Cosine similarity calculado directamente con NumPy
- Lexical score: simple TF-IDF o conteo de términos

**PostgreSQL (nuevo):**
- Score = 0.6 * (1 - embedding <=> query_vector) + 0.4 * ts_rank_cd
- `embedding <=> query_vector` = distancia euclídea en pgvector (NO cosine similarity)
- `ts_rank_cd` = ranking de PostgreSQL full-text search

**Problema:** `embedding <=> query_vector` usa distancia euclídea, no cosine similarity. Aunque para vectores normalizados son equivalentes, puede haber diferencias numéricas.

### Factor 2: Umbral min_score = 0.15

En `main_v2_final.py`:
```python
min_score: float = Field(default=0.15, ge=0, le=1)
```

Esto filtra resultados con score < 0.15. En NumPy no había umbral explícito, permitiendo más resultados de bajo score que podrían ser relevantes.

### Factor 3: top_k * 3 en cada búsqueda

```python
LIMIT %s  -- request.top_k * 3
```

Se recuperan 15 resultados de cada motor (semántico y léxico), se fusionan, y se devuelven top 5. Si un motor devuelve 15 resultados de baja calidad, pueden desplazar resultados buenos del otro motor.

### Factor 4: Inconsistencia en clasificación temática

La BD PostgreSQL usa los temas **exactamente como vienen de datos.gob.es**, sin normalización. Los temas son inconsistentes:
- `demografia` vs `["demografia"]` (con comillas)
- `sector publico` para datasets de turismo, justicia, etc.
- Múltiples temas concatenados en un solo string

---

## Oportunidades de Mejora

### Mejora 1: Ajustar pesos por tipo de query (ALTO IMPACTO)

Implementar clasificador de query que ajuste pesos:
- Query corta (1 palabra) → más peso léxico (0.4 sem, 0.6 lex)
- Query específica (2+ palabras) → más peso semántico (0.7 sem, 0.3 lex)
- Query ambigua → usar expansión de sinónimos + filtrado

### Mejora 2: Query expansion con contexto (MEDIO IMPACTO)

Para queries de 1 palabra, expandir automáticamente:
- "censo" → "censo población demografía"
- "delitos" → "delitos criminalidad infracciones penales"
- "bibliotecas" → "bibliotecas cultura ocio"

Esto guía al embedding hacia el contexto correcto.

### Mejora 3: Normalizar y limpiar temas (MEDIO IMPACTO)

- Unificar `demografia` vs `["demografia"]`
- Reclasificar datasets mal clasificados (especialmente ISTAC)
- Crear índice de temas normalizados

### Mejora 4: Usar cosine similarity en lugar de distancia euclídea (BAJO IMPACTO)

En pgvector:
```sql
-- Actual (distancia euclídea):
ORDER BY embedding <=> query_vector

-- Mejorado (cosine similarity):
ORDER BY embedding <=> query_vector  -- para vectores normalizados, equivalente
-- O explícitamente:
1 - (embedding <=> query_vector) as similarity
```

Verificar que los embeddings estén normalizados (magnitud = 1).

### Mejora 5: Re-ranking con cross-encoder (ALTO IMPACTO, ALTO COSTE)

Usar un modelo cross-encoder (como `cross-encoder/ms-marco-MiniLM-L-6-v2`) para re-rankear los top-20 resultados. Esto captura relaciones query-documento más finas que los embeddings independientes.

---

## Métricas Actuales (PostgreSQL)

```
Queries exitosas: 26/26 (100%)
Precisión promedio@5: 88.5%
Tiempo promedio: 28ms
```

Por categoría:
- economia: 100%
- educacion: 100%
- energia: 100%
- medio ambiente: 100%
- salud: 100%
- transporte: 100%
- urbanismo infraestructuras: 100%
- turismo: 93%
- cultura ocio: 80%
- seguridad: 70%
- demografia: 50%
- empleo: 20%
```

---

## Recomendaciones Prioritarias

1. **Inmediata (hoy):** Implementar query expansion automática para palabras clave problemáticas
2. **Corta (esta semana):** Ajustar pesos dinámicos según longitud de query
3. **Media (Sprint 6):** Normalizar temas y limpiar metadatos
4. **Larga (post-Sprint):** Evaluar cross-encoder para re-ranking

---

*Documento generado automáticamente durante análisis de precisión*
