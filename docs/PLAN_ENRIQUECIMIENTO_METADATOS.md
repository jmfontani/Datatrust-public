# Plan de Enriquecimiento de Metadatos

**Fecha**: 2026-06-23  
**Contexto**: Respuesta al punto de dolor #3 del tutor de EOI: "La creación del metadato..... va a ser 'divertida'". El buscador semántico depende de la calidad de los metadatos; si son pobres, los embeddings y el re-ranking con LLM pierden precisión.

> Este documento se redacta en la **fase de diseño previa a la implementación**. Las propuestas son hipótesis de planificación y requieren validación.

---

## 1. Diagnóstico actual de los metadatos

Auditoría sobre los **87.676 datasets** indexados (tabla `datasets`, junio 2026):

| Campo | Estado | Impacto en búsqueda |
|---|---|---|
| **Descripción** | 72,5% tienen <50 palabras; solo 1,3% tienen ≥200 palabras | **Alto**: embeddings de baja calidad, poco contexto semántico |
| **Tags** | 100% vacíos en nuestra tabla `datasets` | **Alto**: falta vocabulario controlado/normalizado para búsqueda léxica y facetada (el campo `tags` no es parte del core DCAT-AP-ES; se usan `dcat:keyword` → `keywords`) |
| **URL de descarga** | 100% vacíos | **Medio**: el buscador no puede enlazar directamente al recurso; el usuario debe ir a datos.gob.es |
| **Formato** | 49,5% sin formato | **Medio-alto**: filtro por formato inutilizable para la mitad del catálogo |
| **Keywords** | 10,6% sin keywords | **Medio**: menor cobertura para búsqueda por términos específicos |
| **Tema** | 0% vacíos | **Bajo**: ya se puede filtrar por tema |
| **Territorio** | 0% vacíos | **Bajo**: ya se puede filtrar por territorio |

**Conclusión del diagnóstico**: el principal problema no es la ausencia total de metadatos, sino su **pobreza semántica y falta de normalización**:
- Las descripciones cortas generan embeddings poco discriminativos.
- Los `keywords` (procedentes de `dcat:keyword`) existen en ~89% de los datasets, pero a menudo son **ruidosos, repetitivos, multilingües sin control o demasiado genéricos** (ej. "Taula de dades estadístiques"), por lo que no siempre aportan valor semántico.
- El campo `tags` (no estándar en DCAT-AP-ES) está vacío; sería útil crear **tags controlados/normalizados** a partir de `theme`, `keywords`, título y descripción.
- La ausencia de `format` en ~50% de los datasets limita la navegación facetada.
- La falta de URL de descarga directa reduce la utilidad práctica del buscador.

---

## 2. Objetivos del enriquecimiento

1. **Mejorar la calidad de los embeddings** ampliando descripciones con contexto semántico.
2. **Completar campos vacíos** críticos: tags controlados, formato, URL de descarga.
3. **Normalizar y enriquecer keywords** (campo `dcat:keyword`) con sinónimos, términos relacionados y vocabulario controlado.
4. **Generar metadatos derivados**: resumen ejecutivo (TL;DR), variables clave, cobertura temporal/geográfica explícita.
5. **Mantener trazabilidad**: cada metadato enriquecido debe indicar fuente y confianza.

---

## 3. Técnicas de enriquecimiento propuestas

### 3.1 Ampliación de descripciones con LLM (prioridad alta)

**Idea**: usar un LLM para reescribir/expandir la descripción de un dataset a partir de su título, descripción original, tema, territorio y, si es posible, una muestra del contenido.

**Prompt tipo**:
```
A partir del siguiente dataset público:
- Título: {title}
- Descripción original: {description}
- Tema: {theme}
- Territorio: {territory}
- Publicador: {publisher}

Genera una descripción ampliada de 100-150 palabras que explique:
1. Qué datos contiene.
2. Para qué sirve y quién lo publica.
3. Posibles usos o análisis que permite.
```

**Modelo recomendado**: `deepseek-v4-flash:cloud` (equilibrio calidad/coste/velocidad).

**Validación**: comparar embedding de la descripción original vs ampliada con un conjunto de queries de referencia; medir si mejora P@5.

### 3.2 Normalización de keywords y generación de tags controlados (prioridad alta)

**Contexto**: en DCAT-AP-ES las palabras clave van en `dcat:keyword` (nuestro campo `keywords`). Ese campo existe en ~89% de los datasets, pero con calidad muy desigual: años sueltos, términos multilingües sin control, repeticiones, palabras genéricas. El campo `tags` no es parte del core DCAT-AP-ES y está vacío en nuestra tabla.

**Técnicas**:
- **Limpieza de keywords DCAT**: eliminar años sueltos repetidos, stopwords, términos demasiado genéricos; unificar variantes (castellano/euskera/catalán) cuando sea posible.
- **Extracción de entidades** desde título + descripción (NER): lugares, organismos, sectores, indicadores.
- **Keyword extraction** complementaria con modelos léxicos (KeyBERT, RAKE, YAKE) o LLM.
- **Mapeo a vocabulario controlado**: temas DCAT, territorios, formatos estándar.
- **Sugerencia de sinónimos** a partir de `term_synonyms` ya existente en el proyecto.
- **Generación de `tags` controlados**: categorías normalizadas derivadas de `theme` + `keywords` + título + descripción (ej. "demografía", "medio-ambiente", "economía", "transporte", "salud").

**Salida esperada**: `keywords[]` limpio/enriquecido y `tags[]` controlado por dataset.

### 3.3 Inferencia de formato (prioridad media-alta)

**Técnicas**:
- Parsear el campo `raw_metadata` (JSONB) para buscar distribuciones y formatos.
- Inferir formato desde la URL de descarga o acceso (`.csv`, `.xlsx`, `.json`, `.geojson`, `.pdf`, `.xml`, `.rdf`, `.zip`).
- Usar reglas heurísticas: si no hay URL, marcar como "desconocido" y no aplicar filtro por defecto.

### 3.4 Recuperación de URL de descarga (prioridad media)

**Técnicas**:
- Extraer `distribution.accessURL` o `distribution.downloadURL` del JSONB `raw_metadata`.
- Si no existe, usar la URL del dataset en `datos.gob.es` como landing page.
- Esta mejora no afecta a la búsqueda semántica, pero sí a la **utilidad percibida** por el usuario.

### 3.5 Generación de perfiles enriquecidos (TL;DR, variables, cobertura) (prioridad media)

Ya existe un prototipo (`dataset_profiles`). Se propone:
- Generar TL;DR para todos los datasets, no solo una muestra.
- Extraer variables clave (columnas/dimensiones) si se accede al contenido.
- Inferir cobertura temporal y nivel geográfico explícito.

### 3.6 Clustering temático y detección de datasets huérfanos (prioridad baja-media)

**Técnicas**:
- Clustering de embeddings para detectar datasets mal clasificados.
- Detección de datasets con descripción vacía o muy corta que no pueden mejorarse con LLM por falta de contexto.
- Flag de "metadato de baja calidad" para excluir del ranking o bajarlo.

---

## 4. Propuesta de pipeline de enriquecimiento

```
┌─────────────────────────────────────────────────────────────────┐
│  FUENTE: datasets (87.676 registros)                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Preproceso  │     │ Extracción  │     │ Generación  │
│ y limpieza  │     │ de entidades│     │ con LLM     │
│ (reglas)    │     │ (NER/regex) │     │ (descripción│
└──────┬──────┘     └──────┬──────┘     │ ampliada,   │
       │                   │            │ TL;DR)      │
       └─────────┬─────────┘            └──────┬──────┘
                 │                              │
                 ▼                              ▼
       ┌─────────────────┐            ┌─────────────────┐
       │ Fusión y scoring│            │ Validación      │
       │ de confianza    │            │ (muestreo +     │
       │ (0-1)           │            │ juicio humano)  │
       └────────┬────────┘            └────────┬────────┘
                │                              │
                └──────────────┬───────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │  Escritura en datasets y      │
                │  dataset_profiles_enriched    │
                └─────────────────────────────┘
```

### Fases del pipeline

| Fase | Acción | Volumen estimado | Esfuerzo estimado |
|---|---|---|---|
| 1 | Limpieza y normalización de campos existentes | 87.676 registros | Bajo (reglas) |
| 2 | Extracción de formato desde URL/raw_metadata | ~43.394 registros | Medio |
| 3 | Recuperación de URL de descarga/landing | 87.676 registros | Medio |
| 4 | Normalización de keywords y generación de tags controlados | 87.676 registros | Alto |
| 5 | Ampliación de descripciones con LLM | ~63.597 registros | Alto |
| 6 | Generación de perfiles (TL;DR, variables) | 87.676 registros | Muy alto |
| 7 | Validación con muestreo y ajuste | ~1.000-5.000 registros | Medio |

---

## 5. Esfuerzo y viabilidad

### Esfuerzo estimado (horas de ingeniería)

| Tarea | Horas estimadas | Nota |
|---|---|---|
| Diseño del pipeline y schema de metadatos enriquecidos | 20-30 | Incluye trazabilidad y scoring |
| Limpieza/formato/URL (reglas + heurísticas) | 30-50 | Automatizable en su mayoría |
| Extracción de tags/keywords (NER + léxico) | 40-70 | Requiere iteración y validación |
| Ampliación de descripciones con LLM | 60-100 | Coste en tokens/tiempo; debe validarse calidad |
| Generación de perfiles (TL;DR, variables) | 80-120 | El más costoso; depende de acceso al contenido |
| Validación y ajuste con muestreo | 30-50 | Juicio humano o LLM como juez |
| Integración en búsqueda híbrida y re-indexación | 30-50 | Re-generar embeddings y tsvector |
| **Total estimado** | **290-470 h** | Equivalente a 1,5-2,5 FTE de un mes |

### Viabilidad

| Aspecto | Evaluación |
|---|---|
| Técnica | Alta: las herramientas existen (LLM, NER, regex, KeyBERT). |
| Económica | Media: coste de LLM para 87.676 datasets; se puede hacer por lotes. |
| Temporal | Media-alta: 2-4 semanas de trabajo enfocado para las fases 1-5. |
| Calidad | Media: el LLM puede alucinar o generar descripciones genéricas; requiere validación. |

---

## 6. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| LLM genera descripciones genéricas o incorrectas | Alto | Validación por muestreo; score de confianza; fallback a descripción original |
| Coste/tiempo de LLM para 87.676 datasets | Medio | Batch nocturno; uso de `deepseek-v4-flash:cloud`; caching |
| No se puede acceder al contenido real de los datasets | Medio | Enriquecer solo desde metadatos existentes; marcar datasets con baja confianza |
| Mejora de embeddings no se traduce en mejor P@5 | Alto | Evaluación A/B con ground truth antes de desplegar |
| Dependencia del proveedor de LLM | Medio | Diseñar pipeline agnóstico del modelo |

---

## 7. Relación con smolagents

Como se menciona en `docs/ESTRATEGIA_LLM_DEPLOY.md`, **smolagents** puede orquestar el enriquecimiento de metadatos como un **agente multi-herramienta**:

| Herramienta del agente | Función |
|---|---|
| `extract_entities` | Extrae lugares, organismos, indicadores del título/descripción. |
| `infer_format` | Determina el formato desde URL o raw metadata. |
| `expand_description` | LLM que amplía la descripción. |
| `validate_quality` | Compara el metadato original y el enriquecido; asigna score. |
| `write_enriched_metadata` | Escribe el resultado en la BD solo si supera umbral de confianza. |

**Beneficio**: smolagents permite que el LLM decida qué herramienta aplicar según el dataset, en lugar de ejecutar un pipeline rígido.  
**Desventaja**: añade latencia y complejidad; recomendado como **fase 2** del enriquecimiento, no como primer pipeline.

---

## 8. Impacto esperado en el buscador

| Mejora | Efecto esperado | Métrica |
|---|---|---|
| Descripciones ampliadas | Embeddings más discriminativos | Mejora de P@5 y NDCG@10 |
| Keywords normalizados + tags controlados | Mejor recuperación léxica | Mayor recall en términos específicos |
| Formato completado | Filtros facetados más útiles | Mayor uso de filtros |
| URL de descarga | Mejor experiencia de usuario | Reducción de pasos hasta acceder al dato |
| Perfiles enriquecidos | Mejor TL;DR y complementariedad | Mayor satisfacción en chat y complementarios |

---

## 9. Próximos pasos recomendados

1. **Decidir alcance**: ¿enriquecer todos los campos o solo descripción + tags + formato?
2. **Diseñar schema de `datasets_enriched`**: mantener original + enriquecido + score de confianza.
3. **Prototipo con 100-1.000 datasets**: probar las técnicas y medir mejora de P@5.
4. **Definir umbral de confianza** para aceptar metadatos generados por LLM.
5. **Planificar batch de enriquecimiento masivo** y re-indexación.
6. **Evaluar smolagents** como orquestador en la fase 2.

---

## 10. Relación con otros documentos

- `docs/ESTRATEGIA_LLM_DEPLOY.md` — Estrategia de despliegue de LLM; smolagents se menciona como opción futura.
- `docs/BUSINESS_MODEL_CANVAS.md` — El plan de enriquecimiento es un coste clave para cualquier escenario de negocio.
- `02_Idear_Prototipar/entregables/DMC/digital_maturity_canvas.md` — Diagnóstico técnico previo del corpus.
- `docs/NARRATIVA_TFM.md` — Contexto del análisis del catálogo y calidad de metadatos.

---

*Plan de planificación. Las cifras de esfuerzo son estimaciones orientativas y deben ajustarse tras un prototipo piloto.*