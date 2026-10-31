# Analisis de Arquitectura - PFM Buscador Semantico

## 1. Resumen Ejecutivo

El proyecto **Datatrust** es un buscador semantico de datasets publicos del portal [datos.gob.es](https://datos.gob.es), desarrollado como TFM del Master EOI. Combina busqueda semantica (embeddings), busqueda lexica (full-text) y multiples mejoras basadas en Modelos de Lenguaje (LLM) para mejorar la recuperacion de datasets abiertos ante consultas en lenguaje natural.

## 2. Casos de Uso LLM

El Sprint 6 define **14 casos de uso de LLM** para mejorar la busqueda. Segun el indice actualizado (`08_Sprint6_LLM_Mejora/docs/INDICE_CASOS_USO_LLM.md`):

### Implementados y estables (8/14)

| # | Caso | Descripcion | Archivos principales |
|---|------|-------------|----------------------|
| #1 | Re-ranking inteligente | Reordena Top-N por relevancia analitica | `llm_reranker.py`, `routes_llm_v2.py` |
| #2 | Explicaciones de relevancia | Genera justificacion por dataset | `llm_reranker.py` |
| #3 | Interpretacion de query | Extrae tema, territorio, año, conceptos | `query_preprocessor.py` |
| #4 | Expansion semantica | Añade sinonimos y terminos relacionados | `query_preprocessor.py`, `lexical_expander.py` |
| #5 | Datasets complementarios | Detecta datasets combinables analiticamente | `routes_complementary.py`, `batch_generate_profiles.py` |
| #12 | Validacion de queries | Detecta queries invalidas, ambiguas o typos | `query_preprocessor.py` |
| #13 | Sugerencias de queries | Propone busquedas alternativas | `query_suggester.py`, `routes_query_enhanced.py` |
| #14 | Resumen automatico (TL;DR) | Genera resumen de 2-3 frases por dataset | `batch_generate_profiles.py`, `routes_complementary.py` |

### Archivado (1/14)

| # | Caso | Estado | Motivo |
|---|------|--------|--------|
| #8 | Normalizacion semantica de conceptos | Via muerta | 0% mejora por mismatch terminologico administrativo vs coloquial |

### Pendientes (5/14)

| # | Caso | Descripcion |
|---|------|-------------|
| #6 | Evaluacion de compatibilidad | Analiza si dos datasets pueden unirse tecnicamente |
| #7 | Generacion de planes de analisis | Crea propuestas de analisis combinatorio |
| #9 | Perfilado tecnico automatico | Describe campos, formatos, calidad del dataset |
| #10 | Respuestas a preguntas sobre datasets | Chat sobre un dataset especifico |
| #11 | Sintesis de multiples datasets | Resume varios datasets como grupo coherente |

## 3. Componentes Principales

### 3.1 Ingesta y Preprocesamiento
- **Ruta:** `03_Sprint1_Ingesta/`
- **Scripts clave:**
  - `ingest_datos_gob_v2.py`: descarga masiva de metadatos desde datos.gob.es.
  - `clean_datasets.py`: limpieza, normalizacion y deduplicacion.
  - `generate_embeddings.py`: generacion de embeddings con sentence-transformers.
- **Salida:**
  - 134.150 datasets descargados.
  - 87.676 datasets unicos limpios.
  - Embeddings 87.676 x 384D.

### 3.2 Embeddings e Indices
- **Ruta:** `04_Sprint2_Embeddings/`
- **Modelo:** `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones).
- **Indices:**
  - `bm25_index.pkl`: indice lexico BM25.
  - `index_tema.json`, `index_territorio.json`, `index_publisher.json`, `index_formato.json`: indices facetados.
  - `id_position_map.json`: mapeo ID -> posicion en embeddings.

### 3.3 Motor de Busqueda Hibrida
- **Ruta:** `05_Sprint3_Busqueda_UI/codigo/motor/search_engine.py`
- **Tecnicas:**
  - Busqueda semantica por similitud de embeddings.
  - Busqueda lexica con BM25.
  - Normalizacion y combinacion de scores.
  - Filtros facetados por tema, territorio, formato y publisher.

### 3.4 API REST
- **Ruta:** `08_Sprint6_LLM_Mejora/codigo/api/main_v2_final_v07.py`
- **Framework:** FastAPI.
- **Endpoints principales:**
  - `GET /search`: busqueda hibrida.
  - `GET /search/lexical`: busqueda solo lexica.
  - `GET /search/semantic`: busqueda solo semantica.
  - `POST /llm/search/rerank`: re-ranking con LLM (#1, #2).
  - `POST /enhanced/query/*`: preprocesamiento de queries (#3, #4, #12, #13).
  - `GET /complementary/{dataset_id}/tldr`: TL;DR (#14).
  - `POST /complementary/find`: datasets complementarios (#5).
  - `GET /facets/{facet_type}`: valores de facetas.

### 3.5 Pipeline LLM y Mejoras
- **Ruta:** `08_Sprint6_LLM_Mejora/codigo/motor/`
- **Componentes:**
  - `llm_client.py`: cliente generico para Ollama.
  - `llm_reranker.py`: re-ranking con explicaciones (#1, #2).
  - `query_preprocessor.py`: validacion, interpretacion y expansion (#3, #4, #12).
  - `query_suggester.py`: sugerencias de queries (#13).
  - `lexical_expander.py`: fallback lexico para expansion (#4).
  - `batch_generate_profiles.py`: generacion offline de perfiles y TL;DR (#14).
- **Perfiles de datasets:**
  - Tabla `dataset_profiles` (migracion `db/migrations/004_dataset_profiles.sql`).
  - Campos: `tldr`, `variables_key`, `temporal_coverage`, `geographic_level`, `combinable_with`.

### 3.6 Base de Datos
- **Tecnologia:** PostgreSQL 15 + pgvector.
- **Esquema:** `07_Sprint5_Integracion/codigo/db/init.sql`
- **Tablas principales:**
  - `datasets`: metadatos + embedding + tsvector.
  - `dataset_profiles`: perfiles generados por LLM (TL;DR, variables, etc.).
  - `term_synonyms`: sinonimos para expansion.
  - `query_logs`: logs de busquedas.
- **Indices:**
  - HNSW sobre `embedding` para busqueda semantica.
  - GIN sobre `search_vector` para busqueda lexica.
  - B-tree sobre campos de faceta.

### 3.7 Frontends
- **Ruta:** `15_Frontends/`
- **Versiones:**
  - `frontend_a_basico/`: MVP funcional.
  - `frontend_b_intermedio/`: interfaz publica principal con TL;DR y complementarios.
  - `frontend_c_avanzado/`: demo con capacidades LLM.

### 3.8 Evaluacion
- **Ruta:** `06_Nivel4_Evaluacion/` y `09_Sprint7_RAGAS/`
- **Metodos:**
  - Baterias de tests propias (`test_bateria.py`, `test_bateria_extendida.py`).
  - Evaluacion RAGAS con ground truth (`eval_ragas_core.py`).

## 4. Flujo de Datos

1. El usuario introduce una query en el frontend Streamlit.
2. La query llega a la API FastAPI.
3. El preprocesador valida (#12), interpreta (#3) y expande (#4) la query, con fallback lexico.
4. El motor hibrido consulta PostgreSQL: busqueda semantica (pgvector) + lexica (tsvector).
5. Opcionalmente, el LLM reordena los mejores resultados (#1) y genera explicaciones (#2).
6. El frontend puede mostrar TL;DR (#14) y datasets complementarios (#5) bajo demanda.
7. La API devuelve resultados priorizados al frontend.

## 5. Stack Tecnologico

| Capa | Tecnologia |
|---|---|
| Lenguaje | Python 3.11+ |
| Embeddings | sentence-transformers (MiniLM-L12-v2) |
| Base de datos | PostgreSQL 15 + pgvector |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| LLM | Ollama (deepseek-v4-flash:cloud / deepseek-v4-pro:cloud) |
| Contenedores | Docker Compose |
| Evaluacion | RAGAS, pytest |

## 6. Metricas Clave

- Datasets indexados: **87.676**
- Perfiles TL;DR generados (validacion): **100**
- Calidad TL;DR (muestra): **90%**
- Dimensiones embedding: **384**
- Precision @5 (RAGAS baseline): **0.702**
- NDCG@10: **0.792**
- Latencia busqueda hibrida: **~50 ms**
- Latencia re-ranking LLM: **~60-80 s cloud**
- Latencia preprocesamiento LLM: **~10-30 s**
- Latencia TL;DR endpoint: **<100 ms**
- Latencia complementariedad: **~8-15 s**

## 7. Observaciones y Recomendaciones

- **Punto fuerte:** arquitectura modular y bien documentada por sprints. Los 14 casos de uso LLM estan claramente trazados.
- **Punto de atencion:** multiples versiones de routers (`routes_v09`, `routes_v10`, `routes_query_enhanced`, `routes_complementary`) conviene consolidar.
- **Recomendacion:** completar el batch offline de perfiles para los 87.676 datasets y precalcular complementariedad para los mas populares.
- **Recomendacion:** cachear resultados LLM frecuentes y considerar Redis para reducir latencia.
- **Recomendacion:** priorizar los 5 casos pendientes segun valor: #10 (respuestas sobre datasets) y #7 (planes de analisis) son los mas prometedores.
