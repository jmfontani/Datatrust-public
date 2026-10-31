# Sprint 7: Evaluación con RAGAS Framework ✅ COMPLETADO

**Fecha de creación**: 2026-06-03  
**Última actualización**: 2026-06-12 (evaluación completada)  
**Sprint**: 7 (Evaluación sistemática de calidad del buscador)  
**Estado**: ✅ COMPLETADO  
**Owner**: Fonta

---

## 📊 Resultados Finales

| Métrica | Valor | Target | Estado |
|---------|-------|--------|--------|
| **Precision@5** | 0.702 | 0.80 | ⚠️ |
| **Precision@10** | 0.647 | 0.70 | ⚠️ |
| **NDCG@10** | 0.792 | 0.75 | ✅ |
| **Recall** | 1.966 | 0.80 | ✅ |

**Queries evaluadas**: 47 (ground truth basado en resultados reales)  
**Tiempo medio por query**: 0.03s  
**📖 Metodología completa**: ver sección [🔬 Metodología de cálculo de P@5 y P@10](entregables/reporte_evaluacion_final.md#-metodología-de-cálculo-de-p5-y-p10) del informe final.

### Por Categoría (Top 3)

| Categoría | Precision@5 | NDCG@10 |
|-----------|-------------|---------|
| Demografía | 0.920 | 0.918 |
| Educación | 0.880 | 0.891 |
| Transporte | 0.840 | 0.905 |

### Por Categoría (Bottom 3)

| Categoría | Precision@5 | NDCG@10 |
|-----------|-------------|---------|
| Sanidad | 0.400 | 0.534 |
| Empleo | 0.450 | 0.725 |
| Deporte | 0.600 | 0.759 |

### Insights Clave

1. ✅ **NDCG@10 supera target** (0.792 vs 0.75) — El ranking funciona bien cuando hay coincidencia semántica
2. ⚠️ **Precision@5 por debajo** (0.702 vs 0.80) — Mejorable en queries de empleo y sanidad
3. ⚠️ **Queries fáciles** tienen P@5=0.855, **difíciles** P@5=0.511 — Brecha importante

---

## 📁 Entregables

| Archivo | Descripción | Estado |
|---------|-------------|--------|
| `dataset_evaluacion.jsonl` | 48 queries categorizadas | ✅ |
| `ground_truth_real.jsonl` | Ground truth basado en resultados reales | ✅ |
| `ragas_scores_basic_v2.json` | Evaluación modo básico | ✅ |
| `reporte_evaluacion_final.md` | Informe ejecutivo | ✅ |

---

## 🎯 Objetivo

Evaluar sistemáticamente la calidad del **Buscador Semántico de Datasets Públicos** utilizando el framework **RAGAS** (Retrieval Augmented Generation Assessment).

### Por Qué RAGAS

RAGAS proporciona métricas estandarizadas para sistemas RAG (Retrieval + Generation) que permiten:
- ✅ Evaluar retrieval (motor de búsqueda) y generation (LLM) por separado
- ✅ Obtener scores comparables con otros sistemas
- ✅ Identificar áreas específicas de mejora
- ✅ Evaluar sin ground truth extensivo (LLM-assisted)

---

## 📊 Métricas Principales

| Métrica | Rango | Target | Qué mide |
|---------|-------|--------|----------|
| **Context Precision@10** | 0-1 | >0.75 | ¿Los resultados relevantes aparecen primeros? |
| **Context Recall** | 0-1 | >0.80 | ¿Se recuperaron todos los resultados relevantes? |
| **Faithfulness** | 0-1 | >0.85 | ¿La respuesta se basa en el contexto? |
| **Answer Relevance** | 0-1 | >0.80 | ¿La respuesta es relevante a la query? |
| **Precisión@5** | 0-1 | >0.80 | Resultados relevantes en top 5 |
| **NDCG@10** | 0-1 | >0.75 | Calidad del ranking (discounted gain) |

---

## 📁 Estructura

```
09_Sprint7_RAGAS/
├── codigo/
│   ├── crear_dataset_evaluacion.py   # ✅ 44 queries categorizadas
│   ├── generar_ground_truth.py       # ✅ LLM-assisted ground truth
│   ├── eval_ragas_core.py            # ✅ Métricas RAGAS principales (basic/llm)
│   ├── eval_frontend_comparison.py   # ✅ Comparar A vs B vs C
│   ├── generar_reporte.py            # ✅ Reporte markdown + JSON
│   ├── utils/
│   │   ├── ragas_metrics.py          # ✅ Wrapper métricas RAGAS
│   │   └── __init__.py               # ✅ Package init
│   └── requirements.txt              # ✅ Dependencias
├── docs/
│   ├── PLAN_EVALUACION_RAGAS.md      # ✅ Plan completo del sprint
│   ├── ARQUITECTURA_EVALUACION.md    # ⏳ Pendiente
│   └── RESULTADOS_EVALUACION.md      # ⏳ Resultados finales
├── entregables/
│   ├── dataset_evaluacion.jsonl      # ⏳ Pending generation
│   ├── ground_truth.jsonl            # ⏳ Pending generation
│   ├── ragas_scores_basic.json       # ⏳ Pending execution
│   ├── ragas_scores_llm.json         # ⏳ Pending execution
│   ├── frontend_comparison.json      # ⏳ Pending execution
│   ├── reporte_evaluacion.md         # ⏳ Pending generation
│   └── presentation_slides.pdf       # ⏳ Pendiente
└── README.md                         # ✅ ESTE ARCHIVO
```

---

## 🚀 Cómo Ejecutar

### 1. Instalar dependencias

```bash
cd 09_Sprint7_RAGAS/codigo
pip install -r requirements.txt
```

### 2. Crear dataset de evaluación

```bash
python crear_dataset_evaluacion.py --output ../entregables/dataset_evaluacion.jsonl
```

**Output**: 44 queries categorizadas en:
- empleo (5), demografía (5), economía (5), transporte (5)
- medio ambiente (5), cultura (5), deporte (5), sanidad (5), educación (5)
- ambigua (3) — para test de precisión

### 3. Generar ground truth (LLM-assisted)

```bash
python generar_ground_truth.py \
  --input ../entregables/dataset_evaluacion.jsonl \
  --output ../entregables/ground_truth.jsonl \
  --model deepseek-v4-pro:cloud
```

### 4. Ejecutar evaluación RAGAS

```bash
# Evaluar motor base (sin LLM)
python eval_ragas_core.py \
  --dataset ../entregables/ground_truth.jsonl \
  --mode basic \
  --output ../entregables/ragas_scores_basic.json

# Evaluar con re-ranking LLM
python eval_ragas_core.py \
  --dataset ../entregables/ground_truth.jsonl \
  --mode llm \
  --output ../entregables/ragas_scores_llm.json
```

### 5. Generar reporte

```bash
python generar_reporte.py \
  --scores ../entregables/ragas_scores_*.json \
  --output ../entregables/reporte_evaluacion.md
```

---

## 📅 Cronograma

| Semana | Fechas | Fase | Entregables |
|--------|--------|------|-------------|
| **1** | 12-18 jun | Preparación | Dataset + Ground truth |
| **2** | 19-25 jun | Ejecución | Scripts + Scores preliminares |
| **3** | 26 jun - 2 jul | Análisis | Reporte + Insights |
| **4** | 3-9 jul | Documentación | Presentación defensa |

---

## 🔗 Referencias

- **RAGAS Docs**: https://docs.ragas.io/
- **RAGAS Paper**: https://arxiv.org/abs/2309.15217
- **GitHub**: https://github.com/explodinggradients/ragas
- **Plan completo**: [`docs/PLAN_EVALUACION_RAGAS.md`](docs/PLAN_EVALUACION_RAGAS.md)

---

## 📝 Estado Actual

### ✅ Completado (2026-06-03)

- [x] Estructura de carpetas creada
- [x] `PLAN_EVALUACION_RAGAS.md` con plan detallado
- [x] `crear_dataset_evaluacion.py` con 44 queries categorizadas
- [x] `requirements.txt` con dependencias
- [x] `generar_ground_truth.py` - LLM-assisted ground truth generation
- [x] `eval_ragas_core.py` - Evaluación con métricas Precision@K, NDCG@K, Recall
- [x] `eval_frontend_comparison.py` - Comparativa de 3 frontends (A/B/C)
- [x] `generar_reporte.py` - Generación de reporte ejecutivo Markdown
- [x] `utils/ragas_metrics.py` - Wrapper de métricas RAGAS + implementaciones custom

### ⏳ Pendiente de Ejecución

- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Generar dataset: `python crear_dataset_evaluacion.py`
- [ ] Generar ground truth con LLM: `python generar_ground_truth.py`
- [ ] Ejecutar evaluación (modo básico): `python eval_ragas_core.py --mode basic`
- [ ] Ejecutar evaluación (modo LLM): `python eval_ragas_core.py --mode llm`
- [ ] Comparar frontends: `python eval_frontend_comparison.py`
- [ ] Generar reporte ejecutivo: `python generar_reporte.py`
- [ ] Analizar resultados y extraer insights
- [ ] Crear presentación para defensa

---

*Documento creado el 2026-06-03. Próxima revisión: 2026-06-12 (inicio ejecución Sprint 11)*
