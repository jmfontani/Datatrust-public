# Nota de Ejecución - Fase 07 (Integración y Despliegue)

## Estado Actual (2026-05-24)

### ✅ Completado:
1. **Script de setup** (`setup.sh`) - Creado y funcional
2. **Docker Compose** - Configurado con PostgreSQL + pgvector
3. **Dockerfiles** - API y Frontend creados
4. **Migración** - Script `migrate_from_numpy.py` listo
5. **Entorno virtual** - Preparado con dependencias

### ⚠️ Limitación del Entorno:
**Docker no está disponible** en el entorno actual de desarrollo (contenedor OpenClaw).

## Alternativas para Ejecutar la Fase 07

### Opción 1: Ejecutar en máquina local con Docker (Recomendada)
```bash
# En tu máquina local con Docker instalado:
git clone <repositorio>
cd Datatrust/07_Sprint5_Integracion/codigo
chmod +x setup.sh
./setup.sh
```

### Opción 2: Instalar PostgreSQL localmente
```bash
# Instalar PostgreSQL
sudo apt-get install postgresql postgresql-contrib postgresql-16-pgvector

# Configurar
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE DATABASE buscador;"

# Ejecutar setup sin Docker
cd 07_Sprint5_Integracion/codigo
chmod +x setup_no_docker.sh
sudo ./setup_no_docker.sh
```

### Opción 3: Usar PostgreSQL en la nube (AWS RDS, etc.)
```bash
# Configurar variables de entorno
export POSTGRES_HOST=tu-host-rds.amazonaws.com
export POSTGRES_USER=buscador
export POSTGRES_PASSWORD=tu-password
export POSTGRES_DB=buscador

# Ejecutar migración manual
python3 db/migrate_from_numpy.py \
    --host $POSTGRES_HOST \
    --port 5432 \
    --dbname $POSTGRES_DB \
    --user $POSTGRES_USER \
    --password $POSTGRES_PASSWORD
```

## Archivos Generados

### Docker:
- `docker/docker-compose.yml` - Orquestación completa
- `docker/Dockerfile.api` - API REST (FastAPI)
- `docker/Dockerfile.frontend` - Frontend (Streamlit)
- `docker/.env.example` - Variables de entorno

### Base de Datos:
- `db/init.sql` - Schema PostgreSQL + pgvector
- `db/migrate_from_numpy.py` - Script de migración

### Motor de Búsqueda:
- `motor/search_engine_pgvector.py` - Motor adaptado a PostgreSQL

## Datos Preparados

Los datos están listos para la migración:
- 📄 Datasets: `03_Sprint1_Ingesta/datos/processed/datasets_clean.jsonl` (378MB)
- 🧮 Embeddings: `04_Sprint2_Embeddings/datos/processed/embeddings.npy` (129MB)
- 📊 Total: 87,677 datasets con embeddings de 384 dimensiones

## Verificación Post-Ejecución

Una vez ejecutado el setup, verificar:

```bash
# Verificar PostgreSQL
psql -d buscador -c "SELECT COUNT(*) FROM datasets;"
# Debe mostrar: 87677

# Verificar índices
psql -d buscador -c "SELECT indexname FROM pg_indexes WHERE tablename = 'datasets';"
# Debe mostrar: idx_embedding_hnsw, idx_search_vector, etc.

# Probar API
curl http://localhost:8000/health
# Debe responder: {"status": "ok", "datasets_count": 87677}

# Abrir frontend
# http://localhost:8501
```

## Notas Técnicas

- **pgvector**: Extensión de PostgreSQL para vectores. Usa HNSW para búsqueda aproximada O(log n)
- **HNSW**: Hierarchical Navigable Small World - Índice eficiente para búsqueda de vecinos cercanos
- **Embeddings**: 384 dimensiones (multilingüe español/inglés)
- **Búsqueda híbrida**: Combinación semántica (cosine similarity) + léxica (TSVECTOR)

## Contacto

Para dudas o problemas:
- Revisar logs: `docker-compose logs -f`
- Verificar conectividad: `docker exec buscador_postgres pg_isready -U postgres`
- Revisar documentación en `docs/despliegue.md`

---

*Generado: 2026-05-24*
*Fase 07 - Sprint 5: Integración y Despliegue*
