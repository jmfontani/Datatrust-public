# Guía de Conexión a PostgreSQL + pgvector

## Proyecto: Buscador Semántico de Datasets (datos.gob.es)
**Fecha:** 2026-05-20

---

## 🔌 OPCIÓN 1: Conectar desde línea de comandos (psql)

### Desde dentro del contenedor PostgreSQL:

```bash
# Entrar al contenedor y abrir psql
docker compose exec db psql -U pfm_user -d pfm_datasets
```

**Salida esperada:**
```
psql (15.4)
Type "help" for help.

pfm_datasets=#
```

### Comandos útiles de psql:

```sql
-- Ver tablas
\dt

-- Ver esquema de tabla dataset
\d dataset

-- Ver extensión pgvector instalada
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Contar registros
SELECT COUNT(*) FROM dataset;

-- Ver primeros registros
SELECT id, title_es, description_es FROM dataset LIMIT 5;

-- Salir
\q
```

---

## 🔌 OPCIÓN 2: Conectar desde línea de comandos (local)

### Si tienes psql instalado en tu Debian 13:

```bash
# Instalar cliente PostgreSQL si no lo tienes
sudo apt install -y postgresql-client

# Conectar al contenedor
psql -h localhost -p 5432 -U pfm_user -d pfm_datasets

# Te pedirá la contraseña: (la que pusiste en .env)
```

---

## 🌐 OPCIÓN 3: pgAdmin (Interfaz Web)

### 1. Verificar que pgAdmin está corriendo:

```bash
docker compose ps
```

**Debe mostrar:**
```
NAME           STATUS          PORTS
pfm_postgres   Up (healthy)    0.0.0.0:5432->5432/tcp
pfm_pgadmin    Up (healthy)    0.0.0.0:5050->80/tcp
```

### 2. Abrir pgAdmin en navegador:

```
http://localhost:5050
```

O desde otra máquina:
```
http://[IP-DEL-SERVIDOR]:5050
```

### 3. Credenciales de login:

| Campo | Valor |
|-------|-------|
| Email | `admin@pfm.example.com` |
| Password | `***` (la que pusiste en .env) |

### 4. Registrar servidor PostgreSQL:

Una vez dentro de pgAdmin:

1. Click derecho en **Servers** → **Register** → **Server**
2. Pestaña **General**:
   - Name: `PFM Datos Gob ES`
3. Pestaña **Connection**:
   - Host: `db` (nombre del servicio en docker-compose) o `pfm_postgres`
   - Port: `5432`
   - Database: `pfm_datasets`
   - Username: `pfm_user`
   - Password: `(tu contraseña del .env)`
   - Guardar contraseña: ✅
4. Click **Save**

---

## 🐍 OPCIÓN 4: Conectar desde Python

```python
import psycopg2
from psycopg2.extras import RealDictCursor

# Conexión
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="pfm_datasets",
    user="pfm_user",
    password="***"  # tu contraseña
)

# Crear cursor
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Verificar pgvector
cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
print(cursor.fetchall())

# Ver tablas
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
for row in cursor.fetchall():
    print(row)

# Cerrar
cursor.close()
conn.close()
```

---

## 🔧 OPCIÓN 5: DBeaver / TablePlus (Clientes gráficos)

Configuración de conexión:

| Campo | Valor |
|-------|-------|
| Host | `localhost` o IP del servidor |
| Port | `5432` |
| Database | `pfm_datasets` |
| User | `pfm_user` |
| Password | `***` (de .env) |
| SSL | `Disabled` |

---

## 📊 VERIFICACIÓN RÁPIDA

Ejecuta esto para confirmar que todo funciona:

```bash
# 1. Verificar que PostgreSQL está corriendo
docker compose ps

# 2. Probar conexión interna
docker compose exec db psql -U pfm_user -d pfm_datasets -c "SELECT version();"

# 3. Probar conexión externa (si tienes psql local)
psql -h localhost -p 5432 -U pfm_user -d pfm_datasets -c "SELECT 'Conexión OK';"

# 4. Verificar pgvector
docker compose exec db psql -U pfm_user -d pfm_datasets -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

---

## 🚨 SOLUCIÓN DE PROBLEMAS

### "Connection refused"
```bash
# Verificar que el contenedor está corriendo
docker compose ps

# Verificar logs
docker compose logs db
```

### "password authentication failed"
- Revisa el archivo `.env`
- Asegúrate de que la contraseña coincide

### "database does not exist"
```bash
# El script de inicialización no corrió. Forzar reinicio:
docker compose down -v
docker compose up -d
docker compose logs -f db
```

### "pgvector extension not available"
```bash
# Verificar imagen correcta
docker compose exec db psql -U pfm_user -d pfm_datasets -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"
```

---

## 📁 ARCHIVOS IMPORTANTES

| Archivo | Descripción |
|---------|-------------|
| `docker-compose.yml` | Definición de servicios |
| `.env` | Credenciales y configuración |
| `init-db/01_init_database.sh` | Script de inicialización |

---

*Documento actualizado: 2026-05-20*
