# Datatrust — Buscador Semántico de Datasets Públicos

> TFM — Máster EOI · Buscador semántico de datasets del portal [datos.gob.es](https://datos.gob.es)
> con re-ranking e interpretación de consultas mediante LLM, búsqueda híbrida (semántica + léxica) y PostgreSQL + pgvector.

**En producción:** <https://datatrust.ejemplo.com> · interfaz pública y modo avanzado en `?mode=advanced`

![Estado](https://img.shields.io/badge/estado-operativo-success) ![Python](https://img.shields.io/badge/python-3.11+-blue) ![PostgreSQL](https://img.shields.io/badge/postgresql-15%2B-blue) ![pgvector](https://img.shields.io/badge/pgvector-0.5%2B-blue) ![Licencia](https://img.shields.io/badge/licencia-EOI-informational)

---

## 📋 Resumen

Aplicación que convierte **preguntas en lenguaje natural** sobre datos públicos en una **lista priorizada y explicada de datasets** de `datos.gob.es`. Combina búsqueda semántica (embeddings multilingües), búsqueda léxica (full-text) y un LLM local/cloud para re-ranking, expansión de queries y validación de metadatos.

**Problema que resuelve:** la búsqueda por palabras clave en portales de datos abiertos es ineficiente para preguntas de análisis ("paro juvenil en Canarias 2023" → debe devolver datasets relevantes aunque el término exacto no esté en el título).

### Capacidades principales

| Capacidad | Descripción |
|---|---|
| **Búsqueda híbrida** | Combina similitud semántica (BGE-M3, 1.024 d) con ranking léxico (TSVECTOR) en PostgreSQL + pgvector, con pesos ajustables (por defecto 70/30) |
| **Re-ranking con LLM** | Un LLM reordena el top-N de resultados según relevancia analítica y genera explicación por dataset |
| **Interpretación de queries** | Extrae tema, territorio y año de la query; expande con sinónimos (paro → desempleo, atur, parados...) |
| **Validación de metadatos** | Detecta inconsistencias (p. ej. `publisher="Universidad de Barcelona"` mientras el `title` menciona "UEx") |
| **Filtros facetados** | Por tema, territorio, formato, publicador |
| **TL;DR de datasets** | Resumen generado por LLM del propósito y contenido de cada dataset |
| **Datasets complementarios** | Recomienda datasets relacionados por tema/geografía (modo rápido precalculado + opción LLM) |
| **Chat sobre datasets** | Responde con el esquema y una muestra del fichero real descargado (57.269 ficheros), no solo con los metadatos |
| **Fallback léxico** | Diccionario de ~100 términos garantiza expansión instantánea (<1 ms) cuando el LLM falla |

---

## 🚀 Quick Start

### Requisitos

- Python 3.11+
- PostgreSQL 15+ con la extensión `pgvector` 0.5+
- 4 GB RAM mínimo · 10 GB disco (incluye los embeddings)
- (Opcional) Acceso a un LLM — por defecto `deepseek-v4.1-flash` vía Ollama Cloud (OpenAI-compatible), con fallback a `deepseek-v4-pro` y `glm-5.3-flash`

### 1. Clonar e instalar dependencias

```bash
git clone <url-del-repositorio>
cd Datatrust
python3 -m venv venv
source venv/bin/activate
pip install -r 99_Compartido/herramientas/requirements.txt
```

### 2. Configurar PostgreSQL

```bash
# Crear base de datos y extensiones
sudo -u postgres psql -c "CREATE DATABASE buscador;"
sudo -u postgres psql -d buscador -c "CREATE EXTENSION IF NOT EXISTS vector;"
sudo -u postgres psql -d buscador -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# Aplicar esquema (tablas, índices y funciones de búsqueda)
psql -d buscador -f 07_Sprint5_Integracion/codigo/db/init.sql
```

### 3. Variables de entorno

Crear `07_Sprint5_Integracion/codigo/.env`:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=buscador
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
API_PORT=8000
```

### 4. Cargar datos (si la base está vacía)

> ⚠️ **Los datasets crudos y los embeddings NO están en el repositorio** (1.2 GB en total).
> Están excluidos vía `.gitignore` para mantener el repo ligero. Tienes dos opciones:

**Opción A — Re-ingestar desde cero** (recomendado para datos actualizados):

> ℹ️ **Solo hay un `init.sql`** (en `07_Sprint5_Integracion/codigo/db/init.sql`), aplicado en el paso 2 para crear tablas, índices y funciones. No es necesario volver a ejecutarlo si la base de datos ya existe.

```bash
# 4.1 Descargar datasets desde datos.gob.es (~528 MB, 22 min)
python3 03_Sprint1_Ingesta/codigo/conectores/ingest_datos_gob_v2.py

# 4.2 Limpiar y normalizar → 94.461 datasets limpios
python3 03_Sprint1_Ingesta/codigo/limpieza/clean_datasets.py

# 4.3 Generar embeddings (BGE-M3 vía Ollama; el pipeline con sentence-transformers queda como alternativa)
python3 03_Sprint1_Ingesta/codigo/limpieza/generate_embeddings.py

# 4.4 Construir índices BM25 + facetados (~7 segundos)
python3 04_Sprint2_Embeddings/codigo/indexacion/build_indices.py

# 4.5 Insertar en PostgreSQL (las tablas ya existen del paso 2)
python3 07_Sprint5_Integracion/codigo/db/migrate_from_numpy.py
```

**Opción B — Dump SQL pre-generado** (más rápido, recomendado para evaluación):

Si tienes un dump de la base de datos (compartido por el equipo):

```bash
# Restaurar dump
psql -d buscador < backup_buscador_2026XXXX.sql
```

> 💡 **¿Por qué no se suben los datos al repo?**
> - **Tamaño:** catálogo crudo (134.150 registros) + 94.461 vectores de 1.024 d + ficheros descargados · GitHub recomienda repos <1 GB
> - **GitHub Free:** límite estricto de 100 MB por archivo
> - **Frescura:** los datos de `datos.gob.es` se actualizan periódicamente — regenerar garantiza actualidad
> - **Privacidad / coste:** los datos son públicos, pero el repo es académico
>
> Los **scripts de regeneración están versionados** en el repo, así que cualquiera puede reconstruir el estado local con un solo comando.

### 5. Lanzar la API

> ⚠️ **Usa `--app-dir`** (no el path de módulo completo). Si se lanza como
> `uvicorn 08_Sprint6_LLM_Mejora.codigo.api.main_v2_final_v07:app`, los routers LLM
> (`routes_v10`, `routes_query_enhanced`, `routes_complementary`, `routes_dataset_chat`)
> **no se cargan** porque sus `import` planos no resuelven `codigo/api/` en `sys.path`.
> Con `--app-dir` el directorio de la API entra en `sys.path` y se montan los endpoints
> de los casos de uso #1–#14. Ver detalles en [`docs/ARRANQUE_SERVICIOS.md`](docs/ARRANQUE_SERVICIOS.md).

> ⚠️ **Evita `--reload` en sesiones largas**: el repo es grande (docs, PDFs, `.git`) y el watcher de Uvicorn puede consumir ~100% de una CPU constantemente. Para desarrollo usa `--reload-dir 08_Sprint6_LLM_Mejora/codigo/api`; para uso normal quita `--reload`.

```bash
cd Datatrust
source venv/bin/activate
# Uso normal (sin reload)
uvicorn main_v2_final_v07:app \
  --app-dir 08_Sprint6_LLM_Mejora/codigo/api \
  --host 0.0.0.0 --port 8000

# O, solo para desarrollo activo, con reload limitado:
# uvicorn main_v2_final_v07:app \
#   --app-dir 08_Sprint6_LLM_Mejora/codigo/api \
#   --host 0.0.0.0 --port 8000 \
#   --reload --reload-dir 08_Sprint6_LLM_Mejora/codigo/api
```

Verificar que los routers LLM se cargaron (debe haber 4 líneas "cargado correctamente" en el log):

```bash
curl http://localhost:8000/health
# {"status":"ok","postgresql":"connected","pgvector":true,"datasets_count":94461,...}
```

### 6. Lanzar el frontend unificado (opcional)

```bash
cd Datatrust
source venv/bin/activate
cd 15_Frontends/frontend_b_intermedio
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

El frontend lee `API_URL` de una variable de entorno (por defecto `http://localhost:8000`).
Si la API corre en otro puerto, arráncalo así:

```bash
API_URL=http://localhost:8000 streamlit run app.py --server.port 8501 --server.headless true
```

Abrir `http://localhost:8501` para el modo público ligero.

Para el modo avanzado/demostrador técnico:

```bash
streamlit run app.py --server.port 8501 -- --mode advanced
# o visitar http://localhost:8501/?mode=advanced
```

### Despliegue con Docker (vía usada en producción)

```bash
cd 07_Sprint5_Integracion/codigo/docker
docker compose up -d
```

Levanta los tres servicios: PostgreSQL+pgvector (5432), API FastAPI (8000) y frontend Streamlit (8501).

Tras cambiar código del frontend o de la API hay que reconstruir: `docker compose build frontend && docker compose up -d --no-deps frontend`
(el código va copiado dentro de la imagen, no montado por volumen).

### Estado en producción

| Pieza | Dónde |
|---|---|
| Frontend público | <https://datatrust.ejemplo.com> — Streamlit, sin SSO |
| Frontend avanzado | <https://datatrust.ejemplo.com/?mode=advanced> — pesos del motor, filtros y diagnósticos |
| API | `127.0.0.1:8000` (`/health`, `/openapi.json`) |
| PostgreSQL + pgvector | `127.0.0.1:5432` (pgvector 0.5.1) |
| Proxy TLS | nginx propio con certificado por dominio (Let's Encrypt) |
| Contenedores | `buscador_postgres`, `buscador_api`, `buscador_frontend` (healthcheck `/_stcore/health`) |

Medido el 5-nov-2026: 94.461 datasets · 94.461 con vector BGE-M3 · 87.661 con `embedding_text` · 57.269 ficheros · 5.073 perfiles LLM.

---

## 🧱 Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend Streamlit unificado (15_Frontends/frontend_b_)    │
│  ├── Modo público (public/app.py)    Rápido/visual            │
│  └── Modo avanzado (advanced/app.py) Demostrador técnico    │
└──────────────────────────┬───────────────────────────────────┘
                           │  HTTP
┌──────────────────────────▼───────────────────────────────────┐
│  API FastAPI  (08_Sprint6_LLM_Mejora/codigo/api/main_v2_)   │
│  ├── /search                    Búsqueda híbrida (70/30)    │
│  ├── /llm/search/fast           ⚠️ NO USAR: sin motor híbrido │
│  ├── /llm/explain               ⚠️ NO USAR: bug get_v07_url  │
│  ├── /llm/enhance              Búsqueda con re-ranking LLM  │
│  ├── /enhanced/search           Pipeline completo (pre-procesamiento + búsqueda) │
│  ├── /enhanced/query/analyze    Interpretación de query     │
│  ├── /complementary/tldr        TL;DR del dataset (query param: ?dataset_id=) │
│  ├── /complementary/find        Datasets complementarios    │
│  ├── /dataset/chat              Chat sobre un dataset (POST, dataset_id en body) │
│  ├── /datasets, /datasets/{id}  Fichas y metadatos          │
│  ├── /facets/{facet_type}       Valores de facetas          │
│  └── /enhanced/query/{analyze,expand,validate,suggest}      │
└──────────┬─────────────────────────────────┬─────────────────┘
           │                                 │
┌──────────▼──────────────┐    ┌─────────────▼─────────────────┐
│  Motor Híbrido          │    │  LLM  (Ollama / cloud)        │
│  - pgvector (semántico) │    │  - re-ranking analítico       │
│  - TSVECTOR (léxico)    │    │  - expansión de queries       │
│  - BM25 + sinónimos     │    │  - TL;DR y chat               │
│  - fallback léxico      │    │  - validación de metadatos    │
└──────────┬──────────────┘    └───────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────────────────┐
│  PostgreSQL 15 + pgvector (94.461 datasets · 1.024 dims)     │
└──────────────────────────────────────────────────────────────┘
```

**Flujo del pipeline con LLM** (caso `/enhanced/search`):

1. **Validación** de la query (idioma, ambigüedad, completitud)
2. **Interpretación** → JSON con `{tema, territorio, año, conceptos}`
3. **Expansión** → añade sinónimos y términos relacionados (LLM, con fallback léxico <1 ms)
4. **Búsqueda híbrida** → top-20 candidatos (semántico + léxico)
5. **Re-ranking LLM** → reordena por relevancia analítica y genera explicación
6. **Respuesta** → lista priorizada con score, explicación y metadatos

Detalles en [`08_Sprint6_LLM_Mejora/docs/INTEGRACION_API.md`](08_Sprint6_LLM_Mejora/docs/INTEGRACION_API.md).

---

## 🗂️ Estructura del proyecto

El proyecto sigue la **metodología EOI** (Design Thinking + Scrum + Data Model Canvas) en 6 sprints + fases de Design Thinking.

| # | Carpeta | Descripción | Estado |
|---|---------|-------------|--------|
| 00 | `00_Kickoff/` | Acuerdos de equipo, setup inicial | ✅ |
| 01 | `01_Empatizar_Definir/` | 5 entrevistas, 3 personas, journey maps, insights | ✅ |
| 02 | `02_Idear_Prototipar/` | DMC, wireframes, prototipos, ideas descartadas | ✅ |
| 03 | `03_Sprint1_Ingesta/` | Ingesta de 134.150 registros desde datos.gob.es, limpieza a 94.461 datasets | ✅ |
| 04 | `04_Sprint2_Embeddings/` | Embeddings BGE-M3 94.461×1.024 (columna `embedding_bge`), índices BM25 + facetados + HNSW | ✅ |
| 05 | `05_Sprint3_Busqueda_UI/` | Motor de búsqueda híbrido + API REST + frontend Streamlit | ✅ |
| 06 | `06_Nivel4_Evaluacion/` | Batería de tests · 10/12 PASS (83%) en baseline | ✅ |
| 07 | `07_Sprint5_Integracion/` | Docker, PostgreSQL + pgvector, despliegue | ✅ |
| 08 | `08_Sprint6_LLM_Mejora/` | Re-ranking con LLM, expansión, validación, fallback léxico | ✅ |
| 09 | `09_Sprint7_RAGAS/` | Evaluación con ground truth v6: nDCG@10 0,5774 (214 consultas) y 0,7116 (47 humanas) | ✅ |
| 10 | `15_Frontends/` | Frontend unificado: modo público + modo avanzado | ✅ |
| — | `99_Compartido/` | Recursos compartidos: requirements.txt, config | ✅ |

La mayoría de sprints contienen `codigo/`, `docs/`, `entregables/` y un `README_<sprint>.md` con su estado y conclusiones.

---

## 📊 Métricas y resultados

### Calidad del buscador

**KPI oficial: ground truth v6 (14-oct-2026).** Es la única tabla que debe citarse en la defensa.

| Métrica | Todas las consultas (214) | Solo humanas (47) |
|---|---|---|
| **nDCG@10** | **0,5774** · IC95 [0,5311–0,6237] | **0,7116** · IC95 [0,6311–0,7921] |
| P@5 | 0,4318 | 0,6511 |
| P@10 | 0,4000 | 0,5851 |
| MRR | 0,5942 | 0,8039 |
| Cobertura del juicio en el top-10 | 100 % | 100 % |

- Las **214** = 47 humanas + 167 generadas por LLM ancladas en 40 títulos reales (12 categorías × 18; 216 generadas, 214 tras depurar).
- **Mejora mínima detectable** (nDCG@10): 0,0463.
- **Cambio de motor de embeddings** (MiniLM → BGE-M3): **+0,1526** [+0,1113, +0,1938].
- El valor **0,6716** que aparece en la comparación contra el ground truth scrapeado de datos.gob.es **no es el KPI**: es una comparación entre instrumentos de medida.
- Las baterías de `06_Nivel4_Evaluacion` (10/12 PASS) siguen siendo válidas como *smoke test*, no como métrica de calidad.

#### Motor y volumen de datos

| | |
|---|---|
| Datasets indexados | **94.461** |
| Embeddings | **BGE-M3, 1.024 d** (columna `embedding_bge`) en el **100 %** del corpus |
| Texto persistido para el léxico | `embedding_text` en 87.661 (92,8 %); los 6.800 restantes tienen vector real pero no texto guardado |
| Índice HNSW | **738 MB** (queda el índice MiniLM heredado, 182 MB) |
| Peso por defecto del ranking | 70 % semántico / 30 % léxico |
| Contenido de ficheros | **57.269** registros en `dataset_files`: 56.170 con muestra de texto, 56.431 con esquema |
| Perfiles LLM precalculados | **5.073** en `dataset_profiles` (5,4 % del corpus) |

#### Latencia (medida sobre el servicio en producción, 5-nov-2026)

| Operación | Tiempo |
|---|---|
| Búsqueda híbrida, extremo a extremo | **2,5–3,5 s** en caliente · **8–12 s** en frío (el SQL son ~30–50 ms; lo que tarda es el embedding de la consulta) |
| TL;DR con perfil precalculado | instantáneo |
| TL;DR generado bajo demanda | ~1,5 s (y se guarda) |
| Complementarios | ~0,3 s modo rápido · 3–10 s con LLM |
| Chat sobre dataset | 2–4 s (hasta ~9 s si necesita agregar) |
| Re-ranking LLM completo | ~9 s |
| Fallback léxico | **< 1 ms** |

### Mejoras LLM (Sprint 6)

Casos de uso LLM implementados y evaluados:

| # | Caso | Estado | Sprint |
|---|------|--------|--------|
| #1 | Re-ranking inteligente | ✅ | 6 |
| #2 | Explicaciones de relevancia | ✅ | 6 |
| #3 | Interpretación estructurada de queries | ✅ | 6 |
| #4 | Expansión semántica con fallback léxico | ✅ | 6 |
| #5 | Datasets complementarios | ✅ | 8 |
| #10 | Chat sobre datasets | ✅ | 8 |
| #12 | Validación de queries | ✅ | 6 |
| #14 | TL;DR de datasets | ✅ | 8 |
| #13 | Sugerencias de queries relacionadas | ✅ | 8 |
| #8 | Normalización conceptual | ⏸️ Archivado (vía muerta) | 6 |

Detalle completo en [`08_Sprint6_LLM_Mejora/docs/INDICE_CASOS_USO_LLM.md`](08_Sprint6_LLM_Mejora/docs/INDICE_CASOS_USO_LLM.md).

---

## 🛠️ Stack técnico

- **Lenguaje:** Python 3.11+
- **Embeddings:** **BGE-M3** (1.024 d, multilingüe ES/EN) servido por Ollama; columna `embedding_bge`. El motor anterior (`paraphrase-multilingual-MiniLM-L12-v2`, 384 d) se conserva en `embedding` para comparar
- **Base de datos:** PostgreSQL 15 + `pgvector` 0.5.1 (índice HNSW sobre `embedding_bge`)
- **Backend:** FastAPI + Uvicorn
- **Frontend:** Streamlit
- **LLM:** configurable — por defecto `deepseek-v4.1-flash` (Ollama Cloud); fallback `deepseek-v4-pro` y `glm-5.3-flash`; compatible con cualquier endpoint OpenAI
- **Despliegue:** Docker Compose
- **Validación DCAT-AP-ES:** script propio en `03_Sprint1_Ingesta/codigo/validacion/`

---

## 🧪 Pruebas y evaluación

### Batería de tests

```bash
# Lanza primero la API en otro terminal
python3 06_Nivel4_Evaluacion/codigo/benchmark/test_bateria.py
python3 06_Nivel4_Evaluacion/codigo/benchmark/test_bateria_extendida.py
```

Las baterías evalúan la búsqueda híbrida contra ground truth anotado manualmente. Resultados en `06_Nivel4_Evaluacion/entregables/`.

### Evaluación RAGAS contra datos.gob.es

```bash
cd 09_Sprint7_RAGAS/codigo
# Requiere API en localhost:8000 y Playwright + Firefox instalados
python eval_ragas_core.py --mode basic --output ../entregables/ragas_scores_basic.json
python generar_ground_truth_datosgobes.py
python eval_datosgobes_core.py
python eval_nuestro_vs_dge_gt.py
python generar_reporte_comparativo_datosgobes.py
```

Informe resultante: `09_Sprint7_RAGAS/entregables/reporte_comparativo_datosgobes.md`. Las métricas oficiales se recalculan sobre `entregables/fase_h_METRICAS_v6.json` y `gt_etiquetas_v6.json` sin consultar la API.

### Probar el pre-procesador con LLM

```bash
curl -X POST http://localhost:8000/enhanced/query/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "paro juvenil Canarias 2023"}'
```

Devuelve: validación, interpretación estructurada, expansión (LLM o léxica) y metadatos.

### Probar búsqueda con re-ranking

```bash
curl -X POST http://localhost:8000/llm/enhance \
  -H "Content-Type: application/json" \
  -d '{"query": "vulnerabilidad económica juvenil", "top_k": 5}'
```

---

## 🐛 Solución de problemas

| Problema | Causa probable | Solución |
|----------|----------------|----------|
| `Connection refused` al API | API no levantada | `uvicorn main_v2_final_v07:app --app-dir 08_Sprint6_LLM_Mejora/codigo/api --port 8000` |
| Endpoints LLM (#1–#14) no existen / "router no disponible" en el log | API lanzada con el path de módulo completo (los routers no cargan) | Relanzar con `--app-dir 08_Sprint6_LLM_Mejora/codigo/api` (ver [`docs/ARRANQUE_SERVICIOS.md`](docs/ARRANQUE_SERVICIOS.md)) |
| Frontend: `❌ No se puede conectar a la API en http://localhost:8001` | `API_URL` apuntando al puerto equivocado | La API está en `8000`. El default de `common/utils.py` ya es `8000`; si se sobreescribe, arrancar con `API_URL=http://localhost:8000 streamlit run ...` |
| `uvicorn` consume ~100% CPU sin tráfico | `--reload` vigila todo el repo grande (docs, PDFs, `.git`) | Quitar `--reload` o limitar con `--reload-dir 08_Sprint6_LLM_Mejora/codigo/api` |
| `pgvector: false` en `/health` | Extensión no instalada | `CREATE EXTENSION IF NOT EXISTS vector;` en la BD |
| Re-ranking tarda >2 min | LLM remoto saturado | Bajar `top_k` o cambiar a modelo local (Ollama) |
| "paro" devuelve resultados de transporte | Falta el diccionario de palabras ambiguas | Verificar que `08_Sprint6_LLM_Mejora/codigo/motor/lexical_expander.py` está en uso |
| Datasets de Madrid aparecen como Navarra | Mapeo geonames antiguo en cache | Regenerar perfiles con `03_Sprint1_Ingesta/codigo/limpieza/clean_datasets.py` y actualizar BD |
| `/complementary/tldr` devuelve 404 | Dataset sin perfil precalculado | El endpoint genera TL;DR bajo demanda con LLM; verificar timeout |
| Chat o complementarios dan timeout | Timeout de Streamlit corto | Revisar `15_Frontends/frontend_b_intermedio/common/utils.py` (GET 30s / POST 60s) |
| `datasets_count: 0` | Migración no ejecutada o embeddings no regenerados | `python3 07_Sprint5_Integracion/codigo/db/migrate_from_numpy.py` (requiere `embeddings.npy` y `datasets_clean.jsonl` regenerados primero) |
| `FileNotFoundError: embeddings.npy` | Archivo no generado (no incluido en el repo) | `python3 03_Sprint1_Ingesta/codigo/limpieza/generate_embeddings.py` |
| `FileNotFoundError: datasets_clean.jsonl` | Datos limpios no generados (no incluidos en el repo) | `python3 03_Sprint1_Ingesta/codigo/limpieza/clean_datasets.py` |
| Frontend no muestra logo | `assets/` no se copió al desplegar | Verificar `15_Frontends/frontend_b_intermedio/assets/logo_buscador_semantico.png` |
| `POST /llm/explain` → `Error interno: name 'get_v07_url' is not defined` | Import perdido tras un refactor de la API (bug abierto) | No usar; para explicaciones, `/llm/enhance` |
| `POST /llm/search/fast` responde en ~0,1 s con resultados irrelevantes | Ese endpoint no pasa por el motor híbrido | No usar en demos ni en evaluación |

---

## 🔄 Regenerar embeddings localmente

Los embeddings son **grandes (~129 MB)** y **regenerables** desde los metadatos. Se excluyen del repo por peso y porque el catálogo de `datos.gob.es` se actualiza con frecuencia.

### Pipeline completo de regeneración

```bash
# 1. Ingesta desde la API Linked Data de datos.gob.es (~22 min)
python3 03_Sprint1_Ingesta/codigo/conectores/ingest_datos_gob_v2.py
# → genera 03_Sprint1_Ingesta/codigo/datos/raw/batch_*.jsonl (134.150 datasets)

# 2. Limpieza y normalización (DCAT-AP, deduplicación, extracción de embedding_text)
python3 03_Sprint1_Ingesta/codigo/limpieza/clean_datasets.py
# → genera 03_Sprint1_Ingesta/codigo/datos/processed/datasets_clean.jsonl (94.461 datasets)

# 3. Generación de embeddings con sentence-transformers (~20 min en CPU)
python3 03_Sprint1_Ingesta/codigo/limpieza/generate_embeddings.py
# → genera 04_Sprint2_Embeddings/datos/processed/embeddings.npy (94.461 × 1.024 con BGE-M3)

# 4. Construcción de índices BM25 y facetados (~7 segundos)
python3 04_Sprint2_Embeddings/codigo/indexacion/build_indices.py
# → genera 04_Sprint2_Embeddings/datos/indices/{id_position_map,index_tema,...}.json
# → genera 04_Sprint2_Embeddings/datos/indices/bm25_index.pkl

# 5. Migración a PostgreSQL con pgvector
# (las tablas e índices ya deben existir del paso 2; si no, ejecutar init.sql primero)
python3 07_Sprint5_Integracion/codigo/db/migrate_from_numpy.py
```

### Requisitos de hardware para la regeneración

| Paso | CPU | RAM | Disco | Tiempo |
|------|-----|-----|-------|--------|
| Ingesta (134k datasets) | bajo | bajo | 528 MB | ~22 min |
| Limpieza | bajo | bajo | 509 MB | ~2 min |
| **Embeddings** (sentence-transformers) | multi-core recomendado | 4 GB | 129 MB | ~20 min en CPU, ~3 min en GPU |
| Índices | bajo | 2 GB | ~50 MB | ~10 s |
| PostgreSQL | bajo | 1 GB | 724 MB | ~1 min |

### Re-generar solo los embeddings (saltando la ingesta)

Si ya tienes `datasets_clean.jsonl` y solo quieres actualizar el modelo de embeddings:

```bash
python3 03_Sprint1_Ingesta/codigo/limpieza/generate_embeddings.py \
    --input 03_Sprint1_Ingesta/codigo/datos/processed/datasets_clean.jsonl \
    --output 04_Sprint2_Embeddings/datos/processed/embeddings.npy
```

### Cambiar el modelo de embeddings

El modelo por defecto es **BGE-M3** (1.024 d). El pipeline antiguo con `sentence-transformers` sigue disponible para generar la columna `embedding` (384 d) y poder comparar. Para cambiar de modelo:

1. Editar `03_Sprint1_Ingesta/codigo/limpieza/generate_embeddings.py` línea 25:
   ```python
   MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"  # 768 d
   ```
2. Cambiar el `EMBEDDING_DIM` correspondiente.
3. Actualizar el esquema de la tabla `datasets` (`embedding VECTOR(384)` → `VECTOR(768)`).
4. Re-generar todo el pipeline desde el paso 3.

---

## 📚 Documentación adicional

| Documento | Contenido |
|-----------|-----------|
| [`docs/FORMULACION_PROYECTO.md`](docs/FORMULACION_PROYECTO.md) | Plan de fases, gates y matriz de responsabilidades |
| [`docs/IDENTIFICACION_CANVAS_EOI.md`](docs/IDENTIFICACION_CANVAS_EOI.md) | Data Model Canvas del proyecto (11 bloques) |
| [`02_Idear_Prototipar/docs/ideas_descartadas/ideas_rechazadas.md`](02_Idear_Prototipar/docs/ideas_descartadas/ideas_rechazadas.md) | Decisiones de diseño descartadas y por qué |
| [`08_Sprint6_LLM_Mejora/docs/ARQUITECTURA_FALLBACK_LEXICO.md`](08_Sprint6_LLM_Mejora/docs/ARQUITECTURA_FALLBACK_LEXICO.md) | Diseño del fallback léxico que garantiza 100 % de expansión |
| [`08_Sprint6_LLM_Mejora/docs/ESCALADO_MODELOS.md`](08_Sprint6_LLM_Mejora/docs/ESCALADO_MODELOS.md) | Comparativa de modelos LLM (deepseek-flash vs qwen2.5:7b) |
| [`08_Sprint6_LLM_Mejora/docs/SISTEMA_VALIDACION.md`](08_Sprint6_LLM_Mejora/docs/SISTEMA_VALIDACION.md) | Validación de queries y metadatos |
| [`09_Sprint7_RAGAS/entregables/reporte_evaluacion_final.md`](09_Sprint7_RAGAS/entregables/reporte_evaluacion_final.md) | Metodología y resultados RAGAS |
| [`09_Sprint7_RAGAS/entregables/reporte_comparativo_datosgobes.md`](09_Sprint7_RAGAS/entregables/reporte_comparativo_datosgobes.md) | Benchmark comparativo contra datos.gob.es |
| [`docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`](docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md) | Fundamentación bibliográfica de casos de uso y arquitectura (36 papers arXiv) |
| [`03_Sprint1_Ingesta/codigo/docs/ficha_tecnica_datos_gob_es.md`](03_Sprint1_Ingesta/codigo/docs/ficha_tecnica_datos_gob_es.md) | Ficha técnica de la fuente de datos |
| [`07_Sprint5_Integracion/codigo/docs/DESPLIEGUE.md`](07_Sprint5_Integracion/codigo/docs/DESPLIEGUE.md) | Manual de despliegue detallado |
| [`15_Frontends/frontend_b_intermedio/legacy/README.md`](15_Frontends/frontend_b_intermedio/legacy/README.md) | Archivo de interfaces antiguas y lecciones aprendidas |
| [`docs/DEFENSA_PREGUNTAS_RESPUESTAS.md`](docs/DEFENSA_PREGUNTAS_RESPUESTAS.md) | 60 preguntas y respuestas para la defensa (con anexos de cifras) |
| [`docs/diagrama_datatrust.mmd`](docs/diagrama_datatrust.mmd) | Diagrama de arquitectura (pipeline offline + servicio en producción) |
| [`08_Sprint6_LLM_Mejora/docs/DEMO-5MIN-BASURA-EN-CASA-2026-10-30.pdf`](08_Sprint6_LLM_Mejora/docs/DEMO-5MIN-BASURA-EN-CASA-2026-10-30.pdf) | Guion de la demo de 5 minutos |
| [`docs/AUDITORIA-IMPECCABLE-DATATRUST-2026-11-04.pdf`](docs/AUDITORIA-IMPECCABLE-DATATRUST-2026-11-04.pdf) | Auditoría de interfaz (accesibilidad y contraste) y su corrección |

---

## ⚠️ Limitaciones conocidas

| Limitación | Detalle |
|---|---|
| Chat sin fichero | Un dataset sin fichero descargado (unos 37.200 de 94.461) responde «No se encontró información del dataset» en lugar de inventar |
| Chat con ventana de muestra | El chat recibe el esquema y los **primeros 4.000 caracteres** del fichero (`SAMPLE_ROWS_CHARS`). Preguntas por una anualidad o un total fuera de esa ventana devuelven «no puedo determinarlo»: es intencionado, no un fallo |
| Perfiles LLM parciales | 5.073 de 94.461 datasets tienen TL;DR y perfil precalculados (5,4 %); el resto se genera bajo demanda pagando latencia |
| Endpoints en cuarentena | `POST /llm/explain` (bug `get_v07_url`) y `POST /llm/search/fast` (no usa el motor híbrido) |
| Resto del compose | `MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2` sigue declarado en el compose por compatibilidad; el motor real es BGE-M3 (`EXPERIMENTO_COLUMNA=embedding_bge`) |
| Índice heredado | El HNSW de MiniLM (182 MB) sigue construido junto al de BGE-M3 (738 MB); se puede eliminar cuando no se compare |
| Vocabulario del léxico | El motor léxico exige **todas** las palabras y no lematiza: con una frase natural devuelve 0 resultados. Es la razón de combinar ambos motores, no un defecto que se pueda arreglar subiendo el peso |

---

## 👥 Contexto académico

TFM del **Máster EOI** (Data Science & Big Data) · Curso 2025–2026 · Defensa en nov. 2026.

Equipo (6 personas): Producto, Datos, NLP/ML, Backend, Frontend/UX, Storytelling.

Metodología: Design Thinking + Lean Startup + Scrum + Data Model Canvas.

Última actualización del README: **2026-11-05** (puesta al día contra la base de datos y la API en producción: 94.461 datasets, BGE-M3 1.024 d, KPI de ground truth v6, estado del despliegue y limitaciones conocidas).

---

## 📄 Licencia

Material académico EOI. Los datos pertenecen a sus respectivos publicadores en [datos.gob.es](https://datos.gob.es).

---

## Qué incluye esta publicación

Este repositorio es la **copia publicada** del proyecto: recoge el estado final del código y de la
documentación en un único commit, sin el historial de desarrollo (el calendario real está en
[`docs/CRONOLOGIA.md`](docs/CRONOLOGIA.md)).

Para que el clon sea manejable se han dejado fuera artefactos que se regeneran o que no aportan al
código:

| No incluido | Por qué |
|---|---|
| `**/datos/` (datasets descargados, índices invertidos, muestras procesadas) | Se regeneran con el pipeline de `03_Sprint1_Ingesta` y `04_Sprint2_Embeddings` |
| Volcados `.csv` de auditoría de metadatos (~32 MB) | Las conclusiones están en la documentación del sprint |
| `pool_*`, `_checkpoint*` y versiones antiguas (`v2`–`v5`) del ground truth | Sólo se conserva la versión final (`gt_etiquetas_v6.json`) y los resultados agregados |
| PDFs no citados en la documentación | Se referencian con enlace en [`docs/BIBLIOGRAFIA.md`](docs/BIBLIOGRAFIA.md) |

Antes de desplegar, revisar el checklist de
[`07_Sprint5_Integracion/codigo/README_DESPLIEGUE.md`](07_Sprint5_Integracion/codigo/README_DESPLIEGUE.md)
(contraseña de PostgreSQL, proxy con TLS, cabeceras y clave del LLM).
