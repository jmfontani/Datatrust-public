-- Migración 005: Tabla dataset_files — registro + índice léxico del contenido de los ficheros descargados
--
-- Propósito: indexar el contenido real de los 52.887 ficheros descargados en ~/datos
-- (60,3% del catálogo, 67 GB) para:
--   (A) Caso #15 nivel 2: dado un dataset_id, saber qué fichero cargar y su esquema (text-to-SQL).
--   (B) Mejorar el recall de la búsqueda léxica: indexar el contenido del fichero, no solo
--       title + description (el 72,5% de descripciones son <50 palabras).
--
-- C (embeddings semánticos del contenido) aplazado — ver plan/mini-experimento.
--
-- Fuente: 03_Sprint1_Ingesta/codigo/descarga_datos/{manifest.csv, manifest_sniff.csv}
-- Fecha: 2026-06-26

CREATE TABLE IF NOT EXISTS dataset_files (
    dataset_id    TEXT PRIMARY KEY,
    file_path     TEXT NOT NULL,
    format        VARCHAR(10) NOT NULL,      -- CSV/JSON/XLSX/XLS/TXT/ODS
    size_bytes    BIGINT,
    n_rows        BIGINT,
    n_columns     INTEGER,
    columns       JSONB,                     -- [{name, dtype, sample_values:[...]}]
    content_text  TEXT,                       -- representación textual para full-text (cap ~32KB)
    content_tsvector TSVECTOR,                -- índice léxico del contenido (to_tsvector spanish)
    source        VARCHAR(10),                 -- base / sniff
    status        VARCHAR(20) DEFAULT 'pending',  -- pending / done / schema_only / failed
    indexed_at    TIMESTAMPTZ DEFAULT NOW(),
    error         TEXT
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_dataset_files_format     ON dataset_files(format);
CREATE INDEX IF NOT EXISTS idx_dataset_files_content_ts ON dataset_files USING GIN(content_tsvector);
CREATE INDEX IF NOT EXISTS idx_dataset_files_source     ON dataset_files(source);

-- Comentarios
COMMENT ON TABLE dataset_files IS 'Registro + índice léxico del contenido de los ficheros descargados (caso #15)';
COMMENT ON COLUMN dataset_files.file_path IS 'Ruta absoluta del fichero en ~/datos/<format>/<id>.<ext>';
COMMENT ON COLUMN dataset_files.columns IS 'Esquema: [{name, dtype, sample_values}] extraído con pandas';
COMMENT ON COLUMN dataset_files.content_text IS 'Header + muestra de filas (cap 32KB) para full-text; NULL si >5MB (schema_only)';
COMMENT ON COLUMN dataset_files.content_tsvector IS 'to_tsvector(''spanish'', content_text) — búsqueda léxica sobre el contenido real';
COMMENT ON COLUMN dataset_files.status IS 'pending (sin indexar) / done (con contenido) / schema_only (>5MB, solo esquema) / failed';

-- Vista resumen
CREATE OR REPLACE VIEW v_dataset_files_summary AS
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE status='done') AS done,
    COUNT(*) FILTER (WHERE status='schema_only') AS schema_only,
    COUNT(*) FILTER (WHERE status='failed') AS failed,
    COUNT(*) FILTER (WHERE status='pending') AS pending,
    COUNT(*) FILTER (WHERE content_tsvector IS NOT NULL) AS with_tsvector,
    COUNT(*) FILTER (WHERE n_columns IS NOT NULL) AS with_schema,
    pg_size_pretty(SUM(COALESCE(size_bytes,0))) AS total_file_bytes
FROM dataset_files;

-- Función de búsqueda léxica sobre el contenido (B) — lista datasets cuyo contenido coincide
CREATE OR REPLACE FUNCTION search_by_content(
    q TEXT,
    limit_results INTEGER DEFAULT 20
) RETURNS TABLE (
    dataset_id TEXT,
    file_path TEXT,
    format VARCHAR,
    ts_rank FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        df.dataset_id,
        df.file_path,
        df.format,
        ts_rank(df.content_tsvector, query) AS ts_rank
    FROM dataset_files df, to_tsquery('spanish', q) AS query
    WHERE df.content_tsvector @@ query
    ORDER BY ts_rank DESC
    LIMIT limit_results;
END;
$$ LANGUAGE plpgsql;