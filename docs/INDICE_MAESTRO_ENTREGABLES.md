# Índice Maestro de Entregables

> **Fecha:** 2026-06-08  
> **Autor:** TFM - Buscador Semántico de Open Data  
> **Propósito:** Inventario completo de todos los artefactos del proyecto

---

## 📊 Resumen por Categoría

| Categoría | Archivos | Líneas de Código | Estado |
|-----------|----------|------------------|--------|
| **Documentación (.md)** | 125+ | ~50.000 | ✅ Completa |
| **Código Python (.py)** | 95+ | ~25.000 | ✅ Funcional |
| **Datos/Config (.json, .yml)** | 40+ | ~10.000 | ✅ Validado |
| **Visualizaciones (.png)** | 8 | - | ✅ Generadas |
| **Scripts Shell (.sh)** | 10+ | ~500 | ✅ Ejecutables |
| **Total** | 278+ | ~85.500 | - |

---

## 📁 Estructura del Proyecto

```
proyecto/PFM/Datatrust/
│
├── 01_Sprint0_Contexto/              # Documentación inicial
├── 02_Idear_Prototipar/              # POC, prototipos tempranos
├── 03_Sprint1_Ingesta/               # Ingesta, deduplicación, auditoría
├── 04_Sprint2_Busquedas/             # Primeras búsquedas (descartadas)
├── 05_Sprint3_Busqueda_UI/           # API + Frontend inicial
├── 06_Sprint4_Fallback/              # Fallback léxico (archivado)
├── 07_Sprint5_Integracion/           # Integración v2
├── 08_Sprint6_LLM_Mejora/            # Query Preprocessor, Suggester
├── 09_Sprint7_RAGAS/                 # Evaluación RAGAS
├── 10_Sprint8_Produccion/            # (pendiente)
├── 11_Sprint9_Monitorizacion/        # (pendiente)
├── 12_Sprint10_Documentacion/        # (pendiente)
├── 13_Sprint11_Articulo/             # (pendiente)
├── 14_Sprint12_Presentacion/         # (pendiente)
├── 15_Frontends/                     # Frontends centralizados
├── docs/                             # Documentación transversal
├── metodologia/                      # Metodología EOI
└── venv/                             # Entorno virtual (excluido)
```

---

## 📂 Entregables por Sprint

### Sprint 0: Contexto

| Archivo | Ruta | Tipo | Descripción |
|---------|------|------|-------------|
| `README.md` | `01_Sprint0_Contexto/` | Doc | Contexto del TFM |
| `objetivos.md` | `01_Sprint0_Contexto/` | Doc | Objetivos del proyecto |

**Estado:** 🟡 Histórico (referencia)

---

### Sprint 1: Ingesta de Datos

| Archivo | Ruta | Tipo | Descripción |
|---------|------|------|-------------|
| `ingest_datos_gob.py` | `03_Sprint1_Ingesta/codigo/` | Código | Ingesta desde datos.gob.es |
| `deduplicate.py` | `03_Sprint1_Ingesta/codigo/limpieza/` | Código | Deduplicación (123k → 87k) |
| `validate_dcat_ap_es.py` | `03_Sprint1_Ingesta/codigo/validacion/` | Código | Validación DCAT-AP-ES |
| `audit_metadata.py` | `03_Sprint1_Ingesta/codigo/analisis/` | Código | **NUEVO**: Auditoría de metadatos |
| `generate_charts.py` | `03_Sprint1_Ingesta/codigo/analisis/` | Código | **NUEVO**: 8 visualizaciones |
| `metadata_audit.csv` | `03_Sprint1_Ingesta/entregables/analisis_metadatos/` | Datos | Auditoría completa (87k filas) |
| `resumen_ejecutivo.json` | `03_Sprint1_Ingesta/entregables/analisis_metadatos/` | Datos | Métricas clave |
| `README_03_Sprint1_Ingesta.md` | `03_Sprint1_Ingesta/` | Doc | Documentación del sprint |

**Estado:** ✅ Producción

**Métricas:**
- 87.676 datasets únicos (28% duplicados eliminados)
- 81% cumplimiento DCAT-AP-ES

---

### Sprint 2: Primeras Búsquedas

| Archivo | Ruta | Tipo | Descripción |
|---------|------|------|-------------|
| `buscar.py` | `04_Sprint2_Busquedas/codigo/` | Código | Búsqueda básica (descartada) |
| `evaluar_similitud.py` | `04_Sprint2_Busquedas/codigo/` | Código | Evaluación de similitud |

**Estado:** ❌ Descartado (insuficiente)

**Lección:** Búsqueda solo por similitud falló con descripciones cortas.

---

### Sprint 3: Búsqueda + UI

| Archivo | Ruta | Tipo | Descripción |
|---------|------|------|-------------|
| `main.py` | `05_Sprint3_Busqueda_UI/codigo/api/` | Código | Primera API FastAPI |
| `app.py` | `05_Sprint3_Busqueda_UI/codigo/frontend/` | Código | Primer frontend Streamlit |
| `components.py` | `05_Sprint3_Busqueda_UI/codigo/frontend/` | Código | Componentes UI |

**Estado:** 🟡 Histórico (referencia)

**Entregable principal:** Primera versión funcional con búsqueda + facetas.

---

### Sprint 4: Fallback Léxico

| Archivo | Ruta | Tipo | Descripción |
|---------|------|------|-------------|
| `hybrid_search.py` | `06_Sprint4_Fallback/codigo/` | Código | Búsqueda híbrida (archivado) |

**Estado:** 🟡 Integrado en Sprint 5

**Lección:** Fallback léxico necesario → integrado en API v2.

---

### Sprint 5: Integración

| Archivo | Ruta | Tipo | Descripción |
|---------|------|------|-------------|
| `main_v2.py` | `07_Sprint5_Integracion/codigo/api/` | Código | API v2 (integrada) |
| `app_public.py` | `07_Sprint5_Integracion/codigo/frontend_v2/` | Código | Frontend público |
| `components_v2.py` | `07_Sprint5_Integracion/codigo/frontend_v2/` | Código | Componentes v2 |

**Estado:** 🟡 Históricos (movidos a `15_Frontends/`)

---

### Sprint 6: LLM - Query Preprocessor

| Archivo | Ruta | Tipo | Descripción |
|---------|------|------|-------------|
| `query_preprocessor.py` | `08_Sprint6_LLM_Mejora/codigo/motor/` | Código | **PRODUCCIÓN**: Interpretación + expansión |
| `query_suggester.py` | `08_Sprint6_LLM_Mejora/codigo/motor/` | Código | **PRODUCCIÓN**: Sugerencias (Caso #13) |
| `concept_normalizer.py` | `08_Sprint6_LLM_Mejora/codigo/motor/` | Código | Archivado (Caso #8, 0% mejora) |
| `sinonimos.json` | `08_Sprint6_LLM_Mejora/codigo/motor/` | Datos | Diccionario de sinónimos |
| `conceptos_semanticos.yml` | `08_Sprint6_LLM_Mejora/codigo/config/` | Datos | 2857 líneas de conceptos |
| `routes_query_enhanced.py` | `08_Sprint6_LLM_Mejora/codigo/api/` | Código | Endpoints mejorados |
| `main_v2_final_v07.py` | `08_Sprint6_LLM_Mejora/codigo/api/` | Código | **PRODUCCIÓN**: API principal |
| `test_query_preprocessor.py` | `08_Sprint6_LLM_Mejora/codigo/tests/` | Test | 20 tests unitarios |
| `test_query_suggester.py` | `08_Sprint6_LLM_Mejora/codigo/tests/` | Test | Tests de sugerencias |
| `CASO_13_QUERY_SUGGESTIONS.md` | `08_Sprint6_LLM_Mejora/docs/` | Doc | Documentación Caso #13 |
| `EXPERIMENTO_NORMALIZACION_CONCEPTUAL.md` | `08_Sprint6_LLM_Mejora/docs/` | Doc | Vía muerta #8 |
| `INDICE_CASOS_USO_LLM.md` | `08_Sprint6_LLM_Mejora/docs/` | Doc | Índice de casos LLM |

**Estado:** ✅ Producción

**Casos de uso:**
- #3: Interpretación de query ✅
- #4: Expansión con sinónimos ✅
- #8: Normalización conceptual ❌ (archivado)
- #12: Validación de resultados ✅
- #13: Sugerencias de queries ✅

---

### Sprint 7: Evaluación RAGAS

| Archivo | Ruta | Tipo | Descripción |
|---------|------|------|-------------|
| `eval_ragas_core.py` | `09_Sprint7_RAGAS/codigo/` | Código | Evaluación RAGAS |
| `actualizar_ground_truth.py` | `09_Sprint7_RAGAS/codigo/` | Código | Actualización ground truth |
| `ground_truth_actualizado.jsonl` | `09_Sprint7_RAGAS/entregables/` | Datos | 48 queries evaluadas |
| `ragas_scores_basic_final.json` | `09_Sprint7_RAGAS/entregables/` | Datos | Scores búsqueda básica |
| `ragas_scores_llm_final.json` | `09_Sprint7_RAGAS/entregables/` | Datos | Scores búsqueda con LLM |
| `reporte_evaluacion_v3.md` | `09_Sprint7_RAGAS/entregables/` | Doc | Reporte de evaluación |

**Estado:** ✅ Completado

**Métricas clave:**
- Básico P@5: 0.279
- LLM P@5: 0.225 (42s/query)

---

### Sprint 8-11: (Pendientes)

| Sprint | Estado | Notas |
|--------|--------|-------|
| Sprint 8: Producción | ⏳ Pendiente | Docker, deployment |
| Sprint 9: Monitorización | ⏳ Pendiente | Logs, métricas |
| Sprint 10: Documentación | ⏳ Pendiente | Memoria completa |
| Sprint 11: Artículo | ⏳ Pendiente | Paper académico |

---

## 🎨 Frontends Centralizados (`15_Frontends/`)

| Nivel | Archivo | Ruta | Estado | Descripción |
|-------|---------|------|--------|-------------|
| **A** | `app.py` | `frontend_a_basico/` | ✅ MVP | Búsqueda + pesos + facetas |
| **A** | `components.py` | `frontend_a_basico/` | ✅ | Componentes básicos |
| **A** | `utils.py` | `frontend_a_basico/` | ✅ | Utilidades |
| **A** | `facetas.json` | `frontend_a_basico/` | ✅ | Configuración de facetas |
| **B** | `app_public.py` | `frontend_b_intermedio/` | ✅ Principal | Versión usuarios finales |
| **B** | `app.py` | `frontend_b_intermedio/` | 🟡 Bug | Imports rotos (documentado) |
| **B** | `components_public.py` | `frontend_b_intermedio/` | ✅ | Componentes públicos |
| **B** | `components_v2.py` | `frontend_b_intermedio/` | ✅ | Componentes v2 |
| **B** | `utils_v2.py` | `frontend_b_intermedio/` | ✅ | Utilidades v2 |
| **B** | `app_router.py` | `frontend_b_intermedio/` | ✅ | Router de frontends |
| **C** | `app_v09_demo.py` | `frontend_c_avanzado/` | ✅ Demo LLM | Re-ranking + explicaciones |
| **C** | `app_v13_query_suggestions.py` | `frontend_c_avanzado/` | ✅ Demo #13 | Sugerencias de queries |
| **C** | `app_query_enhanced.py` | `frontend_c_avanzado/` | ✅ | Query enhanced demo |

**Documentación:**
- `README.md` — Guía principal de frontends
- `MAPA_DECISION.md` — Criterios para elegir A/B/C
- `DEMO_QUERIES.md` — Queries de ejemplo para demos

---

## 📚 Documentación Transversal (`docs/`)

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `ANALISIS_METADATOS.md` | Doc | **NUEVO**: Análisis de 87k datasets |
| `NARRATIVA_TFM.md` | Doc | **NUEVO**: Estructura de memoria + camino seguido |
| `AUDITORIA_BACKENDS_FRONTENDS.md` | Doc | **NUEVO**: Inventario de componentes |
| `ESTRATEGIA_GIT.md` | Doc | **NUEVO**: Estrategia de branching |
| `INDICE_MAESTRO_ENTREGABLES.md` | Doc | **NUEVO**: Este documento |
| `cumplimiento-DCAT-AP-ES.md` | Doc | 81% cumplimiento (13/16 campos) |
| `GRUPO_2_PROJECT DESIGN.pptx` | Presentación | Presentación del proyecto |

---

## 🔧 Scripts de Utilidad

| Script | Ruta | Propósito |
|--------|------|-----------|
| `launch_dev.sh` | `05_Sprint3_Busqueda_UI/codigo/api/` | Arrancar API en desarrollo |
| `DEMO_LANZAMIENTO.sh` | `15_Frontends/` | Script de lanzamiento de demo |
| `launch_query_enhanced.sh` | `15_Frontends/frontend_c_avanzado/` | Arrancar demo LLM |

---

## 📊 Bases de Datos y Datos

| Archivo/Tabla | Ubicación | Tamaño | Descripción |
|---------------|-----------|--------|-------------|
| `datasets` (tabla) | PostgreSQL | 87.676 filas | Catálogo principal |
| `metadata_audit` (tabla) | PostgreSQL | 87.676 filas | Auditoría de metadatos |
| `metadata_audit.csv` | `03_Sprint1_Ingesta/entregables/` | 33MB | Exportación completa |
| `ground_truth_actualizado.jsonl` | `09_Sprint7_RAGAS/entregables/` | 48 queries | Ground truth para RAGAS |
| `sinonimos.json` | `08_Sprint6_LLM_Mejora/codigo/motor/` | ~100 entradas | Diccionario de sinónimos |
| `conceptos_semanticos.yml` | `08_Sprint6_LLM_Mejora/codigo/config/` | 2857 líneas | Conceptos para normalización |

---

## 🧪 Tests

| Archivo | Ruta | Tests | Estado |
|---------|------|-------|--------|
| `test_query_preprocessor.py` | `08_Sprint6_LLM_Mejora/codigo/tests/` | 20 | ✅ Todos passing |
| `test_query_suggester.py` | `08_Sprint6_LLM_Mejora/codigo/tests/` | 20 | ✅ Todos passing |
| `test_concept_normalizer.py` | `08_Sprint6_LLM_Mejora/codigo/tests/` | 10 | 🟡 Archivado con Caso #8 |

---

## 📈 Visualizaciones

| Archivo | Ruta | Descripción |
|---------|------|-------------|
| `01_formatos.png` | `03_Sprint1_Ingesta/entregables/analisis_metadatos/figuras/` | Distribución de formatos |
| `02_publishers.png` | `.../figuras/` | Top 20 publishers |
| `03_calidad_descripciones.png` | `.../figuras/` | Calidad de descripciones |
| `04_territorio.png` | `.../figuras/` | Cobertura territorial |
| `05_tipos_publishers.png` | `.../figuras/` | Tipos de publishers |
| `06_completitud_campos.png` | `.../figuras/` | Completitud DCAT-AP-ES |
| `07_cobertura_temporal.png` | `.../figuras/` | Cobertura temporal |

---

## 🎯 Matriz de Trazabilidad de Entregables

| Objetivo TFM | Entregables | Estado |
|--------------|-------------|--------|
| **O1: Ingestar 100k+ datasets** | `ingest_datos_gob.py`, `deduplicate.py`, 87.676 datasets en PostgreSQL | ✅ |
| **O2: Búsqueda híbrida** | `main_v2_final_v07.py`, `/search` endpoint, FTS + pgvector | ✅ |
| **O3: Query preprocessing** | `query_preprocessor.py`, 44 datasets únicos en test | ✅ |
| **O4: Evaluación RAGAS** | `eval_ragas_core.py`, 48 queries, ground_truth.jsonl | ✅ |
| **O5: Documentación** | 125+ docs, `ANALISIS_METADATOS.md`, `NARRATIVA_TFM.md` | ✅ |

---

## 📋 Checklist de Verificación

### Producción

- [ ] API corriendo en puerto 8000
- [ ] Frontend corriendo en puerto 8501
- [ ] PostgreSQL con 87.676 datasets
- [ ] Ollama disponible (puerto 11434)
- [ ] Tests passing (40 tests)

### Documentación

- [ ] `ANALISIS_METADATOS.md` — Completado
- [ ] `NARRATIVA_TFM.md` — Completado
- [ ] `AUDITORIA_BACKENDS_FRONTENDS.md` — Completado
- [ ] `ESTRATEGIA_GIT.md` — Completado
- [ ] `INDICE_MAESTRO_ENTREGABLES.md` — Este documento

### Código

- [ ] `query_preprocessor.py` — Producción
- [ ] `query_suggester.py` — Producción
- [ ] `main_v2_final_v07.py` — Producción
- [ ] `audit_metadata.py` — Producción
- [ ] `generate_charts.py` — Producción

---

## 🔗 Referencias Cruzadas

| Documento | Ruta | Propósito |
|-----------|------|-----------|
| Auditoría de componentes | `docs/AUDITORIA_BACKENDS_FRONTENDS.md` | Inventario de backends/frontends |
| Estrategia Git | `docs/ESTRATEGIA_GIT.md` | Convención de branching |
| Análisis de metadatos | `docs/ANALISIS_METADATOS.md` | Hallazgos de 87k datasets |
| Narrativa TFM | `docs/NARRATIVA_TFM.md` | Estructura de memoria |
| Vías muertas | `08_Sprint6_LLM_Mejora/docs/EXPERIMENTO_NORMALIZACION_CONCEPTUAL.md` | Caso #8 archivado |

---

*Documento generado como parte del TFM - Buscador Semántico de Open Data*
