# Endpoints de la API - Buscador Semantico de Datasets

## API principal (main_v2_final_v07.py)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/` | Raiz / mensaje de bienvenida |
| GET | `/health` | Health check con estado de PostgreSQL |
| POST | `/search` | Busqueda hibrida (semantica + lexica) |
| GET | `/datasets/{dataset_id}` | Obtener un dataset por ID |
| GET | `/datasets` | Listar datasets |
| GET | `/facets/{facet_type}` | Valores de faceta (tema, territorio, formato, publisher) |
| POST | `/experimental/concept-normalize` | Normalizacion conceptual (experimental) |
| POST | `/experimental/conceptual-search` | Busqueda conceptual (experimental) |

## Routers incluidos

### routes_llm_v2.py (prefijo /llm) - Casos #1 y #2

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| POST | `/llm/search/rerank` | Re-ranking inteligente de resultados |
| POST | `/llm/search/explain` | Explicaciones de relevancia |
| GET | `/llm/health` | Health check LLM |

### routes_v09.py (prefijo /llm)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| POST | `/llm/enhance` | Mejora de resultados con LLM |
| POST | `/llm/explain` | Explicacion de relevancia |
| GET | `/llm/health` | Health check LLM |
| POST | `/llm/preprocess` | Preprocesamiento de query |
| POST | `/llm/search-enhanced` | Busqueda completa con LLM |

### routes_v10.py (prefijo /llm)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| POST | `/llm/search/fast` | Busqueda rapida con LLM |
| POST | `/llm/explain` | Explicacion de resultados |
| POST | `/llm/enhance` | Mejora de resultados |
| GET | `/llm/health` | Health check LLM |

### routes_query_enhanced.py (prefijo /enhanced) - Casos #3, #4, #12, #13

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| POST | `/enhanced/search` | Busqueda con preprocesamiento |
| POST | `/enhanced/query/analyze` | Analisis de query (#3) |
| POST | `/enhanced/query/validate` | Validacion de query (#12) |
| POST | `/enhanced/query/expand` | Expansion semantica (#4) |
| POST | `/enhanced/query/suggest` | Sugerencias de queries (#13) |
| GET | `/enhanced/query/suggest/{cache_key}/result` | Resultado asincrono de sugerencias |
| POST | `/enhanced/query/suggest/llm` | Sugerencias via LLM (#13) |
| GET | `/enhanced/query/suggest/lexical` | Sugerencias lexicas (#13) |
| GET | `/enhanced/health` | Health check general |
| GET | `/enhanced/query/suggest/health` | Health check sugerencias |

### routes_complementary.py (prefijo /complementary) - Casos #5 y #14

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/complementary/{dataset_id}/tldr` | Resumen TL;DR del dataset (#14) |
| GET | `/complementary/{dataset_id}` | Metadatos complementarios precalculados (#5) |
| POST | `/complementary/find` | Buscar datasets complementarios (#5) |

## Total: 31 endpoints
