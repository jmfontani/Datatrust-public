# Digital Maturity Canvas (DMC)

## Proyecto: Buscador Semántico de Datasets Públicos
**Fase:** 02 - Idear y Prototipar
**Fecha:** Mayo-Junio 2026

---

## 1. PROBLEMA / OPORTUNIDAD

**Problema:**
Los usuarios de datos abiertos en España pierden entre 15-60 minutos buscando datasets relevantes en datos.gob.es. El buscador actual funciona por palabras clave exactas, no entiende intención ni contexto. Los títulos son insuficientes, los metadatos incompletos, y no hay preview de los datos.

**Oportunidad:**
Aplicar embeddings semánticos para permitir búsqueda por intención ("pueblos que se vacían" → datasets de despoblación, censo, migraciones). Reducir tiempo de búsqueda de 15-60 min a <2 minutos.

---

## 2. SOLUCIÓN

**Descripción:**
Sistema de búsqueda semántica de datasets públicos que:
1. Indexa metadatos con embeddings multilingües
2. Permite búsqueda en lenguaje natural
3. Rankea resultados por relevancia semántica + léxica
4. Muestra metadatos enriquecidos con filtros facetados
5. Genera explicaciones de relevancia por resultado

**Diferenciación vs portal actual:**
- ❌ Actual: keywords exactas, lista plana, sin preview
- ✅ Propuesto: semántica, rankeada, metadatos ricos, trazable

---

## 3. FUENTES DE DATOS

| Fuente | Tipo | Formato | Estado |
|--------|------|---------|--------|
| datos.gob.es | Primaria | JSON (Linked Data API) | ✅ Descargado: 134.150 datasets |
| data.europa.eu | Secundaria | JSON/DCAT | ⏳ Fase 2 |
| CKAN API | Primaria | JSON | ✅ Validado |
| SPARQL endpoint | Primaria | RDF/DCAT-AP | ✅ Disponible |

**Metadatos extraídos:**
- Título (es/en), descripción (es/en)
- Temas DCAT, keywords, tags
- Organismo publicador, territorio, licencia
- Formato, tamaño, fechas (publicación/modificación)
- Distribuciones (URLs descarga)

---

## 4. CLIENTES / GRUPOS DE INTERÉS

**Usuarios primarios (3 personas):**

| Persona | Rol | Frecuencia | Necesidad principal |
|-----------|-----|-----------|---------------------|
| Carlos (Analista) | Data Analyst, Barcelona | Diaria | Velocidad, metadatos completos |
| María (Investigadora) | Postdoc, Madrid | 2-3x/semana | Profundidad, trazabilidad |
| Laura (Periodista) | Datos, Valencia | 1-2x/semana | Urgencia, contexto temporal |

**Stakeholders:**
- Equipo de gobierno abierto (datos.gob.es)
- Tutor académico (EOI)
- Revisores de TFM (3 evaluadores)

---

## 5. ACTIVIDADES CLAVE

| Actividad | Sprint | Responsable | Estado |
|-----------|--------|-------------|--------|
| Ingesta de metadatos (datos.gob.es) | Sprint 1 | Datos | ✅ Completado |
| Limpieza y normalización | Sprint 1 | Datos | 🔄 Pendiente |
| Generación de embeddings | Sprint 2 | NLP/ML | ⏳ Planificado |
| Motor de búsqueda híbrida | Sprint 3 | NLP/ML + Backend | ⏳ Planificado |
| API REST (FastAPI) | Sprint 4 | Backend | ⏳ Planificado |
| Interfaz de lista de resultados | Sprint 4 | Frontend/UX | ⏳ Planificado |
| Benchmark y evaluación | Sprint 5 | NLP/ML + Storytelling | ⏳ Planificado |
| Docker + deploy | Sprint 6 | Backend + Storytelling | ⏳ Planificado |

---

## 6. TIPO DE ANÁLISIS

### Análisis Descriptivo (Sprint 1)
- Estadísticas del catálogo: distribución por tema, territorio, formato
- Calidad de metadatos: completitud, consistencia
- Identificación de datasets "huérfanos" (sin descripción)

### Análisis Predictivo (Sprint 2-3)
- Embeddings para predicción de relevancia
- Ranking de resultados por similitud semántica
- Recomendación de datasets relacionados (fase 2)

### Análisis Prescriptivo (Sprint 3-4)
- Sugerencia de filtros facetados según query
- Explicaciones de por qué un dataset es relevante
- Optimización de queries (expansión semántica)

---

## 7. KPIs (Indicadores Clave)

| KPI | Baseline | Objetivo | Métrica |
|-----|----------|----------|---------|
| Precisión@5 | N/A (portal sin ranking) | > 70% | % relevantes en top 5 |
| Recall@10 | N/A | > 60% | % datasets relevantes encontrados |
| Tiempo de búsqueda | 15-60 min | < 2 min | Minutos hasta dataset válido |
| Cobertura del catálogo | 0% | > 90% | % datasets indexados / total |
| Satisfacción usuario | N/A | > 4/5 | Encuesta post-búsqueda |

---

## 8. RECURSOS CLAVE

**Técnicos:**
- Python 3.11+, PostgreSQL 15+, pgvector
- sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
- FastAPI, Streamlit, Docker
- GPU opcional para embeddings (CPU viable con batching)

**Humanos:**
- 6 personas × 200h = 1.200h totales
- Roles: Producto, Datos, NLP/ML, Backend, Frontend/UX, Storytelling

**Datos:**
- 134.150 datasets indexados
- ~147 MB de metadatos + vectores (~500 MB estimado con embeddings)

---

## 9. COSTE DE IMPLEMENTACIÓN

| Categoría | Estimación | Notas |
|-----------|-----------|-------|
| Infraestructura cloud | 0€ (fase MVP local) | PostgreSQL local, sin GPU |
| Modelo embeddings | 0€ (open source) | Hugging Face sentence-transformers |
| Herramientas | 0€ (open source) | Python, FastAPI, Streamlit, Docker |
| Tiempo equipo | 1.200h | 6 personas × 200h |
| **Coste total MVP** | **~0€** | Solo coste oportunidad (tiempo) |

**Escalado (post-MVP):**
- Servidor cloud (AWS/GCP): ~50-100€/mes
- GPU para embeddings: ~100-200€/mes
- data.europa.eu: coste adicional de ingesta

---

## 10. RIESGOS Y MITIGACIONES

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Metadatos de baja calidad | Alta | Alto | Pipeline de limpieza + datasets con descripción vacía marcados |
| Embeddings no capturan intención | Media | Alto | Búsqueda híbrida (semántica + léxica) como fallback |
| Tiempo de respuesta > 2s | Media | Medio | Indexación pgvector + caché + optimización queries |
| Demasiado scope para 200h | Alta | Alto | MVP enfocado: solo datos.gob.es, 4 casos de uso, lista no chatbot |
| Dependencia de datos.gob.es API | Media | Medio | Cache local + tolerancia a fallos + datos descargados |
| Fine-tuning insuficiente | Baja | Medio | Modelo pre-entrenado multilingüe ya cubre español |
| Dificultad evaluación subjetiva | Media | Medio | Benchmark con juicio humano + métricas objetivas |

---

## 11. BENEFICIOS / IMPACTOS

**Beneficios directos:**
- Reducción de 15-60 min a <2 min en búsquedas de datasets
- Descubrimiento de datasets relevantes que keywords exactas no encuentran
- Trazabilidad: cada resultado tiene link verificable a datos.gob.es

**Impactos sociales:**
- Democratización del acceso a datos públicos
- Facilita investigación académica, periodismo de datos, transparencia
- Reduce barrera de entrada para analistas junior y ciudadanos

**Impactos académicos (TFM):**
- Demostración práctica de NLP + vector search
- Benchmark reproducible con métricas objetivas
- Código open source reutilizable

---

## 🚪 Gate de decisión Fase 02

**Para pasar a Fase 03 (Sprint 1 - Ingesta completa + Embeddings):**

- [x] DMC completado y validado
- [x] Wireframes de interfaz definidos
- [ ] Prototipo básico validado (Streamlit mock)
- [ ] Esquema de datos PostgreSQL definido
- [ ] Benchmark queries refinadas

---

*Canvas basado en metodología DMC de EOI - Inteligencia Artificial y Ciencia de Datos*
