# Ideas Descartadas - Fase 02

## Proyecto: Buscador Semántico de Datasets Públicos
**Fase:** 02 - Idear y Prototipar
**Propósito:** Documentar ideas consideradas y rechazadas, con justificación

---

## ❌ Idea 1: Chatbot conversacional como interfaz principal

### Chatbot como modo alternativo (Fase 2)

**Descripción:**
Una vez validada la búsqueda basada en listas como opción principal, se plantea incorporar un chatbot como **modo alternativo de navegación** (no principal) para usuarios que prefieren explorar datos conversacionalmente.

**Funcionalidades previstas:**
- Navegar por los datasets mediante preguntas de seguimiento ("¿y qué datos hay de 2023?", "muéstrame solo los de Castilla y León")
- Obtener resúmenes explicativos de por qué ciertos datasets son relevantes
- Descubrir conexiones entre datasets que no son evidentes en la vista de lista

**Condición de implementación:**
El chatbot se implementará solo si la búsqueda por lista demuestra valor en la evaluación del MVP (Sprint 5).

**Por qué se descartó para MVP:**
- Las entrevistas de Fase 01 revelaron que **4/5 usuarios prefieren lista tradicional** sobre chatbot
- Los usuarios valoran velocidad y control directo sobre la conversación
- El chatbot añade latencia y complejidad innecesaria para el MVP
- Mayor esfuerzo de desarrollo (gestión de contexto, prompts, edge cases)

**Alternativa adoptada:**
Lista de resultados con búsqueda semántica "por detrás". La IA funciona en el motor de ranking, no en la interfaz.

**Revisión para Fase 2 (documentado):**
Ver arriba en "Chatbot como modo alternativo (Fase 2)" — Se replantea como modo secundario tras validación del MVP.

---

## ❌ Idea 2: Modelo de lenguaje grande (LLM) para respuestas

**Descripción:**
Usar GPT-4/Claude/etc. para generar respuestas textuales sobre los datasets encontrados.

**Por qué se descartó:**
- Riesgo de alucinaciones (generar datos inexistentes)
- Coste económico de APIs externas
- No aporta valor diferencial respecto a ChatGPT
- El foco es encontrar datasets, no generar análisis

**Alternativa adoptada:**
Embeddings con modelo sentence-transformers (open source, local, sin coste). Explicaciones de relevancia generadas por reglas heurísticas sobre metadatos.

---

## ❌ Idea 3: Indexar contenido de los archivos (no solo metadatos)

**Descripción:**
Descargar y analizar el contenido real de los datasets (CSV, XLSX) para indexar columnas, valores, estadísticas.

**Por qué se descartó:**
- **134.150 datasets** × descarga + análisis = **prohibitive** para 200h
- Tamaño total estimado: decenas/hundreds de GB
- Legalidad: reutilización de datos públicos OK, pero almacenamiento masivo complica
- El MVP se enfoca en **metadatos** como proxy de contenido

**Alternativa adoptada:**
Indexar solo metadatos (título, descripción, keywords). La descripción suele contener suficiente contexto para búsqueda semántica.

**Posible revisión:**
Fase 2: Para datasets populares, añadir preview de estructura (nombres de columnas, tipos) si la API lo permite sin descarga completa.

---

## ❌ Idea 4: Múltiples fuentes de datos desde el inicio

**Descripción:**
Indexar simultáneamente datos.gob.es, data.europa.eu, Kaggle, UCI ML Repository, etc.

**Por qué se descartó:**
- **Scope muy amplio** para 6 meses / 200h
- Cada fuente tiene API diferente, metadatos distintos, necesita conector propio
- datos.gob.es ya tiene 134k datasets, suficiente para demostrar el concepto
- Calidad de metadatos varía enormemente entre fuentes

**Alternativa adoptada:**
Foco exclusivo en **datos.gob.es** como fuente primaria. data.europa.eu marcada como "Fase 2".

---

## ❌ Idea 5: Fine-tuning del modelo de embeddings

**Descripción:**
Entrenar/fine-tunear un modelo específico para embeddings de datasets en español.

**Por qué se descartó:**
- Requiere dataset de pares (query, dataset relevante) que no existe
- sentence-transformers multilingüe ya funciona bien en español
- Esfuerzo de etiquetado + entrenamiento > beneficio para MVP
- 384 dims de paraphrase-multilingual-MiniLM son suficientes

**Alternativa adoptada:**
Usar modelo pre-entrenado sin fine-tuning. Evaluar en Sprint 5; si métricas son insuficientes, reconsiderar.

---

## ❌ Idea 6: Motor de búsqueda con Elasticsearch/Solr

**Descripción:**
Usar Elasticsearch o Apache Solr como motor de búsqueda en lugar de PostgreSQL + pgvector.

**Por qué se descartó:**
- Añade complejidad de infraestructura (nuevo servicio)
- pgvector en PostgreSQL cubre tanto búsqueda semántica (vectores) como léxica (full-text)
- PostgreSQL es suficiente para 134k registros
- Equipo ya familiarizado con SQL, no necesita aprender query DSL

**Alternativa adoptada:**
PostgreSQL + pgvector para todo (datos estructurados + embeddings + full-text search).

---

## ❌ Idea 7: Sistema de recomendación colaborativo

**Descripción:**
"Usuarios que buscaron X también buscaron Y" (tipo Netflix/Amazon).

**Por qué se descartó:**
- Requiere datos de usuarios y comportamiento (no tenemos usuarios reales)
- Privacidad: almacenar historial de búsquedas complica GDPR
- Para MVP, recomendación basada en similitud de embeddings es suficiente

**Alternativa adoptada:**
Recomendación por similitud semántica: "Datasets relacionados" basado en distancia de embeddings.

---

## ❌ Idea 8: Visualizaciones integradas de datasets

**Descripción:**
Previsualizar gráficos, mapas, tablas de los datos directamente en el buscador.

**Por qué se descartó:**
- Requiere parsear y renderizar múltiples formatos (CSV, GeoJSON, SHP...)
- Esfuerzo de frontend significativo (librerías de visualización)
- No es core del problema: encontrar datasets, no analizarlos
- Los usuarios preferen descargar y analizar con sus herramientas (R, Python, Excel)

**Alternativa adoptada:**
Metadatos enriquecidos (formato, tamaño, fechas, descripción) como "preview" suficiente.

**Posible revisión:**
P2: Preview de estructura (nombres de columnas, tipos de datos) para formatos tabulares.

---

## ❌ Idea 9: Autenticación de usuarios y perfiles

**Descripción:**
Sistema de login, perfiles de usuario, guardar búsquedas, favoritos, historial.

**Por qué se descartó:**
- No crítico para demostración del concepto de búsqueda semántica
- Añade complejidad de seguridad, GDPR, gestión de contraseñas
- El MVP es público/anónimo
- Funcionalidad "nice-to-have" que consume tiempo de desarrollo

**Alternativa adoptada:**
Sin autenticación. Guardar últimas búsquedas en localStorage del navegador (opcional).

**Posible revisión:**
Post-MVP: Si se despliega como servicio público, añadir autenticación para favoritos.

---

## ❌ Idea 10: Pipeline ETL en tiempo real

**Descripción:**
Ingesta continua de datos.gob.es (webhooks, polling cada X horas) para mantener índice actualizado.

**Por qué se descartó:**
- Los datasets públicos no cambian con frecuencia (actualizaciones mensuales/anuales)
- Pipeline en tiempo real = complejidad innecesaria para MVP
- 134k datasets ingestados una vez son suficientes para demo

**Alternativa adoptada:**
Ingesta batch manual. Re-ingesta periódica (semanal/mensual) con script simple.

---

## 📊 Resumen de decisiones

| Dimensión | Decisión | Justificación |
|-----------|----------|---------------|
| **Interfaz** | Lista de resultados (principal) + Chatbot como modo alternativo en Fase 2 | 4/5 usuarios prefieren lista; chatbot replanteado para fase 2 tras validación MVP |
| **Modelo NLP** | sentence-transformers (pre-entrenado) | Suficiente, sin coste |
| **Alcance datos** | Solo datos.gob.es | 134k datasets, scope manejable |
| **Profundidad indexación** | Solo metadatos | Contenido real prohibitive |
| **Motor búsqueda** | PostgreSQL + pgvector | Todo-en-uno, sin infra extra |
| **Recomendación** | Similitud semántica | Sin datos de usuarios |
| **Visualización** | Metadatos + preview básico | No analizar, solo encontrar |
| **Autenticación** | Ninguna | No crítico para MVP |
| **Actualización** | Batch manual | Datos estáticos |

---

*Documento de ideas descartadas - Fase 02. Revisar en Sprint 6 si el scope permite recuperar alguna idea.*
