# Arquitectura del Sistema

> **Nota:** Este documento ha sido consolidado en `AUDITORIA_BACKENDS_FRONTENDS.md` (2026-06-08).  
> Para información actualizada sobre componentes, ver [AUDITORIA_BACKENDS_FRONTENDS.md](AUDITORIA_BACKENDS_FRONTENDS.md).

---

## Diagrama de Componentes

```
┌─────────────────┐
│   Frontend      │  Streamlit / React
│   (Chatbot)     │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│   API REST      │  FastAPI
│   (FastAPI)     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│        Motor de Búsqueda            │
│  ┌─────────────┐  ┌─────────────┐   │
│  │  Búsqueda   │  │  Búsqueda   │   │
│  │  Semántica  │  │   Léxica    │   │
│  │  (pgvector) │  │  (PostgreSQL)│  │
│  └──────┬──────┘  └──────┬──────┘   │
│         │                │          │
│         └───────┬────────┘          │
│                 │                   │
│                 ▼                   │
│         ┌─────────────┐            │
│         │    Ranking    │            │
│         │   Híbrido    │            │
│         └──────┬──────┘            │
└────────────────┼────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│         Pipeline de Ingesta          │
│  ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │  CKAN   │ │ SPARQL  │ │ DCAT-AP│ │
│  │  API    │ │Endpoint │ │Parser  │ │
│  └────┬────┘ └────┬────┘ └───┬────┘ │
│       └───────────┴──────────┘      │
│                  │                   │
│                  ▼                   │
│         ┌─────────────┐            │
│         │ Normalización│            │
│         │  y Limpieza  │            │
│         └──────┬──────┘            │
│                │                    │
│                ▼                    │
│         ┌─────────────┐            │
│         │  Generación  │            │
│         │ Embeddings   │            │
│         └─────────────┘            │
└─────────────────────────────────────┘
```

## Flujo de Datos

1. **Ingesta**
   - Descarga de metadatos desde datos.gob.es
   - Normalización de campos (título, descripción, temas, etc.)
   - Generación de embeddings

2. **Almacenamiento**
   - PostgreSQL: metadatos estructurados
   - pgvector: índice de embeddings

3. **Búsqueda**
   - Query en lenguaje natural
   - Extracción de intención y entidades
   - Búsqueda semántica (embeddings) + léxica (full-text)
   - Ranking híbrido con scores combinados

4. **Respuesta**
   - Lista de datasets ordenada por relevancia
   - Explicación de por qué cada dataset es relevante
   - Metadatos: cobertura, formato, licencia, enlaces

## Estado Actual del Pipeline (Fase 03 — Sprint 1)

### Ingesta
- **Fuente:** datos.gob.es (API CKAN + DCAT-AP)
- **Datasets descargados:** 134.150
- **Datasets únicos tras deduplicación:** 87.677
- **Batches:** 135 archivos JSONL en `03_Sprint1_Ingesta/datos/raw/`

### Limpieza
Pipeline ejecutado vía `clean_datasets.py`:

| Métrica | Valor |
|---------|-------|
| Datasets procesados | 87.677 |
| Duplicados descartados | 46.473 (34,7%) |
| Territorios inferidos | 56.674 (64,6% venían vacíos) |
| Territorios únicos | 20 (todas las CCAA + Ceuta/Melilla) |
| Publishers únicos | 175 (todos con nombres legibles) |
| Temas únicos | 29 (códigos EUROVOC + URIs mapeados) |
| Formatos únicos | 45 |
| Tiempo de ejecución | ~7s |

**Archivos generados:**
- `datasets_clean.jsonl` — 378 MB (87.677 datasets)
- `sample_enriched.json` — 500 datasets para POC (2.5 MB)
- `cleaning_stats.json` — estadísticas completas

### Embeddings
- **Modelo:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Dimensiones:** 384D, L2-normalizados
- **Shape:** (87.677, 384)
- **Tiempo:** 18m 24s en CPU (~79 docs/s)
- **Archivo:** `embeddings.npy` — 129 MB
- **Metadatos:** `embeddings_meta.json`

---

## Decisiones Técnicas

- **PostgreSQL + pgvector**: Base de datos relacional con extensión vectorial
- **Sentence Transformers**: Modelo multilingüe para embeddings
- **FastAPI**: API moderna y rápida
- **Docker**: Contenerización para despliegue fácil
