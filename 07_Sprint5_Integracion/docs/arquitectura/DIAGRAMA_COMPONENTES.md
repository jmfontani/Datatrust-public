# Diagrama de Componentes - Fase 07: Integración y Despliegue

## Fecha: 2026-05-24

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                     SISTEMA COMPLETO                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐          ┌──────────────┐                    │
│  │   USUARIO    │          │   USUARIO    │                    │
│  │   (Navegador)│          │   (API)      │                    │
│  └──────┬───────┘          └──────┬───────┘                    │
│         │                         │                            │
│         ▼                         ▼                            │
│  ┌──────────────────────────────────────────────┐             │
│  │          FRONTEND (Streamlit)                 │             │
│  │          Puerto: 8501                         │             │
│  └──────────────────┬───────────────────────────┘             │
│                     │                                          │
│                     ▼                                          │
│  ┌──────────────────────────────────────────────┐             │
│  │          API REST (FastAPI)                   │             │
│  │          Puerto: 8000                         │             │
│  │                                               │             │
│  │  ┌──────────────┐  ┌──────────────┐          │             │
│  │  │  Endpoints   │  │   Motor de   │          │             │
│  │  │  /search     │──▶│  Búsqueda  │          │             │
│  │  │  /datasets   │  │  PostgreSQL│          │             │
│  │  │  /health     │  └──────┬───────┘          │             │
│  │  └──────────────┘         │                  │             │
│  └───────────────────────────┼──────────────────┘             │
│                              │                                 │
│                              ▼                                 │
│  ┌──────────────────────────────────────────────┐             │
│  │       BASE DE DATOS (PostgreSQL)              │             │
│  │       Puerto: 5432                          │             │
│  │       + Extensión pgvector                  │             │
│  │                                               │             │
│  │  ┌──────────────────────────────────────┐     │             │
│  │  │  Tabla: datasets (87,676 registros) │     │             │
│  │  │  - id, dataset_id                   │     │             │
│  │  │  - title, description               │     │             │
│  │  │  - embedding (VECTOR(384))           │     │             │
│  │  │  - search_vector (TSVECTOR)          │     │             │
│  │  │  - raw_metadata (JSONB)              │     │             │
│  │  └──────────────────────────────────────┘     │             │
│  │                                               │             │
│  │  ┌──────────────┐  ┌──────────────┐         │             │
│  │  │   Índice     │  │   Índice     │         │             │
│  │  │   HNSW       │  │   GIN        │         │             │
│  │  │   (Semántico)│  │   (Léxico)   │         │             │
│  │  └──────────────┘  └──────────────┘         │             │
│  └──────────────────────────────────────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Componentes Detallados

### 1. Frontend (Streamlit)
- **Puerto**: 8501
- **Tecnología**: Python + Streamlit
- **Función**: Interfaz de usuario para búsqueda y visualización
- **Comunicación**: HTTP/REST con API

### 2. API (FastAPI)
- **Puerto**: 8000
- **Tecnología**: Python + FastAPI
- **Endpoints principales**:
  - `GET /health` - Estado del sistema
  - `POST /search` - Búsqueda de datasets
  - `GET /datasets/{id}` - Detalle de dataset
  - `GET /filters` - Opciones de filtrado

### 3. Base de Datos (PostgreSQL + pgvector)
- **Puerto**: 5432
- **Versión**: PostgreSQL 15.4
- **Extensión**: pgvector 0.5.1
- **Datos**: 87,676 datasets

## 📊 Flujo de Datos

### Búsqueda Semántica
```
1. Usuario envía consulta ("demografía España")
2. API genera embedding de la consulta
3. PostgreSQL busca vectores similares (HNSW)
4. Retorna resultados ordenados por similitud
```

### Búsqueda Léxica
```
1. Usuario envía consulta ("demografía España")
2. API convierte a TSQUERY
3. PostgreSQL busca en search_vector (GIN)
4. Retorna resultados ordenados por relevancia
```

### Búsqueda Híbrida
```
1. Usuario envía consulta
2. API ejecuta búsqueda semántica y léxica
3. Combina resultados con pesos configurables
4. Retorna resultados finales ordenados
```

## 🗄️ Esquema de Base de Datos

### Tabla: datasets

| Campo | Tipo | Descripción | Índice |
|-------|------|-------------|--------|
| id | SERIAL PK | Identificador interno | B-tree |
| dataset_id | VARCHAR(255) | ID original | B-tree (UNIQUE) |
| title | TEXT | Título en español | - |
| description | TEXT | Descripción | - |
| publisher | VARCHAR(500) | Publicador | B-tree |
| publisher_id | VARCHAR(255) | URI del publicador | - |
| theme | VARCHAR(255) | Temática | B-tree |
| theme_label | TEXT | Etiquetas de tema | - |
| territory | VARCHAR(255) | Territorio | B-tree |
| territory_label | TEXT | Etiquetas territorio | - |
| format | VARCHAR(50) | Formato de datos | B-tree |
| language | VARCHAR(10) | Idioma | B-tree |
| license | VARCHAR(255) | Licencia | - |
| frequency | VARCHAR(50) | Frecuencia actualización | - |
| temporal_coverage | VARCHAR(255) | Cobertura temporal | - |
| url | TEXT | URL del dataset | - |
| keywords | TEXT[] | Palabras clave | GIN |
| tags | TEXT[] | Etiquetas | GIN |
| embedding | VECTOR(384) | Embedding semántico | HNSW |
| search_vector | TSVECTOR | Índice de búsqueda | GIN |
| raw_metadata | JSONB | Metadatos originales | - |

### Índices

| Nombre | Tipo | Columna(s) | Propósito |
|--------|------|------------|-----------|
| datasets_pkey | B-tree | id | Clave primaria |
| datasets_dataset_id_key | B-tree | dataset_id | Unicidad |
| idx_datasets_embedding_hnsw | HNSW | embedding | Búsqueda semántica |
| idx_datasets_search_vector | GIN | search_vector | Búsqueda léxica |
| idx_datasets_keywords | GIN | keywords | Filtro keywords |
| idx_datasets_tags | GIN | tags | Filtro tags |
| idx_datasets_theme | B-tree | theme | Filtro temático |
| idx_datasets_territory | B-tree | territory | Filtro territorial |
| idx_datasets_format | B-tree | format | Filtro formato |
| idx_datasets_publisher | B-tree | publisher | Filtro publicador |
| idx_datasets_language | B-tree | language | Filtro idioma |
| idx_datasets_dataset_id | B-tree | dataset_id | Búsqueda por ID |
| idx_datasets_theme_territory | B-tree | theme, territory | Filtro combinado |

## 🔌 Interfaces de Conexión

### Desde Python (psycopg2)
```python
import psycopg2

conn = psycopg2.connect(
    host='172.17.0.1',
    port=5432,
    database='buscador',
    user='postgres',
    password='postgres'
)
```

### Desde Docker Compose
```yaml
services:
  postgres:
    image: ankane/pgvector
    environment:
      POSTGRES_DB: buscador
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
```

## 📈 Rendimiento Esperado

| Operación | Tiempo Estimado |
|-----------|----------------|
| Conexión inicial | < 100ms |
| Búsqueda semántica (HNSW) | 10-50ms |
| Búsqueda léxica (GIN) | 5-30ms |
| Búsqueda híbrida | 20-80ms |
| Filtros facetados | 5-20ms |

---

*Documentación generada: 2026-05-24*
*Fase 07 - Integración y Despliegue*
