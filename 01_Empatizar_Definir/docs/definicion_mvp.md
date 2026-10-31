# Definición del MVP

## Proyecto: Buscador Semántico de Datasets Públicos
**Fecha:** Junio 2026
**Estado:** BORRADOR - Pendiente validación con equipo

---

## 🎯 Alcance MVP

### SÍ incluye (Must have)

| Feature | Descripción | Justificación |
|---------|-------------|---------------|
| **Ingesta datos.gob.es** | Pipeline de extracción de metadatos vía CKAN API | Fuente primaria acordada |
| **Embeddings semánticos** | Modelo sentence-transformers multilingüe (384 dims) | Core del producto |
| **Búsqueda híbrida** | Semántica (cosine similarity) + léxica (BM25) | Solución al problema |
| **API REST** | FastAPI con endpoints de búsqueda y dataset | Base para integraciones |
| **Chatbot básico** | Streamlit con preguntas en lenguaje natural | Interfaz conversacional |
| **4 casos de uso** | Despoblación, salud/ambiente, vivienda/turismo, educación/renta | Validación focalizada |
| **Trazabilidad** | Links verificables a datos.gob.es | Valor diferencial |
| **Benchmark inicial** | 50 queries con métricas Precision@5, Recall@10 | Evaluación objetiva |

### NO incluye (Won't have - MVP)

| Feature | Motivo | Fase futura |
|---------|--------|-------------|
| data.europa.eu | Scope, prioridad datos.gob.es | Fase 2 |
| Autenticación de usuarios | No crítico para demostración | Post-MVP |
| Sistema de alertas | Nice-to-have | Post-MVP |
| Visualizaciones integradas | Esfuerzo UI adicional | Post-MVP |
| Fine-tuning de modelo | Suficiente modelo pre-entrenado | Post-MVP si eval lo indica |
| Soporte multi-idioma (fr, de) | Demografía española | Expansión EU |
| Cache distribuido (Redis) | Carga inicial manageable | Escalado |

### Quizás incluye (Could have - si hay tiempo)

| Feature | Condición |
|---------|-----------|
| Dashboard de métricas | Si hay tiempo en Sprint 5 |
| Exportar resultados (CSV, JSON) | Si el API lo permite fácil |
| Filtros facetados avanzados | Si no complica la búsqueda |

---

## 📐 Arquitectura MVP simplificada

```
Usuario → Streamlit UI → FastAPI → PostgreSQL+pgvector
                         ↓
                    datos.gob.es (CKAN API)
```

**Flujo:**
1. Usuario pregunta en lenguaje natural
2. Streamlit envía a FastAPI
3. FastAPI genera embedding de la query
4. Búsqueda híbrida en PostgreSQL
5. Retorna datasets rankeados con metadatos + URLs

---

## ✅ Criterios de aceptación MVP

### Funcionales

- [ ] 90%+ de datasets de datos.gob.es indexados
- [ ] Búsqueda responde en < 2 segundos
- [ ] Top 5 resultados contienen dataset relevante en 80%+ de queries benchmark
- [ ] Cada resultado tiene link verificable a datos.gob.es
- [ ] Chatbot no genera datos inventados (0 alucinaciones)

### Técnicos

- [ ] Pipeline de ingestía ejecutable con un comando
- [ ] API documentada (OpenAPI/Swagger)
- [ ] Docker Compose levanta todo el stack
- [ ] Tests unitarios en core (búsqueda, embeddings)

### Demo

- [ ] 4 casos de uso demostrables end-to-end
- [ ] Video de demo de 5 minutos
- [ ] Presentación para defensa (15 min)

---

## 📅 Timeline MVP

| Sprint | Fechas | Focus | Entregable |
|--------|--------|-------|------------|
| 1 | Julio W1-2 | Ingesta | Datos en PostgreSQL |
| 2 | Julio W3-4 | Embeddings | Vectores indexados |
| 3 | Agosto W1-2 | Búsqueda | API funcionando |
| 4 | Agosto W3-4 | Chatbot | UI conversacional |
| 5 | Sept W1 | Evaluación | Métricas benchmark |
| 6 | Sept W2 | Integración | Docker + tests |

---

## 🚪 Gate de decisión

**Fecha:** 16 de junio 2026 (Sprint Review Fase 01)

**Para pasar a Fase 02 (Idear/Prototipar) se necesita:**

- [ ] MVP definido y acordado por el equipo
- [ ] Casos de uso validados con usuarios reales (3-5)
- [ ] Benchmark queries creadas y ejecutadas
- [ ] Fecha de entrega confirmada: 25/10/2026

---

*Documento vivo: Se actualiza tras feedback del equipo y tutor*
