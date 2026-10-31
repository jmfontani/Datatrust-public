# Manual de Despliegue - Buscador Semántico V2.2

## 1. REQUISITOS PREVIOS

### Hardware/Sistema
- Linux/macOS/Windows con Docker Desktop
- 4GB RAM mínimo (8GB recomendado)
- 10GB espacio en disco (para embeddings)
- Conexión a Internet (para descargar modelos)

### Software
- Docker 24.0+ y Docker Compose v2+
- Python 3.9+ (solo si se ejecuta sin Docker)
- Git (opcional, para clonar)

---

## 2. ESTRUCTURA DEL PROYECTO

```
codigo/
├── api/
│   ├── main_v2_final.py          # ← API principal (USAR ESTE)
│   ├── launch_backend_v2.sh      # ← Script de lanzamiento
│   └── requirements.txt            # Dependencias Python
├── docker/
│   ├── docker-compose.yml          # ← Servicios Docker
│   ├── Dockerfile                  # Imagen API
│   ├── .env                        # ← Variables de entorno
│   └── init-scripts/
│       └── 01-init-db.sql          # Inicialización BD
├── db/
│   └── init.sql                    # Esquema PostgreSQL
├── frontend_v2/
│   └── streamlit_app.py            # Interfaz web
└── docs/
    └── MEJORAS_CALIDAD.md          # Este documento
```

---

## 3. INSTALACIÓN Y CONFIGURACIÓN

### Paso 1: Descargar/Preparar el Código

Si vienes de un repositorio Git:
```bash
git clone <url-repositorio>
cd Datatrust/07_Sprint5_Integracion/codigo
```

Si es un ZIP:
```bash
unzip buscador-semantico.zip
cd buscador-semantico/07_Sprint5_Integracion/codigo
```

### Paso 2: Configurar Variables de Entorno

Editar `docker/.env`:
```bash
nano docker/.env
```

Contenido recomendado:
```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=buscador
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
API_PORT=8000
STREAMLIT_PORT=8501
```

> **IMPORTANTE**: Cambiar `POSTGRES_PASSWORD` en producción.

### Paso 3: Configurar Red Docker

Verificar que Docker Compose crea la red automáticamente:
```bash
cd docker
docker compose config | grep -A 5 "networks"
```

Debería mostrar algo como:
```yaml
networks:
  buscador_network:
    driver: bridge
```

Si no existe, crear manualmente:
```bash
docker network create buscador_network
```

---

## 4. DESPLIEGUE

### Opción A: Docker Compose (Recomendado)

#### Paso 1: Iniciar Servicios

```bash
cd docker
docker compose up -d
```

Esto inicia:
- `buscador_postgres`: PostgreSQL 15 con pgvector
- `buscador_api`: API FastAPI (puerto 8000)
- `buscador_frontend`: Streamlit (puerto 8501)

#### Paso 2: Verificar Estado

```bash
docker compose ps
```

Estado esperado:
```
NAME              STATUS          PORTS
buscador_api      Up 10 seconds   0.0.0.0:8000->8000/tcp
buscador_postgres Up 10 seconds   5432/tcp
buscador_frontend Up 10 seconds   0.0.0.0:8501->8501/tcp
```

#### Paso 3: Verificar Logs

```bash
# PostgreSQL
docker logs -f buscador_postgres

# API
docker logs -f buscador_api

# Frontend
docker logs -f buscador_frontend
```

Debes ver:
- PostgreSQL: "database system is ready to accept connections"
- API: "Uvicorn running on http://0.0.0.0:8000"
- Frontend: "Network URL: http://0.0.0.0:8501"

---

### Opción B: Instalación Manual (Sin Docker)

#### Requisitos
- Python 3.9+
- PostgreSQL 15+ con extensión pgvector
- Modelo de embeddings descargado

#### Paso 1: Instalar PostgreSQL + pgvector

**Ubuntu/Debian:**
```bash
# PostgreSQL 15
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install postgresql-15 postgresql-contrib-15

# pgvector
sudo apt-get install postgresql-15-pgvector
```

**macOS:**
```bash
brew install postgresql@15
brew install pgvector
```

**Windows:**
Descargar instalador de https://www.postgresql.org/download/windows/
Instalar pgvector desde Stack Builder o manualmente.

#### Paso 2: Configurar Base de Datos

```bash
# Iniciar PostgreSQL
sudo systemctl start postgresql

# Crear usuario y base de datos
sudo -u postgres psql -c "CREATE DATABASE buscador;"
sudo -u postgres psql -c "CREATE USER app_user WITH PASSWORD 'app_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE buscador TO app_user;"

# Habilitar pgvector
sudo -u postgres psql -d buscador -c "CREATE EXTENSION IF NOT EXISTS vector;"
sudo -u postgres psql -d buscador -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

#### Paso 3: Crear Tablas

```bash
cd db
sudo -u postgres psql -d buscador -f init.sql
```

#### Paso 4: Instalar Dependencias Python

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencias mínimas (`requirements.txt`):
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg2-binary==2.9.9
sentence-transformers==2.2.2
numpy==1.24.3
```

#### Paso 5: Descargar Modelo de Embeddings

```bash
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
```

El modelo se descarga en `~/.cache/torch/sentence_transformers/`.

#### Paso 6: Configurar Variables de Entorno

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=buscador
export POSTGRES_USER=app_user
export POSTGRES_PASSWORD=app_password
```

O crear archivo `.env` en `api/`.

#### Paso 7: Lanzar API

```bash
cd api
chmod +x launch_backend_v2.sh
./launch_backend_v2.sh
```

O manualmente:
```bash
uvicorn main_v2_final:app --host 0.0.0.0 --port 8000 --reload
```

#### Paso 8: Lanzar Frontend (Opcional)

```bash
cd frontend_v2
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

---

## 5. CARGA DE DATOS

### Verificar Conexión

```bash
curl http://localhost:8000/health
```

Respuesta esperada:
```json
{
  "status": "ok",
  "datasets_count": 0,
  "pgvector": true,
  "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2"
}
```

### Importar Datasets

Si tienes datos en JSON/CSV:

```bash
python3 scripts/import_datasets.py --file datos.json
```

O directamente desde PostgreSQL:
```bash
psql -U postgres -d buscador -c "\COPY datasets FROM 'datos.csv' WITH CSV HEADER"
```

### Verificar Datos Cargados

```bash
curl http://localhost:8000/datasets?limit=5
```

---

## 6. PROBAR EL BUSCADOR

### Test 1: Health Check

```bash
curl http://localhost:8000/health | jq
```

### Test 2: Búsqueda Simple

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "educación",
    "top_k": 5
  }' | jq '.results[].title'
```

### Test 3: Búsqueda con Filtros

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "hospitales",
    "top_k": 5,
    "territorio": "Madrid",
    "tema": "Salud"
  }' | jq '.results[].title'
```

### Test 4: Palabra Ambigua ("paro")

Este es el test más importante para verificar la mejora de calidad:

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "paro",
    "top_k": 5
  }' | jq '.results[] | {title: .title, score: .score}'
```

**Resultado esperado (correcto):**
```json
{
  "title": "Variación relativa del paro registrado",
  "score": 0.8234
}
```

**Resultado incorrecto (antes de la mejora):**
```json
{
  "title": "Paradas de guaguas",
  "score": 0.1234
}
```

### Test 5: Frontend Web

Abrir navegador:
```
http://localhost:8501
```

Verificar:
- [ ] Campo de búsqueda funciona
- [ ] Resultados aparecen en < 2 segundos
- [ ] Filtros laterales funcionan
- [ ] Detalles del dataset se muestran

---

## 7. SOLUCIÓN DE PROBLEMAS

### Problema: PostgreSQL no responde

```bash
# Verificar contenedor
docker ps | grep postgres

# Reiniciar
docker compose restart postgres

# Verificar logs
docker logs buscador_postgres --tail 50
```

### Problema: API no se conecta a PostgreSQL

```bash
# Verificar variables de entorno
cat docker/.env

# Probar conexión manual
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost', port=5432, database='buscador',
    user='postgres', password='postgres'
)
print('Conexión OK')
conn.close()
"
```

### Problema: Modelo de embeddings no carga

```bash
# Verificar instalación
python3 -c "from sentence_transformers import SentenceTransformer; print('OK')"

# Descargar manualmente
python3 -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print('Modelo descargado')
"
```

### Problema: "paro" sigue devolviendo transporte

Verificar que se usa `main_v2_final.py`:
```bash
grep "main_v2" docker/docker-compose.yml
```

Debe decir `main_v2_final:app`, no `main_v2_fixed:app`.

Si es necesario, reconstruir:
```bash
cd docker
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Problema: Puerto 8000 ocupado

```bash
# Buscar proceso
sudo lsof -i :8000

# Matar o cambiar puerto
# Editar docker-compose.yml: API_PORT=8001
```

---

## 8. MONITOREO Y MANTENIMIENTO

### Verificar Estado del Sistema

```bash
# Script de verificación
#!/bin/bash
echo "=== Estado del Sistema ==="
docker compose ps

echo -e "\n=== Health Check ==="
curl -s http://localhost:8000/health | jq

echo -e "\n=== Búsqueda Test ==="
curl -s -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "paro", "top_k": 3}' | jq '.results[].title'
```

### Backup de PostgreSQL

```bash
# Backup
docker exec buscador_postgres pg_dump -U postgres buscador > backup_$(date +%Y%m%d).sql

# Restore
cat backup_20260525.sql | docker exec -i buscador_postgres psql -U postgres -d buscador
```

### Actualizar el Sistema

```bash
cd docker

# Detener servicios
docker compose down

# Actualizar imágenes
docker compose pull

# Reconstruir si hay cambios locales
docker compose build --no-cache

# Iniciar
docker compose up -d

# Verificar
curl http://localhost:8000/health
```

---

## 9. CONFIGURACIONES AVANZADAS

### Cambiar Modelo de Embeddings

Editar `api/main_v2_final.py`:
```python
# Modelo más grande (mejor calidad, más lento)
EMBEDDING_MODEL = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

# Modelo más rápido (menor calidad)
EMBEDDING_MODEL = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
```

### Añadir Nuevas Palabras Ambiguas

Editar `PALABRAS_AMBIGUAS` en `api/main_v2_final.py`:

```python
PALABRAS_AMBIGUAS = {
    'paro': { ... },
    'banco': {
        'contexto': 'finanzas',
        'sinonimos': ['financiero', 'monetario', 'crédito'],
        'stop_patterns': ['banca', 'bancaria'],
        'boost_keywords': ['financiero', 'económico'],
    },
    # Añadir más...
}
```

### Configurar HTTPS (Producción)

Usar reverse proxy (nginx/traefik):

```yaml
# docker-compose.yml (añadir)
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
```

---

## 10. REFERENCIAS

- [Documentación pgvector](https://github.com/pgvector/pgvector)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [Streamlit](https://docs.streamlit.io/)
- [PostgreSQL Full Text Search](https://www.postgresql.org/docs/current/textsearch.html)

---

## 11. CHECKLIST DE DESPLIEGUE

- [ ] Descargar código fuente
- [ ] Configurar `docker/.env` con contraseñas seguras
- [ ] Verificar Docker y Docker Compose instalados
- [ ] Ejecutar `docker compose up -d`
- [ ] Verificar `docker compose ps` (3 servicios UP)
- [ ] Ejecutar health check: `curl http://localhost:8000/health`
- [ ] Probar búsqueda: `curl -X POST http://localhost:8000/search -d '{"query": "paro"}'`
- [ ] Verificar que "paro" devuelve empleo, no transporte
- [ ] Abrir frontend: http://localhost:8501
- [ ] Configurar backup automático (opcional)
- [ ] Documentar credenciales y URLs

---

**Versión**: 2.2.0
**Fecha actualización**: 2026-05-25
**Compatibilidad**: PostgreSQL 15+, Docker 24.0+
