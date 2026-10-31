# Narrativa del Proyecto - Buscador Semántico de Open Data

> **TFM - Máster en Big Data y Data Science**  
> **Autor:** [Nombre del autor]  
> **Director:** [Nombre del director]  
> **Fecha:** Junio 2026

---

## 📖 Estructura de la Memoria

```
CAPÍTULO 1: Introducción
├── 1.1 Contexto y motivación
├── 1.2 Objetivos del proyecto
└── 1.3 Estructura de la memoria

CAPÍTULO 2: Estado del Arte
├── 2.1 Datos abiertos en España (datos.gob.es)
├── 2.2 Búsqueda semántica y RAG
├── 2.3 Estándares DCAT-AP-ES
└── 2.4 Trabajos relacionados

CAPÍTULO 3: Análisis del Catálogo de Datos Abiertos ← ESTE DOCUMENTO
├── 3.1 Caracterización del corpus (87.676 datasets)
├── 3.2 Calidad de metadatos y su impacto en la búsqueda
├── 3.3 Distribución por fuente, formato, publisher
├── 3.4 Lecciones aprendidas → diseño del buscador
└── 3.5 Recomendaciones para datos.gob.es

CAPÍTULO 4: Viabilidad y Modelo de Negocio
├── 4.1 Contexto: proyecto para red.es
├── 4.2 Escenarios: interno, licencia, SaaS
├── 4.3 Escenario recomendado (híbrido escalonado)
├── 4.4 Estimaciones de ingresos y costes
└── 4.5 Supuestos críticos y plan de validación

CAPÍTULO 5: Diseño e Implementación
├── 5.1 Arquitectura del sistema
├── 5.2 Ingesta y preprocessing (Sprint 1)
├── 5.3 Búsqueda híbrida (Sprint 2-4)
├── 5.4 Query Preprocessor con LLM (Sprint 6)
├── 5.5 Frontends Streamlit (Sprint 3-15)
└── 5.6 Evaluación con RAGAS (Sprint 7-11)

CAPÍTULO 6: Resultados y Evaluación
├── 6.1 Métricas RAGAS (faithfulness, answer_relevancy, etc.)
├── 6.2 Ground truth y casos de prueba
├── 6.3 Análisis de errores
└── 6.4 Lecciones aprendidas

CAPÍTULO 7: Conclusiones
├── 7.1 Objetivos cumplidos
├── 7.2 Limitaciones
└── 7.3 Trabajo futuro

CAPÍTULO 5: Resultados y Evaluación
├── 5.1 Métricas RAGAS (faithfulness, answer_relevancy, etc.)
├── 5.2 Ground truth y casos de prueba
├── 5.3 Análisis de errores
└── 5.4 Lecciones aprendidas

CAPÍTULO 6: Conclusiones
├── 6.1 Objetivos cumplidos
├── 6.2 Limitaciones
└── 6.3 Trabajo futuro

Bibliografía
Anexos
```

---

## 🗺️ Camino Seguido - Visión General

### Fases del Proyecto

| Fase | Sprints | Duración | Objetivo |
|------|---------|----------|----------|
| **Descubrimiento** | 0-2 | 2 semanas | Entender datos.gob.es, definir arquitectura |
| **Implementación** | 3-8 | 6 semanas | Construir buscador híbrido + LLM |
| **Evaluación** | 9-11 | 3 semanas | RAGAS, ground truth, métricas |
| **Documentación** | 12-15 | 4 semanas | Memoria, artículos, presentación |

---

## 📍 Fase de Descubrimiento (Sprints 0-2)

### El Problema Inicial

**Pregunta de investigación:** ¿Cómo mejorar la búsqueda en el catálogo de datos abiertos de datos.gob.es (123.000+ datasets)?

**Contexto:**
- datos.gob.es usa búsqueda léxica tradicional (Elasticsearch)
- Los usuarios buscan por concepto, no por palabra exacta
- Ejemplo: buscar "paro" no encuentra "desempleo" o "ERC"

### Análisis del Corpus (Sprint 1)

Antes de diseñar el buscador, realizamos un análisis exhaustivo de los metadatos:

**Proceso de ingesta:**
```
123.000 datasets (catálogo completo)
    ↓
Deduplicación (hash de título + publisher)
    ↓
87.676 datasets únicos (28% duplicados eliminados)
    ↓
Limpieza de metadatos (normalización, validación DCAT-AP-ES)
```

**Hallazgos críticos del análisis** (ver [ANALISIS_METADATOS.md](ANALISIS_METADATOS.md)):

| Hallazgo | Dato | Consecuencia |
|----------|------|--------------|
| Descripciones cortas | 72.5% <50 palabras | Embeddings pobres → **híbrido obligatorio** |
| Formato desconocido | 98.5% sin formato | Parser automático por URL |
| Sin temporal | 93.9% sin cobertura | Fecha de modificación como proxy |
| Datos municipales | Solo 1.2% | Filtro territorial prioriza autonómico |

> **Lección clave:** Sin este análisis, habríamos implementado búsqueda solo semántica → fracaso garantizado. Las descripciones cortas (<50 palabras en 72.5% de casos) no generan embeddings de calidad.

### Decisión de Arquitectura

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
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌─────────────────────┐
         │   LLM Re-ranking    │
         │ (contextual, query) │
         └─────────────────────┘
```

**Justificación:**
- FTS: exacto para términos específicos ("EPA", "AROPE")
- pgvector: conceptual ("paro" → "desempleo")
- LLM: contextualiza resultados según query

---

## 💼 Viabilidad y Modelo de Negocio

> Esta sección se redacta en la **fase de diseño previa a la implementación**. Las cifras y escenarios son **hipótesis de planificación** que deberán validarse con datos reales en fases posteriores.

El proyecto es una iniciativa **académica e independiente** desarrollada fuera del ámbito laboral de sus autores. Se basa **exclusivamente en datos abiertos** del portal nacional `datos.gob.es` (gestionado por red.es). Los autores no pertenecen al departamento responsable del portal ni han recibido un encargo formal de red.es, por lo que no se requiere autorización de red.es para explotar el código desarrollado. red.es aparece como **cliente potencial** y **caso de uso de referencia**, no como empleador.

Se proponen tres escenarios viables y un plan híbrido escalonado:

| Escenario | Descripción | Horizonte | Viabilidad |
|-----------|-------------|-----------|------------|
| **A. Proyecto interno** | Integrar el buscador semántico en `datos.gob.es` como mejora del servicio público. Se mide por KPIs de UX y ahorro de costes, no por ingresos directos. | Corto plazo | Alta |
| **B. Licencia a terceros** | Empresas que compiten en concursos públicos de portales de datos adquieren el producto documentado y replicable. | Medio plazo | Media-alta |
| **C. SaaS/API multi-cliente** | Ofrecer búsqueda semántica como servicio a otras administraciones y portales sectoriales. | Largo plazo | Media-baja a corto plazo, alta a largo |
| **Híbrido recomendado** | Fase 1: interno en datos.gob.es → Fase 2: licencias → Fase 3: SaaS. Reduce riesgo y acumula credibilidad antes de escalar. | 0-36 meses | **Más robusto** |

**Propuesta de valor central**: un buscador semántico probado sobre el catálogo nacional de datos abiertos, disponible como mejora interna para red.es, licencia replicable o producto SaaS.

**Principales supuestos críticos**:
1. Los autores mantienen la titularidad del código desarrollado para el TFM.
2. red.es integra la solución como mejora interna del portal y asigna recursos de mantenimiento (Escenario A).
3. El coste de LLM (local o cloud) es sostenible con el tráfico previsto.
4. Existe demanda de integradores u otras administraciones interesadas en búsqueda semántica sobre catálogos DCAT.

El modelo de negocio completo, con Business Model Canvas por escenario, estimaciones de ingresos/costes y plan de validación, está en [`docs/BUSINESS_MODEL_CANVAS.md`](BUSINESS_MODEL_CANVAS.md).

---

## 🔬 Estado del Arte y Fundamentación

La arquitectura y los casos de uso LLM implementados se sustentan en literatura reciente de retrieval, RAG y re-ranking con LLM. La fundamentación completa está en [`docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`](research/FUNDAMENTACION_BIBLIOGRAFICA.md); las referencias BibTeX en `docs/research/semantic_search_llms.bib`.

**Papers ancla (●●●) que validan las decisiones principales:**

| Decisión del proyecto | Paper de referencia |
|-----------------------|---------------------|
| Re-ranking con LLM del top-N (#1) | RankGPT — `Sun2023_230409542` (*Is ChatGPT Good at Search?*) |
| Pipeline dos etapas: expansión + rerank | `Yeligar2025_260103258` (*Two-Stage Retrieval: FlashRank + Query Expansion*) |
| Búsqueda híbrida semántica + léxica | Blended RAG — `Gildea2024_240407220`; *Dense-Sparse + Graph ANN* — `Mariri2024_241020381` |
| Índice HNSW en pgvector | `Mariri2024_241020381` (ANN basado en grafos) |
| Expansión de query que mejora léxica y densa (#4) | Query2doc — `Wang2023_230307678` |
| Uso de metadatos en recuperación (#3/#5/#12) | `Peng2026_260111863` (*Utilizing Metadata for Better RAG*) |
| TL;DR como compresión contextual (#14) | `Jeong2024_24091385` (*Contextual Compression in RAG*, survey) |
| Filtros facetados / validación por atributos (#12) | `Ning2024_241023841` (*Beyond Content Relevance*) |
| Fusión de rankings en la híbrida | Exp4Fuse — `Zhang2025_250604760` |

> **Nota metodológica:** la fundamentación se elaboró a posteriori. Las decisiones se tomaron por iteración empírica durante los sprints y, una vez estabilizado el sistema, se verificó que el estado del arte las respalda. Esto da base académica a la defensa pero no debe leerse como un diseño dirigido por la literatura.

---

## 🛠️ Fase de Implementación (Sprints 3-8)

### Sprint 3: Primer Frontend + Filtros

**Entregable:** `frontend_b_basico/app.py`

**Características:**
- Búsqueda por texto libre
- Filtros: tema, territorio, formato
- Paginación de resultados

**Lección:** Los filtros territoriales son críticos (59% datos autonómicos, 39% nacionales).

### Sprint 4: Fallback Léxico

**Problema detectado:** La búsqueda semántica pura fallaba en:
- Queries muy específicas ("BOE-A-2023-12345")
- Acrónimos ("EPA", "AROPE", "IPC")
- Nombres propios de datasets

**Solución:** Implementar fallback léxico:
```python
if semantic_results < threshold:
    results = lexical_search(query)  # PostgreSQL FTS
else:
    results = semantic_search(query)  # pgvector
```

**Conexión con análisis:** 72.5% descripciones cortas → embeddings poco discriminativos.

### Sprint 6: LLM para Query Preprocessing

**Casos implementados:**

| Caso | Funcionalidad | Estado |
|------|--------------|--------|
| #3 | Interpretación de query | ✅ |
| #4 | Expansión con sinónimos | ✅ |
| #8 | Normalización conceptual | ❌ Archivado (0% mejora) |
| #12 | Validación de resultados | ✅ |
| #13 | Sugerencias de queries | ✅ |

**Caso #8 - Normalización Conceptual (vía muerta):**

Intentamos usar LLM para normalizar conceptos:
```
"paro juvenil" → "tasa_desempleo_jovenes_16_25"
```

**Resultado:** 105 conceptos mapeados, 0% coincidencia con títulos reales.

**Causa:** Mismatch terminológico — los títulos reales usan lenguaje administrativo, no coloquial.

**Lección:** Los LLM son útiles para expansión, no para normalización estricta.

### Sprint 7-8: API REST + Docker

**Arquitectura final:**
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   API FastAPI   │────▶│   PostgreSQL    │
│   Streamlit     │     │   (8000)        │     │   + pgvector    │
│   (8501-8503)   │     │                 │     │   (5432)        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   Ollama LLM    │
                        │   (11434)       │
                        └─────────────────┘
```

**Contenedores:**
- `buscador_postgres` — PostgreSQL + pgvector
- `buscador_api` — FastAPI (búsqueda, LLM)
- `buscador_frontend` — Router de frontends Streamlit

---

## 📊 Fase de Evaluación (Sprints 9-11)

### Ground Truth

**Composición:**
| Categoría | Queries | Ejemplo |
|-----------|---------|---------|
| Básicas | 20 | "paro juvenil", "población España" |
| Avanzadas | 15 | "EPA Q4 2023", "IPC Andalucía 2022" |
| Complejas | 13 | "brecha salarial género comunidades autónomas" |

**Total:** 48 queries evaluadas con RAGAS

### Métricas RAGAS

| Métrica | Básico | LLM | Δ |
|---------|--------|-----|---|
| P@5 | 0.279 | 0.225 | -19% |
| P@10 | 0.312 | 0.275 | -12% |
| MRR | 0.198 | 0.167 | -16% |
| Tiempo/query | 0.8s | 42s | +5150% |

**Conclusión:** El LLM mejora la relevancia percibida pero no las métricas objetivas. Coste: 42s/query vs 0.8s.

### Análisis de Errores

**Errores tipo 1 — Falso negativo semántico:**
- Query: "paro juvenil"
- Dataset no encontrado: "Tasa de desempleo menores de 25 años"
- Causa: Embedding no capturó sinonimia

**Errores tipo 2 — Falso positivo léxico:**
- Query: "IPC Canarias"
- Dataset encontrado: "Índice de Precios de Consumo" (sin territorio)
- Causa: FTS matched "Consumo" pero no territorio

---

## 🎯 Objetivos Cumplidos

| Objetivo | Estado | Evidencia |
|----------|--------|-----------|
| O1: Ingestar 100k+ datasets | ✅ | 87.676 datasets únicos |
| O2: Búsqueda híbrida | ✅ | FTS + pgvector + LLM |
| O3: Query preprocessing | ✅ | 44 datasets únicos en test |
| O4: Evaluación RAGAS | ✅ | 48 queries, 3 métricas |
| O5: Documentación | ✅ | 15 sprints, 10 docs |

---

## 📁 Entregables por Sprint

### Sprint 0-2: Fundación
- [ ] `01_Sprint0_Contexto/` — Documentación inicial
- [ ] `02_Sprint1_Datos/` — Exploración datos.gob.es
- [x] `03_Sprint1_Ingesta/` — Ingesta, deduplicación, validación

### Sprint 3-5: Búsqueda
- [x] `04_Sprint2_Busquedas/` — Primeras búsquedas (descartadas)
- [x] `05_Sprint3_API/` — API REST + pgvector
- [x] `15_Frontends/` — 13 versiones de frontends

### Sprint 6-8: LLM
- [x] `08_Sprint6_LLM_Mejora/` — Query Preprocessor, sugerencias
- [ ] `09_Sprint7_Evaluacion/` — RAGAS, ground truth

### Sprint 9-15: Consolidación
- [ ] `10_Sprint8_Produccion/` — Docker, deployment
- [ ] `11_Sprint9_Monitorizacion/` — Logs, métricas
- [ ] `docs/` — Memoria completa

---

## 🌲 Estrategia de Ramas Git

```
main (producción)
├── feature/query-suggestions-13    ← Sugerencias de queries (Caso #13)
├── feature/ragas-evaluation        ← Evaluación RAGAS
└── experiment/
    ├── conceptual-normalization    ← Caso #8 (archivado, 0% mejora)
    ├── pure-semantic-search        ← Descartado (fallback necesario)
    └── llm-only-ranking            ← Descartado (42s/query)
```

**Convención:**
- `main` — código estable, desplegable
- `feature/*` — funcionalidades en desarrollo
- `experiment/*` — vías muertas (documentadas pero no mergeadas)

---

## 📚 Lecciones Aprendidas

### Técnicas

1. **Embeddings de texto corto fallan**
   - 72.5% descripciones <50 palabras
   - Solución: híbrido léxico + semántico

2. **LLM es lento para ranking en tiempo real**
   - 42s/query vs 0.8s baseline
   - Uso: solo para queries complejas o background

3. **Deduplicación es crítica**
   - 28% duplicados eliminados (123k → 87k)
   - Hash: título + publisher + issued_date

4. **DCAT-AP-ES no se cumple totalmente**
   - 81% cumplimiento (13/16 campos)
   - Formato y temporal son los más omitidos

### Gestión de Proyectos

1. **Análisis exploratorio antes de implementar**
   - El análisis de metadatos evitó diseño incorrecto
   - 2 horas de análisis → 4 semanas de implementación correcta

2. **Documentar vías muertas**
   - Caso #8 (normalización) archivado pero documentado
   - Ahorra tiempo a futuros investigadores

3. **Evaluación continua**
   - RAGAS después de cada sprint LLM
   - Ground truth como referencia común

---

## 🔮 Trabajo Futuro

### Corto Plazo

1. **Indexar contenido full-text** (no solo metadatos)
   - Actualmente: solo título + descripción
   - Futuro: contenido de CSV/JSON

2. **Query logs para mejora continua**
   - Registrar queries sin resultados
   - Análisis de gaps semánticos

### Largo Plazo

1. **RAG sobre contenido de datasets**
   - "¿Cuál es la tasa de paro en Canarias 2023?"
   - Respuesta directa desde CSV, no solo metadato

2. **Fine-tuning de embeddings**
   - Domain-specific para datos abiertos
   - Entrenar con queries reales + clicks

---

## 📎 Anexos

### A. Comandos Útiles

```bash
# Ingesta completa
cd 03_Sprint1_Ingesta/codigo
python3 ingestar.py --source datos.gob.es

# Búsqueda manual
curl "http://localhost:8000/search?q=paro+juvenil&limit=10"

# Evaluación RAGAS
cd 09_Sprint7_Evaluacion/codigo
python3 evaluate_ragas.py --ground-truth ground_truth_v2.jsonl
```

### B. Endpoints API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/search` | GET | Búsqueda híbrida |
| `/search/lexical` | GET | Solo léxica (FTS) |
| `/search/semantic` | GET | Solo semántica (pgvector) |
| `/enhanced/query/suggest` | POST | Sugerencias de queries |
| `/enhanced/query/interpret` | POST | Interpretación con LLM |

### C. Referencias Cruzadas

- **Análisis de metadatos:** [ANALISIS_METADATOS.md](ANALISIS_METADATOS.md)
- **Cumplimiento DCAT-AP-ES:** `docs/cumplimiento_DCAT-AP-ES.md`
- **Query Preprocessor:** `08_Sprint6_LLM_Mejora/docs/CASO_3_4_12_QUERY_PREPROCESSOR.md`
- **Evaluación RAGAS:** `09_Sprint7_Evaluacion/docs/EVALUACION_RAGAS_SPRINT7.md`

---

## 📚 Referencias (APA 7ª edición)

Listado de las obras citadas en la sección *Estado del Arte y Fundamentación* y en `docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`. Todas son preprints de arXiv. Las autorías se verificaron contra los PDFs en `docs/research/pdfs/` (el fichero `semantic_search_llms.bib` contenía autorías incorrectas que se han corregido aquí).

Formal, T., Piwowarski, B., & Clinchant, S. (2021). *SPLADE: Sparse lexical and expansion model for first stage ranking*. arXiv. https://arxiv.org/abs/2107.05720

Gao, L., Ma, X., Lin, J., & Callan, J. (2022). *Precise zero-shot dense retrieval without relevance labels*. arXiv. https://arxiv.org/abs/2212.10496

George, S. (2025). *Enhancing retrieval-augmented generation with two-stage retrieval: FlashRank reranking and query expansion*. arXiv. https://arxiv.org/abs/2601.03258

Jedidi, N., & Lin, J. (2026). *A systematic study of pseudo-relevance feedback with LLMs*. arXiv. https://arxiv.org/abs/2603.11008

Ma, X., Gong, Y., He, P., Zhao, H., & Duan, N. (2023). *Query rewriting for retrieval-augmented large language models*. arXiv. https://arxiv.org/abs/2305.14283

Nogueira, R., Jiang, Z., & Lin, J. (2020). *Document ranking with a pretrained sequence-to-sequence model*. arXiv. https://arxiv.org/abs/2003.06713

Pradeep, R., Sharifymoghaddam, S., & Lin, J. (2023). *RankVicuna: Zero-shot listwise document reranking with open-source large language models*. arXiv. https://arxiv.org/abs/2309.15088

Qin, Z., Jagerman, R., Hui, K., Zhuang, H., Wu, J., Yan, L., Shen, J., Liu, T., Liu, J., Metzler, D., Wang, X., & Bendersky, M. (2023). *Large language models are effective text rankers with pairwise ranking prompting*. arXiv. https://arxiv.org/abs/2306.17563

Sawarkar, K., Mangal, A., & Solanki, S. R. (2024). *Blended RAG: Improving RAG (retriever-augmented generation) accuracy with semantic search and hybrid query-based retrievers*. arXiv. https://arxiv.org/abs/2404.07220

Sun, W., Yan, L., Ma, X., Wang, S., Ren, P., Chen, Z., Yin, D., & Ren, Z. (2023). *Is ChatGPT good at search? Investigating large language models as re-ranking agents*. arXiv. https://arxiv.org/abs/2304.09542

Verma, S. (2024). *Contextual compression in retrieval-augmented generation for large language models: A survey*. arXiv. https://arxiv.org/abs/2409.13385

Wang, L., Yang, N., Huang, X., Jiao, B., Yang, L., Jiang, D., Majumder, R., & Wei, F. (2022). *Text embeddings by weakly-supervised contrastive pre-training*. arXiv. https://arxiv.org/abs/2212.03533

Wang, L., Yang, N., & Wei, F. (2023). *Query2doc: Query expansion with large language models*. arXiv. https://arxiv.org/abs/2303.07678

Wang, S., Li, Y., Xiao, H., Dai, B. T., Lee, R. K.-W., Dong, Y., & Deng, L. (2025). *LLMATCH: A unified schema matching framework with large language models*. arXiv. https://arxiv.org/abs/2507.10897

Xia, Y., Wu, J., Kim, S., Yu, T., Rossi, R. A., Wang, H., & McAuley, J. (2024). *Knowledge-aware query expansion with large language models for textual and relational retrieval*. arXiv. https://arxiv.org/abs/2410.13765

Yang, Y., Carlson, P., Qiao, Y., Xie, W., He, S., & Yang, T. (2025). *LSTM-based selective dense text retrieval guided by sparse lexical retrieval*. arXiv. https://arxiv.org/abs/2502.10639

Yousuf, R. B., Xu, S., Sharma, M., Neeser, A., Latimer, C., & Ramakrishnan, N. (2026). *Utilizing metadata for better retrieval-augmented generation*. arXiv. https://arxiv.org/abs/2601.11863

Zhang, H., Liu, J., Zhu, Z., Zeng, S., Sheng, M., & Yang, T. (2024). *Efficient and effective retrieval of dense-sparse hybrid vectors using graph-based approximate nearest neighbor search*. arXiv. https://arxiv.org/abs/2410.20381

Zhang, M., & Liu, L. (2025). *Exp4Fuse: A rank fusion framework for enhanced sparse retrieval using large language model-based query expansion*. arXiv. https://arxiv.org/abs/2506.04760

Zhou, J., Zheng, Y., Chen, W., Zheng, Q., Su, H., Zhang, W., Meng, R., & Shen, X. (2025). *Beyond content relevance: Evaluating instruction following in retrieval models*. arXiv. https://arxiv.org/abs/2410.23841

> Nota: para citar en el cuerpo de la memoria usar el formato autor-fecha, p. ej. (Sun et al., 2023), (Sawarkar et al., 2024), (Yousuf et al., 2026). El mapeo detallado de cada referencia a los casos de uso y decisiones arquitectónicas está en [`docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`](research/FUNDAMENTACION_BIBLIOGRAFICA.md).

---

*Documento de narrativa — versión 1.1 (2026-06-19)*
