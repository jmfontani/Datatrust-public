# Docker Compose - Buscador Semántico

## Inicio Rápido

### 1. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

### 2. Iniciar servicios

```bash
docker-compose up -d
```

### 3. Verificar estado

```bash
docker-compose ps
```

### 4. Acceder a servicios

| Servicio | URL | Descripción |
|----------|-----|-------------|
| PostgreSQL | `localhost:5432` | Base de datos con pgvector |
| Backend API | `http://localhost:8000` | FastAPI |
| Frontend | `http://localhost:8501` | Streamlit |
| pgAdmin | `http://localhost:5050` | Gestión PostgreSQL |

---

## Estructura

```
.
├── docker-compose.yml        # Definición de servicios
├── .env                      # Variables de entorno (no versionar)
├── .env.example             # Plantilla de variables
├── init-db/
│   └── 01_init_database.sh  # Script de inicialización
└── README.md                # Este archivo
```

---

## Servicios

### PostgreSQL + pgvector
- **Imagen:** `ankane/pgvector:latest`
- **Base de datos:** `pfm_datasets`
- **Usuario:** según `.env`
- **Volumen:** Persistente (`postgres_data`)
- **Healthcheck:** Verifica conexión cada 10s

### Backend FastAPI
- **Puerto:** 8000
- **Dependencias:** PostgreSQL (espera a que esté healthy)
- **Healthcheck:** Endpoint `/health` cada 30s

### Frontend Streamlit
- **Puerto:** 8501
- **Dependencias:** Backend
- **Configuración:** Headless mode

### pgAdmin (opcional)
- **Puerto:** 5050
- **Descripción:** Interfaz visual para gestión PostgreSQL

---

## Comandos útiles

```bash
# Iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f db
docker-compose logs -f backend
docker-compose logs -f frontend

# Detener
docker-compose down

# Detener y eliminar volúmenes
docker-compose down -v

# Reconstruir imágenes
docker-compose up -d --build

# Ejecutar comando en contenedor
docker-compose exec db psql -U pfm_user -d pfm_datasets

# Backup base de datos
docker-compose exec db pg_dump -U pfm_user pfm_datasets > backup.sql

# Restaurar base de datos
docker-compose exec -T db psql -U pfm_user pfm_datasets < backup.sql
```

---

## Configuración avanzada

### Personalizar puertos

Editar `.env`:
```env
POSTGRES_PORT=5433      # Cambiar si hay conflicto
API_PORT=8001           # Puerto alternativo para API
FRONTEND_PORT=8502      # Puerto alternativo para Streamlit
PGADMIN_PORT=5051       # Puerto alternativo para pgAdmin
```

### Persistencia de datos

Los datos se almacenan en volúmenes Docker:
- `postgres_data`: Datos de PostgreSQL
- `pgadmin_data`: Configuración de pgAdmin
- `backend_logs`: Logs del backend

### Red

Los servicios se comunican en la red `pfm_network` (bridge):
- Subred: `172.20.0.0/16`
- Backend accede a PostgreSQL via: `db:5432`
- Frontend accede a Backend via: `backend:8000`

---

## Troubleshooting

### Error: "pgvector extension not available"

Asegurarse de usar la imagen correcta: `ankane/pgvector:latest`

### Error: "database does not exist"

El script de inicialización se ejecuta solo la primera vez. Para reiniciar:

```bash
docker-compose down -v
docker-compose up -d
```

### Error: "port already in use"

Cambiar el puerto en `.env` y reiniciar:

```bash
docker-compose down
docker-compose up -d
```

---

## Recursos

- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [PostgreSQL 15 Docs](https://www.postgresql.org/docs/15/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Streamlit Docs](https://docs.streamlit.io/)
