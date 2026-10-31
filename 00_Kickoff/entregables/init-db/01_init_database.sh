#!/usr/bin/env bash
# =================================================================
# init-db/01_init_database.sh
# Script de inicialización de la base de datos PostgreSQL + pgvector
# Se ejecuta automáticamente al crear el contenedor
# =================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}============================================================${NC}"
echo -e "${YELLOW}INICIALIZACIÓN DE BASE DE DATOS PFM${NC}"
echo -e "${YELLOW}============================================================${NC}"
echo ""

# =================================================================
# 1. CREAR EXTENSIÓN PGVECTOR
# =================================================================
echo -e "${YELLOW}[1/6]${NC} Creando extensión pgvector..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOF'
    CREATE EXTENSION IF NOT EXISTS vector;
    
    -- Verificar versión
    SELECT * FROM pg_extension WHERE extname = 'vector';
EOF

echo -e "${GREEN}✓${NC} Extensión pgvector creada"
echo ""

# =================================================================
# 2. CREAR TABLAS PRINCIPALES
# =================================================================
echo -e "${YELLOW}[2/6]${NC} Creando tablas..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOF'
    -- ============================================
    -- TABLA: dataset (Entidad principal)
    -- ============================================
    CREATE TABLE IF NOT EXISTS dataset (
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
        spatial_level VARCHAR(50) CHECK (spatial_level IN ('país', 'autonomía', 'provincia', 'municipio')),
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
        
        -- Distribuciones (JSON para flexibilidad)
        distributions JSONB,
        
        -- Búsqueda léxica
        search_vector TSVECTOR,
        
        -- Auditoría
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        last_sync_at TIMESTAMP
    );

    -- ============================================
    -- TABLA: distribution
    -- ============================================
    CREATE TABLE IF NOT EXISTS distribution (
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

    -- ============================================
    -- TABLA: organization
    -- ============================================
    CREATE TABLE IF NOT EXISTS organization (
        id SERIAL PRIMARY KEY,
        uri TEXT UNIQUE NOT NULL,
        code VARCHAR(50),
        name TEXT NOT NULL,
        type VARCHAR(50),
        spatial_uri TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    -- ============================================
    -- TABLA: theme
    -- ============================================
    CREATE TABLE IF NOT EXISTS theme (
        id SERIAL PRIMARY KEY,
        uri TEXT UNIQUE NOT NULL,
        label_es TEXT NOT NULL,
        label_en TEXT,
        parent_uri TEXT REFERENCES theme(uri),
        created_at TIMESTAMP DEFAULT NOW()
    );

    -- ============================================
    -- TABLA: benchmark_query
    -- ============================================
    CREATE TABLE IF NOT EXISTS benchmark_query (
        id SERIAL PRIMARY KEY,
        query_text TEXT NOT NULL,
        query_vector VECTOR(384),
        expected_dataset_ids INTEGER[],
        category VARCHAR(100),
        difficulty VARCHAR(20) CHECK (difficulty IN ('fácil', 'medio', 'difícil')),
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    -- ============================================
    -- TABLA: search_log
    -- ============================================
    CREATE TABLE IF NOT EXISTS search_log (
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

    -- ============================================
    -- TABLA: evaluation_result
    -- ============================================
    CREATE TABLE IF NOT EXISTS evaluation_result (
        id SERIAL PRIMARY KEY,
        benchmark_query_id INTEGER REFERENCES benchmark_query(id) ON DELETE CASCADE,
        metric_name VARCHAR(50) NOT NULL,
        metric_value FLOAT NOT NULL,
        model_name VARCHAR(100),
        parameters JSONB,
        created_at TIMESTAMP DEFAULT NOW()
    );
EOF

echo -e "${GREEN}✓${NC} Tablas creadas"
echo ""

# =================================================================
# 3. CREAR ÍNDICES
# =================================================================
echo -e "${YELLOW}[3/6]${NC} Creando índices..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOF'
    -- Índices vectoriales (usando ivfflat para eficiencia)
    CREATE INDEX IF NOT EXISTS idx_dataset_vector ON dataset USING ivfflat (metadata_vector vector_cosine_ops);
    CREATE INDEX IF NOT EXISTS idx_benchmark_query_vector ON benchmark_query USING ivfflat (query_vector vector_cosine_ops);
    
    -- Índices de búsqueda léxica
    CREATE INDEX IF NOT EXISTS idx_dataset_search ON dataset USING GIN (search_vector);
    
    -- Índices para filtros comunes
    CREATE INDEX IF NOT EXISTS idx_dataset_themes ON dataset USING GIN (themes);
    CREATE INDEX IF NOT EXISTS idx_dataset_keywords ON dataset USING GIN (keywords);
    CREATE INDEX IF NOT EXISTS idx_dataset_spatial ON dataset (spatial_level, spatial_name);
    CREATE INDEX IF NOT EXISTS idx_dataset_publisher ON dataset (publisher_name);
    CREATE INDEX IF NOT EXISTS idx_dataset_issued ON dataset (issued);
    CREATE INDEX IF NOT EXISTS idx_dataset_identifier ON dataset (identifier);
    
    -- Índices para foreign keys
    CREATE INDEX IF NOT EXISTS idx_distribution_dataset ON distribution (dataset_id);
    CREATE INDEX IF NOT EXISTS idx_distribution_format ON distribution (format);
    CREATE INDEX IF NOT EXISTS idx_organization_name ON organization (name);
    CREATE INDEX IF NOT EXISTS idx_theme_label ON theme (label_es);
    CREATE INDEX IF NOT EXISTS idx_search_log_created ON search_log (created_at);
    CREATE INDEX IF NOT EXISTS idx_search_log_session ON search_log (session_id);
    CREATE INDEX IF NOT EXISTS idx_evaluation_query ON evaluation_result (benchmark_query_id);
    CREATE INDEX IF NOT EXISTS idx_evaluation_metric ON evaluation_result (metric_name);
EOF

echo -e "${GREEN}✓${NC} Índices creados"
echo ""

# =================================================================
# 4. CREAR TRIGGERS
# =================================================================
echo -e "${YELLOW}[4/6]${NC} Creando triggers..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOF'
    -- Trigger para actualizar search_vector automáticamente
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
        NEW.updated_at := NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS trigger_update_search_vector ON dataset;
    CREATE TRIGGER trigger_update_search_vector
        BEFORE INSERT OR UPDATE ON dataset
        FOR EACH ROW
        EXECUTE FUNCTION update_search_vector();

    -- Trigger para actualizar updated_at
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS trigger_dataset_updated ON dataset;
    CREATE TRIGGER trigger_dataset_updated
        BEFORE UPDATE ON dataset
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    
    DROP TRIGGER IF EXISTS trigger_organization_updated ON organization;
    CREATE TRIGGER trigger_organization_updated
        BEFORE UPDATE ON organization
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    
    DROP TRIGGER IF EXISTS trigger_benchmark_query_updated ON benchmark_query;
    CREATE TRIGGER trigger_benchmark_query_updated
        BEFORE UPDATE ON benchmark_query
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
EOF

echo -e "${GREEN}✓${NC} Triggers creados"
echo ""

# =================================================================
# 5. INSERTAR DATOS DE CONFIGURACIÓN
# =================================================================
echo -e "${YELLOW}[5/6]${NC} Insertando datos iniciales..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOF'
    -- Insertar temas del vocabulario de datos.gob.es
    INSERT INTO theme (uri, label_es, label_en) VALUES
        ('http://datos.gob.es/kos/sector-publico/sector/agricultura-pesca', 'Agricultura y pesca', 'Agriculture and fishing'),
        ('http://datos.gob.es/kos/sector-publico/sector/ciencia-tecnologia', 'Ciencia y tecnología', 'Science and technology'),
        ('http://datos.gob.es/kos/sector-publico/sector/comercio', 'Comercio', 'Commerce'),
        ('http://datos.gob.es/kos/sector-publico/sector/cultura-ocio', 'Cultura y ocio', 'Culture and leisure'),
        ('http://datos.gob.es/kos/sector-publico/sector/demografia', 'Demografía', 'Demography'),
        ('http://datos.gob.es/kos/sector-publico/sector/deporte', 'Deporte', 'Sports'),
        ('http://datos.gob.es/kos/sector-publico/sector/economia', 'Economía', 'Economy'),
        ('http://datos.gob.es/kos/sector-publico/sector/educacion', 'Educación', 'Education'),
        ('http://datos.gob.es/kos/sector-publico/sector/empleo', 'Empleo', 'Employment'),
        ('http://datos.gob.es/kos/sector-publico/sector/energia', 'Energía', 'Energy'),
        ('http://datos.gob.es/kos/sector-publico/sector/hacienda', 'Hacienda', 'Finance'),
        ('http://datos.gob.es/kos/sector-publico/sector/industria', 'Industria', 'Industry'),
        ('http://datos.gob.es/kos/sector-publico/sector/legislacion-justicia', 'Legislación y justicia', 'Legislation and justice'),
        ('http://datos.gob.es/kos/sector-publico/sector/medio-ambiente', 'Medio ambiente', 'Environment'),
        ('http://datos.gob.es/kos/sector-publico/sector/salud', 'Salud', 'Health'),
        ('http://datos.gob.es/kos/sector-publico/sector/sector-publico', 'Sector público', 'Public sector'),
        ('http://datos.gob.es/kos/sector-publico/sector/seguridad', 'Seguridad', 'Security'),
        ('http://datos.gob.es/kos/sector-publico/sector/sociedad', 'Sociedad', 'Society'),
        ('http://datos.gob.es/kos/sector-publico/sector/transporte', 'Transporte', 'Transport'),
        ('http://datos.gob.es/kos/sector-publico/sector/turismo', 'Turismo', 'Tourism'),
        ('http://datos.gob.es/kos/sector-publico/sector/urbanismo-infraestructuras', 'Urbanismo e infraestructuras', 'Urban planning and infrastructure')
    ON CONFLICT (uri) DO NOTHING;
    
    -- Insertar niveles territoriales comunes
    INSERT INTO organization (uri, code, name, type, spatial_uri) VALUES
        ('http://datos.gob.es/recurso/sector-publico/territorio/Pais/España', 'ES', 'España', 'país', NULL),
        ('http://datos.gob.es/recurso/sector-publico/territorio/Autonomia/Aragon', 'AR', 'Aragón', 'autonomía', 'http://datos.gob.es/recurso/sector-publico/territorio/Pais/España'),
        ('http://datos.gob.es/recurso/sector-publico/territorio/Autonomia/Cataluña', 'CT', 'Cataluña', 'autonomía', 'http://datos.gob.es/recurso/sector-publico/territorio/Pais/España'),
        ('http://datos.gob.es/recurso/sector-publico/territorio/Autonomia/Madrid', 'MD', 'Comunidad de Madrid', 'autonomía', 'http://datos.gob.es/recurso/sector-publico/territorio/Pais/España'),
        ('http://datos.gob.es/recurso/sector-publico/territorio/Autonomia/Castilla-Leon', 'CL', 'Castilla y León', 'autonomía', 'http://datos.gob.es/recurso/sector-publico/territorio/Pais/España')
    ON CONFLICT (uri) DO NOTHING;
EOF

echo -e "${GREEN}✓${NC} Datos iniciales insertados"
echo ""

# =================================================================
# 6. VERIFICACIÓN FINAL
# =================================================================
echo -e "${YELLOW}[6/6]${NC} Verificando instalación..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOF'
    -- Verificar tablas
    SELECT 'Tablas creadas: ' || COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    
    -- Verificar índices
    SELECT 'Índices creados: ' || COUNT(*) FROM pg_indexes WHERE schemaname = 'public';
    
    -- Verificar extensión pgvector
    SELECT 'Extensión pgvector: OK' WHERE EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector');
    
    -- Verificar datos iniciales
    SELECT 'Temas insertados: ' || COUNT(*) FROM theme;
    SELECT 'Organizaciones insertadas: ' || COUNT(*) FROM organization;
EOF

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}BASE DE DATOS INICIALIZADA CORRECTAMENTE${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "Base de datos: ${YELLOW}${POSTGRES_DB}${NC}"
echo -e "Usuario:       ${YELLOW}${POSTGRES_USER}${NC}"
echo -e "PostgreSQL:    ${YELLOW}15+${NC}"
echo -e "pgvector:      ${YELLOW}instalado${NC}"
echo ""
echo -e "Tablas creadas:"
echo -e "  • dataset${NC}"
echo -e "  • distribution${NC}"
echo -e "  • organization${NC}"
echo -e "  • theme${NC}"
echo -e "  • benchmark_query${NC}"
echo -e "  • search_log${NC}"
echo -e "  • evaluation_result${NC}"
echo ""
echo -e "${GREEN}✓ Listo para usar${NC}"
