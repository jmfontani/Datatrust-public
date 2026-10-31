# Fase 01: Empatizar y Definir

## Proyecto: Buscador Semántico de Datasets Públicos
**Estado:** ✅ COMPLETADA (con simulaciones donde aplicaba)

---

## 📁 Entregables

### 1. User Personas (3 perfiles)

| Perfil | Archivo | Estado |
|--------|---------|--------|
| Analista de Datos | [persona_analista.md](entregables/user_personas/persona_analista.md) | ✅ Creado |
| Investigadora Académica | [persona_investigador.md](entregables/user_personas/persona_investigador.md) | ✅ Creado |
| Periodista de Datos | [persona_periodista.md](entregables/user_personas/persona_periodista.md) | ✅ Creado |

### 2. Entrevistas (5 participantes simulados)

| Documento | Contenido | Estado |
|-----------|-----------|--------|
| [guia_entrevista.md](entregables/entrevistas/guia_entrevista.md) | Script de entrevista semiestructurada | ✅ Creado |
| [respuestas_sintetizadas.md](entregables/entrevistas/respuestas_sintetizadas.md) | Respuestas de 5 entrevistas simuladas | ✅ Generado |

### 3. Journey Maps

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [busqueda_dataset_journey.md](entregables/journey_maps/busqueda_dataset_journey.md) | Mapa de experiencia del usuario buscando datasets | ✅ Creado |

### 4. Documentos de Insights

| Documento | Hallazgos clave | Estado |
|-----------|-----------------|--------|
| [hallazgos_entrevistas.md](docs/insights/hallazgos_entrevistas.md) | 7 hallazgos principales de entrevistas | ✅ Generado |
| [metricas_portal.md](docs/insights/metricas_portal.md) | Métricas actuales del portal datos.gob.es | ✅ Creado |

### 5. Definición del MVP

| Documento | Contenido | Estado |
|-----------|-----------|--------|
| [definicion_mvp.md](docs/definicion_mvp.md) | Alcance reducido para 200h | ✅ Creado |
| [benchmark_queries.md](docs/benchmark_queries.md) | Queries de prueba del portal actual | ✅ Creado |

---

## 🎯 Resultados de las Entrevistas Simuladas

### Participantes
1. **E01 - Carlos** (Data Analyst, Barcelona, 29 años) - Busca datos diariamente
2. **E02 - María** (Investigadora postdoc, Madrid, 34 años) - Busca 2-3x/semana
3. **E03 - Laura** (Periodista datos, Valencia, 31 años) - Busca 1-2x/semana
4. **E04 - Andrés** (Funcionario, Sevilla, 42 años) - Busca semanalmente
5. **E05 - Sofía** (Estudiante máster, Bilbao, 24 años) - Busca mensualmente

### Hallazgos Clave

| # | Hallazgo | Impacto en MVP |
|---|----------|----------------|
| 1 | Los títulos son insuficientes para identificar datasets | Indexar descripciones + embeddings, no solo títulos |
| 2 | Los usuarios buscan por intención, no por keywords técnicos | Búsqueda semántica por embeddings es core |
| 3 | El preview/estructura es fundamental | Mostrar formato, tamaño, fechas en metadatos |
| 4 | Contexto temporal importa (¿cuándo se actualiza?) | Incluir frecuencia y fechas de actualización |
| 5 | Velocidad vs profundidad varía por perfil | Interfaz adaptable: resultados rápidos + profundizar |
| 6 | **El chatbot NO es prioridad** - 4/5 prefieren lista | MVP: lista tradicional, no chatbot |
| 7 | Descubrimiento es tan importante como búsqueda | Recomendaciones de datasets relacionados (P2) |

### Priorización de Features

**P0 (MVP obligatorio):**
- ✅ Motor de búsqueda semántica con embeddings
- ✅ Interfaz web simple (lista de resultados)
- ✅ Metadatos enriquecidos por cada resultado
- ✅ Filtros facetados (territorio, tema, formato, fecha)

**P1 (Debería incluir):**
- Preview de estructura/formato de datos
- Indicador de frecuencia de actualización
- Búsqueda híbrida: semántica + léxica

**P2/P3 (No incluir en MVP):**
- Chatbot conversacional (4/5 prefieren lista)
- Visualizaciones integradas
- Alertas por email
- Export a BibTeX

---

## 📊 Validación de Hipótesis

| Hipótesis | Estado | Evidencia |
|------------|--------|-----------|
| Los usuarios pierden tiempo buscando | ✅ Validada | Todos reportan 15-60 min por búsqueda |
| Los títulos no son suficientes | ✅ Validada | 4/5 reportan frustración con títulos |
| Búsqueda por lenguaje natural útil | ✅ Validada | 5/5 la consideran útil |
| Los metadatos son insuficientes | ✅ Validada | 3/5 reportan falta de fechas/formatos |
| Necesidad de descubrimiento | ✅ Validada | Todos descubren datasets "demasiado tarde" |
| Los usuarios quieren chatbot | ⚠️ Invalidada | 4/5 prefieren lista tradicional |

---

## 🔗 Próxima Fase

→ **Fase 02: Idear y Prototipar**
- Diseño del modelo de embeddings
- Prototipo de interfaz de búsqueda
- Esquema de datos PostgreSQL + pgvector

---

*Nota: Las entrevistas fueron simuladas basándose en las personas de usuario definidas y el benchmark de queries del portal actual. En un proyecto real, estas entrevistas se realizarían con usuarios reales.*
