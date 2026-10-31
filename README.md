# Datatrust — Buscador Semántico de Datasets Públicos

> TFM — Máster EOI · Buscador semántico de datasets del portal [datos.gob.es](https://datos.gob.es)
> con re-ranking e interpretación de consultas mediante LLM, búsqueda híbrida (semántica + léxica) y PostgreSQL + pgvector.

![Estado](https://img.shields.io/badge/estado-operativo-success) ![Python](https://img.shields.io/badge/python-3.11+-blue) ![PostgreSQL](https://img.shields.io/badge/postgresql-15%2B-blue) ![pgvector](https://img.shields.io/badge/pgvector-0.5%2B-blue) ![Licencia](https://img.shields.io/badge/licencia-EOI-informational)

---

## 📋 Resumen

Aplicación que convierte **preguntas en lenguaje natural** sobre datos públicos en una **lista priorizada y explicada de datasets** de `datos.gob.es`. Combina búsqueda semántica (embeddings multilingües), búsqueda léxica (full-text) y un LLM local/cloud para re-ranking, expansión de queries y validación de metadatos.

**Problema que resuelve:** la búsqueda por palabras clave en portales de datos abiertos es ineficiente para preguntas de análisis ("paro juvenil en Canarias 2023" → debe devolver datasets relevantes aunque el término exacto no esté en el título).

### Capacidades principales

| Capacidad | Descripción |
|---|---|
| **Búsqueda híbrida** | Combina similitud semántica (embeddings 384d) con ranking léxico (TSVECTOR) en PostgreSQL + pgvector |
| **Re-ranking con LLM** | Un LLM reordena el top-N de resultados según relevancia analítica y genera explicación por dataset |
| **Interpretación de queries** | Extrae tema, territorio y año de la query; expande con sinónimos (paro → desempleo, atur, parados...) |
| **Validación de metadatos** | Detecta inconsistencias (p. ej. `publisher="Universidad de Barcelona"` mientras el `title` menciona "UEx") |
| **Filtros facetados** | Por tema, territorio, formato, publicador |
| **TL;DR de datasets** | Resumen generado por LLM del propósito y contenido de cada dataset |
| **Datasets complementarios** | Recomienda datasets relacionados por tema/geografía (modo rápido precalculado + opción LLM) |
| **Chat sobre datasets** | Responde preguntas sobre metadatos y relaciones de un dataset concreto |
| **Fallback léxico** | Diccionario de ~100 términos garantiza expansión instantánea (<1 ms) cuando el LLM falla |

---

## 🚀 Quick Start

### Requisitos

- Python 3.11+
- PostgreSQL 15+ con la extensión `pgvector` 0.5+
- 4 GB RAM mínimo · 10 GB disco (incluye los embeddings)
- (Opcional) Clave o servidor para un LLM — por defecto usa modelos Ollama (`deepseek-v4-flash:cloud`, `deepseek-v4-pro:cloud`) o equivalentes OpenAI-compatible

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

# 4.2 Limpiar y normalizar → 87.676 datasets limpios
python3 03_Sprint1_Ingesta/codigo/limpieza/clean_datasets.py

# 4.3 Generar embeddings con sentence-transformers (~129 MB, ~20 min)
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
> - **Tamaño:** 134.150 datasets + 87.676 embeddings = ~1.2 GB · GitHub recomienda repos <1 GB
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
# {"status":"ok","postgresql":"connected","pgvector":true,"datasets_count":87676,...}
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

### Despliegue con Docker

```bash
cd 07_Sprint5_Integracion/codigo/docker
docker compose up -d
```

Levanta los tres servicios: PostgreSQL+pgvector (5432), API FastAPI (8000) y frontend Streamlit (8501).

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
│  ├── /search                    Búsqueda híbrida pura      │
│  ├── /llm/search/fast           Búsqueda rápida sin re-ranking │
│  ├── /llm/enhance              Búsqueda con re-ranking LLM  │
│  ├── /enhanced/search           Pipeline completo (pre-procesamiento + búsqueda) │
│  ├── /enhanced/query/analyze    Interpretación de query     │
│  ├── /complementary/tldr        TL;DR del dataset (query param: ?dataset_id=) │
│  ├── /complementary/find        Datasets complementarios    │
│  └── /dataset/chat              Chat sobre un dataset (POST, dataset_id en body) │
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
│  PostgreSQL 15 + pgvector (87 676 datasets · 384 dims)       │
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
| 03 | `03_Sprint1_Ingesta/` | Ingesta de 134.150 datasets desde datos.gob.es, limpieza a 87.676 | ✅ |
| 04 | `04_Sprint2_Embeddings/` | Embeddings 87.676×384, índices BM25 + facetados | ✅ |
| 05 | `05_Sprint3_Busqueda_UI/` | Motor de búsqueda híbrido + API REST + frontend Streamlit | ✅ |
| 06 | `06_Nivel4_Evaluacion/` | Batería de tests · 10/12 PASS (83%) en baseline | ✅ |
| 07 | `07_Sprint5_Integracion/` | Docker, PostgreSQL + pgvector, despliegue | ✅ |
| 08 | `08_Sprint6_LLM_Mejora/` | Re-ranking con LLM, expansión, validación, fallback léxico | ✅ |
| 09 | `09_Sprint7_RAGAS/` | Evaluación RAGAS: P@5=0.70, NDCG@10=0.79 | ✅ |
| 10 | `15_Frontends/` | Frontend unificado: modo público + modo avanzado | ✅ |
| — | `99_Compartido/` | Recursos compartidos: requirements.txt, config | ✅ |

La mayoría de sprints contienen `codigo/`, `docs/`, `entregables/` y un `README_<sprint>.md` con su estado y conclusiones.

---

## 📊 Métricas y resultados

### Calidad del buscador

| Métrica | Valor |
|---------|-------|
| Datasets indexados | **87 676** |
| Dimensiones embedding | 384 (paraphrase-multilingual-MiniLM-L12-v2) |
| Precisión baseline @5 | 83 % (10/12) — *batería corta* |
| Precisión extendida @5 | ~75 % — *batería ampliada, ver `06_Nivel4_Evaluacion`* |
| **P@5 evaluación RAGAS (Sprint 7)** | **0.702** sobre 47 queries, ground truth realista |
| **NDCG@10 evaluación RAGAS (Sprint 7)** | **0.792** |
| **P@5 datos.gob.es (mismo test, web real)** | **0.622** |
| Latencia búsqueda híbrida | ~30–50 ms (PostgreSQL) |
| Latencia TL;DR / chat | ~0.5–2 s con perfil precalculado; bajo demanda con LLM |
| Latencia complementarios | ~0.3 s modo rápido; ~3–10 s con LLM |
| Latencia fallback léxico | **< 1 ms** |
| Tasa de éxito expansión (con fallback) | **100 %** |

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
- **Embeddings:** `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers, 384 d, multilingüe ES/EN)
- **Base de datos:** PostgreSQL 15 + `pgvector` 0.5.1
- **Backend:** FastAPI + Uvicorn
- **Frontend:** Streamlit
- **LLM:** configurable — por defecto `deepseek-v4-flash:cloud`; compatible con Ollama, OpenAI-compatible
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

Informe resultante: `09_Sprint7_RAGAS/entregables/reporte_comparativo_datosgobes.md`.

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
| Frontend no muestra logo | `assets/` no se copió al desplegar | Verificar `15_Frontends/frontend_b_intermedio/legacy/assets/logo_buscador_semantico.png` |

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
# → genera 03_Sprint1_Ingesta/codigo/datos/processed/datasets_clean.jsonl (87.676 datasets)

# 3. Generación de embeddings con sentence-transformers (~20 min en CPU)
python3 03_Sprint1_Ingesta/codigo/limpieza/generate_embeddings.py
# → genera 04_Sprint2_Embeddings/datos/processed/embeddings.npy (87.676 × 384)

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

El modelo por defecto es `paraphrase-multilingual-MiniLM-L12-v2` (384 d, multilingüe ES/EN). Para usar otro:

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

---

## 👥 Contexto académico

TFM del **Máster EOI** (Data Science & Big Data) · Curso 2025–2026 · Defensa prevista sept. 2026.

Equipo (6 personas): Producto, Datos, NLP/ML, Backend, Frontend/UX, Storytelling.

Metodología: Design Thinking + Lean Startup + Scrum + Data Model Canvas.

Última actualización del README: 2026-08-11 (auditoría de coherencia + corrección de 19 discrepancias).

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
