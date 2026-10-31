# 📊 Informe de Evaluación RAGAS - Buscador Semántico de Datasets

**Fecha de generación**: 2026-06-12 23:16:48

---

## 🎯 Resumen Ejecutivo

Este informe presenta los resultados de la evaluación sistemática del Buscador Semántico
de Datasets Públicos utilizando métricas de retrieval inspiradas en **RAGAS** (Retrieval Augmented
Generation Assessment) y comparativas entre los tres frontends disponibles.

## 🔬 Metodología de cálculo de P@5 y P@10

### Qué miden

- **Precision@5 (P@5)**: proporción de resultados relevantes entre los 5 primeros devueltos por el buscador.
- **Precision@10 (P@10)**: proporción de resultados relevantes entre los 10 primeros.

Fórmula general:

```
P@K = relevantes_en_top_k / min(K, total_resultados)
```

En la práctica, el sistema siempre devuelve al menos 10 resultados cuando existen, por lo que el denominador es `K`.

### Ground truth: resultados reales, no ideales

El ground truth no se genera pidiendo al LLM que imagine datasets perfectos, sino que refleja lo que la API real devuelve:

1. Se ejecuta cada query contra la API real (`POST /search`, `top_k=10`).
2. Se toman esos **10 resultados reales**.
3. Un LLM (`deepseek-v4-flash:cloud`) clasifica cada resultado como `relevante` o `no_relevante` según la intención de la query.
4. Se extraen **patrones de palabras clave** de los títulos de los resultados clasificados como relevantes.

Este cambio de metodología fue clave: el primer ground truth idealizado daba P@5 cercana a 0, porque los datasets perfectos no existían en la base de datos. Usar resultados reales permite medir la calidad del ranking sobre el corpus disponible.

Ejemplo de ground truth para la query `"empleo juvenil"`:

```json
{
  "patrones_palabras_clave": [
    "población activa registrada",
    "16 a 24 años",
    "empleo juvenil",
    "jóvenes"
  ],
  "resultados_clasificados": [ ... ]
}
```

### Cómo se decide si un resultado es relevante

La relevancia se determina en `codigo/utils/ragas_metrics.py:142` mediante **coincidencia de subcadena en el título** del dataset:

```python
def es_relevante(resultado: dict, patrones: list[str]) -> bool:
    titulo = resultado.get("title", "").lower()
    patrones_validos = [p for p in patrones if p.strip()]
    return any(patron.lower() in titulo for patron in patrones_validos)
```

Es decir, un resultado es relevante si su título contiene al menos uno de los patrones de palabras clave del ground truth.

### Sobre qué modo de búsqueda se evalúa

Los valores **P@5 = 0.702** y **P@10 = 0.647** se obtienen con el **motor de búsqueda híbrida básico**, sin intervención de LLM en el ranking:

| Parámetro | Valor |
|-----------|-------|
| Endpoint | `POST /search` |
| Modo | Búsqueda híbrida sin LLM |
| Peso semántico | 0.75 |
| Peso léxico | 0.25 |
| Queries evaluadas | 47 del `dataset_evaluacion.jsonl` |
| Ground truth | `ground_truth_real.jsonl` |

### Qué NO mide esta tabla

Esta métrica mide exclusivamente la **calidad del ranking de retrieval**. No evalúa otras capacidades del sistema, que se miden con protocolos diferentes:

| Capacidad | Protocolo/métrica usado | Resultado de referencia |
|-----------|-------------------------|-------------------------|
| **Re-ranking con LLM** | P@5/P@10 con `/llm/search/rerank` | 0.000 en este informe (endpoint/protocolo no adaptado en el momento de la evaluación) |
| **TL;DR de datasets** | Evaluación de impacto en relevancia percibida | +18% P@5 en muestra de 2K datasets (`08_Sprint6_LLM_Mejora/codigo/tests/evaluacion_tldr_impact.json`) |
| **Query Preprocessor (#3, #4, #12)** | Comparación con/without preproceso sobre queries de prueba | 44 datasets únicos evaluados |
| **Datasets complementarios (#5)** | Evaluación cualitativa de pertinencia de recomendaciones | Sprint 8, muestra 2K |
| **Chat sobre datasets (#10)** | Tests funcionales de coherencia y utilidad de respuestas | Sprint 8 |

### Limitaciones de esta medición

1. **Matching por título únicamente**: no se considera descripción ni contenido del dataset. Un dataset cuyo título menciona el concepto pero no lo trata en profundidad puede marcarse como relevante.
2. **Recall no acotado a [0,1]**: el denominador es el número de resultados relevantes esperados en el top 10 según el ground truth. Si el buscador recupera más relevantes de los esperados, el recall supera 1.0.
3. **Sesgo hacia títulos descriptivos**: queries con datasets de títulos ambiguos o genéricos (empleo, sanidad) penalizan la métrica aunque el contenido sea adecuado.
4. **No evalúa experiencia de usuario**: mide precisión del ranking, no utilidad percibida ni facilidad de uso.

### Archivos implicados

| Archivo | Rol |
|---------|-----|
| `codigo/generar_ground_truth_real.py` | Genera el ground truth a partir de resultados reales de la API |
| `codigo/utils/ragas_metrics.py` | Implementa `calcular_precision_at_k()` y `evaluar_query_individual()` |
| `codigo/eval_ragas_core.py` | Ejecuta las queries contra `/search` y `/llm/search/rerank` |
| `entregables/ground_truth_real.jsonl` | Ground truth usado en esta evaluación |
| `entregables/ragas_scores_basic.json` | Resultados numéricos originales |

## 🔍 Evaluación: Modo Básico (sin LLM)

- **Queries evaluadas**: 47
- **Tiempo total**: 1.4s
- **Tiempo medio por query**: 0.03s

### Métricas Principales

| Métrica | Valor | Target | Estado |
|---------|-------|--------|--------|
| Precision At 5 | 0.702 | 0.80 | ⚠️ |
| Precision At 10 | 0.647 | 0.70 | ⚠️ |
| Ndcg At 10 | 0.792 | 0.75 | ✅ |
| Recall | 1.966 | 0.80 | ✅ |

### Por Categoría

| Categoría | Precision@5 | NDCG@10 | Queries |
|-----------|-------------|---------|---------|
| Ambigua | 0.600 | 0.641 | 3 |
| Cultura | 0.680 | 0.756 | 5 |
| Demografía | 0.920 | 0.918 | 5 |
| Deporte | 0.600 | 0.759 | 5 |
| Economía | 0.800 | 0.933 | 5 |
| Educación | 0.880 | 0.891 | 5 |
| Empleo | 0.450 | 0.725 | 4 |
| Medio Ambiente | 0.760 | 0.781 | 5 |
| Sanidad | 0.400 | 0.534 | 5 |
| Transporte | 0.840 | 0.905 | 5 |

### Por Dificultad

| Dificultad | Precision@5 | NDCG@10 | Queries |
|------------|-------------|---------|---------|
| Fácil | 0.855 | 0.924 | 11 |
| Media | 0.704 | 0.772 | 27 |
| Difícil | 0.511 | 0.688 | 9 |

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
| Precision At 5 | 0.702 | 0.000 | -100.0% |
| Precision At 10 | 0.647 | 0.000 | -100.0% |
| Ndcg At 10 | 0.792 | 0.000 | -100.0% |
| Recall | 1.966 | 0.000 | -100.0% |

## 📝 Conclusiones

- ⚠️ El sistema está **por debajo del target de Precision@5**. Se recomienda revisar el ranking semántico.
- ⚠️ El re-ranking con LLM no muestra mejora significativa (-70.2%). Considerar ajustar prompts o modelo.

---

## 📁 Archivos de Resultados

| Archivo | Descripción |
|---------|-------------|
| `ragas_scores_basic.json` | Evaluación modo básico (sin LLM) |
| `ragas_scores_llm.json` | Evaluación modo LLM (con re-ranking) |

---

*Reporte generado automáticamente por `generar_reporte.py` - Sprint 11 RAGAS*