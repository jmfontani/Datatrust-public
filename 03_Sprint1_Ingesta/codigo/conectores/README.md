# Script de Ingesta - datos.gob.es

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `ingest_datos_gob.py` | Script principal de ingesta masiva |
| `test_api.py` | Test rápido de conectividad y estructura |
| `README_INGESTA.md` | Este documento |

## API Utilizada

**Linked Data API** de datos.gob.es (no CKAN tradicional)
- URL: `https://datos.gob.es/apidata/catalog/dataset.json`
- Formato: JSON con paginación (`_page`, `_pageSize`)
- Estructura: DCAT-AP con campos multilingües

## Uso

### Test rápido (recomendado antes de ingesta)
```bash
python3 test_api.py
```

### Ingesta completa
```bash
# Ingestar todos los datasets
python3 ingest_datos_gob.py --output ../../data/raw/

# Ingestar solo 1000 datasets
python3 ingest_datos_gob.py --limit 1000 --output ../../data/raw/

# Reanudar ingesta interrumpida
python3 ingest_datos_gob.py --resume --output ../../data/raw/

# Configurar tamaño de batch
python3 ingest_datos_gob.py --limit 5000 --batch-size 1000 --output ../../data/raw/
```

### Opciones

| Opción | Descripción | Default |
|--------|-------------|---------|
| `--output, -o` | Directorio de salida | `../data/raw/` |
| `--limit, -l` | Máximo de datasets | Todos |
| `--resume, -r` | Reanudar ingesta | `false` |
| `--batch-size, -b` | Datasets por archivo | `500` |
| `--page-size, -p` | Datasets por página API | `100` |
| `--format, -f` | `jsonl` o `json` | `jsonl` |
| `--verbose, -v` | Logs detallados | `false` |

## Salida

### Formato JSONL
Cada línea es un dataset JSON:
```json
{"identifier": "...", "title_es": "...", "embedding_text": "...", ...}
```

### Archivos generados
```
data/raw/
├── batch_0000.jsonl     # 500 datasets
├── batch_0001.jsonl     # 500 datasets
├── .ingest_state.json   # Estado para reanudación
└── ...
```

## Estado de reanudación

El archivo `.ingest_state.json` guarda el progreso:
```json
{
  "page": 15,
  "batch_num": 3,
  "total_ingested": 1500,
  "errors": 0,
  "completed": false,
  "last_update": "2026-05-21T18:00:00"
}
```

Para reanudar: `python3 ingest_datos_gob.py --resume`

## Estructura del Dataset Normalizado

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `identifier` | string | UUID del dataset |
| `source_url` | string | URL del dataset en datos.gob.es |
| `title_es` | string | Título en español |
| `title_en` | string | Título en inglés |
| `description_es` | string | Descripción en español |
| `description_en` | string | Descripción en inglés |
| `embedding_text` | string | Texto concatenado para embeddings |
| `metadata_vector` | null | Reservado para embeddings (paso posterior) |
| `themes` | string[] | Temas DCAT normalizados |
| `keywords` | string[] | Keywords del dataset |
| `spatial_uri` | string | URI de territorio |
| `spatial_level` | string | `pais`, `autonomia`, `provincia`, `municipio` |
| `spatial_name` | string | Nombre del territorio |
| `publisher_uri` | string | URI del organismo |
| `publisher_name` | string | Código del organismo |
| `license_uri` | string | URI de licencia |
| `license_name` | string | Nombre de licencia |
| `distributions` | object[] | Formatos y URLs de descarga |
| `search_text` | string | Texto para búsqueda léxica |
| `ingested_at` | string | Timestamp ISO 8601 |

## Consideraciones

- **Sin dependencias**: Solo usa librerías estándar de Python
- **Rate limiting**: 0.5s entre requests para no saturar la API
- **Retry automático**: Reintentos con backoff exponencial
- **Manejo de errores**: Continúa con el siguiente dataset si falla uno
- **Campos multilingües**: Extrae `_value` según `_lang` (es/en)
