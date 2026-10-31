# 📊 Informe de Evaluación RAGAS - Buscador Semántico de Datasets

**Fecha de generación**: 2026-06-04
**Versión**: v3 (ground truth actualizado)

---

## 🎯 Resumen Ejecutivo

Este informe presenta los resultados de la evaluación sistemática del Buscador Semántico de Datasets Públicos utilizando métricas adaptadas del framework **RAGAS** (Retrieval Augmented Generation Assessment).

**Evaluación completada**: 48 queries en dos modos (básico vs LLM re-ranking)

---

## 📈 Comparación: Modo Básico vs Modo LLM

| Métrica | Básico | LLM | Mejoría | Estado |
|---------|--------|-----|---------|--------|
| **Precision@5** | 0.279 | 0.225 | -19% | ❌ Empeora |
| **Precision@10** | 0.173 | 0.173 | 0% | ⚠️ Igual |
| **NDCG@10** | 0.653 | 0.640 | -2% | ❌ Empeora |
| **Recall** | 2.050 | 1.931 | -6% | ❌ Empeora |
| **Tiempo/query** | 0.03s | 42.10s | -1400x | ❌ Mucho más lento |

### 🚨 Hallazgo Principal

**El re-ranking con LLM no aporta valor** en su estado actual:
- 1400x más lento (42s vs 0.03s por query)
- Precisión ligeramente inferior en todas las métricas
- No mejora el ranking de resultados relevantes

**Recomendación**: Desactivar re-ranking LLM hasta mejorar el prompt o modelo.

---

## 🔍 Evaluación: Modo Básico (sin LLM)

- **Queries evaluadas**: 48
- **Tiempo total**: 1.5s
- **Tiempo medio por query**: 0.03s

### Métricas Principales

| Métrica | Valor | Target | Estado |
|---------|-------|--------|--------|
| Precision At 5 | 0.279 | 0.80 | ❌ |
| Precision At 10 | 0.173 | 0.70 | ❌ |
| Ndcg At 10 | 0.653 | 0.75 | ⚠️ |
| Recall | 2.050 | 0.80 | ✅ |

### Por Categoría

| Categoría | Precision@5 | NDCG@10 | Queries |
|-----------|-------------|---------|---------|
| Medio Ambiente | 0.480 | 0.971 | 5 |
| Educación | 0.480 | 0.802 | 5 |
| Deporte | 0.360 | 0.829 | 5 |
| Transporte | 0.280 | 0.857 | 5 |
| Cultura | 0.240 | 0.746 | 5 |
| Sanidad | 0.240 | 0.538 | 5 |
| Economía | 0.200 | 0.600 | 5 |
| Demografía | 0.200 | 0.307 | 5 |
| Empleo | 0.160 | 0.533 | 5 |
| Ambigua | 0.067 | 0.153 | 3 |

### Por Dificultad

| Dificultad | Precision@5 | NDCG@10 | Queries |
|------------|-------------|---------|---------|
| Media | 0.300 | 0.701 | 28 |
| Fácil | 0.273 | 0.649 | 11 |
| Difícil | 0.222 | 0.510 | 9 |

---

## 🤖 Evaluación: Modo LLM (con re-ranking)

- **Queries evaluadas**: 48
- **Tiempo total**: 2020.6s (33.7 min)
- **Tiempo medio por query**: 42.10s

### Métricas Principales

| Métrica | Valor | Target | Estado |
|---------|-------|--------|--------|
| Precision At 5 | 0.225 | 0.80 | ❌ |
| Precision At 10 | 0.173 | 0.70 | ❌ |
| Ndcg At 10 | 0.640 | 0.75 | ⚠️ |
| Recall | 1.931 | 0.80 | ✅ |

### Por Categoría

| Categoría | Precision@5 | NDCG@10 | Queries |
|-----------|-------------|---------|---------|
| Medio Ambiente | 0.400 | 0.740 | 5 |
| Sanidad | 0.240 | 0.770 | 5 |
| Economía | 0.240 | 0.607 | 5 |
| Educación | 0.240 | 0.383 | 5 |
| Deporte | 0.240 | 0.965 | 5 |
| Cultura | 0.240 | 0.422 | 5 |
| Transporte | 0.200 | 0.811 | 5 |
| Ambigua | 0.133 | 0.667 | 3 |
| Demografía | 0.160 | 0.417 | 5 |
| Empleo | 0.120 | 0.633 | 5 |

---

## 📝 Conclusiones y Recomendaciones

### Problemas Identificados

1. **Ground truth desactualizado**: Los patrones de título originales no coincidían con datasets reales. Fue necesario regenerar el ground truth con patrones extraídos de resultados reales.

2. **Re-ranking LLM ineficaz**: El LLM no mejora el ranking. Posibles causas:
   - Prompt no optimizado para re-ranking
   - Modelo LLM no adecuado para esta tarea
   - Criterio de relevancia del LLM no alineado con ground truth

3. **Queries ambiguas problemáticas**: Términos como "paro", "banco", "planta" tienen P@5=0.067 porque el sistema no filtra bien sin contexto adicional.

4. **Falta de sinónimos en dominio específico**: El diccionario léxico no cubre todos los términos técnicos.

### Recomendaciones Prioritarias

| Prioridad | Acción | Impacto Esperado |
|-----------|--------|------------------|
| 🥇 Alta | Desactivar re-ranking LLM por defecto | Reducir latencia 1400x sin pérdida de calidad |
| 🥇 Alta | Mejorar filtrado de palabras ambiguas | P@5 de 0.067 → 0.40+ en queries ambiguas |
| 🥈 Media | Expandir diccionario de sinónimos | Mejorar recall en dominios específicos |
| 🥈 Media | Revisar prompt de re-ranking | Potencial mejora de 0.225 → 0.40+ P@5 |
| 🥉 Baja | Pre-computar queries comunes | Latencia <10ms para queries frecuentes |

---

## 📁 Archivos de Resultados

| Archivo | Descripción |
|---------|-------------|
| `ragas_scores_basic_final.json` | Evaluación modo básico (48 queries) |
| `ragas_scores_llm_final.json` | Evaluación modo LLM (48 queries) |
| `ground_truth_actualizado.jsonl` | Ground truth con patrones reales |

---

*Reporte generado automáticamente - Sprint 7 RAGAS*
