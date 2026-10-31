# Fase 02: Idear y Prototipar

## Proyecto: Buscador Semántico de Datasets Públicos
**Estado:** ✅ COMPLETADA
**Fecha:** Mayo-Junio 2026

---

## 📁 Entregables Generados

### 1. Digital Maturity Canvas (DMC)

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [digital_maturity_canvas.md](entregables/DMC/digital_maturity_canvas.md) | Canvas completo con 11 bloques DMC | ✅ Creado |

**Bloques cubiertos:**
1. ✅ Problema/Oportunidad
2. ✅ Solución
3. ✅ Fuentes de Datos
4. ✅ Clientes/Grupos de Interés
5. ✅ Actividades Clave
6. ✅ Tipo de Análisis (Descriptivo, Predictivo, Prescriptivo)
7. ✅ KPIs
8. ✅ Recursos Clave
9. ✅ Coste de Implementación
10. ✅ Riesgos y Mitigaciones
11. ✅ Beneficios/Impactos

### 2. Wireframes

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [wireframe_busqueda_principal.md](entregables/wireframes/wireframe_busqueda_principal.md) | Diseño ASCII + especificaciones de UI | ✅ Creado |

**Pantallas diseñadas:**
- ✅ Pantalla principal (barra de búsqueda + filtros + resultados)
- ✅ Estado inicial (sin búsqueda)
- ✅ Estado sin resultados
- ✅ Pantalla de detalle de dataset
- ✅ Responsive (desktop, tablet, móvil)

### 3. Prototipos

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [prototipo_streamlit.md](entregables/prototipos/prototipo_streamlit.md) | Especificación técnica del prototipo funcional | ✅ Creado |
| `codigo/poc/app.py` | Aplicación Streamlit con TF-IDF (baseline) | ✅ Implementado |
| `codigo/poc/app_v2.py` | Aplicación Streamlit con embeddings semánticos | ✅ Implementado |
| `codigo/poc/utils/search_mock.py` | Motor TF-IDF con scikit-learn | ✅ Implementado |
| `codigo/poc/utils/search_semantic.py` | Motor semántico con Sentence Transformers | ✅ Implementado |
| `codigo/poc/data/embeddings.npy` | Embeddings precalculados (100 × 384) | ✅ Generado |

**Componentes especificados:**
- ✅ Arquitectura del prototipo
- ✅ Especificación de componentes Streamlit
- ✅ Búsqueda simulada (TF-IDF como proxy temporal)
- ✅ Dataset de muestra (100 registros)
- ✅ Flujo de interacción
- ✅ Evolución planeada por sprints
- ✅ **Motor semántico con embeddings reales (v2)**
- ✅ **Comparativa TF-IDF vs Semántico documentada**

### 4. Documentación de decisiones

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [ideas_rechazadas.md](docs/ideas_descartadas/ideas_rechazadas.md) | 10 ideas consideradas y descartadas con justificación | ✅ Creado |
| [chatbot_fase2_plan.md](docs/chatbot_fase2_plan.md) | Plan del chatbot como modo alternativo para Fase 2 | ✅ Creado |

**Ideas documentadas:**
1. ⚠️ Chatbot conversacional — replanteado para Fase 2 como modo alternativo tras validación MVP (4/5 prefieren lista en MVP)
2. ❌ LLM para respuestas (alucinaciones, coste)
3. ❌ Indexar contenido de archivos (scope prohibitive)
4. ❌ Múltiples fuentes desde inicio (demasiado scope)
5. ❌ Fine-tuning de embeddings (sin datos de entrenamiento)
6. ❌ Elasticsearch/Solr (PostgreSQL+pgvector es suficiente)
7. ❌ Recomendación colaborativa (sin usuarios reales)
8. ❌ Visualizaciones integradas (no core del problema)
9. ❌ Autenticación de usuarios (no crítico para MVP)
10. ❌ Pipeline ETL en tiempo real (datos estáticos)

---

## 🎯 Decisiones clave de la fase

### Interfaz de usuario
- **Decisión:** Lista de resultados con filtros facetados (principal) + chatbot como modo alternativo en Fase 2
- **Motivo:** Las entrevistas de Fase 01 mostraron que 4/5 usuarios prefieren control directo sobre conversación para el MVP. El chatbot se plantea como modo alternativo de navegación para Fase 2, una vez validada la búsqueda por lista.
- **Impacto:** La búsqueda semántica funciona "por detrás", el usuario no interactúa con un chatbot en el MVP. El modo conversacional se implementará tras validación del MVP (Sprint 5).

### Arquitectura técnica
- **Decisión:** PostgreSQL + pgvector (todo-en-uno)
- **Motivo:** Evitar infraestructura adicional (Elasticsearch, etc.)
- **Impacto:** Simplifica deploy y mantenimiento

### Alcance del MVP
- **Decisión:** Solo datos.gob.es, solo metadatos
- **Motivo:** 134k datasets son suficientes para demostrar el concepto; contenido real de archivos es prohibitive
- **Impacto:** MVP enfocado y alcanzable en 200h

### Motor de búsqueda del POC
- **Decisión:** Implementar ambos motores: TF-IDF (v1, baseline) y Embeddings Semánticos (v2)
- **Motivo:** El TF-IDF original no demostraba valor diferencial vs datos.gob.es. El motor semántico con Sentence Transformers captura contexto, sinónimos y lenguaje natural.
- **Impacto:** El POC v2 demuestra claramente la ventaja de la búsqueda semántica sobre el portal actual
- **Tecnología:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384D), cosine similarity en memoria con NumPy

### Modelo de embeddings
- **Decisión:** sentence-transformers pre-entrenado (sin fine-tuning)
- **Motivo:** Suficiente para español, sin coste, sin datos de entrenamiento
- **Impacto:** Sprint 2 puede empezar inmediatamente

---

## 📊 Estado de los entregables DMC

| Bloque | Estado | Calidad |
|--------|--------|---------|
| Problema/Oportunidad | ✅ | Basado en entrevistas reales (simuladas) |
| Solución | ✅ | Diferenciación clara vs portal actual |
| Fuentes de Datos | ✅ | datos.gob.es validado y descargado |
| Clientes | ✅ | 3 personas definidas en Fase 01 |
| Actividades Clave | ✅ | Mapeadas a sprints 1-6 |
| Tipo de Análisis | ✅ | Descriptivo → Predictivo → Prescriptivo |
| KPIs | ✅ | Métricas objetivas con baseline |
| Recursos Clave | ✅ | Humanos + técnicos + datos |
| Coste | ✅ | ~0€ (solo tiempo) |
| Riesgos | ✅ | 7 riesgos identificados con mitigaciones |
| Beneficios | ✅ | Medibles y alineados con ODS |

---

## 🚪 Gate de decisión

**Para pasar a Fase 03 (Sprint 1 - Ingesta completa y limpieza):**

- [x] DMC completado y validado
- [x] Wireframes definidos y alineados con insights de usuarios
- [x] Prototipo especificado (Streamlit + TF-IDF mock)
- [x] Ideas descartadas documentadas con justificación
- [x] Esquema de datos PostgreSQL definido (implícito en DMC)
- [x] Benchmark queries refinadas (de Fase 01)

**⚠️ NOTA IMPORTANTE:** La ingesta de datos ya está completada (134.150 datasets en `03_Sprint1_Ingesta/datos/raw/`). La Fase 03 comenzará con **limpieza y normalización** de estos datos, no con descarga.

---

## 🔗 Próxima Fase

→ **03_Sprint1_Ingesta (continuación)**
- Limpieza de metadatos (campos vacíos, duplicados, normalización)
- Generación de `embedding_text` consolidado
- Validación de calidad de datos (completitud, consistencia)
- Dataset `processed` listo para embeddings

---

## 📋 Resumen de archivos creados

```
02_Idear_Prototipar/
├── README_02_Idear_Prototipar.md           # ✅ Este documento
├── codigo/
│   └── poc/                                 # (vacío - código en Sprint 3-4)
├── docs/
│   ├── ideas_descartadas/
│   │   └── ideas_rechazadas.md              # ✅ 10 ideas documentadas (chatbot replanteado para Fase 2)
│   └── chatbot_fase2_plan.md                # ✅ Plan del chatbot como modo alternativo (Fase 2)
└── entregables/
    ├── DMC/
    │   └── digital_maturity_canvas.md       # ✅ Canvas completo
    ├── prototipos/
    │   └── prototipo_streamlit.md            # ✅ Especificación técnica
    └── wireframes/
        └── wireframe_busqueda_principal.md   # ✅ Diseño ASCII + specs
```

---

*Fase completada. Listo para Sprint 1 (limpieza de datos).*
