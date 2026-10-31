# Formulación del Proyecto

**Fecha**: 2026-06-23  
**Propósito**: Resumen estructurado del TFM para la reunión con el tutor de EOI: hipótesis del problema, solución, impacto, clientes, fuentes de datos y proveedores.

---

## 1. Hipótesis del problema

**Hipótesis principal**: los usuarios de `datos.gob.es` pierden entre **15 y 60 minutos** buscando datasets relevantes porque el buscador actual funciona por **palabras clave exactas**, no entiende la intención ni el contexto de la consulta.

### Causas del problema

| Causa | Evidencia del proyecto |
|---|---|
| Búsqueda por keywords exactas | El buscador web de datos.gob.es no rankea por semejanza semántica. |
| Vocabulario divergente | El usuario pregunta por "pueblos que se vacían"; el dataset se titula "población por municipio". |
| Descripciones cortas | **72,5%** de los 87.676 datasets tienen descripciones de menos de 50 palabras. |
| Keywords de baja calidad | Las palabras clave DCAT (`dcat:keyword`) existen en ~89% de los datasets, pero son ruidosas, repetitivas, multilingües sin control o demasiado genéricas. |
| Filtros incompletos | El 49,5% de los datasets carece de formato identificado; el campo `tags` está vacío. |

### Consecuencias

- **Baja reutilización** de datos públicos a pesar de que están abiertos.
- **Frustración del usuario**: investigadores, analistas y periodistas abandonan la búsqueda.
- **Pérdida de valor público**: datos relevantes para transparencia, investigación y toma de decisiones permanecen ocultos.

---

## 2. Solución propuesta

**Sistema**: un **buscador semántico híbrido** de datasets públicos españoles que permita consultas en lenguaje natural, rankee resultados por relevancia semántica + léxica y enriquezca la experiencia con funciones LLM (re-ranking, expansión de queries, TL;DR, complementariedad y chat sobre datasets).

### Arquitectura resumida

```
Query del usuario
        │
        ├──▶ Búsqueda léxica (PostgreSQL FTS / tsvector)
        ├──▶ Búsqueda semántica (pgvector / embeddings 384D)
        └──▶ Re-ranking con LLM (contextual)
                        │
                        ▼
              Resultados rankeados + explicación + filtros facetados
```

### Componentes clave

| Componente | Tecnología | Función |
|---|---|---|
| Embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Vectorización multilingüe de metadatos. |
| Búsqueda híbrida | PostgreSQL 15 + pgvector + FTS | Combinar similitud coseno (semántica) y full-text search (léxico). |
| LLM generativo | Modelos `:cloud` vía Ollama Cloud (`deepseek-v4-flash`, `qwen3-coder-next`, etc.) | Re-ranking, expansión de queries, TL;DR, chat, complementariedad. |
| API | FastAPI | Exponer endpoints de búsqueda, LLM y perfiles. |
| Frontend | Streamlit | Interfaz pública y modo avanzado/demostrador. |

### Casos de uso implementados (plan)

| # | Caso | Descripción |
|---|---|---|
| #1 | Re-ranking inteligente | Reordenar top-N resultados según la query. |
| #3 | Interpretación estructurada | Analizar la intención de la query. |
| #4 | Expansión semántica con fallback léxico | Ampliar la query con sinónimos y términos relacionados. |
| #5 | Datasets complementarios | Encontrar datasets que combinen bien con uno dado. |
| #10 | Chat sobre datasets | Responder preguntas sobre un dataset usando sus metadatos. |
| #12 | Validación semántica de queries | Detectar queries ambiguas o poco claras. |
| #14 | TL;DR / perfiles de datasets | Resumen ejecutivo y variables clave de un dataset. |

---

## 3. Marco normativo y motivo de datos.gob.es

`datos.gob.es` es el **portal nacional de datos abiertos** de España, gestionado por **red.es** en cumplimiento de la política de transparencia y reutilización de información del sector público. La existencia del portal no es voluntaria: responde a un marco normativo europeo y nacional que obliga a las administraciones públicas a publicar y facilitar el acceso a sus datos.

### Marco normativo relevante

| Norma | Año | Relevancia para el proyecto |
|---|---|---|
| **Ley 19/2013, de 9 de diciembre, de Transparencia, Acceso a la Información Pública y Buen Gobierno** | 2013 | Establece el derecho de acceso a la información pública y obliga a las administraciones a publicar información de forma activa y reutilizable. |
| **Ley 37/2007, de 16 de noviembre, reutilización de la información del sector público** | 2007 | Regula la reutilización de datos públicos; posteriormente desarrollada por el **Real Decreto 1495/2011**, de 24 de octubre. |
| **Directiva (UE) 2019/1024 (Directiva Open Data y reutilización de información del sector público)** | 2019 | Obliga a los Estados miembros a publicar datos de alta valor (transporte, medio ambiente, estadística, empresas, meteorología, etc.) en formatos abiertos y accesibles. |
| **Ley 39/2015, de 1 de octubre, del Procedimiento Administrativo Común de las Administraciones Públicas** | 2015 | Impulsa la interoperabilidad y la publicación electrónica de información administrativa. |
| **Real Decreto 1027/2017**, de 15 de diciembre | 2017 | Regula la **aplicación de datos abiertos** en el ámbito de la Administración General del Estado; datos.gob.es es el catálogo nacional que agrega y da visibilidad a estos datos. |
| **Ley 40/2015, de 1 de octubre, de Régimen Jurídico del Sector Público** | 2015 | Establece principios de eficiencia, transparencia y servicio público digital. |

### ¿Por qué existe datos.gob.es?

`datos.gob.es` cumple tres funciones estratégicas para la Administración española:

1. **Transparencia**: garantiza el derecho de los ciudadanos a conocer y acceder a la información pública.
2. **Reutilización**: facilita que empresas, investigadores y ciudadanos utilicen datos públicos para generar valor económico y social.
3. **Interoperabilidad**: agrega catálogos de distintas administraciones (estatal, autonómica, local) bajo un esquema común basado en el estándar **DCAT-AP-ES**.

### Implicación para el proyecto

Si la búsqueda en `datos.gob.es` es deficiente, se incumple parcialmente el **objetivo de transparencia**: los datos existen, pero no son descubribles. El buscador semántico se alinea con el propósito normativo del portal:

- **Ley 19/2013** y **Real Decreto 1027/2017** favorecen cualquier mejora que aumente la accesibilidad real de la información pública.
- La **Directiva (UE) 2019/1024** exige datos de "alajo valor" fácilmente accesibles; un buscador semántico mejora el acceso sin alterar los datos originales.
- El proyecto responde a la **Estrategia Nacional de Datos Abiertos** y a la **Agenda 2030** (ODS 16: paz, justicia e instituciones sólidas), impulsando una administración más transparente y eficiente.

### Referencias bibliográficas / normativas

- Ley 19/2013, de 9 de diciembre, de Transparencia, Acceso a la Información Pública y Buen Gobierno. BOE núm. 289, de 10 de diciembre de 2013.
- Ley 37/2007, de 16 de noviembre, sobre reutilización de la información del sector público. BOE núm. 276, de 17 de noviembre de 2007.
- Real Decreto 1495/2011, de 24 de octubre, por el que se desarrolla la Ley 37/2007. BOE núm. 258, de 25 de octubre de 2011.
- Real Decreto 1027/2017, de 15 de diciembre, por el que se regula la aplicación de datos abiertos. BOE núm. 302, de 18 de diciembre de 2017.
- Directiva (UE) 2019/1024 del Parlamento Europeo y del Consejo, de 20 de junio de 2019, relativa a los datos abiertos y la reutilización de la información del sector público.
- Ley 39/2015, de 1 de octubre, del Procedimiento Administrativo Común de las Administraciones Públicas. BOE núm. 236, de 2 de octubre de 2015.
- Ley 40/2015, de 1 de octubre, de Régimen Jurídico del Sector Público. BOE núm. 236, de 2 de octubre de 2015.
- Portal datos.gob.es: https://datos.gob.es/
- INAP, Guía de aplicación de datos abiertos en España.

---

## 4. Impacto esperado

### Impacto directo (para el usuario)

| Métrica | Baseline | Objetivo |
|---|---|---|
| Tiempo hasta dataset relevante | 15-60 minutos | < 2 minutos |
| Precisión en top-5 (P@5) | Buscador datos.gob.es: 0,62 | **> 0,70** (ya alcanzado 0,70 en benchmark propio) |
| Satisfacción de usuario | No medida | > 4/5 |
| Tasa de éxito de búsqueda | No medida | > 70% |

### Impacto institucional (Escenario A: proyecto interno en red.es)

| Métrica | Objetivo |
|---|---|
| Reducción de tickets de soporte | -20% |
| Reutilización de datasets | +15% |
| Cumplimiento de políticas de datos abiertos | Mejor cumplimiento de transparencia |
| Alineación con marco normativo | Refuerzo de Ley 19/2013, Real Decreto 1027/2017 y Directiva (UE) 2019/1024 |
| Visibilidad de datos de alto valor | Mejor descubribilidad de datasets estratégicos |

### Impacto económico (Escenarios B/C: licencia / SaaS)

| Escenario | Ingresos año 3 estimados | Costes año 3 estimados | Resultado estimado |
|---|---:|---:|---:|
| B. Licencia a terceros | 150.000-400.000 € | 140.000-300.000 € | -20.000 a +100.000 € |
| C. SaaS/API multi-cliente | 300.000-800.000 € | 200.000-500.000 € | +100.000 a +300.000 € |

### Impacto social

- **Democratización del acceso** a datos públicos.
- **Facilitación de la investigación académica**, el periodismo de datos y la transparencia.
- **Reducción de la brecha técnica** para analistas junior y ciudadanos.

---

## 4. Clientes y usuarios

### Segmentos de clientes/usuarios

| Segmento | Rol | Necesidad principal | Frecuencia |
|---|---|---|---|
| **Analistas de datos** | Data Analyst en empresa/consultora | Velocidad, metadatos completos, filtros | Diaria |
| **Investigadores** | Postdoc, doctorando, equipo de I+D | Profundidad, trazabilidad, descubrimiento de datasets relacionados | 2-3x/semana |
| **Periodistas de datos** | Redactor en medio de comunicación | Urgencia, contexto temporal, fuentes verificables | 1-2x/semana |
| **Administraciones públicas** | Gestores de datos abiertos | Cumplimiento, reutilización, mejora del portal | Mensual |
| **Desarrolladores / integradores** | Empresas de software | API replicable, documentación, casos de uso para concursos | Por proyecto |

### Clientes en cada escenario de negocio

| Escenario | Cliente principal |
|---|---|
| A. Proyecto interno red.es | Ciudadanía y usuarios de `datos.gob.es` |
| B. Licencia a terceros | Consultoras e integradores que compiten en concursos públicos |
| C. SaaS/API multi-cliente | CC.AA., ayuntamientos, universidades, portales sectoriales |

---

## 5. Fuentes de datos

### Fuente principal

| Fuente | Tipo | Formato | Estado |
|---|---|---|---|
| **datos.gob.es** | Portal nacional de datos abiertos | JSON (Linked Data API), CKAN API, SPARQL RDF/DCAT-AP | ✅ Descargados 134.150 datasets iniciales; 87.676 datasets únicos tras limpieza. |

### Campos extraídos

- Título y descripción (es/en).
- Temas DCAT (`theme`, `theme_label`).
- Subtemas (`subtheme`, `subtheme_label`).
- Territorio (`territory`, `territory_label`, `municipality`).
- Publicador (`publisher`, `publisher_id`).
- Palabras clave (`keywords` procedentes de `dcat:keyword`).
- Formato, licencia, frecuencia, cobertura temporal/espacial.
- Fechas de publicación y modificación.
- Metadatos en bruto (`raw_metadata` JSONB) para enriquecimientos futuros.

### Fuentes futuras (plan)

| Fuente | Motivo |
|---|---|
| data.europa.eu | Ampliar cobertura a datasets europeos. |
| Catálogos autonómicos/ locales | Mayor granularidad territorial. |
| Contenido de los datasets (cuando sea accesible) | Enriquecer perfiles con variables reales. |

---

## 6. Proveedores y socios clave

### Proveedores tecnológicos

| Proveedor | Qué aporta | Tipo |
|---|---|---|
| **Hugging Face** | `sentence-transformers` (modelo de embeddings) | Open source / modelo descargable |
| **Ollama Cloud** | LLM generativos (`deepseek-v4-flash:cloud`, `qwen3-coder-next:cloud`, etc.) | Cloud gestionada |
| **PostgreSQL / pgvector** | Base de datos vectorial + full-text search | Open source |
| **FastAPI / Uvicorn** | Framework API | Open source |
| **Streamlit** | Framework frontend | Open source |
| **Python ecosystem** | `psycopg2`, `requests`, etc. | Open source |

### Proveedores cloud (evaluación futura)

| Proveedor | Uso potencial |
|---|---|
| OpenAI (GPT-4o / GPT-4o-mini) | Re-ranking complejo, chat avanzado |
| Anthropic (Claude 3.5 Sonnet / Haiku) | Generación de perfiles de alta calidad |
| Google (Gemini Flash) | Alternativa de bajo coste |
| AWS / GCP / Azure | Infraestructura de producción si se escala |

### Socios clave

| Socio | Rol |
|---|---|
| **red.es** | Cliente potencial y caso de uso de referencia (`datos.gob.es`). |
| **Integradores de portales de datos** | Canal de distribución para licencias (Escenario B). |
| **Otras administraciones públicas** | Clientes potenciales de SaaS/API (Escenario C). |
| **Comunidad de reutilizadores de datos abiertos** | Validadores y difusores del producto. |

---

## 7. Resumen en una frase

> **Buscador semántico híbrido de datasets públicos españoles que reduce el tiempo de búsqueda de 15-60 minutos a menos de 2 minutos, mejora la precisión frente al buscador oficial de datos.gob.es y puede desplegarse como mejora interna del portal, producto licenciable o SaaS multi-cliente.**

---

## Documentos relacionados

- `docs/BUSINESS_MODEL_CANVAS.md` — Modelo de negocio detallado con 3 escenarios.
- `docs/BUSINESS_MODEL_CANVAS_RESUMEN.md` — Resumen ejecutivo para la reunión con el tutor.
- `docs/ESTRATEGIA_LLM_DEPLOY.md` — Arquitectura de LLM, opciones cloud/local, latencias.
- `docs/PLAN_ENRIQUECIMIENTO_METADATOS.md` — Diagnóstico y plan de mejora de metadatos.
- `docs/NARRATIVA_TFM.md` — Narrativa completa del proyecto.