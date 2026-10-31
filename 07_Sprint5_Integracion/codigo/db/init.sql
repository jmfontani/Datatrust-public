-- Schema PostgreSQL + pgvector para Buscador Semántico
-- Fase 07: Sprint 5 - Integración y Despliegue

-- Habilitar extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla principal de datasets
CREATE TABLE IF NOT EXISTS datasets (
    id SERIAL PRIMARY KEY,
    dataset_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT,
    description TEXT,
    publisher VARCHAR(500),
    publisher_id VARCHAR(255),
    theme VARCHAR(255),
    theme_label VARCHAR(500),
    territory VARCHAR(255),
    territory_label VARCHAR(500),
    format VARCHAR(50),
    language VARCHAR(10),
    license VARCHAR(255),
    frequency VARCHAR(50),
    temporal_coverage VARCHAR(255),
    url VARCHAR(1000),
    keywords TEXT,
    tags TEXT,
    embedding VECTOR(384),           -- Embeddings semánticos (384D)
    search_vector TSVECTOR,          -- Índice de texto para búsqueda léxica
    raw_metadata JSONB,              -- Metadatos originales completos
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice HNSW para búsqueda semántica (cosine similarity)
CREATE INDEX IF NOT EXISTS idx_datasets_embedding_hnsw 
ON datasets USING hnsw (embedding vector_cosine_ops);

-- Índice GIN para búsqueda léxica (full-text search)
CREATE INDEX IF NOT EXISTS idx_datasets_search_vector 
ON datasets USING GIN(search_vector);

-- Índices B-tree para filtros facetados
CREATE INDEX IF NOT EXISTS idx_datasets_theme ON datasets(theme);
CREATE INDEX IF NOT EXISTS idx_datasets_territory ON datasets(territory);
CREATE INDEX IF NOT EXISTS idx_datasets_format ON datasets(format);
CREATE INDEX IF NOT EXISTS idx_datasets_publisher ON datasets(publisher);
CREATE INDEX IF NOT EXISTS idx_datasets_language ON datasets(language);

-- Índice compuesto para combinaciones comunes de filtros
CREATE INDEX IF NOT EXISTS idx_datasets_theme_territory 
ON datasets(theme, territory);

-- Tabla para sinónimos de términos (expansión de queries)
CREATE TABLE IF NOT EXISTS term_synonyms (
    id SERIAL PRIMARY KEY,
    term VARCHAR(255) NOT NULL,
    synonym VARCHAR(255) NOT NULL,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(term, synonym)
);

-- Tabla para logs de búsqueda (análisis de uso)
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    query_vector VECTOR(384),
    results_count INTEGER,
    response_time_ms FLOAT,
    filters_used JSONB,
    user_ip INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para query_logs
CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON query_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_query_logs_query ON query_logs USING GIN(to_tsvector('spanish', query));

-- Función para búsqueda semántica con filtros
CREATE OR REPLACE FUNCTION search_datasets_semantic(
    query_embedding VECTOR(384),
    filter_theme VARCHAR DEFAULT NULL,
    filter_territory VARCHAR DEFAULT NULL,
    filter_format VARCHAR DEFAULT NULL,
    limit_results INTEGER DEFAULT 10
) RETURNS TABLE (
    id INTEGER,
    dataset_id VARCHAR,
    title TEXT,
    description TEXT,
    publisher VARCHAR,
    theme VARCHAR,
    territory VARCHAR,
    format VARCHAR,
    similarity FLOAT,
    raw_metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id,
        d.dataset_id,
        d.title,
        d.description,
        d.publisher,
        d.theme,
        d.territory,
        d.format,
        1 - (d.embedding <=> query_embedding) AS similarity,
        d.raw_metadata
    FROM datasets d
    WHERE d.embedding IS NOT NULL
        AND (filter_theme IS NULL OR d.theme = filter_theme)
        AND (filter_territory IS NULL OR d.territory = filter_territory)
        AND (filter_format IS NULL OR d.format = filter_format)
    ORDER BY d.embedding <=> query_embedding
    LIMIT limit_results;
END;
$$ LANGUAGE plpgsql;

-- Función para búsqueda léxica con tsquery
CREATE OR REPLACE FUNCTION search_datasets_lexical(
    query_text TEXT,
    filter_theme VARCHAR DEFAULT NULL,
    filter_territory VARCHAR DEFAULT NULL,
    limit_results INTEGER DEFAULT 10
) RETURNS TABLE (
    id INTEGER,
    dataset_id VARCHAR,
    title TEXT,
    description TEXT,
    publisher VARCHAR,
    theme VARCHAR,
    territory VARCHAR,
    format VARCHAR,
    rank FLOAT,
    raw_metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id,
        d.dataset_id,
        d.title,
        d.description,
        d.publisher,
        d.theme,
        d.territory,
        d.format,
        ts_rank(d.search_vector, plainto_tsquery('spanish', query_text)) AS rank,
        d.raw_metadata
    FROM datasets d
    WHERE d.search_vector @@ plainto_tsquery('spanish', query_text)
        AND (filter_theme IS NULL OR d.theme = filter_theme)
        AND (filter_territory IS NULL OR d.territory = filter_territory)
    ORDER BY ts_rank(d.search_vector, plainto_tsquery('spanish', query_text)) DESC
    LIMIT limit_results;
END;
$$ LANGUAGE plpgsql;

-- Comentarios para documentación
COMMENT ON TABLE datasets IS 'Tabla principal con todos los datasets indexados';
COMMENT ON COLUMN datasets.embedding IS 'Vector de embeddings semánticos (384 dimensiones)';
COMMENT ON COLUMN datasets.search_vector IS 'Índice tsvector para búsqueda léxica en español';
