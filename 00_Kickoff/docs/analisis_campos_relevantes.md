# Análisis de Campos Relevantes para Búsqueda Semántica

## Proyecto: Buscador Semántico de Datasets Públicos (datos.gob.es)
**Fecha:** 2026-05-20
**Fuente de datos:** Muestra de 10 datasets de datos.gob.es

---

## 📊 ESTRUCTURA DE DATOS OBSERVADA

Tras analizar la muestra de datos.gob.es, se identificaron los siguientes campos:

### Campos Principales (presentes en >90% de datasets)

| Campo | Tipo | Presencia | Formato Observado | Idioma |
|-------|------|-----------|-------------------|--------|
| **title** | Lista de objetos | 100% | `[{"_value": "texto", "_lang": "es"}]` | Multilingüe (es/en) |
| **description** | Lista de objetos | 100% | `[{"_value": "texto", "_lang": "es"}]` | Multilingüe (es/en) |
| **theme** | URI/String | 100% | URIs de datos.gob.es | Español |
| **identifier** | String | 100% | UUID o URL | - |
| **publisher** | URI | 100% | URI del organismo | - |
| **spatial** | URI | 100% | URI de territorio | - |
| **license** | URI | 100% | URI de licencia | - |
| **distribution** | Objeto/Lista | 100% | Detalles de formatos | - |

### Campos Secundarios (presentes en <50%)

| Campo | Presencia | Notas |
|-------|-----------|-------|
| **tags** | ~10% | Pocas veces presente en datos.gob.es |
| **contactPoint** | 0% | Objeto vacío en la muestra |
| **temporal** | Variable | URI o lista de URIs |
| **accrualPeriodicity** | Variable | URI de frecuencia o objeto DurationDescription |
| **keyword** | ~10% | Alternativa a tags |

### Campos ausentes comunes en otros portales

| Campo | Motivo de ausencia |
|-------|-------------------|
| organization | Campo vacío (N/A) - se usa `publisher` |
| notes | Usado en CKAN nativo, no en datos.gob.es |
| extras | No presente en formato Linked Data API |

---

## 🔍 PRIORIDAD DE CAMPOS PARA EMBEDDINGS

Basado en investigación académica y estándares DCAT-AP:

### 🥇 CRÍTICOS (Peso alto en embeddings)

#### 1. **TITLE** - Peso: 40%
- **Justificación:** Paper de arXiv [2509.14457v1] identifica `title` como campo más importante para alineación con intención del usuario
- **Características:**
  - Multilingüe (español/inglés)
  - Términos clave del dominio
  - Nombre descriptivo del dataset
- **Tratamiento recomendado:**
  - Concatenar versiones en español e inglés
  - Extraer texto: `title_es + " " + title_en`
  - Normalizar: minúsculas, eliminar acentos opcional

#### 2. **DESCRIPTION** - Peso: 35%
- **Justificación:** Paper confirma que `description` juega rol central en alineación con queries en lenguaje natural
- **Características:**
  - Texto más extenso y contextual
  - Explica el contenido real del dataset
  - Frecuentemente incluye fuente y metodología
- **Tratamiento recomendado:**
  - Extraer versión en español (prioridad) + inglés
  - Limpiar saltos de línea y espacios múltiples
  - Truncar si excede 512 tokens (límite de modelo)

### 🥈 IMPORTANTES (Peso medio - filtros y contexto)

#### 3. **THEME** - Peso: 10%
- **Justificación:** Categorización semántica del dataset según estándar EU
- **Características:**
  - URIs como: `http://datos.gob.es/kos/sector-publico/sector/medio-ambiente`
  - Categorías controladas
- **Tratamiento recomendado:**
  - Extraer última parte de URI como texto
  - Ej: `medio-ambiente` → `medio ambiente`
  - Incluir como metadato separado (no en embeddings principal)

#### 4. **SPATIAL** - Peso: 5%
- **Justificación:** Filtro geográfico crucial para queries territoriales
- **Características:**
  - URIs como: `http://datos.gob.es/recurso/sector-publico/territorio/Pais/España`
- **Tratamiento recomendado:**
  - Extraer nivel territorial: país, autonomía, provincia, municipio
  - Indexar como campo separado para filtrado

#### 5. **PUBLISHER** - Peso: 5%
- **Justificación:** Organismo publicador añade contexto institucional
- **Características:**
  - URIs como: `http://datos.gob.es/recurso/sector-publico/org/Organismo/E05068001`
- **Tratamiento recomendado:**
  - Extraer código de organismo
  - Mapear a nombre legible (vía API o tabla auxiliar)

### 🥉 AUXILIARES (Metadatos para filtros, no embeddings)

#### 6. **LICENSE** 
- Uso: Filtrado por tipo de licencia (reuso abierto)
- Formato: URI como `http://publications.europa.eu/resource/authority/licence/CC_BY_4_0`

#### 7. **ACCRUALPERIODICITY**
- Uso: Filtro por frecuencia de actualización
- Formato: URI o objeto con campo `years`

#### 8. **TEMPORAL**
- Uso: Filtro por rango de fechas del dataset
- Formato: URI o lista de URIs

#### 9. **DISTRIBUTION**
- Uso: Información de formatos disponibles
- Formato: Objeto o lista de objetos con `format`, `accessURL`, `byteSize`

---

## 📐 ESTRATEGIA DE EMBEDDINGS RECOMENDADA

### Texto para Generar Embeddings

```python
# Ejemplo de construcción del texto para embeddings

def build_embedding_text(dataset):
    """Construye texto enriquecido para embeddings"""
    
    # Extraer títulos (español + inglés)
    titles = [t['_value'] for t in dataset.get('title', [])]
    title_text = ' '.join(titles)
    
    # Extraer descripciones (español + inglés)
    descriptions = [d['_value'] for d in dataset.get('description', [])]
    desc_text = ' '.join(descriptions)
    
    # Extraer temas (convertir URIs a texto)
    themes = dataset.get('theme', [])
    if isinstance(themes, str):
        themes = [themes]
    theme_text = ' '.join([t.split('/')[-1].replace('-', ' ') for t in themes])
    
    # Extraer territorio
    spatial = dataset.get('spatial', '')
    spatial_text = spatial.split('/')[-1] if spatial else ''
    
    # Construir texto final (con pesos implícitos por orden y repetición)
    embedding_text = f"""
    {title_text}
    {title_text}  # Repetir título para darle más peso
    
    {desc_text}
    
    Temas: {theme_text}
    Territorio: {spatial_text}
    """
    
    return embedding_text.strip()
```

### Ejemplo con Dataset Real

**Dataset:** "Mapas estratégicos de Ruido"

```
TÍTULO: Mapas estratégicos de Ruido Strategic Noise maps
DESCRIPCIÓN: Mapas estratégicos de ruido (MER) de la tercera fase de implementación de la Directiva 2002/49/CE del Parlamento Europeo y del Consejo, de 25 de junio de 2002, sobre evaluación y gestión del ruido ambiental (END, por sus siglas en inglés).
TEMA: medio-ambiente, ac, ENVI
TERRITORIO: España
```

**Texto para embeddings:**
```
Mapas estratégicos de Ruido Strategic Noise maps
Mapas estratégicos de Ruido Strategic Noise maps
Mapas estratégicos de ruido (MER) de la tercera fase de implementación de la Directiva 2002/49/CE del Parlamento Europeo y del Consejo, de 25 de junio de 2002, sobre evaluación y gestión del ruido ambiental (END, por sus siglas en inglés).
Temas: medio ambiente ac ENVI
Territorio: España
```

---

## 🎯 SCHEMA DE POSTGRESQL RECOMENDADO

```sql
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    
    -- Identificación
    identifier VARCHAR(255) UNIQUE NOT NULL,
    source_url TEXT,
    
    -- Metadatos principales (para embeddings)
    title_es TEXT NOT NULL,
    title_en TEXT,
    description_es TEXT,
    description_en TEXT,
    
    -- Campos para embeddings
    embedding_text TEXT,  -- Texto concatenado para generar embeddings
    metadata_vector VECTOR(384),  -- Embeddings del modelo
    
    -- Categorización
    themes TEXT[],  -- Array de temas
    keywords TEXT[],  -- Array de palabras clave
    
    -- Contexto geográfico
    spatial_uri TEXT,
    spatial_level VARCHAR(50),  -- 'pais', 'autonomia', 'provincia', 'municipio'
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
    
    -- Distribuciones
    distributions JSONB,  -- Formatos disponibles, URLs
    
    -- Búsqueda léxica
    search_vector TSVECTOR,  -- Para full-text search de PostgreSQL
    
    -- Metadatos del sistema
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_sync_at TIMESTAMP
);

-- Índices
CREATE INDEX idx_datasets_vector ON datasets USING ivfflat (metadata_vector vector_cosine_ops);
CREATE INDEX idx_datasets_search ON datasets USING GIN (search_vector);
CREATE INDEX idx_datasets_themes ON datasets USING GIN (themes);
CREATE INDEX idx_datasets_spatial ON datasets (spatial_level, spatial_name);
CREATE INDEX idx_datasets_publisher ON datasets (publisher_name);
```

---

## 📚 REFERENCIAS

1. **Paper:** "Keywords are not always the key: A metadata field analysis for natural language search on open data portals" (arXiv:2509.14457v1, 2025)
   - Conclusión: `description` y `title` son campos críticos para alineación con queries en lenguaje natural
   - El paper demuestra que búsqueda basada en embeddings supera a keyword-matching

2. **Estándar:** DCAT-AP 3.0 (EU)
   - Define campos obligatorios: title, description, publisher, license, spatial, temporal
   - Categorías: theme (usando vocabularios controlados EU)

3. **Formato de datos.gob.es:** Linked Data API v0.2
   - Estructura: `result.items[]` con campos DCAT estándar
   - Multilingüe: Campos `title` y `description` como arrays con `_lang`

---

## ✅ CONCLUSIONES

### Campos para Embeddings (orden de prioridad):
1. **title** (español + inglés) - 40%
2. **description** (español + inglés) - 35%
3. **theme** - 10%
4. **spatial** - 5%
5. **publisher** - 5%

### Campos para Filtros/Facets:
- theme, spatial, publisher, license, accrualPeriodicity, distribution.format

### Campos para UI/Display:
- title, description, identifier, source_url, distributions

---

*Documento vivo: Actualizar si se detectan nuevos campos en la API*
