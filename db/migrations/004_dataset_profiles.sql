-- Migración 004: Tabla dataset_profiles para Sprint 8 (Paquete A: #5 + #14)
--
-- Propósito: Almacenar perfiles precalculados de datasets para:
--   #14: Resúmenes TL;DR (2-3 frases)
--   #5:  Detección de datasets complementarios
--
-- Fecha: 2026-06-12

-- Tabla principal de perfiles
CREATE TABLE IF NOT EXISTS dataset_profiles (
    dataset_id TEXT PRIMARY KEY,

    -- #14: TL;DR (resumen ejecutivo)
    tldr TEXT,
    tldr_generated_at TIMESTAMPTZ,

    -- #5: Perfil para complementariedad
    variables_key TEXT[],           -- Variables detectadas (ej: ["paro", "desempleo", "tasa"])
    temporal_coverage TEXT,         -- Cobertura temporal (ej: "2005-2023", "mensual")
    geographic_level TEXT,          -- Nivel geográfico (ej: "nacional", "autonómico", "municipal")
    geographic_entity TEXT,         -- Entidad específica (ej: "Canarias", "España")

    -- Metadatos técnicos para matching
    formatos TEXT[],                -- Formatos disponibles (ej: ["CSV", "JSON", "XML"])
    frecuencia TEXT,                -- Frecuencia de actualización (ej: "mensual", "anual")
    tema_principal TEXT,            -- Tema DCAT principal

    -- #5: Datasets complementarios (precalculado offline)
    combinable_with TEXT[],         -- IDs de datasets complementarios
    combinable_score NUMERIC(3,2),  -- Score de complementariedad (0-1)

    -- Metadatos de generación
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    profile_version INTEGER DEFAULT 1
);

-- Índices para búsquedas eficientes
CREATE INDEX IF NOT EXISTS idx_dataset_profiles_tema ON dataset_profiles(tema_principal);
CREATE INDEX IF NOT EXISTS idx_dataset_profiles_geographic ON dataset_profiles(geographic_level);
CREATE INDEX IF NOT EXISTS idx_dataset_profiles_temporal ON dataset_profiles(temporal_coverage);
CREATE INDEX IF NOT EXISTS idx_dataset_profiles_variables ON dataset_profiles USING GIN(variables_key);
CREATE INDEX IF NOT EXISTS idx_dataset_profiles_combinable ON dataset_profiles USING GIN(combinable_with);

-- Comentario descriptivo
COMMENT ON TABLE dataset_profiles IS 'Perfiles precalculados de datasets para Sprint 8 (TL;DR + Complementariedad)';
COMMENT ON COLUMN dataset_profiles.tldr IS 'Resumen ejecutivo de 2-3 frases generado por LLM';
COMMENT ON COLUMN dataset_profiles.variables_key IS 'Palabras clave extraídas del título/descripción para matching';
COMMENT ON COLUMN dataset_profiles.combinable_with IS 'IDs de datasets que pueden combinarse analíticamente';
COMMENT ON COLUMN dataset_profiles.combinable_score IS 'Score de confianza de la complementariedad (0-1)';

-- Vista para debugging
CREATE OR REPLACE VIEW v_dataset_profiles_summary AS
SELECT
    COUNT(*) as total_profiles,
    COUNT(tldr) as with_tldr,
    COUNT(combinable_with) as with_combinations,
    AVG(array_length(combinable_with, 1)) FILTER (WHERE combinable_with IS NOT NULL) as avg_combinations
FROM dataset_profiles;
