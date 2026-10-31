# 📊 Informe de Evaluación RAGAS - Buscador Semántico de Datasets

**Fecha de generación**: 2026-06-12 22:49:27

---

## 🎯 Resumen Ejecutivo

Este informe presenta los resultados de la evaluación sistemática del Buscador Semántico
de Datasets Públicos utilizando métricas del framework **RAGAS** (Retrieval Augmented
Generation Assessment) y comparativas entre los tres frontends disponibles.

## 🔍 Evaluación: Modo Básico (sin LLM)

- **Queries evaluadas**: 96
- **Tiempo total**: 5.3s
- **Tiempo medio por query**: 0.06s

### Métricas Principales

| Métrica | Valor | Target | Estado |
|---------|-------|--------|--------|
| Precision At 5 | 0.002 | 0.80 | ❌ |
| Precision At 10 | 0.001 | 0.70 | ❌ |
| Ndcg At 10 | 0.010 | 0.75 | ❌ |
| Recall | 0.227 | 0.80 | ❌ |

### Por Categoría

| Categoría | Precision@5 | NDCG@10 | Queries |
|-----------|-------------|---------|---------|
| Ambigua | 0.000 | 0.000 | 6 |
| Cultura | 0.000 | 0.000 | 10 |
| Demografía | 0.000 | 0.000 | 10 |
| Deporte | 0.020 | 0.100 | 10 |
| Economía | 0.000 | 0.000 | 10 |
| Educación | 0.000 | 0.000 | 10 |
| Empleo | 0.000 | 0.000 | 10 |
| Medio Ambiente | 0.000 | 0.000 | 10 |
| Sanidad | 0.000 | 0.000 | 10 |
| Transporte | 0.000 | 0.000 | 10 |

### Por Dificultad

| Dificultad | Precision@5 | NDCG@10 | Queries |
|------------|-------------|---------|---------|
| Fácil | 0.000 | 0.000 | 22 |
| Media | 0.004 | 0.018 | 56 |
| Difícil | 0.000 | 0.000 | 18 |

## 🤖 Evaluación: Modo LLM (con re-ranking)

- **Queries evaluadas**: 10
- **Tiempo total**: 503.0s
- **Tiempo medio por query**: 50.30s

### Métricas Principales

| Métrica | Valor | Target | Estado |
|---------|-------|--------|--------|
| Precision At 5 | 0.000 | 0.80 | ❌ |
| Precision At 10 | 0.000 | 0.70 | ❌ |
| Ndcg At 10 | 0.000 | 0.75 | ❌ |
| Recall | 0.000 | 0.80 | ❌ |

### Comparación: Básico vs LLM

| Métrica | Básico | LLM | Mejora |
|---------|--------|-----|--------|
| Precision At 5 | 0.002 | 0.000 | -100.0% |
| Precision At 10 | 0.001 | 0.000 | -100.0% |
| Ndcg At 10 | 0.010 | 0.000 | -100.0% |
| Recall | 0.227 | 0.000 | -100.0% |

## 📝 Conclusiones

- ⚠️ El sistema está **por debajo del target de Precision@5**. Se recomienda revisar el ranking semántico.
- ⚠️ El re-ranking con LLM no muestra mejora significativa (-0.2%). Considerar ajustar prompts o modelo.

---

## 📁 Archivos de Resultados

| Archivo | Descripción |
|---------|-------------|
| `ragas_scores_basic.json` | Evaluación modo básico (sin LLM) |
| `ragas_scores_llm.json` | Evaluación modo LLM (con re-ranking) |

---

*Reporte generado automáticamente por `generar_reporte.py` - Sprint 11 RAGAS*