# Fase 03: Sprint 1 — Ingesta y Limpieza

## Proyecto: Buscador Semántico de Datasets Públicos
**Estado:** ✅ COMPLETADA
**Última actualización:** 2026-05-23

---

## ✅ Completado

### 1. Ingesta de datos (datos.gob.es)
- **134.150 datasets** descargados vía API CKAN
- 135 batches JSONL en `datos/raw/`
- Scripts: `ingest_datos_gob.py`, `ingest_datos_gob_v2.py` (con anti-duplicados)
- Ficha técnica documentada en `docs/ficha_tecnica_datos_gob_es.md`

### 2. Limpieza de datos
- **87.677 datasets únicos** (de 134.150 raw → 46.473 duplicados descartados)
- Pipeline: `codigo/limpieza/clean_datasets.py`
- Resultados en `datos/processed/datasets_clean.jsonl` (378 MB)

#### Normalizaciones aplicadas:
| Operación | Resultado |
|-----------|-----------|
| `spatial_name` inferido | 64,6% inferidos desde texto → 100% completos |
| Territorios normalizados | Fusionados duplicados/typos → 20 CCAA únicos |
| Publishers | Códigos → nombres legibles (175 únicos) |
| Formatos | URI MIME → etiquetas cortas (45 tipos) |
| Temas | URI + códigos EUROVOC → labels legibles (29 temas) |
| `embedding_text` | Reconstruido enriquecido con territorio y publisher |
| Fechas | Normalizadas a ISO 8601 |
| Keywords | Deduplicadas |

#### Top territorios:
| Territorio | Datasets |
|------------|----------|
| Canarias | 23.489 |
| España | 20.622 |
| Illes Balears | 14.005 |
| País Vasco | 12.912 |
| Aragón | 2.658 |
| Cataluña | 2.300 |
| Navarra | 2.275 |
| Comunidad de Madrid | 2.018 |
| Andalucía | 1.986 |
| Comunitat Valenciana | 1.048 |
| Castilla y León | 967 |
| Región de Murcia | 933 |
| Galicia | 614 |
| Asturias | 535 |
| Castilla-La Mancha | 406 |
| Cantabria | 339 |
| Extremadura | 269 |
| La Rioja | 181 |
| Melilla | 70 |
| Ceuta | 50 |

#### Top publishers:
| Publisher | Datasets |
|-----------|----------|
| ISTAC - Gobierno de Canarias | 21.639 |
| INE - Instituto Nacional de Estadística | 14.167 |
| Gobierno Vasco (Open Data Euskadi) | 9.064 |
| Congreso de los Diputados | 4.346 |
| Comunidad de Madrid | 3.792 |
| Ministerio de Agricultura, Pesca y Alimentación | 2.828 |
| Ministerio de Transportes y Movilidad Sostenible | 2.552 |
| IAEST - Gobierno de Aragón | 2.015 |
| Gobierno de Navarra | 1.868 |
| Ayto. de Lasarte-Oria | 1.830 |

#### Top temas:
| Tema | Datasets |
|------|----------|
| sector publico | 22.802 |
| demografia | 14.946 |
| empleo | 12.543 |
| sociedad bienestar | 8.142 |
| medio ambiente | 8.019 |
| hacienda | 7.209 |
| economia | 6.640 |
| legislacion justicia | 5.512 |
| educacion | 5.092 |
| salud | 5.073 |

### 3. Generación de embeddings
- **Modelo:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Dimensiones:** 384D, L2-normalizados
- **Shape:** (87.677, 384)
- **Tiempo:** 18m 24s en CPU (~79 docs/s)
- **Output:** `datos/processed/embeddings.npy` (129 MB)
- **Metadatos:** `datos/processed/embeddings_meta.json`
- **Script:** `codigo/limpieza/generate_embeddings.py`

---

## ✅ Validación DCAT-AP-ES Completada

### 4. Validación de cumplimiento de estándar
- Script: `codigo/validacion/validate_dcat_ap_es.py`
- Reporte: `datos/processed/dcat_validation_report.json` (generado al ejecutar)
- **Cobertura**: 13/16 campos DCAT-AP-ES (81%)
- **Sin impacto en flujo**: Solo documentación, NO filtra datasets

**Uso**:
```bash
cd codigo/validacion/
python validate_dcat_ap_es.py \
    --input ../../datos/processed/datasets_clean.jsonl \
    --output ../../datos/processed/dcat_validation_report.json
```

**Nota**: El validador documenta el estado de cumplimiento sin modificar los datos, permitiendo decidir posteriormente si filtrar datasets no conformes.

## 🔜 Pendiente (Fase 04)

### 5. Crear índices de búsqueda
- Índice inverso tema → IDs
- Índice inverso territorio → IDs
- Mapa ID → posición en embeddings

### 6. Actualizar POC con datos limpios
- Regenerar embeddings del POC desde `sample_enriched.json`
- Verificar filtros con todos los territorios

---

## Rendimiento del pipeline

| Paso | Tiempo | Throughput |
|------|--------|------------|
| Carga 135 batches | ~2s | 134.150 datasets |
| Limpieza + deduplicación | ~7s | 19.164 datasets/s |
| Embeddings (CPU) | 18m 24s | 79 docs/s |
| **Total pipeline** | **~18m 33s** | — |

---

## Estructura de archivos

```
03_Sprint1_Ingesta/
├── README_03_Sprint1_Ingesta.md          # ← este documento
├── codigo/
│   ├── conectores/
│   │   ├── ingest_datos_gob.py           # V1 sin anti-duplicados
│   │   ├── ingest_datos_gob_v2.py        # V2 con anti-duplicados
│   │   ├── test_api.py                   # Test de conectividad
│   │   └── README.md
│   └── limpieza/
│       ├── clean_datasets.py             # Pipeline de limpieza
│       └── generate_embeddings.py        # Generador de embeddings
├── datos/
│   └── raw/                              # 135 archivos JSONL (134k datasets)
│   └── processed/
│       ├── datasets_clean.jsonl          # 87.677 datasets limpios (378 MB)
│       ├── sample_enriched.json          # Muestra 500 datasets (2.5 MB)
│       ├── embeddings.npy                # Embeddings 87.677 × 384 (129 MB)
│       ├── embeddings_meta.json          # Metadatos del modelo
│       └── cleaning_stats.json           # Estadísticas completas
└── docs/
    └── ficha_tecnica_datos_gob_es.md     # Documentación API datos.gob.es
```

---

## Métricas de calidad

| Métrica | Valor |
|---------|-------|
| Datasets únicos / raw | 87.677 / 134.150 (65,3%) |
| Duplicados descartados | 46.473 (34,7%) |
| Territorios completos | 100% (56.674 inferidos) |
| Publishers resueltos | 100% (175 únicos, todos con nombre legible) |
| Temas mapeados | 100% (29 temas, códigos EUROVOC → labels) |
| Formatos normalizados | 45 tipos distintos |
| Embeddings generados | 87.677 / 87.677 (100%) |

---

## Decisiones técnicas

1. **Spatial inference**: Cuando `spatial_name` viene vacío (~65%), se infiere desde publisher + título + descripción usando patrones por CCAA.
2. **Publisher codes → nombres**: Mapeo manual de 82 códigos + fallback por prefijo (`A01` → "Junta de Andalucía", `E0` → "Organismo Estatal", etc.).
3. **Temas EUROVOC**: Códigos cortos (`ENVI`, `GOVE`, `TRAN`) mapeados a etiquetas legibles en español.
4. **Formatos MIME**: Normalización de URIs a etiquetas cortas (`CSV`, `JSON`, `XLSX`, etc.).
5. **Deduplicación**: Por `identifier` único del dataset, descartando duplicados exactos.

---

## Notas

- El dataset limpio (`datasets_clean.jsonl`) es la fuente de verdad para las siguientes fases.
- Los embeddings (`embeddings.npy`) están L2-normalizados: dot product = cosine similarity.
- La muestra (`sample_enriched.json`) contiene 500 datasets representativos para testing.
- Stats completos disponibles en `cleaning_stats.json`.

---

## 📋 DCAT-AP-ES: Perfil de Metadatos

Este proyecto consume datos del catálogo **datos.gob.es**, que implementa el perfil **DCAT-AP-ES** para descripción de datasets abiertos en España.

### ¿Qué es DCAT-AP-ES?

**DCAT-AP-ES** es el perfil español basado en **DCAT-AP** (Data Catalog Vocabulary - Application Profile), el estándar europeo para describir conjuntos de datos abiertos. Define los metadatos obligatorios, recomendados y opcionales para catalogación de datos públicos.

- **Especificación**: https://datosgobes.github.io/DCAT-AP-ES/
- **Estándar base**: DCAT-AP (Unión Europea)
- **Formato**: JSON-LD (Linked Data API)

### API de datos.gob.es

El proyecto consume datos a través de la **Linked Data API v0.2**:

```
https://datos.gob.es/apidata/catalog/dataset.json
```

**Características**:
- Paginación: `_page` y `_pageSize` (máx 100/página)
- Respuesta: JSON-LD con contexto DCAT
- Campos multilingües: `_value` + `_lang` (es/en)
- Total descargado: **134.150 datasets**

### Mapeo de Campos DCAT-AP-ES

| Campo DCAT-AP-ES | Campo en Proyecto | Descripción | Obligatoriedad |
|-------------------|-------------------|-------------|----------------|
| `dct:identifier` | `identifier` | ID único del dataset | ✅ Obligatorio |
| `dct:title` | `title_es`, `title_en` | Título multilingüe | ✅ Obligatorio |
| `dct:description` | `description_es`, `description_en` | Descripción multilingüe | ✅ Obligatorio |
| `dct:publisher` | `publisher_uri`, `publisher_name` | Organismo publicador (DIR3) | ✅ Obligatorio |
| `dcat:theme` | `themes` | Temática (taxonomía datos.gob.es) | ✅ Obligatorio |
| `dcat:keyword` | `keywords` | Etiquetas libres | ⚪ Recomendado |
| `dct:spatial` | `spatial_uri`, `spatial_name` | Ámbito geográfico | ⚪ Recomendado |
| `dct:temporal` | `temporal_coverage` | Cobertura temporal | ⚪ Recomendado |
| `dcat:distribution` | `distributions` | Formatos y URLs | ⚪ Recomendado |
| `dct:license` | `license_uri` | Licencia de uso | ⚪ Recomendado |
| `dct:issued` | `issued` | Fecha publicación | ⚪ Recomendado |
| `dct:modified` | `modified` | Fecha modificación | ⚪ Recomendado |

**Cobertura**: 13/16 campos DCAT-AP-ES (81%)

### Taxonomías Utilizadas

Los temas se extraen de múltiples vocabularios controlados:

| Vocabulario | URI Base | Uso |
|-------------|----------|-----|
| **Sectores datos.gob.es** | `http://datos.gob.es/kos/sector-publico/sector/` | Obligatorio en España |
| **EU Data Themes** | `http://publications.europa.eu/resource/authority/data-theme/` | Estándar EU |
| **INSPIRE** | `http://inspire.ec.europa.eu/theme/` | Datos geoespaciales |

### Identificadores de Organismos (DIR3)

Los publishers siguen el patrón DCAT-AP-ES con códigos **DIR3**:

```
http://datos.gob.es/recurso/sector-publico/org/Organismo/{ID-DIR3}
```

**Ejemplos**:
- `E05068001` → MITECO
- `A01002820` → Junta de Andalucía
- `L01080193` → Ayuntamiento de Barcelona

Ver mapeo completo en `clean_datasets.py` → `PUBLISHER_MAP`

### Campos No Implementados

| Campo | Motivo | Prioridad |
|-------|--------|-----------|
| `dcat:contactPoint` | No crítico para búsqueda | Baja |
| `dcatap:applicableLegislation` | Solo para HVD (High Value Datasets) | Baja |
| `foaf:page` | Landing page no esencial | Baja |

### Documentación Adicional

- **Ficha técnica**: `docs/ficha_tecnica_datos_gob_es.md`
- **Especificación DCAT-AP-ES**: https://datosgobes.github.io/DCAT-AP-ES/
- **Linked Data API**: http://purl.org/linked-data/api/vocab
