# 2.2. IA tradicional. Recopilación y origen de los datos

> Apartado redactado conforme a la guía *"2. Guía proyecto CD_IA.pdf"* (Valvanera Castro), sección 2.2, aplicado al proyecto **DataTrust — Buscador Semántico de Datasets Públicos** (datos.gob.es).

La recopilación de datos constituye el primer paso operativo del proyecto y la base sobre la que se asienta todo el sistema. El objetivo de esta etapa es identificar, evaluar y conectar la fuente de datos que alimenta el flujo de trabajo del buscador, garantizando que la información recolectada sea relevante, precisa y compatible con los objetivos del negocio, al tiempo que se optimizan los costes y tiempos de integración.

En el caso de DataTrust, la fuente de datos es única y de carácter externo: el **Catálogo Nacional de Datos Abiertos** gestionado por Red.es a través del portal [datos.gob.es](https://datos.gob.es). Se trata de un proyecto *in company* cuyo cliente principal es el propio gestor del catálogo, por lo que la recopilación se centra en un único origen de verdad, pero con una complejidad interna elevada derivada de la heterogeneidad de sus metadatos.

---

## 2.2.1. Identificación de fuentes de datos

### Origen y naturaleza de la fuente

| Atributo | Descripción |
|---|---|
| **Fuente** | datos.gob.es — Catálogo Nacional de Datos Abiertos |
| **Organismo** | Red.es / Ministerio para la Transformación Digital |
| **Tipo de fuente** | **Externa** (API pública de terceros) |
| **Naturaleza de los datos** | **Semiestructurados** (JSON con vocabulario DCAT-AP-ES) |
| **Volumen** | 134.150 registros brutos → **87.676 datasets únicos** tras deduplicación |
| **Periodo de ingesta** | Mayo 2026 |

La fuente es **externa** en el sentido de que los datos no se generan dentro de la organización que desarrolla el proyecto, sino que provienen de un tercero (la Administración Pública). Sin embargo, al tratarse de un proyecto *in company* para Red.es, la fuente es a la vez el cliente y el origen de los datos, lo que elimina fricciones de acceso y licencia.

Los datos son de tipo **semiestructurado**: cada dataset se expone como un documento JSON que sigue el perfil de aplicación **DCAT-AP-ES** (Data Catalog Vocabulary — Application Profile, adaptación española del estándar europeo DCAT-AP). No se trabaja con los datos *contenidos* en los datasets (tablas, series, mapas), sino con sus **metadatos descriptivos**, que son precisamente el objeto de la búsqueda semántica.

### Canales de acceso disponibles

La ficha técnica de la fuente identifica cuatro vías de acceso, de las cuales se seleccionó una como principal:

| Canal | URL | Uso en el proyecto |
|---|---|---|
| **Linked Data API** | `https://datos.gob.es/apidata/catalog/dataset.json` | ✅ **Principal** — ingesta batch paginada |
| **API CKAN** | `https://datos.gob.es/apidata` | Alternativa (no usada en producción) |
| **SPARQL Endpoint** | `https://datos.gob.es/sparql` | Consultas complejas sobre grafos RDF (no usada) |
| **Descarga RDF** | RDF/XML, Turtle, JSON-LD | Referencia de vocabulario (no usada) |

La **Linked Data API** fue la elegida por su simplicidad (JSON paginado con `_page`/`_pageSize`) y porque devuelve el registro completo de cada dataset en una sola llamada, evitando la doble consulta que exigiría la API CKAN (`package_list` + `package_show` por cada identificador).

### Campos de metadatos capturados (DCAT-AP-ES)

El conector de ingesta extrae y normaliza los siguientes campos por dataset:

| Campo DCAT | Contenido | Obligatorio |
|---|---|---|
| `dct:title` | Título (ES/EN) | ✅ |
| `dct:description` | Descripción (ES/EN) | ✅ |
| `dct:publisher` | Publicador (URI + nombre) | ✅ |
| `dcat:theme` | Temas | ✅ |
| `dcat:keyword` | Palabras clave | Recomendado |
| `dct:spatial` | Cobertura geográfica (nivel: país/autonomía/provincia/municipio) | Recomendado |
| `dct:temporal` | Cobertura temporal | Recomendado |
| `dcat:distribution` | Distribuciones (formato, URL de acceso/descarga) | Recomendado |
| `dct:license` | Licencia | Recomendado |
| `dct:issued` / `dct:modified` | Fechas de publicación/modificación | Recomendado |
| `dct:accrualPeriodicity` | Frecuencia de actualización | Recomendado |
| `identifier` | Identificador único | — |

Además de los campos DCAT, el conector construye dos campos derivados que son la base del motor de búsqueda:

- **`embedding_text`**: texto enriquecido que combina título, descripción, temas, palabras clave y territorio, destinado a la generación de embeddings semánticos.
- **`search_text`**: concatenación plana de los mismos campos para la búsqueda léxica (full-text).

---

## 2.2.2. Evaluación de la calidad y disponibilidad de los datos

Antes de integrar la fuente, se realizó un **análisis exploratorio del catálogo completo** (87.676 datasets) mediante un script de auditoría (`audit_metadata.py`) que midió la calidad, completitud y disponibilidad de los metadatos. El detalle completo de este análisis (distribuciones por formato, publicador, territorio y cobertura temporal, con sus gráficos) se presenta en el **apartado 1.5 (Análisis preliminar de datos)**; aquí se recoge únicamente lo relevante para justificar la estrategia de recopilación.

### Relevancia

Los metadatos de datos.gob.es son **directamente aplicables** a la pregunta de negocio: el buscador responde consultas analíticas en lenguaje natural devolviendo datasets relevantes, y para ello necesita exactamente los campos descriptivos que el catálogo expone (título, descripción, tema, territorio, publicador). La relevancia es total, sin necesidad de fuentes complementarias.

### Calidad — hallazgos críticos

El análisis reveló una **calidad heterogénea** de los metadatos, con cinco hallazgos que condicionaron el diseño:

| Hallazgo | Dato | Impacto en el diseño |
|---|---|---|
| **Descripciones breves** | 72,5 % con < 50 palabras | Embeddings pobres → búsqueda híbrida obligatoria |
| **Formato no declarado** | 98,5 % sin campo `format` | Inferencia de formato desde la URL (47,2 % recuperable) |
| **Sin cobertura temporal** | 93,9 % sin `dct:temporal` | Fecha de modificación como proxy de frescura |
| **Baja representación municipal** | Solo 1,2 % municipal | Filtro territorial prioriza autonómico |
| **Completitud media** | 64,1 % de campos completos | Validación DCAT no bloqueante |

El hallazgo más determinante es el de las **descripciones breves**: el 72,5 % de los datasets tiene descripciones de menos de 50 palabras (ejemplos reales: *"Datos de población"*, *"Paro registrado por sectores"*). Esto significa que una búsqueda **puramente semántica** (basada solo en embeddings) habría fracasado, porque el contexto textual es insuficiente para generar vectores de calidad. La consecuencia directa fue la adopción de una **arquitectura híbrida** que combina búsqueda léxica (full-text), semántica (pgvector) y re-ranking con LLM.

### Validación DCAT-AP-ES

Se implementó un validador propio (`validate_dcat_ap_es.py`) que comprueba 14 reglas del estándar (4 obligatorias + 10 recomendadas). Resultados:

| Nivel | Cumplimiento |
|---|---|
| **Campos obligatorios** (title, description, publisher, theme) | **100 %** |
| **Campos recomendados** | 0 % (ningún dataset los completa todos) |
| **Cobertura global** | 81 % (13/16 campos) |

Los campos obligatorios se cumplen en el 100 % de los registros, lo que garantiza un mínimo viable de calidad. Los campos recomendados presentan carencias generalizadas: `dct:license` solo en el 1,24 %, `dct:spatial` en el 35,36 %, `dct:temporal` en el 13,49 %, y `dcat:contactPoint` y `dcatap:applicableLegislation` no implementados (0 %).

**Decisión de diseño clave**: la validación DCAT se aplica de forma **no bloqueante**. No se descarta ningún dataset por incumplir campos recomendados; en su lugar, la calidad se mide, se registra y se expone al usuario como parte de la explicación de cada resultado. Esto evita perder el 99 % del catálogo por carencias de metadatos que son responsabilidad de los publicadores, no del buscador.

### Disponibilidad

La fuente es **accesible de forma regular y fiable** a través de su API pública, sin autenticación ni límites de licencia (los datos son abiertos por definición). La ingesta completa de 134.150 registros se realizó en ~22 minutos con una tasa de error del 0 %, gracias a la implementación de reintentos con *backoff* exponencial y control de ritmo (*rate limiting*).

### Actualización

El catálogo de datos.gob.es se **actualiza periódicamente** (los publicadores federados publican y modifican datasets de forma continua). Esto tiene dos implicaciones:

1. **Frescura**: los datos ingeridos en mayo de 2026 son un *snapshot* puntual. Para mantener actualidad, el proyecto incluye un conector de **ingesta incremental** (`ingest_incremental.py`) que permite re-sincronizar solo los datasets nuevos o modificados.
2. **Proxy de frescura**: dado que el 93,9 % de los datasets no declara cobertura temporal, el buscador usa la fecha de **modificación** (`dct:modified`) como indicador de frescura visible para el usuario.

---

## 2.2.3. Estrategias para la extracción de datos

La extracción se implementó mediante **integración por API** con un patrón *batch* paginado, complementado con mecanismos de robustez y trazabilidad.

### Pipeline de ingesta

El conector principal (`ingest_datos_gob_v2.py`) ejecuta el siguiente flujo:

1. **Paginación**: recorre la Linked Data API con `_page`/`_pageSize=100`, acumulando los datasets en lotes de 1.000 registros.
2. **Deduplicación**: mantiene un conjunto de identificadores ya vistos (`seen_identifiers`) y descarta los duplicados, reduciendo 134.150 registros brutos a 87.676 únicos.
3. **Normalización**: transforma cada registro JSON crudo a un esquema canónico (extracción de campos multilingües, inferencia de nivel territorial desde la URI, extracción de distribuciones).
4. **Persistencia por lotes**: guarda los resultados en archivos `batch_XXXX.jsonl` para evitar pérdidas ante interrupciones.
5. **Checkpoint / resume**: persiste el estado de la ingesta (página, lote, contadores) en un archivo `.ingest_state.json`, permitiendo reanudar la ingesta desde el punto de interrupción.

### Mecanismos de robustez

| Mecanismo | Implementación |
|---|---|
| **Reintentos** | 3 intentos con *backoff* exponencial (1s → 2s → 4s) |
| **Errores tratados** | HTTP 429/500/502/503/504 disparan reintento |
| **Control de ritmo** | *delay* de 0,5 s entre páginas para no saturar la API |
| **Tolerancia a fallos** | Los errores de transformación se registran y no abortan la ingesta |
| **Idempotencia** | Deduplicación por `identifier` garantiza re-ingestas seguras |

### Estrategias contempladas y descartadas

| Estrategia | Decisión | Justificación |
|---|---|---|
| **Integración por API (Linked Data)** | ✅ Usada | JSON paginado, registro completo en una llamada |
| **API CKAN** | Descartada | Requiere doble consulta (lista + detalle) |
| **SPARQL** | Descartada | Complejidad innecesaria para ingesta masiva |
| **Scraping web** | Descartada | La API oficial cubre el 100 % del catálogo |
| **Streaming** | No aplica | La fuente no emite eventos en tiempo real |
| **Bases de datos relacionales** | No aplica | La fuente es una API, no una BD accesible |

### Trazabilidad (data lineage)

Siguiendo la metodología de la guía, el proyecto registra el **linaje del dato** en cada etapa: cada dataset conserva su `identifier` y `source_url` originales, y el modelo de datos actualizado (apartado 1.2) hace auditable el recorrido completo *fuente → transformación → índice → consulta → ranking → explicación → dataset oficial*. Cada inferencia (formato desde URL, nivel territorial, proxy de frescura) se registra con su método y confianza, de modo que el sistema no oculta la incertidumbre de los metadatos sino que la expone.

### Cumplimiento legal

Los datos de datos.gob.es son **datos abiertos** publicados bajo licencias de reutilización, por lo que no existen restricciones de uso. Al tratarse de metadatos descriptivos (no datos personales), el proyecto no está sujeto a obligaciones RGPD sobre el contenido ingerido. No obstante, el diseño respeta los principios de **ENS** (Esquema Nacional de Seguridad) y trazabilidad exigidos por el cliente Red.es, y cada resultado enlaza siempre al dataset oficial como fuente de verdad, sin sustituir el catálogo.

---

## Resumen del apartado

| Subapartado | Conclusión para DataTrust |
|---|---|
| **2.2.1 Identificación** | Fuente externa única: datos.gob.es (Linked Data API), 87.676 datasets semiestructurados en DCAT-AP-ES |
| **2.2.2 Calidad/disponibilidad** | Metadatos heterogéneos (72,5 % descripciones breves, 98,5 % sin formato); validación DCAT no bloqueante; fuente fiable y actualizable |
| **2.2.3 Extracción** | Ingesta batch paginada por API con deduplicación, checkpoint, reintentos y trazabilidad completa |
