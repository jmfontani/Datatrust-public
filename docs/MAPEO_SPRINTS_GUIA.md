# Mapeo de sprints: proyecto original → guía CD_IA (Valvanera Castro)

> **Objetivo:** fijar la correspondencia entre los sprints de desarrollo que ya ejecutó el equipo y los 6 sprints de la guía oficial, para que la memoria use **únicamente** la nomenclatura de la guía.
>
> **Regla de oro:** en la memoria solo se nombran los 6 sprints de la guía. Los sprints originales (carpetas 00–09) son hitos internos de trabajo y **no deben aparecer como "sprints"** en el documento final.

---

## 1. Por qué no hay mapeo 1:1

Las dos metodologías son de naturaleza distinta y no se pueden emparejar directamente:

| | Sprints originales (ejecutados) | Sprints de la guía (a entregar) |
|---|---|---|
| **Naturaleza** | Scrum de *desarrollo técnico* | Gestión de *proyecto de datos* |
| **Foco** | Construir el buscador | Justificar, planificar y defender el proyecto |
| **Unidad** | Incremento de producto (ingesta → embeddings → búsqueda → LLM) | Bloque de la memoria (problema → plan → beneficios → entrega → presentación) |
| **Resultado** | Código + métricas | Documento de 60 págs + POC + defensa |

**Consecuencia clave:** el desarrollo técnico completo (carpetas 03–09) se condensa **casi entero en el Sprint 2 de la guía** (Plan de Acción), porque la guía no tiene sprints de desarrollo separados. Los sprints 3–6 de la guía son bloques de la memoria que **aún no se han redactado**.

---

## 2. Mapeo maestro

| Sprint guía | Apartado(s) | Contenido técnico original que lo rellena | Estado |
|---|---|---|---|
| **Sprint 1** — Definición problema/solución | 1.1 Definición problema | 00 Kickoff + 01 Empatizar + 02 Idear (Ishikawa, personas, insights) | ✅ Material existente |
| | 1.2 Solución (Data Model) | DMC (11 bloques) + propuesta refinada | ✅ Material existente |
| | 1.3 Validación Data Model | Matriz H1–H17 + encuesta/simulación (informe DataTrust) | ✅ Material existente |
| | 1.4 Análisis contexto | PESTEL + análisis competitivo europeo | ✅ Material existente |
| | 1.5 Análisis preliminar de datos | **Auditoría de metadatos (87.676 datasets)** | ✅ Material existente |
| | 1.6 Diagnóstico (DAFO) | DAFO consolidado | ✅ Material existente |
| **Sprint 2** — Plan de Acción | 2.1 Alcance (objetivos y métricas) | Objetivos del DMC + métricas de evaluación (P@5, NDCG@10) | ✅ Material existente |
| | 2.2 Recopilación y origen de datos | 03 Ingesta (pipeline, estrategias de extracción) | ✅ **Redactado** |
| | 2.3 Desarrollo analítico | 04 Embeddings + 05 Búsqueda + 08 LLM + 09 RAGAS | ✅ Material existente |
| | 2.4 Recursos | 07 Integración (Docker, infraestructura, stack) | ✅ Material existente |
| | 2.5 Gestión del tiempo | Cronograma/Gantt | ⚠️ Parcial (Gantt en Sprint 2 original) |
| **Sprint 3** — Beneficios-Riesgos-Rentabilidad | 3.1 Beneficios | Nuevo (apoyado en DAFO y análisis competitivo) | ❌ Por redactar |
| | 3.2 Gestión de riesgos | Nuevo (matriz probabilidad×impacto) | ❌ Por redactar |
| | 3.3 Rentabilidad | Nuevo (VAN/TIR, coste-beneficio institucional) | ❌ Por redactar |
| **Sprint 4** — Resumen Ejecutivo / One Page | 4.1 Resumen Ejecutivo | Nuevo (3–5 págs) | ❌ Por redactar |
| | 4.2 One Page | Nuevo (1 hoja) | ❌ Por redactar |
| **Sprint 5** — Entrega | 5 | Nuevo (formato, índice, bibliografía) | ❌ Por redactar |
| **Sprint 6** — Presentación | 6 | Nuevo (slides 15 min + FAQ) | ❌ Por redactar |

---

## 3. Detalle del Sprint 2 (el que concentra el desarrollo técnico)

El Sprint 2 de la guía es el más denso: absorbe **todo** el desarrollo técnico. Mapeo interno:

| Apartado guía | Carpeta original | Contenido |
|---|---|---|
| 2.1 Alcance | 02 Idear (DMC) + 06 Evaluación | Objetivos medibles + KPIs (P@5=0.70, NDCG@10=0.79) |
| 2.2 Recopilación | 03 Ingesta | Pipeline de ingesta, estrategias de extracción, calidad |
| 2.3 Desarrollo analítico | 04 Embeddings + 05 Búsqueda + 08 LLM + 09 RAGAS | Modelado, visualización, arquitectura |
| 2.4 Recursos | 07 Integración | Docker, PostgreSQL+pgvector, stack, recursos humanos |
| 2.5 Tiempo | (Gantt) | Cronograma del proyecto |

---

## 4. Solapes entre apartados (cómo evitar duplicar)

Algunos materiales sirven a **dos apartados distintos** de la guía. Regla: presentar el detalle en el apartado que le corresponde por función, y en el otro hacer **referencia cruzada breve**.

| Material | Apartado principal (detalle completo) | Apartado secundario (referencia breve) |
|---|---|---|
| **Auditoría de metadatos** (5 hallazgos) | **1.5** Análisis preliminar de datos | **2.2.2** Evaluación de calidad (resumen + "ver 1.5") |
| **DAFO** | **1.6** Diagnóstico | **3.1/3.2** Beneficios y riesgos (insumo) |
| **Análisis competitivo** | **1.4.2** Análisis competitivo | **3.1** Beneficios (posicionamiento) |
| **Métricas de evaluación** (P@5, NDCG) | **2.1** Alcance (KPIs) | **2.3** Desarrollo analítico (resultados) |
| **Arquitectura** | **2.3.4** Diagrama de arquitectura | **2.4** Recursos (infraestructura) |

---

## 5. Nomenclatura permitida en la memoria

| ✅ Usar | ❌ No usar |
|---|---|
| "Sprint 1 (Definición problema/solución)" | "Sprint 1 (Ingesta)" |
| "apartado 1.5 (Análisis preliminar de datos)" | "Sprint 1 de ingesta" |
| "apartado 2.2 (Recopilación de datos)" | "Sprint 3 de búsqueda" |
| "fase de desarrollo analítico (2.3)" | "Sprint 6 de LLM" |
| "el análisis preliminar (1.5)" | "el análisis de metadatos del Sprint 1" |

**Regla práctica:** si una frase necesita mencionar un sprint original para tener sentido, reformúlala refiriéndote al **apartado de la guía** donde vive ese contenido.

---

## 6. Plan de trabajo restante

| Bloque | Estado | Prioridad |
|---|---|---|
| 2.2 Recopilación de datos | ✅ Redactado (pendiente corregir referencia a "Sprint 1") | — |
| 1.1–1.6 (Sprint 1) | Material existente, falta redactar en formato memoria | Alta |
| 2.1, 2.3, 2.4, 2.5 (Sprint 2) | Material existente, falta redactar | Alta |
| 3.1–3.3 (Sprint 3) | Por redactar desde cero | Media |
| 4.1–4.2 (Sprint 4) | Por redactar desde cero | Media |
| 5 (Sprint 5) | Por redactar desde cero | Baja |
| 6 (Sprint 6) | Por redactar desde cero | Baja |

---

*Documento de referencia interna del equipo. No forma parte de la memoria.*
