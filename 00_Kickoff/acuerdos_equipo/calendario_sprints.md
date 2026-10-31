# Calendario de Sprints

## Proyecto: Buscador Semántico de Datasets Públicos

**Fecha de inicio:** 2026-05-20  
**Fecha de entrega:** 2026-09-15  
**Duración total:** ~17 semanas

---

## 📅 DISTRIBUCIÓN TEMPORAL

### FASE 0: KICKOFF (Semanas 0-1)

| Semana | Fechas | Actividades | Entregables |
|--------|--------|-------------|-------------|
| 0 | 20-26 Mayo | Setup de equipo, asignación de roles, acuerdos | Acuerdo de equipo, calendario |
| 1 | 27 Mayo - 02 Junio | Selección de herramientas, repositorio, primer contacto API | Repo configurado, script de prueba |

---

### FASE 1: EMPATIZAR Y DEFINIR (Semanas 2-3)

| Semana | Fechas | Actividades | Entregables |
|--------|--------|-------------|-------------|
| 2 | 03-09 Junio | Entrevistas informales, benchmark, análisis exploratorio | Notas de entrevistas, tabla benchmark |
| 3 | 10-16 Junio | User personas, journey maps, definición del MVP | 3-4 personas, journey map, MVP definido |

**Sprint Review:** 16 de Junio - Demo de insights y presentación de personas

---

### FASE 2: IDEAR Y PROTOTIPAR (Semanas 4-5)

| Semana | Fechas | Actividades | Entregables |
|--------|--------|-------------|-------------|
| 4 | 17-23 Junio | Wireframes, PoC de embeddings, validación | Wireframes v1, PoC funcionando |
| 5 | 24-30 Junio | Iteración de wireframes, DMC final, arquitectura | Prototipos v2, DMC v2, diagrama de arquitectura |

**Sprint Review:** 30 de Junio - Demo de prototipos y arquitectura

---

### FASE 3: DESARROLLO (Semanas 6-13)

#### Sprint 1: INGESTA DE DATOS (Semanas 6-7)

| Semana | Fechas | Actividades | Entregables |
|--------|--------|-------------|-------------|
| 6 | 01-07 Julio | Conexión CKAN API, extracción de metadatos | Pipeline de ingestión básico |
| 7 | 08-14 Julio | Limpieza, normalización, schema PostgreSQL | Datos limpios, schema definido |

**Sprint Review:** 14 de Julio - Pipeline funcionando con datos reales

---

#### Sprint 2: EMBEDDINGS (Semanas 8-9)

| Semana | Fechas | Actividades | Entregables |
|--------|--------|-------------|-------------|
| 8 | 15-21 Julio | Evaluación de modelos, generación de embeddings | Comparativa de modelos, vectores generados |
| 9 | 22-28 Julio | Indexación en pgvector, optimización | Base de datos con vectores indexados |

**Sprint Review:** 28 de Julio - Demo de búsqueda básica por similitud

---

#### Sprint 3: BÚSQUEDA HÍBRIDA (Semanas 10-11)

| Semana | Fechas | Actividades | Entregables |
|--------|--------|-------------|-------------|
| 10 | 29 Julio - 04 Agosto | Búsqueda semántica + léxica, ranking combinado | API de búsqueda funcionando |
| 11 | 05-11 Agosto | Refinamiento de algoritmos, tests | Queries de benchmark definidas |

**Sprint Review:** 11 de Agosto - Demo de búsqueda híbrida

---

#### Sprint 4: CHATBOT (Semanas 12-13)

| Semana | Fechas | Actividades | Entregables |
|--------|--------|-------------|-------------|
| 12 | 12-18 Agosto | Desarrollo de interfaz Streamlit, API conversacional | Chatbot básico funcionando |
| 13 | 19-25 Agosto | Explicaciones de resultados, refinamiento UI | Chatbot con explicaciones, UI pulida |

**Sprint Review:** 25 de Agosto - Demo del chatbot completo

---

### FASE 4: EVALUACIÓN E INTEGRACIÓN (Semanas 14-15)

#### Sprint 5: EVALUACIÓN (Semana 14)

| Semana | Fechas | Actividades | Entregables |
|--------|--------|-------------|-------------|
| 14 | 26 Agosto - 01 Septiembre | Métricas de ranking, testing manual, recolección de feedback | Dashboard de métricas, informe de evaluación |

**Sprint Review:** 01 de Septiembre - Presentación de métricas

---

#### Sprint 6: INTEGRACIÓN (Semana 15)

| Semana | Fechas | Actividades | Entregables |
|--------|--------|-------------|-------------|
| 15 | 02-08 Septiembre | Dockerización, tests end-to-end, optimización | Proyecto dockerizado, tests pasando |

**Sprint Review:** 08 de Septiembre - Demo del sistema completo

---

### FASE 5: DOCUMENTACIÓN Y ENTREGA (Semanas 16-17)

| Semana | Fechas | Actividades | Entregables |
|--------|--------|-------------|-------------|
| 16 | 09-15 Septiembre | Redacción de memoria, pulido de documentación | Memoria v1 completa |
| 17 | 16-20 Septiembre | Preparación de defensa, ensayos | Presentación final, demo preparado |

**ENTREGA FINAL:** 15 de Septiembre (Memoria)  
**DEFENSA:** 15-20 de Septiembre (Pendiente de confirmar)

---

## 📊 RESUMEN DE HITOS

| Fecha | Hito | Estado |
|-------|------|--------|
| 16 Junio | Empatizar/Definir completado | 🔵 Pendiente |
| 30 Junio | Idear/Prototipar completado | 🔵 Pendiente |
| 14 Julio | Sprint 1: Ingesta | 🔵 Pendiente |
| 28 Julio | Sprint 2: Embeddings | 🔵 Pendiente |
| 11 Agosto | Sprint 3: Búsqueda | 🔵 Pendiente |
| 25 Agosto | Sprint 4: Chatbot | 🔵 Pendiente |
| 01 Septiembre | Sprint 4: Evaluación | 🔵 Pendiente |
| 08 Septiembre | Sprint 5: Integración | 🔵 Pendiente |
| 15 Septiembre | Entrega memoria | 🔵 Pendiente |
| 15-20 Septiembre | Defensa | 🔵 Pendiente |

---

## 🏖️ VACACIONES Y BLOQUEOS

**Periodos de baja disponibilidad estimados:**
- Verano (Julio-Agosto): Reducir a ~4-5h/semana por persona
- Posibles semanas de vacaciones individuales: Comunicar con anticipación

**Buffers incluidos:**
- Semana 16: Buffer de documentación
- Semana 17: Buffer de defensa

---

## 📅 PRÓXIMA REUNIÓN

**Sprint Planning 1:** 27 de Mayo, 2026  
**Objetivo:** Definir backlog del Sprint 1 (Ingesta)

---

*Calendario vivo: Actualizar si hay cambios en fechas o disponibilidad*
