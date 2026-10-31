# Arranque de los servicios del Buscador Semántico

**Fecha:** 2026-06-22
**Propósito:** Guía única y reproducible para levantar el sistema completo (PostgreSQL+pgvector, Ollama, API FastAPI, frontend Streamlit) tanto en el **arranque diario** (datos ya poblados) como **desde cero** (BD vacía).

> Documento de referencia para el README principal. Corrige y sustituye a las instrucciones dispersas que había en versiones anteriores, donde el comando del API dejaba los routers LLM sin cargar y el frontend apuntaba al puerto equivocado.

---

## 0. Requisitos previos

| Componente | Versión / Notas |
|---|---|
| Python | 3.11+ (probado con 3.13.5) — usar el `venv/` del proyecto |
| Docker + Docker Compose | Para PostgreSQL+pgvector (y opcionalmente el stack completo) |
| PostgreSQL 15 + pgvector | Contenedor `buscador_postgres` (imagen `ankane/pgvector:latest`) |
| Ollama | Servidor LLM en `http://localhost:11434` |
| Modelos Ollama | `deepseek-v4-flash:cloud` y `deepseek-v4-pro:cloud` (re-ranking / chat / perfiles) |
| Modelo de embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (384D, se descarga de HuggingFace al arrancar la API) |

Puertos del sistema:

| Servicio | Puerto |
|---|---|
| PostgreSQL + pgvector | 5432 |
| Ollama | 11434 |
| API FastAPI | **8000** |
| Frontend Streamlit | 8501 |

> El frontend lee `API_URL` de una variable de entorno; el **default es `http://localhost:8000`** (corregido el 2026-06-22; antes era `8001` y causaba el error `❌ No se puede conectar a la API en http://localhost:8001`).

---

## 1. Arranque diario (datos ya poblados)

Usar esta sección cuando la BD ya contiene los 87.676 datasets, los embeddings y los perfiles. Es el caso habitual de puesta en marcha.

### 1.1 PostgreSQL + pgvector

El contenedor debe estar levantado y *healthy*:

```bash
docker ps --filter "name=buscador_postgres" --format "{{.Names}}\t{{.Status}}"
# buscador_postgres   Up X hours (healthy)
```

Si está parado, levantarlo (una sola vez, el volumen persiste los datos):

```bash
cd 07_Sprint5_Integracion/codigo/docker
docker compose up -d postgres
```

> El `docker-compose.yml` monta automáticamente `07_Sprint5_Integracion/codigo/db/init.sql` como `01_init.sql` del entrypoint. **Solo se ejecuta la primera vez** que se crea el volumen (BD vacía). Si el volumen ya existe, init.sql **no se re-ejecuta** — es el comportamiento esperado de Docker. No hay un segundo init.sql.

### 1.2 Ollama

Debe escuchar en el 11434 y tener los modelos `:cloud` disponibles:

```bash
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json;print([m['name'] for m in json.load(sys.stdin)['models']])"
# ['deepseek-v4-flash:cloud', 'deepseek-v4-pro:cloud', ...]
```

Si no hay modelos `:cloud`, el re-ranking / chat / complementarios fallarán con timeout, pero la búsqueda híbrida básica (`/search`) seguirá funcionando.

### 1.3 API FastAPI (puerto 8000)

> ⚠️ **Importante — usar `--app-dir`, no el path de módulo completo.**
>
> El `main_v2_final_v07.py` carga los routers LLM con imports planos:
> ```python
> from routes_v10 import router_v10
> from routes_query_enhanced import router_query_enhanced
> from routes_complementary import router_complementary
> from routes_dataset_chat import router_dataset_chat
> ```
> Estos archivos viven en `08_Sprint6_LLM_Mejora/codigo/api/`. El `main` añade a `sys.path` los directorios `codigo/` y `codigo/db/` (vía `Path(__file__).parent.parent`), pero **no** `codigo/api/`. Cuando se lanza como `uvicorn 08_Sprint6_LLM_Mejora.codigo.api.main_v2_final_v07:app`, el directorio del módulo no entra en `sys.path` y los imports planos fallan con `No module named 'routes_v10'`: la API arranca **sin** los endpoints de los casos de uso #1–#14.
>
> Con `--app-dir 08_Sprint6_LLM_Mejora/codigo/api`, ese directorio sí entra en `sys.path` y los 4 routers se montan correctamente.

> ⚠️ **Evita `--reload` en sesiones largas.** El repositorio contiene miles de archivos (docs, PDFs, datos temporales, `.git`). Uvicorn con `--reload` vigila todos los `.py` alcanzables y puede consumir **~100% de una CPU de forma constante** sin atender peticiones. Si quieres hot-reload, limita el directorio con `--reload-dir`.

**Comando recomendado para uso normal** (sin reload):

```bash
cd Datatrust
source venv/bin/activate
uvicorn main_v2_final_v07:app \
  --app-dir 08_Sprint6_LLM_Mejora/codigo/api \
  --host 0.0.0.0 --port 8000
```

**Comando con hot-reload limitado** (solo desarrollo activo en la API):

```bash
uvicorn main_v2_final_v07:app \
  --app-dir 08_Sprint6_LLM_Mejora/codigo/api \
  --host 0.0.0.0 --port 8000 \
  --reload --reload-dir 08_Sprint6_LLM_Mejora/codigo/api
```

**Verificar** que los routers LLM cargaron (4 líneas "cargado correctamente" en el log) y que la BD conecta:

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Salida esperada:
```json
{
  "status": "ok",
  "postgresql": "connected",
  "pgvector": true,
  "datasets_count": 87676,
  "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
  ...
}
```

Log esperado al arrancar:
```
V10: Router LLM Optimizado cargado correctamente (fast search + explain on-demand)
Query Enhanced: Router cargado correctamente (#3, #4, #12)
Sprint 8: Complementarios router cargado correctamente (#5)
Sprint 8: Dataset Chat router cargado correctamente (#10)
INFO:     Application startup complete.
```

> **Nota sobre `POSTGRES_HOST`:** el API usa por defecto `POSTGRES_HOST=172.17.0.1` (pensado para correr **dentro** de un contenedor). Lanzándolo en el host, ese default funciona porque el puente Docker de `buscador_postgres` es reachable en `172.17.0.1:5432`. Para hacerlo explícito y robusto, arrancar con `POSTGRES_HOST=localhost`:
> ```bash
> POSTGRES_HOST=localhost uvicorn main_v2_final_v07:app --app-dir 08_Sprint6_LLM_Mejora/codigo/api --host 0.0.0.0 --port 8000 --reload
> ```

### 1.4 Frontend Streamlit (puerto 8501)

```bash
cd Datatrust
source venv/bin/activate
cd 15_Frontends/frontend_b_intermedio
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

La URL de la API se toma de `API_URL` (default `http://localhost:8000`). Si la API estuviera en otro puerto:

```bash
API_URL=http://localhost:8000 streamlit run app.py --server.port 8501 --server.headless true
```

**Puntos de acceso:**
- Modo público (ligero): `http://localhost:8501`
- Modo avanzado / demostrador técnico: `http://localhost:8501/?mode=advanced`

### 1.5 Verificación rápida de cadena completa

```bash
# 1) Búsqueda híbrida (POST /search)
curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"paro juvenil","limit":3}' | python3 -m json.tool

# 2) Endpoints LLM presentes
curl -s http://localhost:8000/openapi.json | python3 -c \
  "import sys,json;print(sorted(json.load(sys.stdin)['paths']))"
# Debe incluir: /llm/search/fast, /enhanced/query/analyze, /complementary/find, /dataset/chat, ...

# 3) Frontend responde
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8501/   # 200
```

---

## 2. Arranque desde cero (BD vacía)

Solo la primera vez, o si se quiere reconstruir el corpus. La ingesta completa descarga ~134.150 datasets de datos.gob.es; tras limpieza/deduplicación quedan **87.676** datasets únicos.

### 2.1 Crear el venv e instalar dependencias

```bash
cd Datatrust
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # fastapi uvicorn streamlit psycopg2-binary sentence-transformers requests ...
```

### 2.2 Levantar PostgreSQL + pgvector y aplicar el esquema

```bash
cd 07_Sprint5_Integracion/codigo/docker
docker compose up -d postgres
```

El `init.sql` (`07_Sprint5_Integracion/codigo/db/init.sql`) se aplica automáticamente al crear el volumen: crea la extensión `vector`, la tabla `datasets` (con `embedding vector(384)`, `search_vector tsvector`, índices HNSW y GIN), `dataset_profiles`, `term_synonyms` y `query_logs`.

Verificar el esquema y la extensión:

```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d buscador -c "\dt"
PGPASSWORD=postgres psql -h localhost -U postgres -d buscador -c "SELECT extname FROM pg_extension WHERE extname='vector';"
```

> Si por algún motivo init.sql no se aplicó (volumen preexistente), ejecutarlo a mano:
> ```bash
> PGPASSWORD=postgres psql -h localhost -U postgres -d buscador -f 07_Sprint5_Integracion/codigo/db/init.sql
> ```

### 2.3 Ingesta, limpieza y deduplicación

```bash
cd 03_Sprint1_Ingesta/codigo
# Descarga masiva de metadatos desde datos.gob.es
python ingestar.py            # (o el script de ingesta vigente en este directorio)
# Limpieza, normalización y deduplicación (123k → 87.676 únicos)
python limpieza/clean_datasets.py
```

### 2.4 Generar embeddings e índices

```bash
# Embeddings 384D con paraphrase-multilingual-MiniLM-L12-v2
python 03_Sprint1_Ingesta/codigo/limpieza/generate_embeddings.py

# Índices facetados (tema, territorio, formato, publisher) y BM25
python 04_Sprint2_Embeddings/codigo/indexacion/build_indices.py
```

### 2.5 Perfiles LLM (TL;DR, variables, complementariedad) — opcional

Los perfiles (`dataset_profiles`) alimentan los casos #5 (complementarios), #10 (chat) y #14 (TL;DR). Se generan en batch offline:

```bash
cd 08_Sprint6_LLM_Mejora/codigo
python batch_generate_profiles.py
```

Requiere Ollama con `deepseek-v4-flash:cloud` corriendo. Actualmente hay 4.391 perfiles generados (muestra); el batch completo para los 87.676 es trabajo futuro.

### 2.6 Continuar con el arranque diario

Una vez poblada la BD, volver a la **sección 1** (1.2 Ollama → 1.3 API → 1.4 Frontend).

---

## 3. Despliegue con Docker (stack completo)

Alternativa para levantar los tres servicios (postgres + api + frontend) en contenedores:

```bash
cd 07_Sprint5_Integracion/codigo/docker
docker compose up -d
```

Esto levanta `buscador_postgres` (5432), `buscador_api` (8000) y `buscador_frontend` (8501). Dentro de la red Docker, el frontend usa `API_URL=http://api:8000` y la API `POSTGRES_HOST=postgres` (ya configurados en el `docker-compose.yml`).

> El `Dockerfile.frontend` del compose referencia `../frontend_v2`; el frontend unificado actual vive en `15_Frontends/frontend_b_intermedio`. Para el arranque de demostración/desarrollo se recomienda el procedimiento manual de la **sección 1**.

---

## 4. Solución de problemas

| Síntoma | Causa | Solución |
|---|---|---|
| `No module named 'routes_v10'` / "router no disponible" en el log de la API | API lanzada con path de módulo completo (`uvicorn 08_Sprint6...:app`) | Relanzar con `--app-dir 08_Sprint6_LLM_Mejora/codigo/api` (sección 1.3) |
| Endpoints LLM (`/llm/...`, `/enhanced/...`, `/complementary/...`, `/dataset/...`) no existen | Los routers no se cargaron (mismo motivo que arriba) | Igual que arriba; verificar las 4 líneas "cargado correctamente" |
| Frontend: `❌ No se puede conectar a la API en http://localhost:8001` | `API_URL` apuntando al puerto equivocado | La API está en `8000`. El default de `common/utils.py` ya es `8000` (corregido 2026-06-22). Si se sobreescribe, arrancar con `API_URL=http://localhost:8000 streamlit run ...` |
| `/health` devuelve `postgresql: disconnected` o `pgvector: false` | Postgres caído o sin extensión `vector` | `docker compose up -d postgres`; luego `CREATE EXTENSION IF NOT EXISTS vector;` |
| `Connection refused` al API | API no levantada | `uvicorn main_v2_final_v07:app --app-dir 08_Sprint6_LLM_Mejora/codigo/api --port 8000` |
| Re-ranking / chat / complementarios dan timeout | Ollama sin modelos `:cloud` o saturado | `curl http://localhost:11434/api/tags`; comprobar `deepseek-v4-flash:cloud` |
| `/search` devuelve `405 Method Not Allowed` | Se llamó con GET | `/search` es **POST** con body `{"query":"...","limit":N}` |
| La primera petición tarda varios segundos | Carga perezosa del modelo de embeddings | Normal; se cachea tras el primer arranque |

---

## 5. Notas técnicas

### 5.1 Por qué `--app-dir` y no el path de módulo completo

`main_v2_final_v07.py` añade a `sys.path`:
```python
sys.path.insert(0, str(Path(__file__).parent.parent))          # .../codigo/
sys.path.insert(0, str(Path(__file__).parent.parent / "db"))   # .../codigo/db/
```
Esto permite `from motor.concept_normalizer import ...` (motor está en `codigo/motor/`) pero **no** resuelve `import routes_v10` (routes está en `codigo/api/`, el mismo dir del `main`). Cuando uvicorn importa el módulo como `paquete.ruta:app`, `codigo/api/` no entra en `sys.path`. Con `--app-dir codigo/api`, uvicorn lo añade y los imports planos resuelven.

Solución alternativa (no aplicada, para no tocar código): añadir `sys.path.insert(0, str(Path(__file__).parent))` al `main`. Se prefirió `--app-dir` por ser no invasiva.

### 5.2 Configuración de BD del API

```python
DB_HOST     = os.getenv('POSTGRES_HOST', '172.17.0.1')  # default: host visto desde un contenedor
DB_PORT     = int(os.getenv('POSTGRES_PORT', '5432'))
DB_NAME     = os.getenv('POSTGRES_DB', 'buscador')
DB_USER     = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'postgres')
```

Arrancando en el host, usar `POSTGRES_HOST=localhost` para ser explícito (aunque `172.17.0.1` también funciona porque `buscador_postgres` publica el puerto en `0.0.0.0:5432`).

### 5.3 Cambios aplicados el 2026-06-22

1. `15_Frontends/frontend_b_intermedio/common/utils.py`: default `API_URL` cambiado de `http://localhost:8001` → `http://localhost:8000`.
2. `README.md`: comando del API corregido a `--app-dir`; sección de troubleshooting ampliada.
3. Este documento: guía de arranque consolidada.