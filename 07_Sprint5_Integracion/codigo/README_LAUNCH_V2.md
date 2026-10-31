# Scripts de Lanzamiento V2

## 🚀 Scripts Creados

### Backend V2 (PostgreSQL + pgvector)
```bash
# Lanzar solo backend
codigo/api/launch_backend_v2.sh
```

**Características:**
- Conecta a PostgreSQL con pgvector
- Verifica dependencias antes de iniciar
- Chequea conexión a base de datos
- Puerto configurable via `API_PORT` (default: 8000)

### Frontend V2 (Streamlit)
```bash
# Lanzar solo frontend
codigo/frontend_v2/launch_frontend_v2.sh
```

**Características:**
- Frontend con soporte Enter
- Tema personalizable
- Puerto configurable via `FRONTEND_PORT` (default: 8501)

### Lanzar Todo (Backend + Frontend)
```bash
# Lanzar ambos servicios
codigo/launch_all_v2.sh
```

**Características:**
- Verifica puertos disponibles
- Lanza backend y frontend en paralelo
- Guarda PIDs para gestión posterior
- Muestra URLs de acceso

### Detener Servicios
```bash
# Detener ambos servicios
codigo/stop_backend_frontend_v2.sh
```

### Validación
```bash
# Verificar todo antes de lanzar
codigo/validate_v2.py
```

## 📋 Uso Rápido

### Paso 0: Validar entorno
```bash
cd /home/node/.openclaw/workspace/PFM/Datatrust/07_Sprint5_Integracion/codigo
python3 validate_v2.py
```

### Opción 1: Lanzar todo de una vez
```bash
./launch_all_v2.sh
```

Accede a:
- Backend: http://localhost:8000
- Frontend: http://localhost:8501

### Opción 2: Lanzar por separado
```bash
# Terminal 1: Backend
cd codigo/api
./launch_backend_v2.sh

# Terminal 2: Frontend
cd codigo/frontend_v2
./launch_frontend_v2.sh
```

### Opción 3: Detener todo
```bash
./stop_backend_frontend_v2.sh
```

## 🔧 Configuración

### Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `API_PORT` | 8000 | Puerto del backend |
| `API_HOST` | 0.0.0.0 | Host del backend |
| `FRONTEND_PORT` | 8501 | Puerto del frontend |

### Ejemplo con puertos personalizados
```bash
API_PORT=8080 FRONTEND_PORT=3000 ./launch_all_v2.sh
```

## 🗄️ Requisitos

### Dependencias Python
```bash
pip install fastapi uvicorn psycopg2-binary streamlit requests numpy
```

### PostgreSQL
- PostgreSQL 14+ con extensión pgvector
- Base de datos `buscador` creada
- Tabla `datasets` con datos migrados

### Verificar PostgreSQL
```bash
psql -h localhost -U postgres -d buscador -c "SELECT COUNT(*) FROM datasets;"
```

## 📊 Diferencias V1 vs V2

| Aspecto | Backend V1 | Backend V2 |
|---------|-----------|------------|
| Almacenamiento | NumPy en memoria | PostgreSQL + pgvector |
| Persistencia | Volátil | Persistente |
| Escalabilidad | Limitada | Alta |
| Búsqueda | In-memory | HNSW index |

| Aspecto | Frontend V1 | Frontend V2 |
|---------|------------|------------|
| Buscar con Enter | ❌ | ✅ |
| Temas personalizables | ❌ | ✅ |
| Diseño | Básico | Avanzado |

## 🐛 Troubleshooting

### Puerto ocupado
```bash
# Verificar qué proceso usa el puerto
lsof -i :8000
lsof -i :8501

# Matar proceso
kill -9 <PID>
```

### PostgreSQL no accesible
```bash
# Verificar PostgreSQL corriendo
sudo systemctl status postgresql

# Reiniciar
sudo systemctl restart postgresql
```

### Dependencias faltantes
```bash
# Instalar todas las dependencias
pip install -r requirements.txt
```

## 📚 Documentación Relacionada

- [Backend V2 README](../api/README.md)
- [Frontend V2 README](../frontend_v2/README.md)
- [Guía de Despliegue](../../docs/DESPLIEGUE.md)
