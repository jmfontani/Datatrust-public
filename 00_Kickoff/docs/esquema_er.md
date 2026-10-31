# Esquema Entidad-Relación (ER) - Base de Datos

## Proyecto: Buscador Semántico de Datasets Públicos (datos.gob.es)

**Fecha:** 2026-05-20
**Base de datos:** PostgreSQL 15+ con extensión pgvector

---

## 📊 DIAGRAMA ENTIDAD-RELACIÓN

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATASET                                    │
├─────────────────────────────────────────────────────────────────┤
│ PK  id                          SERIAL                            │
│     identifier                  VARCHAR(255) UNIQUE NOT NULL        │
│     source_url                  TEXT                              │
│     title_es                    TEXT NOT NULL                     │
│     title_en                    TEXT                              │
│     description_es              TEXT                              │
│     description_en              TEXT                              │
│     embedding_text              TEXT                              │
│     metadata_vector             VECTOR(384)                       │
│     themes                      TEXT[]                            │
│     keywords                    TEXT[]                            │
│     spatial_uri                 TEXT                              │
│     spatial_level               VARCHAR(50)                       │
│     spatial_name                TEXT                              │
│     publisher_uri               TEXT                              │
│     publisher_name              TEXT                              │
│     license_uri                 TEXT                              │
│     license_name                TEXT                              │
│     temporal_coverage           TEXT                              │
│     accrual_periodicity         VARCHAR(100)                      │
│     issued                      DATE                              │
│     modified                    DATE                              │
│     distributions               JSONB                             │
│     search_vector               TSVECTOR                          │
│     created_at                  TIMESTAMP DEFAULT NOW()            │
│     updated_at                  TIMESTAMP DEFAULT NOW()            │
│     last_sync_at                TIMESTAMP                         │
└──────────────┬──────────────────────────────────────────────────┘
               │
               │ 1:N
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DISTRIBUTION                                   │
├─────────────────────────────────────────────────────────────────┤
│ PK  id                          SERIAL                            │
│ FK  dataset_id                  INTEGER REFERENCES dataset(id)     │
│     access_url                  TEXT NOT NULL                     │
│     format                      VARCHAR(100)                      │
│     format_type                 VARCHAR(50)                       │
│     title_es                    TEXT                              │
│     title_en                    TEXT                              │
│     byte_size                   BIGINT                          │
│     download_url                TEXT                              │
│     description_es              TEXT                              │
│     description_en              TEXT                              │
│     issued                      DATE                              │
│     modified                    DATE                              │
│     license_uri                 TEXT                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    BENCHMARK_QUERY                                │
├─────────────────────────────────────────────────────────────────┤
│ PK  id                          SERIAL                            │
│     query_text                  TEXT NOT NULL                     │
│     query_vector                VECTOR(384)                       │
│     expected_dataset_ids        INTEGER[]                         │
│     category                    VARCHAR(100)                      │
│     difficulty                  VARCHAR(20)                       │
│     created_at                  TIMESTAMP DEFAULT NOW()            │
│     updated_at                  TIMESTAMP DEFAULT NOW()            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  SEARCH_LOG                                     │
├─────────────────────────────────────────────────────────────────┤
│ PK  id                          SERIAL                            │
│     query_text                  TEXT NOT NULL                     │
│     query_vector                VECTOR(384)                       │
│     results_count               INTEGER                           │
│     top_result_id               INTEGER REFERENCES dataset(id)    │
│     execution_time_ms           INTEGER                           │
│     search_type                 VARCHAR(20)                       │
│     user_feedback               VARCHAR(10)                       │
│     created_at                  TIMESTAMP DEFAULT NOW()            │
│     session_id                  VARCHAR(255)                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  ORGANIZATION                                   │
├─────────────────────────────────────────────────────────────────┤
│ PK  id                          SERIAL                            │
│     uri                         TEXT UNIQUE NOT NULL              │
│     code                        VARCHAR(50)                       │
│     name                        TEXT NOT NULL                     │
│     type                        VARCHAR(50)                       │
│     spatial_uri                 TEXT                              │
│     created_at                  TIMESTAMP DEFAULT NOW()            │
│     updated_at                  TIMESTAMP DEFAULT NOW()            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  THEME                                          │
├─────────────────────────────────────────────────────────────────┤
│ PK  id                          SERIAL                            │
│     uri                         TEXT UNIQUE NOT NULL              │
│     label_es                    TEXT NOT NULL                   │
│     label_en                    TEXT                              │
│     parent_uri                  TEXT REFERENCES theme(uri)      │
│     created_at                  TIMESTAMP DEFAULT NOW()            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  EVALUATION_RESULT                              │
├─────────────────────────────────────────────────────────────────┤
│ PK  id                          SERIAL                            │
│ FK  benchmark_query_id          INTEGER REFERENCES benchmark_query(id)│
│     metric_name                 VARCHAR(50) NOT NULL             │
│     metric_value                FLOAT NOT NULL                   │
│     model_name                  VARCHAR(100)                      │
│     parameters                  JSONB                             │
│     created_at                  TIMESTAMP DEFAULT NOW()            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 DESCRIPCIÓN DE ENTIDADES

### 1. DATASET (Principal)

Almacena los metadatos de cada dataset del catálogo.

**Cardinalidad:** 1 dataset → N distributions

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL | Identificador interno |
| `identifier` | VARCHAR(255) | Identificador único del dataset (UUID o URL) |
| `source_url` | TEXT | URL original en datos.gob.es |
| `title_es` | TEXT | Título en español |
| `title_en` | TEXT | Título en inglés (si existe) |
| `description_es` | TEXT | Descripción en español |
| `description_en` | TEXT | Descripción en inglés (si existe) |
| `embedding_text` | TEXT | Texto concatenado para generar embeddings |
| `metadata_vector` | VECTOR(384) | Vector de embeddings generado |
| `themes` | TEXT[] | Array de URIs de temas (DCAT-AP) |
| `keywords` | TEXT[] | Array de palabras clave extraídas |
| `spatial_uri` | TEXT | URI del territorio (País, CCAA, Provincia...) |
| `spatial_level` | VARCHAR(50) | Nivel territorial: país, autonomía, provincia, municipio |
| `spatial_name` | TEXT | Nombre legible del territorio |
| `publisher_uri` | TEXT | URI del organismo publicador |
| `publisher_name` | TEXT | Nombre del organismo publicador |
| `license_uri` | TEXT | URI de la licencia |
| `license_name` | TEXT | Nombre legible de la licencia |
| `temporal_coverage` | TEXT | Cobertura temporal del dataset |
| `accrual_periodicity` | VARCHAR(100) | Frecuencia de actualización |
| `issued` | DATE | Fecha de publicación |
| `modified` | DATE | Fecha de última modificación |
| `distributions` | JSONB | Distribuciones en formato JSON (alternativa a tabla separada) |
| `search_vector` | TSVECTOR | Índice para full-text search de PostgreSQL |
| `created_at` | TIMESTAMP | Fecha de creación en nuestra BD |
| `updated_at` | TIMESTAMP | Fecha de última actualización |
| `last_sync_at` | TIMESTAMP | Fecha de última sincronización con datos.gob.es |

---

### 2. DISTRIBUTION (Detalle)

Almacena las distribuciones/descargas de cada dataset.

**Cardinalidad:** Pertenece a 1 dataset

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL | Identificador interno |
| `dataset_id` | INTEGER | FK al dataset padre |
| `access_url` | TEXT | URL de acceso al recurso |
| `format` | VARCHAR(100) | Formato: CSV, JSON, XLSX, etc. |
| `format_type` | VARCHAR(50) | Tipo MIME |
| `title_es` | TEXT | Título de la distribución |
| `title_en` | TEXT | Título en inglés |
| `byte_size` | BIGINT | Tamaño en bytes |
| `download_url` | TEXT | URL directa de descarga |
| `description_es` | TEXT | Descripción en español |
| `description_en` | TEXT | Descripción en inglés |
| `issued` | DATE | Fecha de publicación |
| `modified` | DATE | Fecha de modificación |
| `license_uri` | TEXT | URI de licencia específica |

---

### 3. BENCHMARK_QUERY (Evaluación)

Almacena las queries de prueba para evaluar el sistema.

**Cardinalidad:** 1 query → N evaluation_results

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL | Identificador interno |
| `query_text` | TEXT | Texto de la query en lenguaje natural |
| `query_vector` | VECTOR(384) | Vector de la query para búsqueda semántica |
| `expected_dataset_ids` | INTEGER[] | IDs de datasets esperados como resultado |
| `category` | VARCHAR(100) | Categoría temática de la query |
| `difficulty` | VARCHAR(20) | fácil, medio, difícil |
| `created_at` | TIMESTAMP | Fecha de creación |
| `updated_at` | TIMESTAMP | Fecha de última actualización |

---

### 4. SEARCH_LOG (Logging)

Registra las búsquedas realizadas para análisis y mejora.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL | Identificador interno |
| `query_text` | TEXT | Texto buscado por el usuario |
| `query_vector` | VECTOR(384) | Vector de la query |
| `results_count` | INTEGER | Número de resultados devueltos |
| `top_result_id` | INTEGER | ID del primer resultado (si fue relevante) |
| `execution_time_ms` | INTEGER | Tiempo de ejecución en milisegundos |
| `search_type` | VARCHAR(20) | Tipo: semántica, léxica, híbrida |
| `user_feedback` | VARCHAR(10) | Feedback del usuario: positivo, negativo |
| `created_at` | TIMESTAMP | Fecha de la búsqueda |
| `session_id` | VARCHAR(255) | ID de sesión del usuario |

---

### 5. ORGANIZATION (Catálogo)

Catálogo de organismos publicadores normalizado.

**Cardinalidad:** Referenciada por N datasets

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL | Identificador interno |
| `uri` | TEXT | URI única del organismo en datos.gob.es |
| `code` | VARCHAR(50) | Cigo identificativo |
| `name` | TEXT | Nombre del organismo |
| `type` | VARCHAR(50) | Tipo: ministerio, ayuntamiento, comunidad autónoma... |
| `spatial_uri` | TEXT | URI del territorio al que pertenece |
| `created_at` | TIMESTAMP | Fecha de creación |
| `updated_at` | TIMESTAMP | Fecha de última actualización |

---

### 6. THEME (Catálogo)

Catálogo de temas según vocabulario controlado.

**Cardinalidad:** Referenciada por N datasets

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL | Identificador interno |
| `uri` | TEXT | URI única del tema |
| `label_es` | TEXT | Etiqueta en español |
| `label_en` | TEXT | Etiqueta en inglés |
| `parent_uri` | TEXT | URI del tema padre (jerarquía) |
| `created_at` | TIMESTAMP | Fecha de creación |

---

### 7. EVALUATION_RESULT (Métricas)

Resultados de las evaluaciones del sistema.

**Cardinalidad:** Pertenece a 1 benchmark_query

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL | Identificador interno |
| `benchmark_query_id` | INTEGER | FK a la query de benchmark |
| `metric_name` | VARCHAR(50) | Nombre de la métrica: precision@5, recall@10, ndcg, mrr |
| `metric_value` | FLOAT | Valor de la métrica (0-1) |
| `model_name` | VARCHAR(100) | Nombre del modelo evaluado |
| `parameters` | JSONB | Parámetros de la evaluación |
| `created_at` | TIMESTAMP | Fecha de la evaluación |

---

## 🔗 RELACIONES

```
DATASET ||--o{ DISTRIBUTION : "1:N"
DATASET }o--|| ORGANIZATION : "N:1"
DATASET }o--o{ THEME : "N:M"
BENCHMARK_QUERY ||--o{ EVALUATION_RESULT : "1:N"
SEARCH_LOG }o--|| DATASET : "N:1 (top_result)"
```

| Relación | Cardinalidad | Descripción |
|----------|-------------|-------------|
| Dataset → Distribution | 1:N | Un dataset tiene múltiples distribuciones |
| Dataset → Organization | N:1 | Múltiples datasets de un mismo organismo |
| Dataset → Theme | N:M | Un dataset puede tener múltiples temas |
| Benchmark_Query → Evaluation_Result | 1:N | Una query tiene múltiples métricas |
| Search_Log → Dataset | N:1 | Referencia al top result (opcional) |

---

## 📐 SQL DDL COMPLETO

```sql
-- Extensión para vectores
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- ENTIDAD PRINCIPAL: DATASET
-- ============================================
CREATE TABLE dataset (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(255) UNIQUE NOT NULL,
    source_url TEXT,
    
    -- Metadatos multilingües
    title_es TEXT NOT NULL,
    title_en TEXT,
    description_es TEXT,
    description_en TEXT,
    
    -- Campos para embeddings
    embedding_text TEXT,
    metadata_vector VECTOR(384),
    
    -- Categorización
    themes TEXT[],
    keywords TEXT[],
    
    -- Contexto geográfico
    spatial_uri TEXT,
    spatial_level VARCHAR(50),
    spatial_name TEXT,
    
    -- Publicador
    publisher_uri TEXT,
    publisher_name TEXT,
    
    -- Licencia y uso
    license_uri TEXT,
    license_name TEXT,
    
    -- Temporal
    temporal_coverage TEXT,
    accrual_periodicity VARCHAR(100),
    issued DATE,
    modified DATE,
    
    -- Distribuciones (formato JSON para flexibilidad)
    distributions JSONB,
    
    -- Búsqueda léxica
    search_vector TSVECTOR,
    
    -- Auditoría
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_sync_at TIMESTAMP
);

-- Índices para dataset
CREATE INDEX idx_dataset_vector ON dataset USING ivfflat (metadata_vector vector_cosine_ops);
CREATE INDEX idx_dataset_search ON dataset USING GIN (search_vector);
CREATE INDEX idx_dataset_themes ON dataset USING GIN (themes);
CREATE INDEX idx_dataset_keywords ON dataset USING GIN (keywords);
CREATE INDEX idx_dataset_spatial ON dataset (spatial_level, spatial_name);
CREATE INDEX idx_dataset_publisher ON dataset (publisher_name);
CREATE INDEX idx_dataset_issued ON dataset (issued);

-- Trigger para actualizar search_vector
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('spanish', COALESCE(NEW.title_es, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.title_en, '')), 'A') ||
        setweight(to_tsvector('spanish', COALESCE(NEW.description_es, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.description_en, '')), 'B') ||
        setweight(to_tsvector('spanish', COALESCE(array_to_string(NEW.keywords, ' '), '')), 'C') ||
        setweight(to_tsvector('spanish', COALESCE(NEW.spatial_name, '')), 'D') ||
        setweight(to_tsvector('spanish', COALESCE(NEW.publisher_name, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_search_vector
    BEFORE INSERT OR UPDATE ON dataset
    FOR EACH ROW
    EXECUTE FUNCTION update_search_vector();

-- ============================================
-- ENTIDAD: DISTRIBUTION
-- ============================================
CREATE TABLE distribution (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES dataset(id) ON DELETE CASCADE,
    access_url TEXT NOT NULL,
    format VARCHAR(100),
    format_type VARCHAR(50),
    title_es TEXT,
    title_en TEXT,
    byte_size BIGINT,
    download_url TEXT,
    description_es TEXT,
    description_en TEXT,
    issued DATE,
    modified DATE,
    license_uri TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_distribution_dataset ON distribution (dataset_id);
CREATE INDEX idx_distribution_format ON distribution (format);

-- ============================================
-- ENTIDAD: BENCHMARK_QUERY
-- ============================================
CREATE TABLE benchmark_query (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_vector VECTOR(384),
    expected_dataset_ids INTEGER[],
    category VARCHAR(100),
    difficulty VARCHAR(20) CHECK (difficulty IN ('fácil', 'medio', 'difícil')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_benchmark_query_vector ON benchmark_query USING ivfflat (query_vector vector_cosine_ops);
CREATE INDEX idx_benchmark_query_category ON benchmark_query (category);

-- ============================================
-- ENTIDAD: SEARCH_LOG
-- ============================================
CREATE TABLE search_log (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_vector VECTOR(384),
    results_count INTEGER,
    top_result_id INTEGER REFERENCES dataset(id),
    execution_time_ms INTEGER,
    search_type VARCHAR(20) CHECK (search_type IN ('semántica', 'léxica', 'híbrida')),
    user_feedback VARCHAR(10) CHECK (user_feedback IN ('positivo', 'negativo')),
    session_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_search_log_created ON search_log (created_at);
CREATE INDEX idx_search_log_session ON search_log (session_id);

-- ============================================
-- ENTIDAD: ORGANIZATION
-- ============================================
CREATE TABLE organization (
    id SERIAL PRIMARY KEY,
    uri TEXT UNIQUE NOT NULL,
    code VARCHAR(50),
    name TEXT NOT NULL,
    type VARCHAR(50),
    spatial_uri TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_organization_name ON organization (name);
CREATE INDEX idx_organization_type ON organization (type);

-- ============================================
-- ENTIDAD: THEME
-- ============================================
CREATE TABLE theme (
    id SERIAL PRIMARY KEY,
    uri TEXT UNIQUE NOT NULL,
    label_es TEXT NOT NULL,
    label_en TEXT,
    parent_uri TEXT REFERENCES theme(uri),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_theme_label ON theme (label_es);

-- ============================================
-- ENTIDAD: EVALUATION_RESULT
-- ============================================
CREATE TABLE evaluation_result (
    id SERIAL PRIMARY KEY,
    benchmark_query_id INTEGER REFERENCES benchmark_query(id) ON DELETE CASCADE,
    metric_name VARCHAR(50) NOT NULL,
    metric_value FLOAT NOT NULL,
    model_name VARCHAR(100),
    parameters JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_evaluation_query ON evaluation_result (benchmark_query_id);
CREATE INDEX idx_evaluation_metric ON evaluation_result (metric_name);
```

---

## 📊 DIAGRAMA DE FLUJO DE DATOS

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  datos.gob.es   │     │  Pipeline ETL    │     │   PostgreSQL    │
│   API CKAN      │────▶│  (Python)        │────▶│   + pgvector    │
│   Linked Data   │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                         │
                                                         │
                              ┌──────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   API FastAPI    │
                    │   (Backend)      │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Streamlit UI    │
                    │  (Frontend)      │
                    └──────────────────┘
```

---

## 🎯 DECISIONES DE DISEÑO

### 1. **JSONB vs Tablas Relacionales**
- **Distribuciones:** Usamos `JSONB` en `dataset` para flexibilidad, pero también tabla `distribution` para queries específicas
- **Razón:** Los formatos de distribución varían mucho entre datasets

### 2. **Índices Vectoriales**
- **pgvector con IVFFlat:** Eficiente para 10K+ vectores (384 dims)
- **Recomendación:** Para >100K vectores, considerar HNSW

### 3. **Full-Text Search**
- **TSVECTOR con pesos:** 
  - Peso A: títulos (máxima importancia)
  - Peso B: descripciones
  - Peso C: keywords
  - Peso D: spatial, publisher

### 4. **Normalización**
- **Organization y Theme:** Tablas separadas para evitar duplicación
- **Dataset:** Desnormalizado para queries rápidas (publisher_name vs publisher_uri)

---

## 📈 ESTIMACIÓN DE TAMAÑO

Con ~113.313 datasets (dato actual de datos.gob.es):

| Tabla | Registros | Tamaño estimado |
|-------|-----------|-----------------|
| dataset | ~113.000 | ~2 GB (incluyendo vectores) |
| distribution | ~300.000 | ~500 MB |
| search_log | ~10.000/día | ~1 GB/mes |
| benchmark_query | ~50 | ~1 MB |
| organization | ~5.000 | ~10 MB |
| theme | ~100 | ~1 MB |

**Total estimado:** ~5-10 GB con logs de 1 mes

---

*Documento vivo: Actualizar si cambian los requisitos o se detectan nuevos campos*
