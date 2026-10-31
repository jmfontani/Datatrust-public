# Arquitectura de Almacenamiento — Fase 05

## Estado actual (PoC)

El motor de búsqueda funciona con **almacenamiento en memoria** usando NumPy para los embeddings y diccionarios Python para los índices léxicos y facetados.

| Componente | Tecnología | Persistencia |
|---|---|---|
| Embeddings | NumPy array en memoria | `data/embeddings.npy` (archivo binario) |
| Índice léxico (BM25) | Diccionario Python en memoria | Reconstruido al arrancar |
| Índices facetados | Sets Python en memoria | Reconstruidos al arrancar |
| Metadatos de datasets | Lista de diccionarios en memoria | `data/datasets.jsonl` |

### Ventajas del enfoque actual
- **Simplicidad**: Sin dependencias de base de datos
- **Velocidad**: ~105ms por consulta (sin latencia de red)
- **Portabilidad**: Un solo proceso Python, fácil de desplegar

### Limitaciones
- **RAM**: Toda la base de datos debe caber en memoria (~500MB para 87K datasets)
- **Escalabilidad**: No escala horizontalmente
- **Concurrencia**: Un solo proceso sirve todas las peticiones
- **Persistencia de índices**: Los índices léxicos se reconstruyen al arrancar (lento)
- **Consultas SQL**: No se pueden hacer consultas complejas sobre metadatos

---

## Roadmap: Migración a PostgreSQL + pgvector

### ¿Por qué PostgreSQL + pgvector?

| Requisito | NumPy (PoC) | PostgreSQL + pgvector |
|---|---|---|
| **Escalabilidad** | Limitada a RAM | Ilimitada (disco + índices) |
| **Persistencia** | Archivos .npy | Base de datos relacional |
| **Concurrencia** | Single-process | Multi-conexión nativa |
| **Consultas complejas** | No | SQL + joins + agregaciones |
| **Filtros facetados** | Sets en memoria | Índices B-tree + WHERE |
| **Backup/restore** | Manual | pg_dump / pg_restore |
| **Transacciones** | No | ACID |
| **Replicación** | No | Streaming replication |

### Plan de migración

#### Fase 1: Schema y datos (Sprint posterior)
```sql
-- Tabla principal de datasets
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    identifier TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    publisher_name TEXT,
    theme_labels TEXT[],
    spatial_name TEXT,
    format_labels TEXT[],
    embedding VECTOR(384),  -- extensión pgvector
    metadata JSONB
);

-- Índices
CREATE INDEX idx_datasets_embedding ON datasets 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
CREATE INDEX idx_datasets_theme ON datasets USING GIN(theme_labels);
CREATE INDEX idx_datasets_spatial ON datasets(spatial_name);
CREATE INDEX idx_datasets_publisher ON datasets(publisher_name);
```

#### Fase 2: Motor híbrido adaptado
```python
# Pseudocódigo del motor con pgvector
async def search_postgres(query, top_k=10, filters=None):
    # 1. Generar embedding de la query
    query_embedding = model.encode(query)
    
    # 2. Búsqueda semántica en PostgreSQL
    semantic_results = await pg.fetch("""
        SELECT id, title, description, 
               1 - (embedding <=> $1) as cosine_sim
        FROM datasets
        WHERE 1 - (embedding <=> $1) > 0.2
        ORDER BY embedding <=> $1
        LIMIT $2
    """, query_embedding, top_k * 3)
    
    # 3. Búsqueda léxica con tsvector
    lexical_results = await pg.fetch("""
        SELECT id, title, description,
               ts_rank(search_vector, plainto_tsquery('spanish', $1)) as rank
        FROM datasets
        WHERE search_vector @@ plainto_tsquery('spanish', $1)
        ORDER BY rank DESC
        LIMIT $2
    """, query, top_k * 3)
    
    # 4. Combinar (misma lógica que ahora)
    return combine_and_rank(semantic_results, lexical_results)
```

#### Fase 3: Dockerización
```yaml
# docker-compose.yml (futuro)
services:
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: buscador
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  api:
    build: ./api
    environment:
      DATABASE_URL: postgresql://app:${DB_PASSWORD}@postgres:5432/buscador
    depends_on:
      - postgres
    ports:
      - "8000:8000"
```

### Timeline estimado

| Fase | Duración | Actividades |
|---|---|---|
| **1. Schema** | 2-3 días | Diseño tablas, migración datos, índices pgvector |
| **2. Motor** | 3-4 días | Adaptar search_engine.py, tests de regresión |
| **3. Docker** | 1-2 días | docker-compose, healthchecks, volumen persistente |
| **4. Validación** | 2-3 días | Benchmark vs. NumPy, validar métricas |
| **Total** | **1-1.5 semanas** | |

---

## Comparativa técnica detallada

### Rendimiento (estimado)

| Escenario | NumPy | PostgreSQL + pgvector (HNSW) |
|---|---|---|
| 87K datasets | ~105ms | ~50-80ms (con índice HNSW) |
| 500K datasets | No soportado | ~80-120ms |
| 1M datasets | No soportado | ~100-150ms |
| Cold start | ~10s (cargar .npy) | Instantáneo (BBDD persistente) |

### Coste computacional

| Recurso | NumPy | PostgreSQL |
|---|---|---|
| RAM | ~500MB fijos | ~100MB base + caché |
| CPU | 100% durante búsqueda | Escalable con conexiones |
| Disco | ~200MB (embeddings) | ~1GB (datos + índices) |

---

## Decisiones de diseño

### ¿Por qué no migrar ahora?
1. **Velocidad de desarrollo**: NumPy permite iterar rápido en el algoritmo
2. **Suficiente para el TFM**: 87K datasets caben en memoria, rendimiento aceptable
3. **Prioridad académica**: Es más valioso validar la búsqueda híbrica que la infraestructura
4. **Riesgo**: Migrar ahora introduciría complejidad sin beneficio inmediato

### ¿Cuándo migrar?
- **Post-entrega del TFM**: Como trabajo de mantenimiento
- **Si se escala a >200K datasets**: NumPy se vuelve inviable
- **Si se necesita alta disponibilidad**: PostgreSQL con replicación
- **Integración con otros servicios**: Que ya usen PostgreSQL

---

## Referencias

- [pgvector — extensión PostgreSQL para vectores](https://github.com/pgvector/pgvector)
- [Índices HNSW en pgvector](https://github.com/pgvector/pgvector#hnsw)
- [FAISS vs pgvector benchmark](https://medium.com/@stephenmbam/pgvector-vs-faiss-performance-comparison-771545d74285)
- [Arquitectura original del proyecto](https://github.com/fonta99/pfm_buscador_semantico)

---

*Documento creado: 2026-05-24*  
*Estado: Arquitectura PoC documentada, roadmap a PostgreSQL definido*