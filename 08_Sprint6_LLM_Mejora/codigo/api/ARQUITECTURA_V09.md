# Arquitectura V09 - Endpoints Separados para LLM

**Fecha**: 2026-05-27  
**Versión**: Sprint 09 (Opción 3 implementada)

---

## Resumen

Se ha implementado la **Opción 3: Endpoints Separados** para las funcionalidades LLM. Esta arquitectura mantiene el endpoint `/search` base (v07) intacto y añade nuevos endpoints independientes para funcionalidades LLM.

---

## Endpoints Disponibles

### Core (v07) - Sin cambios

| Método | Endpoint | Descripción | Tiempo |
|--------|----------|-------------|--------|
| POST | `/search` | Búsqueda híbrida (semántica + léxica) | ~0.1s |
| GET | `/health` | Estado de PostgreSQL/pgvector | - |
| GET | `/datasets/{id}` | Dataset por ID | - |
| GET | `/datasets` | Listado de datasets | - |
| GET | `/facets/{type}` | Valores de facetas | - |

### V09 - LLM Features (Nuevos)

| Método | Endpoint | Descripción | Tiempo |
|--------|----------|-------------|--------|
| POST | `/llm/enhance` | Búsqueda + re-ranking LLM | ~50-90s |
| POST | `/llm/explain` | Explicación de relevancia | ~5-15s |
| GET | `/llm/health` | Estado de conexión LLM | - |

---

## Uso de Endpoints

### `/llm/enhance` - Búsqueda Mejorada

```bash
curl -X POST http://localhost:8000/llm/enhance \
  -H "Content-Type: application/json" \
  -d '{
    "query": "paro juvenil desempleo jóvenes",
    "limit": 10,
    "rerank_top_n": 15,
    "include_explanations": true
  }'
```

**Campos:**
- `query` (requerido): Consulta del usuario
- `limit` (opcional, default 10): Cuántos resultados devolver
- `rerank_top_n` (opcional, default 15): Cuántos items re-rankear con LLM
- `include_explanations` (opcional, default true): Incluir justificaciones
- `filters` (opcional): `{ "theme": "...", "territory": "..." }`

**Response:**
```json
{
  "query": "paro juvenil desempleo jóvenes",
  "results": [
    {
      "dataset_id": "l0208012-tasa-de-paro-de-las-personas-jovenes",
      "title": "Tasa de paro de las personas jóvenes",
      "description": "...",
      "publisher": "Ayuntamiento de Barcelona",
      "theme": "Empleo",
      "territory": "Barcelona",
      "format": "CSV",
      "original_rank": 2,
      "new_rank": 1,
      "original_score": 0.85,
      "llm_relevance_score": 9.2,
      "explanation": "Dataset altamente relevante: contiene tasas de paro específicamente para población joven"
    }
  ],
  "total": 10,
  "metadata": {
    "status": "success",
    "model": "deepseek-v4-flash:cloud",
    "total_time_ms": 87500
  }
}
```

---

### `/llm/explain` - Explicación de Relevancia

```bash
curl -X POST http://localhost:8000/llm/explain \
  -H "Content-Type: application/json" \
  -d '{
    "query": "paro juvenil",
    "dataset_id": "l0208012-tasa-de-paro-de-las-personas-jovenes"
  }'
```

**Response:**
```json
{
  "dataset_id": "l0208012-tasa-de-paro-de-las-personas-jovenes",
  "title": "Tasa de paro de las personas jóvenes",
  "explanation": "Este dataset es altamente relevante porque contiene tasas de paro específicas para población joven (16-24 años), que coincide exactamente con la búsqueda.",
  "relevance_score": 9.2,
  "factors": [
    {
      "factor": "Coincidencia temática",
      "score": 0.95,
      "description": "El título y descripción mencionan explícitamente 'paro' y 'jóvenes'"
    },
    {
      "factor": "Cobertura geográfica",
      "score": 0.8,
      "description": "No se especificó territorio en la query"
    },
    {
      "factor": "Calidad de metadatos",
      "score": 0.85,
      "description": "Descripción completa con definición de 'jóvenes'"
    }
  ],
  "metadata": {
    "model": "deepseek-v4-flash:cloud",
    "time_ms": 8200
  }
}
```

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
├─────────────────────────────────────────────────────────────┤
│  Core Endpoints (v07)          │  LLM Endpoints (v09)       │
│  ─────────────────────────       │  ───────────────────        │
│  POST /search                   │  POST /llm/enhance         │
│  GET  /health                   │  POST /llm/explain         │
│  GET  /datasets/{id}            │  GET  /llm/health          │
│  GET  /datasets                 │                             │
│  GET  /facets/{type}            │                             │
├─────────────────────────────────────────────────────────────┤
│                    Router Integration                        │
│         (main_v2_final_v07.py + routes_v09.py)             │
├─────────────────────────────────────────────────────────────┤
│  Motor Híbrido (v07)  │  LLM Reranker  │  LLM Explanation   │
│  - PostgreSQL         │  (motor/)      │  (motor/)          │
│  - pgvector           │                │                    │
│  - Embeddings         │                │                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Flujo de Datos

### `/llm/enhance`

```
Usuario → /llm/enhance
              ↓
    routes_v09.py (router_v09)
              ↓
    [1] Llama a v07 vía HTTP (/search)
              ↓
    main_v2_final_v07.py (motor híbrido)
              ↓
    PostgreSQL + pgvector
              ↓
    [2] Recibe resultados híbridos
              ↓
    LLMReranker.rerank()
              ↓
    Ollama (deepseek-v4-flash:cloud)
              ↓
    Resultados reordenados con scores y explicaciones
```

### `/llm/explain`

```
Usuario → /llm/explain
              ↓
    routes_v09.py
              ↓
    [1] Llama a v07 vía HTTP (/datasets/{id})
              ↓
    main_v2_final_v07.py
              ↓
    PostgreSQL
              ↓
    [2] Recibe metadatos del dataset
              ↓
    LLMClient.generate() [preset="explanation"]
              ↓
    Ollama (deepseek-v4-flash:cloud)
              ↓
    Explicación estructurada con factores
```

---

## Configuración

### Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://localhost:11434` | URL de Ollama |
| `API_PORT` | `8000` | Puerto de la API |

### Modelos LLM

Los presets están definidos en `motor/llm_client.py`:

- **Re-ranking**: `deepseek-v4-flash:cloud` (temperatura 0.1, 4000 tokens)
- **Explanations**: `deepseek-v4-flash:cloud` (temperatura 0.2, 800 tokens)

---

## Ventajas de esta Arquitectura

1. **Separación Clara**: Cada endpoint tiene una responsabilidad única
2. **Backward Compatible**: `/search` sigue funcionando exactamente igual
3. **Escalable**: Fácil añadir nuevos endpoints LLM sin tocar código existente
4. **Desacoplado**: El router v09 usa HTTP para comunicarse con v07 (no imports circulares)
5. **Tiempos Predecibles**: `/search` es rápido, `/llm/*` es explícitamente lento

---

## Decisiones de Diseño

### ¿Por qué endpoints separados vs parámetros?

- **Claridad**: El usuario sabe explícitamente qué está usando
- **Timeouts**: Los endpoints LLM necesitan timeouts mayores (180s vs 30s)
- **Caching**: Fácil cachear `/search` sin afectar a funcionalidades LLM
- **Coste**: El usuario elige conscientemente si quiere usar LLM (más lento)

### ¿Por qué HTTP vs import directo?

- **Evita deadlocks**: No hay riesgo de bloqueos circulares
- **Independencia**: v07 y v09 podrían correr en servicios separados
- **Hot reload**: Cambios en v09 no requieren reiniciar v07

---

## Próximos Pasos (V10+)

Posibles extensiones de esta arquitectura:

1. **`/llm/suggest`**: Sugerir queries relacionadas
2. **`/llm/summarize`**: Resumir el contenido de un dataset
3. **`/llm/compare`**: Comparar múltiples datasets
4. **`/llm/chat`**: Chat interactivo sobre los datos

---

## Archivos Modificados/Creados

| Archivo | Estado | Descripción |
|---------|--------|-------------|
| `routes_v09.py` | Creado | Nuevo router con endpoints LLM |
| `main_v2_final_v07.py` | Modificado | Incluye `router_v09` |

---

**Autor**: Fonta  
**Sprint**: 09 (Arquitectura LLM v3)
