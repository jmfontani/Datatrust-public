# Auditoría de Backends y Frontends

> **Fecha:** 2026-06-08  
> **Autor:** TFM - Buscador Semántico de Open Data  
> **Propósito:** Inventario completo de componentes desplegados y su estado

---

## 📊 Resumen Ejecutivo

| Tipo | Componentes Activos | Componentes Históricos | Total |
|------|---------------------|------------------------|-------|
| **Backends (API)** | 1 | 3 | 4 |
| **Frontends (Streamlit)** | 3 | 5 | 8 |
| **Base de Datos** | 1 | 0 | 1 |
| **Servicios Externos** | 1 (Ollama) | - | 1 |

---

## 🖥️ Backends (API FastAPI)

### Backend en Producción

| Componente | Ruta | Estado | Puerto | Descripción |
|------------|------|--------|--------|-------------|
| `main_v2_final_v07.py` | `08_Sprint6_LLM_Mejora/codigo/api/` | ✅ Activo | 8000 | API principal con búsqueda híbrida + LLM |

**Endpoints principales:**

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/search` | GET | Búsqueda híbrida (FTS + pgvector) |
| `/search/lexical` | GET | Búsqueda solo léxica |
| `/search/semantic` | GET | Búsqueda solo semántica |
| `/enhanced/query/suggest` | POST | Sugerencias de queries (Caso #13) |
| `/enhanced/query/interpret` | POST | Interpretación con LLM (Casos #3, #4, #12) |
| `/llm/enhance` | POST | Re-ranking con LLM |
| `/llm/explain` | POST | Explicación de resultados |

**Rutas históricas (archivadas):**

| Ruta | Estado | Notas |
|------|--------|-------|
| `05_Sprint3_Busqueda_UI/codigo/api/main.py` | 🟡 Histórico | Primera API (Sprint 3) |
| `07_Sprint5_Integracion/codigo/api/historial/` | 🟡 Histórico | APIs intermedias (Sprint 5) |

---

## 🎨 Frontends (Streamlit)

### Frontends Activos (Centralizados en `15_Frontends/`)

| Nivel | Componente | Ruta | Puerto | Estado | Descripción |
|-------|------------|------|--------|--------|-------------|
| **A** | `app.py` | `frontend_a_basico/` | 8501 | ✅ MVP | Búsqueda + pesos + facetas |
| **B** | `app_public.py` | `frontend_b_intermedio/` | 8501 | ✅ Principal | Versión usuarios finales |
| **C** | `app_v09_demo.py` | `frontend_c_avanzado/` | 8502 | ✅ Demo LLM | Re-ranking + explicaciones |
| **C** | `app_v13_query_suggestions.py` | `frontend_c_avanzado/` | 8503 | ✅ Demo #13 | Sugerencias de queries |

### Frontends Históricos (en Sprints)

| Sprint | Ruta | Estado | Notas |
|--------|------|--------|-------|
| Sprint 3 | `05_Sprint3_Busqueda_UI/codigo/frontend/` | 🟡 Archivado | Primer frontend funcional |
| Sprint 5 | `07_Sprint5_Integracion/codigo/frontend_v2/` | 🟡 Archivado | Versión con Enter key |
| Sprint 6 | `08_Sprint6_LLM_Mejora/codigo/frontend/` | 🟡 Archivado | Demo LLM original |

---

## 🗄️ Base de Datos

| Componente | Imagen | Puerto | Estado | Descripción |
|------------|--------|--------|--------|-------------|
| `buscador_postgres` | `ankane/pgvector:latest` | 5432 | ✅ Activo | PostgreSQL + pgvector |

**Esquema de tablas:**

| Tabla | Columnas principales | Propósito |
|-------|---------------------|-----------|
| `datasets` | id, title, description, publisher, embedding, search_vector | Catálogo principal (87.676 datasets) |
| `query_logs` | query, results_count, timestamp | Logs de búsquedas |
| `term_synonyms` | term, synonyms, created_at | Diccionario de sinónimos |
| `metadata_audit` | dataset_id, format, publisher, territory_level, description_quality | Auditoría de metadatos (Task #18) |

---

## 🔌 Servicios Externos

| Servicio | URL | Propósito |
|----------|-----|-----------|
| **Ollama** | `http://host.docker.internal:11434` | LLM local (deepseek-v4-flash:cloud) |
| **datos.gob.es** | `https://datos.gob.es/` | Fuente de datasets (API externa) |

---

## 🐳 Docker Compose (Producción)

| Contenedor | Imagen | Puerto | Health |
|------------|--------|--------|--------|
| `buscador_frontend` | `docker-frontend` | 8501 | ✅ Healthy |
| `buscador_api` | `docker-api` | 8000 | ✅ Healthy |
| `buscador_postgres` | `ankane/pgvector:latest` | 5432 | ✅ Healthy |

**Comandos de gestión:**

```bash
# Ver estado
docker ps | grep buscador

# Ver logs
docker logs buscador_api --tail 50
docker logs buscador_frontend --tail 50

# Reiniciar servicio
docker restart buscador_api
```

---

## 📁 Estructura de Código

```
proyecto/PFM/Datatrust/
├── 03_Sprint1_Ingesta/
│   └── codigo/
│       ├── analisis/              ← NUEVO: Auditoría de metadatos
│       │   ├── audit_metadata.py  # Script principal
│       │   └── generate_charts.py # Visualizaciones
│       └── validacion/
│           └── validate_dcat_ap_es.py
│
├── 05_Sprint3_Busqueda_UI/
│   └── codigo/
│       ├── api/                   ← Histórico
│       │   └── main.py
│       └── frontend/              ← Histórico
│           └── app.py
│
├── 07_Sprint5_Integracion/
│   └── codigo/
│       └── api/
│           └── historial/         ← Histórico
│
├── 08_Sprint6_LLM_Mejora/
│   └── codigo/
│       ├── api/                   ← PRODUCCIÓN
│       │   ├── main_v2_final_v07.py
│       │   └── routes_query_enhanced.py
│       ├── motor/
│       │   ├── query_preprocessor.py
│       │   ├── query_suggester.py
│       │   └── concept_normalizer.py
│       ├── tests/
│       │   ├── test_query_preprocessor.py
│       │   └── test_query_suggester.py
│       └── frontend/              ← Histórico
│
├── 09_Sprint7_RAGAS/
│   └── codigo/
│       ├── eval_ragas_core.py
│       └── actualizar_ground_truth.py
│
├── 15_Frontends/                  ← CENTRALIZADO
│   ├── frontend_a_basico/         ← MVP
│   ├── frontend_b_intermedio/     ← Principal
│   └── frontend_c_avanzado/       ← Demo LLM
│
└── docs/
    ├── ANALISIS_METADATOS.md
    ├── NARRATIVA_TFM.md
    └── AUDITORIA_BACKENDS_FRONTENDS.md  ← ESTE DOCUMENTO
```

---

## 🔄 Flujo de Datos

```
┌─────────────────┐
│   Usuario       │
│   (Navegador)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│   Frontend Streamlit                    │
│   - frontend_a_basico (MVP)             │
│   - frontend_b_intermedio (Principal)   │
│   - frontend_c_avanzado (Demo LLM)      │
└────────┬────────────────────────────────┘
         │ HTTP/REST (puerto 8000)
         ▼
┌─────────────────────────────────────────┐
│   API FastAPI                           │
│   - Búsqueda híbrida (FTS + pgvector)   │
│   - LLM endpoints (Ollama)              │
│   - Query Preprocessor                  │
└────────┬────────────────────────────────┘
         │
         ├──► PostgreSQL + pgvector (5432)
         │    - datasets (87.676)
         │    - metadata_audit
         │
         └──► Ollama (11434)
              - deepseek-v4-flash:cloud
```

---

## 📋 Checklist de Despliegue

### Pre-requisitos

- [ ] Docker + Docker Compose instalados
- [ ] Ollama corriendo (`ollama serve`)
- [ ] Modelo disponible: `deepseek-v4-flash:cloud`

### Pasos de Despliegue

```bash
# 1. Verificar PostgreSQL
docker ps | grep buscador_postgres

# 2. Verificar API
docker ps | grep buscador_api
curl http://localhost:8000/search?q=test&limit=1

# 3. Verificar Frontend
docker ps | grep buscador_frontend
curl http://localhost:8501

# 4. Verificar Ollama
curl http://host.docker.internal:11434/api/tags
```

### Endpoints de Health Check

| Servicio | Endpoint | Esperado |
|----------|----------|----------|
| API | `GET /search?q=test&limit=1` | 200 OK + JSON |
| Frontend | `GET /` | 200 OK + HTML |
| PostgreSQL | `docker exec buscador_postgres psql -U postgres -d buscador -c "SELECT 1"` | 1 |
| Ollama | `curl http://host.docker.internal:11434/api/tags` | 200 OK + JSON |

---

## 🎯 Matriz de Trazabilidad

| Componente | Sprint | Casos de Uso | Estado |
|------------|--------|--------------|--------|
| API `main_v2_final_v07.py` | #6 (integración) | #1, #2, #3, #4, #12, #13 | ✅ Producción |
| `query_preprocessor.py` | #6 | #3, #4, #12 | ✅ Producción |
| `query_suggester.py` | #6 | #13 | ✅ Producción |
| `concept_normalizer.py` | #6 | #8 | ❌ Archivado (0% mejora) |
| `frontend_a_basico` | #3 | MVP | ✅ Mantenimiento |
| `frontend_b_intermedio` | #5 | Principal | ✅ Producción |
| `frontend_c_avanzado` | #6 | Demo LLM | ✅ Demo |
| `app_v13_query_suggestions.py` | #13 | #13 | ✅ Demo |

---

## 📊 Métricas de Uso

| Métrica | Valor | Fuente |
|---------|-------|--------|
| Datasets indexados | 87.676 | PostgreSQL |
| Endpoints API | 10+ | FastAPI |
| Frontends activos | 4 | Streamlit |
| Tiempo respuesta API (p95) | <1s | Logs |
| Tiempo LLM (p95) | 3-5s | Ollama |

---

## 🔒 Seguridad

| Aspecto | Estado | Notas |
|---------|--------|-------|
| API expuesta | localhost only | Puerto 8000 |
| Frontend expuesto | localhost only | Puerto 8501-8503 |
| PostgreSQL | localhost only | Puerto 5432 |
| Ollama | localhost only | Puerto 11434 |
| CORS | Configurado | Orígenes permitidos |

---

## 📝 Recomendaciones

### Corto Plazo

1. **Consolidar frontends** — Unificar A/B/C en un solo frontend con modos (`?mode=basic|advanced|llm`)
2. **Documentar API** — OpenAPI/Swagger ya disponible en `/docs`
3. **Agregar autenticación** — Si se expone públicamente

### Largo Plazo

1. **Migrar a Kubernetes** — Para escalabilidad
2. **Agregar CDN** — Para assets estáticos
3. **Implementar caching Redis** — Para queries frecuentes

---

*Documento generado como parte del TFM - Buscador Semántico de Open Data*
