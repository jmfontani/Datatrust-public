# datos.gob.es - Ficha Técnica

## Información General
- **URL:** https://datos.gob.es
- **Catálogo Nacional de Datos Abiertos**
- **Total datasets:** 113.313+ (a mayo 2026)
- **Organismo:** Ministerio para la Transformación Digital

## APIs Disponibles

### 1. API CKAN
- **URL base:** https://datos.gob.es/apidata
- **Documentación:** https://docs.ckan.org/en/latest/api/
- **Formato:** JSON
- **Endpoints principales:**
  - `/api/3/action/package_list` - Listar datasets
  - `/api/3/action/package_show?id={id}` - Detalle de dataset
  - `/api/3/action/package_search?q={query}` - Búsqueda
  - `/api/3/action/tag_list` - Listar etiquetas
  - `/api/3/action/group_list` - Listar grupos

### 2. SPARQL Endpoint
- **URL:** https://datos.gob.es/sparql
- **Lenguaje:** SPARQL 1.1
- **Grafos RDF disponibles**
- **Consultas complejas sobre metadatos DCAT**

### 3. Descarga RDF
- **Formatos:** RDF/XML, Turtle, JSON-LD
- **Vocabulario:** DCAT-AP, GeoDCAT-AP

## Metadatos Disponibles

### Campos Principales (DCAT-AP)
- **Título** (dct:title)
- **Descripción** (dct:description)
- **Palabras clave** (dcat:keyword)
- **Tema** (dcat:theme)
- **Publicador** (dct:publisher)
- **Frecuencia de actualización** (dct:accrualPeriodicity)
- **Licencia** (dct:license)
- **Cobertura geográfica** (dct:spatial)
- **Cobertura temporal** (dct:temporal)
- **Distribuciones** (dcat:distribution)
  - Formato
  - URL de descarga
  - Tamaño
- **Idioma** (dct:language)
- **Calidad** (dcat:contactPoint, dct:issued, dct:modified)

### Campos Adicionales
- Identificador único
- Fecha de creación
- Fecha de modificación
- Organismo responsable
- Nivel administrativo (estatal, autonómico, local)

## Estructura del Catálogo

### Por Tema
- Medio ambiente
- Transporte
- Salud
- Educación
- Economía
- Demografía
- Urbanismo
- Turismo
- etc.

### Por Publicador
- Ministerios
- Comunidades Autónomas
- Ayuntamientos
- Organismos públicos
- Universidades

### Por Formato
- CSV
- JSON
- XML
- RDF
- XLS/XLSX
- Shapefile
- GeoJSON
- API

## Ejemplos de Consultas SPARQL

### Listar todos los datasets
```sparql
SELECT ?dataset ?title WHERE {
  ?dataset a dcat:Dataset .
  ?dataset dct:title ?title .
}
LIMIT 100
```

### Buscar datasets por tema
```sparql
SELECT ?dataset ?title ?theme WHERE {
  ?dataset a dcat:Dataset .
  ?dataset dct:title ?title .
  ?dataset dcat:theme ?theme .
  FILTER(CONTAINS(LCASE(STR(?theme)), "medio-ambiente"))
}
```

### Datasets con distribuciones CSV
```sparql
SELECT ?dataset ?title ?downloadUrl WHERE {
  ?dataset a dcat:Dataset .
  ?dataset dct:title ?title .
  ?dataset dcat:distribution ?dist .
  ?dist dcat:downloadURL ?downloadUrl .
  ?dist dct:format "text/csv" .
}
```

## Limitaciones Conocidas
- Metadatos heterogéneos entre publicadores
- Calidad variable de las descripciones
- Duplicados potenciales entre niveles administrativos
- No todos los datasets tienen distribuciones descargables
- Desactualización en algunos catálogos federados

## Referencias
- [Documentación datos.gob.es](https://datos.gob.es/es/documentacion)
- [CKAN API Guide](https://docs.ckan.org/en/latest/api/)
- [DCAT-AP Specification](https://joinup.ec.europa.eu/collection/semantic-interoperability-community-semic/solution/dcat-application-profile-data-portals-europe/release/210)
- [SPARQL Examples](https://datos.gob.es/en/ejemplos-sparql)
