# Arquitectura de Evaluación RAGAS

**Fecha**: 2026-06-03  
**Sprint**: 11  
**Propósito**: Documentar cómo encaja RAGAS en la arquitectura del Buscador Semántico

---

## 📐 Visión General

La evaluación RAGAS se integra en el Buscador Semántico como una **capa de validación sistemática** que opera sobre los componentes existentes:

```
┌─────────────────────────────────────────────────────────────────┐
│                     CAPA DE EVALUACIÓN RAGAS                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Dataset    │───▶│   Ground     │───▶│  Evaluación  │      │
│  │  (48 queries)│    │   Truth      │    │   RAGAS      │      │
│  │              │    │   (LLM)      │    │   Metrics    │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │               │
│         │                   │                   ▼               │
│         │            ┌──────────────┐    ┌──────────────┐      │
│         │            │   Ollama     │    │   Reportes   │      │
│         │            │  (LLM API)   │    │   Markdown   │      │
│         │            └──────────────┘    └──────────────┘      │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────────────────────────────────────────┐          │
│  │            MOTOR DE BÚSQUEDA (API)               │          │
│  │  - PostgreSQL + pgvector                         │          │
│  │  - Búsqueda híbrida (semántica + léxica)         │          │
│  │  - Opcional: Re-ranking con LLM                  │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Componentes de Evaluación

### 1. Dataset de Evaluación

**Archivo**: `entregables/dataset_evaluacion.jsonl`

| Característica | Detalle |
|----------------|---------|
| **Total queries** | 48 |
| **Categorías** | 9 (empleo, demografía, economía, transporte, medio ambiente, cultura, deporte, sanidad, educación) |
| **Queries ambiguas** | 3 (paro, banco, planta) |
| **Dificultad** | Fácil (11), Media (28), Difícil (9) |

**Estructura por query:**
```json
{
  "id": "empleo_001",
  "query": "empleo juvenil",
  "categoria": "empleo",
  "dificultad": "fácil",
  "descripcion": "Búsqueda directa de estadísticas de empleo para jóvenes",
  "datasets_esperados": ["INE.*empleo.*joven", "SEPE.*juvenil"],
  "criterios_relevancia": [
    "Contiene datos de empleo para rango 16-29 años",
    "Incluye desglose por comunidades autónomas"
  ]
}
```

---

### 2. Ground Truth Generation

**Script**: `generar_ground_truth.py`

**Proceso**:
1. Para cada query, el LLM genera:
   - **Respuesta ideal**: Descripción de 2-3 frases de qué información debería encontrar el usuario
   - **Datasets relevantes**: Lista de 3+ datasets con patrón de título, tema, territorio
   - **Criterios de evaluación**: Qué debe/no debe contener la respuesta

**Modelo LLM**: `deepseek-v4-pro:cloud` (vía Ollama)

**Tiempo estimado**: ~45-60 segundos por query → ~36-48 minutos para 48 queries

**Estructura del ground truth:**
```json
{
  "id": "empleo_001",
  "query": "empleo juvenil",
  "categoria": "empleo",
  "ground_truth": {
    "respuesta_ideal": "El usuario busca estadísticas oficiales sobre empleo de jóvenes...",
    "datasets_relevantes": [
      {
        "titulo_patron": "Estadísticas de Empleo Joven",
        "tema": "Empleo",
        "territorio": "España",
        "razon_relevancia": "Contiene datos específicos de empleo juvenil 16-29 años"
      }
    ],
    "criterios_evaluacion": {
      "debe_contener": ["empleo", "jóvenes", "estadísticas"],
      "no_debe_contener": ["pensiones", "jubilación"],
      "minimo_datasets_relevantes": 3
    }
  }
}
```

---

### 3. Evaluación RAGAS Core

**Script**: `eval_ragas_core.py`

**Métricas implementadas:**

| Métrica | Fórmula | Target |
|---------|---------|--------|
| **Precision@5** | (relevantes en top 5) / 5 | >0.80 |
| **Precision@10** | (relevantes en top 10) / 10 | >0.70 |
| **NDCG@10** | DCG / IDCG (discounted cumulative gain) | >0.75 |
| **Recall** | (relevantes encontrados) / (total relevantes) | >0.80 |

**Modos de evaluación:**

| Modo | Descripción | Tiempo estimado |
|------|-------------|-----------------|
| `basic` | Búsqueda híbrida sin LLM | ~5 min |
| `llm` | Búsqueda + re-ranking con LLM | ~10 min |

**Análisis por dimensiones:**
- Por categoría (empleo, demografía, etc.)
- Por dificultad (fácil, media, difícil)

---

### 4. Comparación de Frontends

**Script**: `eval_frontend_comparison.py`

**Frontends evaluados:**

| Frontend | Descripción | Configuración |
|----------|-------------|---------------|
| **A** | Básico (MVP Sprint 3) | `semantic_weight=0.5`, `lexical_weight=0.5` |
| **B** | Intermedio (producto principal) | `semantic_weight=0.75`, `lexical_weight=0.25` |
| **C** | Avanzado (demo LLM) | Re-ranking con LLM, `rerank_top_n=20` |

**Métricas de UX:**
- Usabilidad (0-1)
- Velocidad percibida (0-1)
- Claridad de resultados (0-1)
- Satisfacción general (0-1)

---

### 5. Generación de Reporte

**Script**: `generar_reporte.py`

**Output**: `reporte_evaluacion.md`

**Secciones del reporte:**
1. Resumen ejecutivo
2. Evaluación modo básico (métricas, por categoría, por dificultad)
3. Evaluación modo LLM (comparación básico vs LLM)
4. Comparación de frontends (ranking, métricas por frontend)
5. Conclusiones automáticas
6. Archivos de resultados

---

## 🔄 Flujo Completo de Evaluación

```
┌─────────────────────────────────────────────────────────────────┐
│  PASO 1: crear_dataset_evaluacion.py                            │
│  ─────────────────────────────────────                          │
│  Input: -                                                       │
│  Output: dataset_evaluacion.jsonl (48 queries)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASO 2: generar_ground_truth.py                                │
│  ─────────────────────────────────────                          │
│  Input: dataset_evaluacion.jsonl                                │
│  LLM: deepseek-v4-pro:cloud                                     │
│  Output: ground_truth.jsonl (48 queries + ground truth)         │
│  Tiempo: ~45 min                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASO 3: eval_ragas_core.py --mode basic                        │
│  ─────────────────────────────────────                          │
│  Input: ground_truth.jsonl                                      │
│  API: http://localhost:8000/search                              │
│  Output: ragas_scores_basic.json                                │
│  Tiempo: ~5 min                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASO 4: eval_ragas_core.py --mode llm                          │
│  ─────────────────────────────────────                          │
│  Input: ground_truth.jsonl                                      │
│  API: http://localhost:8000/llm/search/rerank                   │
│  Output: ragas_scores_llm.json                                  │
│  Tiempo: ~10 min                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASO 5: eval_frontend_comparison.py                            │
│  ─────────────────────────────────────                          │
│  Input: ground_truth.jsonl                                      │
│  Output: frontend_comparison.json                               │
│  Tiempo: ~15 min                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASO 6: generar_reporte.py                                     │
│  ─────────────────────────────────────                          │
│  Input: ragas_scores_*.json, frontend_comparison.json           │
│  Output: reporte_evaluacion.md                                  │
│  Tiempo: <1 min                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Integración con el Sistema Existente

### Dependencias del Buscador

| Componente | Versión | Uso en Evaluación |
|------------|---------|-------------------|
| PostgreSQL | 15.4 | Almacenamiento de datasets |
| pgvector | 0.5.1 | Búsqueda semántica (embedding <=> query) |
| FastAPI | 0.100+ | Endpoints `/search` y `/llm/search/rerank` |
| Ollama | latest | LLM para ground truth + re-ranking |
| sentence-transformers | 2.2.2 | Embeddings (paraphrase-multilingual-MiniLM-L12-v2) |

### Endpoints Utilizados

| Endpoint | Método | Parámetros | Uso |
|----------|--------|------------|-----|
| `/search` | POST | query, top_k, semantic_weight, lexical_weight | Evaluación básica |
| `/llm/search/rerank` | POST | query, rerank_top_n, use_llm | Evaluación con LLM |
| `/health` | GET | - | Verificación inicial |

---

## 🎯 Criterios de Aceptación

La evaluación se considera completada cuando:

- [x] Dataset de 48 queries generado
- [ ] Ground truth generado para todas las queries
- [ ] Evaluación básica completada (Precision@5 > 0.80 target)
- [ ] Evaluación con LLM completada (mejora > 5% vs básico)
- [ ] Comparación de 3 frontends completada
- [ ] Reporte ejecutivo generado
- [ ] Insights documentados para la defensa del TFM

---

## 📈 Métricas de Éxito del Sprint 11

| Métrica | Target | Justificación |
|---------|--------|---------------|
| **Precision@5** | >0.80 | Los primeros 5 resultados deben ser altamente relevantes |
| **NDCG@10** | >0.75 | El ranking debe priorizar resultados relevantes |
| **Recall** | >0.80 | Debe recuperar la mayoría de resultados relevantes |
| **Mejora con LLM** | >5% | El re-ranking debe justificar la latencia adicional |
| **Frontend B** | Mayor satisfacción | Es el producto principal de la defensa |

---

## 🔗 Referencias

- **RAGAS Paper**: https://arxiv.org/abs/2309.15217
- **RAGAS Docs**: https://docs.ragas.io/
- **Plan del Sprint 11**: `PLAN_EVALUACION_RAGAS.md`
- **Resultados**: `../entregables/reporte_evaluacion.md` (al completar)

---

*Documento creado el 2026-06-03. Sprint 11 - Evaluación RAGAS*
