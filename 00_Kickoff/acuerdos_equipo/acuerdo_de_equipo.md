# Acuerdo de Equipo

## Proyecto: Buscador Semántico de Datasets Públicos (datos.gob.es)

**Fecha de inicio:** 2026-07-01 (tras semana presencial EOI)
**Fecha objetivo de entrega:** 2026-10-25 (según guía académica EOI)
**Horas totales presupuestadas:** 1.200h (6 personas × 200h)
**Semana presencial EOI:** 21-27 junio 2026

---

## 1. Miembros del Equipo y Roles

| Miembro | Rol Principal | Responsabilidades | Horas/Semana Est. |
|---------|---------------|-------------------|-------------------|
| **Alejandro** | Product Owner / Project Manager | Visión del producto, priorización, contacto con stakeholders, facilitación de ceremonias | 8-10h |
| **Jordi** | Data Engineer | Pipeline de datos, limpieza, transformación, calidad de datos | 8-10h |
| **Jose Maria** | ML/NLP Engineer | Modelos de embeddings, búsqueda semántica, fine-tuning | 8-10h |
| **Gonzalo** | Backend / DevOps | API REST, infraestructura, Docker, deploy | 8-10h |
| **Daniel** | Frontend Developer | Interfaz de usuario, Streamlit, experiencia de usuario | 8-10h |
| **Pablo** | Technical Writer / Storytelling | Documentación, memoria, presentación, métricas de comunicación | 8-10h |

---

## 2. Responsabilidades por Sprint

### Sprint 1: Ingesta de Datos (Semanas 1-2)
- **Jordi (Lead):** Conexión a API CKAN, extracción de metadatos
- **Gonzalo:** Diseño de schema PostgreSQL
- **Jose Maria:** Análisis de campos relevantes para embeddings
- **Pablo:** Documentación del proceso de ingestión

### Sprint 2: Embeddings (Semanas 3-4)
- **Jose Maria (Lead):** Selección y evaluación de modelos
- **Jordi:** Pipeline de generación de vectores
- **Gonzalo:** Configuración de pgvector
- **Pablo:** Benchmark de modelos

### Sprint 3: Búsqueda Híbrida (Semanas 5-6)
- **Jose Maria (Lead):** Algoritmo de búsqueda semántica
- **Gonzalo:** API de búsqueda
- **Alejandro:** Definición de queries de test
- **Daniel:** Wireframes de resultados

### Sprint 4: Chatbot (Semanas 7-8)
- **Daniel (Lead):** Interfaz Streamlit
- **Gonzalo:** API conversacional
- **Jose Maria:** Generación de explicaciones
- **Pablo:** Testing de usabilidad

### Sprint 4: Evaluación (Semanas 9-10)
- **Alejandro (Lead):** Diseño de evaluación
- **Jose Maria:** Métricas de ranking
- **Pablo:** Dashboard de resultados
- **Todos:** Testing manual

### Sprint 5: Integración (Semanas 11-12)
- **Gonzalo (Lead):** Docker, tests, CI/CD
- **Jordi:** Optimización de pipeline
- **Daniel:** Pulido de UI
- **Pablo:** Documentación final

---

## 3. Herramientas y Comunicación

### Comunicación
- **Diario:** Slack/Discord (mensajes cortos, bloqueos)
- **Reuniones:**
  - Daily: 15 min (asíncrono en Slack si es necesario)
  - Sprint Planning: 2h al inicio de cada sprint
  - Sprint Review: 1h al final de cada sprint
  - Retrospective: 1h después de cada review

### Desarrollo
- **Repositorio:** GitHub
- **Base de datos:** PostgreSQL + pgvector (Docker)
- **API:** FastAPI
- **Frontend:** Streamlit
- **Modelos:** sentence-transformers (Hugging Face)
- **Containerización:** Docker + Docker Compose

### Documentación
- **Wiki/Notion:** Decisiones técnicas, acuerdos
- **Google Drive:** Documentos compartidos, presentaciones
- **Carpetas del proyecto:** Estructura acordada (00-10)

---

## 4. Definición de Hecho (Definition of Done)

Para considerar una tarea completada:

- [ ] Código funcionando en entorno local
- [ ] Tests unitarios pasando (si aplica)
- [ ] Documentación técnica actualizada en carpeta correspondiente
- [ ] Commit en repositorio con mensaje descriptivo
- [ ] Revisado por al menos un compañero
- [ ] Demo funcional (si es entregable de sprint)

---

## 5. Gestión de Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Cambios en API datos.gob.es | Media | Alto | Abstraer capa de conexión, cache de datos |
| Disponibilidad limitada del equipo | Alta | Medio | Documentación clara, parejas de respaldo |
| Problemas de rendimiento con embeddings | Media | Alto | Evaluar modelos ligeros, batching |
| Cambio de requisitos del tutor | Baja | Alto | Comunicación frecuente, prototipos tempranos |

---

## 6. Acuerdos de Trabajo

1. **Commits diarios:** Cada uno hace commit al menos cada 2-3 días
2. **Documentación inmediata:** Se documenta mientras se desarrolla, no al final
3. **Preguntar antes de bloquearse:** Si estás atascado >30 min, pedir ayuda
4. **Compartir avances:** Screenshot/demo en canal cada vez que hay avance visible
5. **Calidad sobre cantidad:** Mejor un entregable pulido que dos a medias

---

## 7. Firmas

Al firmar este documento, cada miembro se compromete a:
- Cumplir con sus responsabilidades
- Comunicar bloqueos y retrasos con anticipación
- Ayudar a otros miembros cuando sea necesario
- Mantener la calidad del proyecto

| Miembro | Firma | Fecha |
|---------|-------|-------|
| Alejandro | | |
| Jordi | | |
| Jose Maria | | |
| Gonzalo | | |
| Daniel | | |
| Pablo | | |

---

*Documento vivo: Se puede actualizar por acuerdo del equipo*
