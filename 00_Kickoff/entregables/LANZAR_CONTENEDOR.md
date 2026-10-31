# Guía de Lanzamiento del Contenedor Docker

## Proyecto: Buscador Semántico de Datasets (datos.gob.es)

**Fecha:** 2026-05-20  
**Entorno:** Debian 13 + Google Drive montado

---

## 📋 PRERREQUISITOS

### 1. Instalar Docker y Docker Compose

```bash
# Actualizar repositorios
sudo apt update

# Instalar Docker
sudo apt install -y docker.io docker-compose

# Iniciar servicio Docker
sudo systemctl start docker
sudo systemctl enable docker

# Verificar instalación
docker --version
docker-compose --version
```

### 2. Verificar permisos de usuario

```bash
# Añadir usuario al grupo docker (para no usar sudo)
sudo usermod -aG docker $USER

# Cerrar sesión y volver a entrar para aplicar cambios
# O ejecutar:
newgrp docker
```

---

## 🚀 LANZAMIENTO PASO A PASO

### PASO 1: Navegar al directorio del proyecto

```bash
# Desde tu servidor Debian 13
cd <ruta-repo>/00_Kickoff/entregables

# Verificar que existen los archivos
ls -la
```

**Archivos esperados:**
```
docker-compose.yml
.env.example
init-db/
└── 01_init_database.sh
README_DOCKER.md
```

---

### PASO 2: Crear archivo de configuración .env

```bash
# Copiar plantilla
cp .env.example .env

# Editar con tus preferencias (nano, vim, o cualquier editor)
nano .env
```

**Contenido recomendado para desarrollo:**

```ini
# PostgreSQL Configuration
POSTGRES_USER=pfm_user
POSTGRES_PASSWORD=<elige-una-password>
POSTGRES_DB=pfm_datasets
POSTGRES_PORT=5432

# API Configuration
API_PORT=8000

# Frontend Configuration
FRONTEND_PORT=8501

# pgAdmin Configuration (opcional)
PGADMIN_EMAIL=admin@pfm.local
PGADMIN_PASSWORD=***
PGADMIN_PORT=5050

# Modelo de embeddings
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=384

# Logging
LOG_LEVEL=info
```

> **NOTA IMPORTANTE:** Cambia las contraseñas en producción.

---

### PASO 3: Iniciar los servicios

```bash
# Opción A: En primer plano (ver logs en tiempo real)
docker-compose up

# Opción B: En segundo plano (detached)
docker-compose up -d

# Opción C: Reconstruir imágenes e iniciar
docker-compose up -d --build
```

**Salida esperada:**
```
Creating network "entregables_pfm_network" with driver "bridge"
Creating volume "entregables_postgres_data" with local driver
Creating volume "entregables_backend_logs" with local driver
Creating volume "entregables_pgadmin_data" with local driver
Creating pfm_postgres ... done
Creating pfm_backend  ... done
Creating pfm_frontend ... done
Creating pfm_pgadmin  ... done
```

---

### PASO 4: Verificar que todo funciona

```bash
# Ver estado de los contenedores
docker-compose ps
```

**Estado esperado:**
```
NAME                COMMAND                  SERVICE             STATUS              PORTS
pfm_backend         "uvicorn main:app --…"   backend             running (healthy)   0.0.0.0:8000->8000/tcp
pfm_frontend        "streamlit run app.py…"  frontend            running             0.0.0.0:8501->8501/tcp
pfm_pgadmin         "/entrypoint.sh"         pgadmin             running             0.0.0.0:5050->80/tcp
pfm_postgres        "docker-entrypoint.s…"   db                  running (healthy)   0.0.0.0:5432->5432/tcp
```

> **Importante:** Esperar a que `db` y `backend` muestren `(healthy)` antes de usar.

---

### PASO 5: Verificar logs de inicialización

```bash
# Ver logs de la base de datos (primer arranque)
docker-compose logs -f db
```

**Buscar mensajes de éxito:**
```
✓ Extensión pgvector creada
✓ Tablas creadas
✓ Índices creados
✓ Triggers creados
✓ Datos iniciales insertados
✓ BASE DE DATOS INICIALIZADA CORRECTAMENTE
```

**Salir de logs:** `Ctrl + C`

---

## 🌐 ACCESO A LOS SERVICIOS

Una vez iniciados, acceder desde el navegador o herramientas:

| Servicio | URL local | Descripción |
|----------|-----------|-------------|
| **PostgreSQL** | `localhost:5432` | Base de datos (con pgvector) |
| **API Backend** | `http://localhost:8000` | FastAPI - Documentación automática en `/docs` |
| **Frontend** | `http://localhost:8501` | Streamlit - Interfaz de usuario |
| **pgAdmin** | `http://localhost:5050` | Gestión visual PostgreSQL |

### Verificar API Backend

```bash
# Desde el servidor o máquina local
curl http://localhost:8000/health
```

**Respuesta esperada:**
```json
{"status": "healthy", "database": "connected"}
```

### Verificar Documentación API

Abrir en navegador: `http://localhost:8000/docs`

> Swagger UI con todos los endpoints documentados automáticamente.

---

## 🛠️ COMANDOS ÚTILES

### Estado y diagnóstico

```bash
# Ver todos los contenedores activos
docker-compose ps

# Ver logs en tiempo real (todos los servicios)
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f db
docker-compose logs -f backend

# Ver uso de recursos
docker stats
```

### Gestión de servicios

```bash
# Detener servicios (conservar datos)
docker-compose stop

# Iniciar servicios detenidos
docker-compose start

# Reiniciar un servicio específico
docker-compose restart backend

# Detener y eliminar contenedores
docker-compose down

# Detener y eliminar TODO (incluyendo datos)
docker-compose down -v
```

### Acceso a la base de datos

```bash
# Entrar al contenedor PostgreSQL
docker-compose exec db psql -U pfm_user -d pfm_datasets

# Listar tablas
\dt

# Ver esquema de una tabla
\d dataset

# Consultar datasets
SELECT COUNT(*) FROM dataset;

# Salir
\q
```

### Backup y restauración

```bash
# Crear backup
docker-compose exec db pg_dump -U pfm_user -d pfm_datasets > backup_$(date +%Y%m%d).sql

# Restaurar backup
docker-compose exec -T db psql -U pfm_user -d pfm_datasets < backup_20260520.sql
```

---

## 🔧 SOLUCIÓN DE PROBLEMAS

### Error: "Cannot connect to the Docker daemon"

```bash
# Verificar que Docker está corriendo
sudo systemctl status docker

# Si no está corriendo
sudo systemctl start docker
```

### Error: "port is already allocated"

```bash
# Ver qué proceso usa el puerto
sudo lsof -i :5432

# O cambiar el puerto en .env
# POSTGRES_PORT=5433
```

### Error: "Permission denied" al ejecutar docker-compose

```bash
# Verificar grupo docker
groups $USER

# Si no aparece "docker", ejecutar:
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar
```

### Error: "database does not exist" o tablas no creadas

```bash
# El script de inicialización solo corre la primera vez.
# Para forzar reinicialización:
docker-compose down -v
docker-compose up -d
```

### Error: "unhealthy" en servicios

```bash
# Ver logs detallados
docker-compose logs db | tail -50
docker-compose logs backend | tail -50

# Verificar conectividad entre contenedores
docker-compose exec backend ping db
```

### Google Drive: lentitud o desconexión

Si los archivos están en Google Drive montado y es lento:

```bash
# Copiar archivos a directorio local primero
cp -r <ruta-repo>/00_Kickoff/entregables ~/pfm-docker/
cd ~/pfm-docker

# Ejecutar desde local
docker-compose up -d
```

---

## 📁 ESTRUCTURA DE ARCHIVOS EN SERVIDOR

```
<ruta-repo>/00_Kickoff/entregables/
├── docker-compose.yml           # Definición de servicios
├── .env                          # Variables de entorno (CREAR)
├── .env.example                  # Plantilla
├── README_DOCKER.md             # Guía general Docker
├── LANZAR_CONTENEDOR.md         # ESTE DOCUMENTO
├── init-db/
│   └── 01_init_database.sh      # Script inicialización BD
└── [volumes Docker creados automáticamente]
    ├── postgres_data/           # Datos persistentes PostgreSQL
    ├── backend_logs/            # Logs del backend
    └── pgadmin_data/            # Configuración pgAdmin
```

---

## ✅ CHECKLIST DE VERIFICACIÓN

- [ ] Docker instalado (`docker --version`)
- [ ] Docker Compose instalado (`docker-compose --version`)
- [ ] Usuario en grupo docker (`groups $USER`)
- [ ] Archivo `.env` creado desde `.env.example`
- [ ] Puerto 5432 disponible (o cambiado en `.env`)
- [ ] Puerto 8000 disponible (o cambiado en `.env`)
- [ ] Puerto 8501 disponible (o cambiado en `.env`)
- [ ] `docker-compose up -d` ejecutado sin errores
- [ ] Contenedores en estado `running` (`docker-compose ps`)
- [ ] Base de datos inicializada (logs muestran "✓ BASE DE DATOS INICIALIZADA")
- [ ] pgvector extension verificada (`docker-compose exec db psql -U pfm_user -d pfm_datasets -c "SELECT * FROM pg_extension WHERE extname = 'vector';"`)
- [ ] API responde en `http://localhost:8000/health`
- [ ] Frontend accesible en `http://localhost:8501`

---

## 🔄 FLUJO TÍPICO DE DESARROLLO

```bash
# 1. Ir al directorio
cd <ruta-repo>/00_Kickoff/entregables

# 2. Verificar que todo está detenido
docker-compose ps

# 3. Iniciar servicios
docker-compose up -d

# 4. Esperar 30 segundos a que la BD inicialice
sleep 30

# 5. Verificar estado
docker-compose ps

# 6. Verificar logs
docker-compose logs -f db | grep "INICIALIZADA"

# 7. Probar conexión a BD
docker-compose exec db psql -U pfm_user -d pfm_datasets -c "SELECT 'Conexión OK';"

# 8. Abrir frontend en navegador
# http://localhost:8501

# 9. Al terminar de trabajar, detener
docker-compose stop

# 10. O detener y eliminar si no se necesita más
docker-compose down
```

---

## 📞 SOPORTE

Si tienes problemas:

1. **Revisar logs:** `docker-compose logs -f [servicio]`
2. **Verificar estado:** `docker-compose ps`
3. **Reiniciar servicio:** `docker-compose restart [servicio]`
4. **Reiniciar todo:** `docker-compose down && docker-compose up -d`
5. **Limpiar todo:** `docker-compose down -v` (⚠️ pierde datos)

---

*Documento actualizado: 2026-05-20*  
*Versión: 1.0*
