# Guía de Despliegue - Fase 07: Integración y Despliegue

**Fecha:** 2026-05-24
**Versión:** 1.0

## 📋 Prerrequisitos

### Hardware Recomendado
- **CPU**: 4+ cores
- **RAM**: 8GB mínimo (16GB recomendado)
- **Disco**: 5GB libres (SSD recomendado)
- **Red**: Acceso a puertos 5432, 8000, 8501

### Software Requerido

#### Opción A: Con Docker (Recomendado)
- Docker Engine 20.10+
- Docker Compose 2.0+

#### Opción B: Sin Docker
- PostgreSQL 15+
- Extensión pgvector 0.5.1+
- Python 3.9+

## 🚀 Despliegue con Docker (Recomendado)

### Paso 1: Clonar el Proyecto
```bash
git clone <repositorio>
cd Datatrust/07_Sprint5_Integracion/codigo
```

### Paso 2: Configurar Variables de Entorno
```bash
cp docker/.env.example docker/.env
# Editar .env con tus valores
```

### Paso 3: Ejecutar Setup
```bash
chmod +x setup.sh
./setup.sh
```

Este script automatizado:
1. Verifica dependencias
2. Crea red Docker
3. Inicia PostgreSQL + pgvector
4. Ejecuta scripts SQL de inicialización
5. Migra datos desde NumPy
6. Verifica integridad
7. Inicia API y Frontend

### Paso 4: Verificar Despliegue
```bash
# Verificar PostgreSQL
docker exec buscador_postgres pg_isready -U postgres

# Verificar API
curl http://localhost:8000/health

# Verificar Frontend
# Abrir navegador en http://localhost:8501
```

### Paso 5: Detener el Sistema
```bash
docker-compose down
```

### Paso 6: Detener y Eliminar Datos
```bash
docker-compose down -v  # Elimina volúmenes también
```

## 🔧 Despliegue Manual (Sin Docker)

### Paso 1: Instalar PostgreSQL
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Instalar pgvector
sudo apt-get install postgresql-15-pgvector  # Ajustar versión
```

### Paso 2: Configurar Base de Datos
```bash
# Iniciar PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Crear base de datos
sudo -u postgres psql -c "CREATE DATABASE buscador;"
sudo -u postgres psql -d buscador -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Paso 3: Ejecutar Scripts SQL
```bash
# Schema
psql -d buscador -U postgres -f db/init.sql
```

### Paso 4: Migrar Datos
```bash
# Instalar dependencias Python
pip install psycopg2-binary numpy tqdm sentence-transformers

# Ejecutar migración
python3 db/migrate_from_numpy.py \
    --host localhost \
    --port 5432 \
    --dbname buscador \
    --user postgres \
    --password postgres
```

### Paso 5: Verificar Migración
```bash
psql -d buscador -c "SELECT COUNT(*) FROM datasets;"
# Debe mostrar: 87676
```

### Paso 6: Iniciar API
```bash
cd codigo/api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Paso 7: Iniciar Frontend
```bash
cd codigo/frontend
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

## 🔍 Verificación Post-Despliegue

### Verificar PostgreSQL
```bash
# Conectar
psql -d buscador -U postgres

# Verificar tablas
\dt

# Verificar datasets
SELECT COUNT(*) FROM datasets;

# Verificar índices
\di datasets*

# Verificar extensión pgvector
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Verificar API
```bash
# Health check
curl http://localhost:8000/health

# Búsqueda
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "demografia poblacion", "limit": 5}'
```

### Verificar Frontend
- Abrir navegador en `http://localhost:8501`
- Probar búsqueda con diferentes términos
- Verificar filtros facetados

## 🔧 Configuración Avanzada

### Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| POSTGRES_HOST | Host de PostgreSQL | localhost |
| POSTGRES_PORT | Puerto de PostgreSQL | 5432 |
| POSTGRES_DB | Nombre de base de datos | buscador |
| POSTGRES_USER | Usuario PostgreSQL | postgres |
| POSTGRES_PASSWORD | Contraseña PostgreSQL | postgres |
| API_PORT | Puerto de la API | 8000 |
| FRONTEND_PORT | Puerto del frontend | 8501 |

### Optimización de PostgreSQL

#### postgresql.conf recomendado
```ini
# Memoria
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 16MB
maintenance_work_mem = 512MB

# WAL
wal_buffers = 16MB
max_wal_size = 2GB
min_wal_size = 512MB

# Conexiones
max_connections = 100

# Paralelismo
max_parallel_workers = 4
max_parallel_maintenance_workers = 2
```

### Optimización de pgvector

```sql
-- Configurar HNSW
CREATE INDEX idx_datasets_embedding_hnsw 
ON datasets USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Ajustar ef_search (mayor = más preciso, más lento)
SET hnsw.ef_search = 64;
```

## 🐛 Troubleshooting

### Problema: Docker no inicia
```bash
# Verificar logs
docker-compose logs postgres
docker-compose logs api
docker-compose logs frontend

# Verificar recursos
docker system df
docker volume ls
```

### Problema: PostgreSQL no accesible
```bash
# Verificar puerto
sudo netstat -tlnp | grep 5432

# Verificar PostgreSQL
sudo systemctl status postgresql

# Verificar logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

### Problema: Migración fallida
```bash
# Verificar espacio
df -h

# Verificar memoria
free -h

# Reintentar con batch size más pequeño
python3 db/migrate_from_numpy.py --batch-size 500
```

### Problema: Búsqueda lenta
```sql
-- Verificar índices
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'datasets';

-- Reconstruir índices
REINDEX INDEX idx_datasets_embedding_hnsw;
REINDEX INDEX idx_datasets_search_vector;

-- Actualizar estadísticas
ANALYZE datasets;
```

## 📝 Checklist de Despliegue

### Pre-Despliegue
- [ ] Verificar prerrequisitos de hardware
- [ ] Verificar prerrequisitos de software
- [ ] Configurar variables de entorno
- [ ] Verificar archivos de datos (embeddings.npy, datasets_clean.jsonl)

### Durante Despliegue
- [ ] PostgreSQL iniciado y accesible
- [ ] Extensión pgvector instalada
- [ ] Schema creado correctamente
- [ ] Datos migrados sin errores
- [ ] Índices creados correctamente

### Post-Despliegue
- [ ] API responde en /health
- [ ] Búsqueda léxica funciona
- [ ] Búsqueda semántica funciona
- [ ] Filtros facetados funcionan
- [ ] Frontend carga correctamente
- [ ] Rendimiento aceptable (< 100ms)

## 🔒 Seguridad

### Credenciales
- Cambiar contraseña por defecto de PostgreSQL
- Usar variables de entorno para credenciales
- No commitear archivos .env con credenciales

### Red
- Limitar acceso a puertos necesarios
- Usar firewall para restringir acceso a PostgreSQL
- Considerar SSL para conexiones

### Datos
- Realizar backups periódicos
- Encriptar datos sensibles
- Auditar accesos a base de datos

## 📊 Monitoreo

### Métricas Importantes
- Uso de CPU y memoria
- Conexiones a PostgreSQL
- Tiempo de respuesta de búsquedas
- Errores en logs

### Herramientas Recomendadas
- pg_stat_statements para queries lentas
- Grafana + Prometheus para métricas
- pgAdmin para administración visual

---

## 🆕 Frontend - Dos Versiones Disponibles (2026-05-25)

El frontend tiene **dos versiones** para diferentes tipos de usuarios:

### Versión Pública (por defecto)

**Para:** Ciudadanos, periodistas, investigadores

**Características:**
- Interfaz limpia tipo Google
- Sin controles técnicos
- Búsqueda con Enter
- Filtros desplegables con todas las opciones
- Indicador de tipo de enlace (📥 archivo vs 🌐 web)
- Relevancia con estrellas ⭐⭐⭐⭐⭐

**URL:**
```
http://localhost:8501
```

### Versión Avanzada

**Para:** Desarrolladores, administradores

**Características:**
- Sliders de peso semántico/léxico
- Configuración de score mínimo
- Panel de estado de API
- Controles técnicos completos

**URL:**
```
http://localhost:8501?mode=advanced
```

### Configuración

**Por defecto (pública):**
El `Dockerfile.frontend` ejecuta `app_router.py` que carga la versión pública por defecto:
```dockerfile
CMD ["streamlit", "run", "app_router.py"]
```

**Forzar versión avanzada:**

Opción 1 - URL:
```
http://localhost:8501?mode=advanced
```

Opción 2 - Variable de entorno:
```yaml
services:
  frontend:
    environment:
      - APP_MODE=advanced
```

Opción 3 - Comando directo:
```bash
docker exec buscador_frontend streamlit run app.py
```

---

**Documento generado:** 2026-05-24
**Versión:** 1.1
**Última actualización:** 2026-05-25 (añadida documentación del frontend dual)
**Mantenimiento:** Actualizar con cada despliegue
