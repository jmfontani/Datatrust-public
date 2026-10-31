# Sprint 11: Evaluación con RAGAS Framework

**Fecha de creación**: 2026-06-03  
**Sprint**: 11 (Evaluación sistemática de la calidad del sistema RAG)  
**Objetivo**: Evaluar los tres frontends (A, B, C) con métricas estandarizadas del framework RAGAS

---

## 📋 Tabla de Contenidos

1. [Objetivos del Sprint](#objetivos-del-sprint)
2. [¿Qué es RAGAS?](#qué-es-ragas)
3. [Métricas a Utilizar](#métricas-a-utilizar)
4. [Plan de Evaluación](#plan-de-evaluación)
5. [Estructura de Archivos](#estructura-de-archivos)
6. [Cronograma](#cronograma)

---

## 🎯 Objetivos del Sprint

### Objetivo Principal

Evaluar sistemáticamente la calidad del **Buscador Semántico de Datasets Públicos** utilizando el framework **RAGAS** (Retrieval Augmented Generation Assessment), proporcionando métricas cuantitativas comparables para:

1. **Motor de búsqueda** (retrieval) — PostgreSQL + pgvector
2. **Re-ranking con LLM** — deepseek-v4-flash:cloud
3. **Tres frontends** — A (básico), B (intermedio), C (avanzado)

### Objetivos Específicos

| # | Objetivo | Métrica RAGAS |
|---|----------|---------------|
| 1 | Evaluar calidad del retrieval | Context Precision, Context Recall |
| 2 | Evaluar calidad del re-ranking | NDCG@10, MRR |
| 3 | Comparar frontends | User satisfaction proxy |
| 4 | Establecer baseline | Scores actuales para comparación futura |
| 5 | Identificar áreas de mejora | Análisis por categoría de queries |

---

## 🤖 ¿Qué es RAGAS?

**RAGAS** (Retrieval Augmented Generation Assessment) es un framework de evaluación para sistemas RAG que proporciona métricas estandarizadas sin necesidad de ground truth extensivo.

### Componentes de RAGAS

```
┌─────────────────────────────────────────────────────────────┐
│  SISTEMA RAG (Buscador Semántico)                           │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │   Query     │ ──▶ │  Retrieval  │ ──▶ │  Response   │   │
│  │  (Usuario)  │     │ (Contexto)  │     │   (LLM)     │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│  RAGAS METRICS                                              │
│  ├── Faithfulness      (¿La respuesta se basa en el contexto?) │
│  ├── Answer Relevance (¿La respuesta es relevante a la query?) │
│  ├── Context Precision (¿El contexto relevante está arriba?)  │
│  ├── Context Recall    (¿Se recuperó todo el contexto relevante?) │
│  └── ... (15+ métricas disponibles)                           │
└─────────────────────────────────────────────────────────────┘
```

### Por Qué RAGAS

| Ventaja | Descripción |
|---------|-------------|
| **Sin ground truth extensivo** | RAGAS genera evaluaciones sin necesitar respuestas "correctas" predefinidas |
| **Métricas estandarizadas** | Comparables con otros sistemas RAG |
| **Evaluación por componentes** | Separa retrieval de generation |
| **Automático** | Scripts ejecutables, reproducible |
| **Open source** | `pip install ragas` |

---

## 📊 Métricas a Utilizar

### Métricas Principales (Core)

| Métrica | Rango | Qué mide | Target |
|---------|-------|----------|--------|
| **Context Precision@K** | 0-1 | ¿Los documentos relevantes aparecen primeros? | >0.75 |
| **Context Recall** | 0-1 | ¿Se recuperaron todos los documentos relevantes? | >0.80 |
| **Faithfulness** | 0-1 | ¿La respuesta se basa únicamente en el contexto? | >0.85 |
| **Answer Relevance** | 0-1 | ¿La respuesta es relevante a la query? | >0.80 |

### Métricas Secundarias

| Métrica | Rango | Qué mide | Target |
|---------|-------|----------|--------|
| **Context Entities Recall** | 0-1 | ¿Se recuperaron las entidades correctas? | >0.75 |
| **Semantic Similarity** | 0-1 | Similitud semántica respuesta/query | >0.70 |
| **Noise Sensitivity** | 0-1 | ¿Cómo afecta el ruido al retrieval? | <0.30 |

### Métricas Específicas del Buscador

| Métrica | Fórmula | Target |
|---------|---------|--------|
| **Precisión@5** | (relevantes en top 5) / 5 | >0.80 |
| **Precisión@10** | (relevantes en top 10) / 10 | >0.70 |
| **NDCG@10** | Normalized Discounted Cumulative Gain | >0.75 |
| **MRR** | Mean Reciprocal Rank | >0.70 |

---

## 🔬 Plan de Evaluación

### Fase 1: Preparación del Dataset de Evaluación

**Duración**: 2-3 días

```python
# 09_Sprint7_RAGAS/codigo/crear_dataset_evaluacion.py

QUERIES_EVALUACION = [
    # Categoría: Empleo
    {"query": "empleo juvenil", "categoria": "empleo", "dificultad": "fácil"},
    {"query": "paro registrado por comunidades", "categoria": "empleo", "dificultad": "media"},
    
    # Categoría: Demografía
    {"query": "censo población 2024", "categoria": "demografía", "dificultad": "fácil"},
    {"query": "pirámide poblacional Andalucía", "categoria": "demografía", "dificultad": "media"},
    
    # Categoría: Economía
    {"query": "vulnerabilidad económica", "categoria": "economía", "dificultad": "difícil"},
    {"query": "renta media por hogar", "categoria": "economía", "dificultad": "media"},
    
    # ... 40+ queries total
]
```

**Criterios de selección de queries:**
- 40+ queries (mismo set que Sprint 6 Evaluación)
- Cubrir todas las categorías: empleo, demografía, economía, transporte, medio ambiente, cultura, deporte
- 3 niveles de dificultad: fácil, media, difícil
- Incluir queries ambiguas: "paro", "banco", "planta"

### Fase 2: Generación de Ground Truth

**Duración**: 2-3 días

**Método**: LLM-assisted ground truth generation

```python
# 09_Sprint7_RAGAS/codigo/generar_ground_truth.py

# Para cada query, el LLM genera:
# 1. Respuesta ideal (golden answer)
# 2. Datasets relevantes esperados
# 3. Criterios de relevancia

from ollama import chat

def generar_ground_truth(query: str) -> dict:
    response = chat(model='deepseek-v4-pro:cloud', messages=[
        {"role": "user", "content": f"""
        Para la query de búsqueda: "{query}"
        
        Genera:
        1. Respuesta ideal (2-3 frases)
        2. Lista de datasets que deberían aparecer (mínimo 3)
        3. Criterios de relevancia (qué hace que un dataset sea relevante)
        """}
    ])
    return parse_response(response)
```

### Fase 3: Ejecución de Evaluación

**Duración**: 3-4 días

**Scripts a crear:**

| Script | Descripción | Output |
|--------|-------------|--------|
| `eval_ragas_core.py` | Métricas RAGAS principales | `ragas_scores.json` |
| `eval_precision_recall.py` | Precisión@K, Recall | `precision_recall.json` |
| `eval_frontend_comparison.py` | Comparar A vs B vs C | `frontend_comparison.json` |
| `eval_llm_reranking.py` | Impacto del re-ranking | `reranking_impact.json` |

**Ejecución:**

```bash
cd 09_Sprint7_RAGAS/codigo

# 1. Evaluar motor base (sin LLM)
python eval_ragas_core.py --mode basic

# 2. Evaluar con re-ranking LLM
python eval_ragas_core.py --mode llm

# 3. Comparar frontends
python eval_frontend_comparison.py

# 4. Generar reporte
python generar_reporte.py
```

### Fase 4: Análisis de Resultados

**Duración**: 2 días

**Métricas a reportar:**

```markdown
## Resultados de Evaluación

### Context Precision@10
| Frontend | Score | vs Baseline |
|----------|-------|-------------|
| A (básico) | 0.72 | - |
| B (intermedio) | 0.75 | +4% |
| C (avanzado + LLM) | 0.82 | +14% |

### Answer Relevance
| Frontend | Score | vs Baseline |
|----------|-------|-------------|
| A (básico) | 0.78 | - |
| B (intermedio) | 0.80 | +2% |
| C (avanzado + LLM) | 0.87 | +11% |

### Impacto del Re-ranking LLM
| Métrica | Sin LLM | Con LLM | Mejora |
|---------|---------|---------|--------|
| Context Precision | 0.72 | 0.82 | +14% |
| NDCG@10 | 0.68 | 0.79 | +16% |
| MRR | 0.65 | 0.74 | +14% |
```

---

## 📁 Estructura de Archivos

```
09_Sprint7_RAGAS/
├── codigo/
│   ├── crear_dataset_evaluacion.py       # 40+ queries categorizadas
│   ├── generar_ground_truth.py           # LLM-assisted ground truth
│   ├── eval_ragas_core.py                # Métricas RAGAS principales
│   ├── eval_precision_recall.py          # Precisión@K, Recall
│   ├── eval_frontend_comparison.py       # Comparar A vs B vs C
│   ├── eval_llm_reranking.py             # Impacto del re-ranking
│   ├── generar_reporte.py                # Reporte markdown + JSON
│   ├── utils/
│   │   ├── ragas_metrics.py              # Wrapper métricas RAGAS
│   │   └── ground_truth_validator.py     # Validar ground truth
│   └── requirements.txt                  # ragas, ollama, pandas, matplotlib
├── docs/
│   ├── PLAN_EVALUACION_RAGAS.md          # ESTE ARCHIVO
│   ├── ARQUITECTURA_EVALUACION.md        # Cómo encaja RAGAS en el sistema
│   └── RESULTADOS_EVALUACION.md          # Resultados finales (al terminar)
├── entregables/
│   ├── dataset_evaluacion.jsonl          # 40+ queries + ground truth
│   ├── ragas_scores.json                 # Scores RAGAS por query
│   ├── frontend_comparison.json          # Comparativa A/B/C
│   ├── reporte_evaluacion.md             # Reporte ejecutivo
│   └── presentation_slides.pdf           # Diapositivas para defensa
└── README.md                             # Resumen del sprint
```

---

## 📅 Cronograma

| Semana | Fase | Entregables |
|--------|------|-------------|
| **Semana 1** (12-18 jun) | Preparación | Dataset evaluación, Ground truth |
| **Semana 2** (19-25 jun) | Ejecución | Scripts RAGAS, Scores preliminares |
| **Semana 3** (26 jun - 2 jul) | Análisis | Reporte ejecutivo, Comparativa frontends |
| **Semana 4** (3-9 jul) | Documentación | Presentación defensa, Lecciones aprendidas |

### Hitos Clave

| Fecha | Hito | Criterio de Aceptación |
|-------|------|------------------------|
| 18-jun | Dataset completado | 40+ queries categorizadas + ground truth |
| 25-jun | Evaluación completada | Todos los scripts ejecutados, scores generados |
| 02-jul | Análisis completado | Reporte con insights accionables |
| 09-jul | Sprint cerrado | Documentación + presentación listas |

---

## 🔗 Referencias

- **RAGAS Documentation**: https://docs.ragas.io/
- **RAGAS Paper**: https://arxiv.org/abs/2309.15217
- **GitHub**: https://github.com/explodinggradients/ragas
- **Sprint 6 Evaluación**: `06_Nivel4_Evaluacion/codigo/benchmark/test_bateria_extendida.py`
- **Frontend B Docs**: `15_Frontends/frontend_b_intermedio/DOCUMENTACION_SPRINT10.md`

---

## 📝 Notas Técnicas

### Instalación de RAGAS

```bash
cd 09_Sprint7_RAGAS/codigo
pip install ragas langchain openai  # o ollama para local
```

### Configuración de API Keys

```bash
# Para RAGAS con OpenAI (recomendado para evaluación)
export OPENAI_API_KEY="sk-..."

# O para Ollama local
export OLLAMA_HOST="http://localhost:11434"
```

### Requisitos de Hardware

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| RAM | 8GB | 16GB |
| GPU | No requerida | NVIDIA 8GB+ (para embeddings locales) |
| Storage | 1GB | 5GB (para cache de embeddings) |

---

*Documento creado el 2026-06-03. Próxima revisión: 2026-06-12 (inicio Sprint 11)*
