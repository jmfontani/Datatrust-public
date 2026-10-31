# Fase 08 - Sprint 6: Mejoras con LLM (PARCIALMENTE IMPLEMENTADO)

## 📋 Resumen

Integración de Modelos de Lenguaje (LLM) para mejorar el buscador semántico. **No es un chatbot conversacional** - son mejoras "por detrás" que mejoran la calidad de resultados sin cambiar la interfaz de lista.

## ✅ Estado: RE-RANKING + VALIDACIÓN IMPLEMENTADOS

**Fecha:** 2026-05-25  
**Implementado:**
- ✅ Propuesta #2 - Re-ranking inteligente con LLM
- ✅ **NUEVO:** Sistema general de validación de metadatos

### Qué está funcionando:
- ✅ **Re-ranking con LLM** - Toma Top N resultados del motor híbrido y los reordena según relevancia analítica
- ✅ **Explicaciones de relevancia** - Cada resultado incluye justificación del LLM
- ✅ **Arquitectura escalable** - Soporte para múltiples modelos (flash/pro/future)
- ✅ **Cliente LLM genérico** - Fácil añadir nuevas mejoras
- ✅ **API REST** - Endpoints `/llm/search/rerank` disponibles
- ✅ **Validación de metadatos** - Detecta inconsistencias (ej: UEx vs Barcelona)

### Caso Real Detectado:
El validador encontró y explica automáticamente el error de metadatos UEx/Barcelona:
```
🔴 WARNING: Inconsistencia: 'title' menciona ['UEx'] pero 'publisher' no lo refleja
   'UEx' → 'Universidad de Extremadura' (esperado) vs 'Universidad de Barcelona' (actual)
```

### Qué sigue diferido:
- ⏸️ Propuesta #1: Interpretación estructurada de queries
- ⏸️ Propuesta #3+: Otras mejoras (detección complementarios, análisis compatibilidad, etc.)

---

## 🏗️ Arquitectura Implementada

### Flujo de Re-ranking

```
Usuario
  ↓
Query: "vulnerabilidad económica juvenil"
  ↓
Motor Híbrido (PostgreSQL + pgvector)
  ↓
Top 20 resultados (por similitud + BM25)
  ↓
LLM (deepseek-v4-flash:cloud)
  ↓
Re-ranking analítico + explicaciones
  ↓
Top 10 reordenados con justificaciones
  ↓
Usuario ve lista con indicadores de relevancia
```

### Componentes Creados

```
08_Sprint6_LLM_Mejora/
├── codigo/
│   ├── motor/
│   │   ├── llm_client.py          # Cliente genérico LLM (configurable)
│   │   └── llm_reranker.py        # Re-ranking con explicaciones
│   └── api/
│       └── routes_llm.py          # Endpoints REST /llm/*
│   └── validator/
│       └── metadata_validator.py  # Sistema de validación de metadatos
└── docs/
│   ├── ESCALADO_MODELOS.md        # Cómo cambiar a modelos grandes
│   ├── SISTEMA_VALIDACION.md      # Documentación del validador
│   └── propuestas_llm.md          # Las 14 propuestas originales
```

---

## 🚀 Uso

### ⚠️ Requisito Previo: Activar Entorno Virtual

**Antes de ejecutar cualquier script de Python:**

```bash
source ~/datos/PFM/Datatrust/venv/bin/activate
```

### Desde Python (Directo)

```python
from motor.llm_reranker import LLMReranker
from search_engine_pgvector import SearchEnginePgvector

# Motor base
engine = SearchEnginePgvector()
results, _ = engine.search_hybrid(query, embedding, limit=20)

# Re-ranking con LLM
reranker = LLMReranker()
reranked, metadata = reranker.rerank(
    query="vulnerabilidad económica juvenil",
    results=results,
    top_n=10
)

# Resultados con explicaciones
for r in reranked:
    print(f"{r.title} - Score LLM: {r.llm_relevance_score}")
    print(f"Explicación: {r.explanation}")
```

### Desde API REST

```bash
# Búsqueda con re-ranking
POST /llm/search/rerank
{
    "query": "paro juvenil",
    "limit": 10,
    "rerank_top_n": 20,
    "use_llm": true
}

# Respuesta incluye explicaciones
{
    "results": [{
        "dataset_id": "ine-001",
        "title": "Estadísticas de empleo juvenil",
        "llm_relevance_score": 9.5,
        "explanation": "Directamente sobre empleo juvenil 16-29 años"
    }],
    "metadata": {
        "model": "deepseek-v4-flash:cloud"
    }
}
```

---

## 🔧 Configuración de Modelos

### Por Defecto (Flash - Rápido)

```python
# Re-ranking rápido y económico
reranker = LLMReranker()  # Usa deepseek-v4-flash:cloud
```

### Para Queries Complejas (Pro - Más profundo)

```python
# Para análisis que requieran más razonamiento
reranker = LLMReranker(model="deepseek-v4-pro:cloud")
```

### Ver Modelos Disponibles

```bash
curl http://localhost:11434/api/tags
```

---

## 📊 Resultados del Test

Query: "vulnerabilidad económica juvenil"

| Posición Original | Nueva | Dataset | Score LLM | Explicación |
|-------------------|-------|---------|-----------|-------------|
| 1 | 1 | Empleo juvenil | 9.5/10 | Directamente relacionado con empleo juvenil |
| 2 | 2 | Paro registrado | 7.5/10 | Relevante pero sin desglose por edad |
| 3 | 3 | Renta media | 6.5/10 | Indicador general, no específico jóvenes |

**Latencia:** ~45s (primer llamada, incluye warm-up)
**Tokens:** ~345 prompt → ~829 response

---

## 🔮 Futuras Mejoras (Diferidas)

| # | Mejora | Modelo Sugerido | Complejidad |
|---|--------|-----------------|-------------|
| 1 | Interpretación estructurada de queries | Flash | Media |
| 3 | Detección datasets complementarios | Pro | Media |
| 4 | Evaluación compatibilidad | Pro | Alta |
| 7 | Generación planes de análisis | Pro | Media |
| 9 | Explicaciones ampliadas | Flash | Baja |

**Decisión:** Estas mejoras se activarán si el re-ranking demuestra valor suficiente.

---

## 🔗 Integración con Sprint 7

El re-ranking se integra con la API del Sprint 7 añadiendo el router:

```python
# En app principal del Sprint 7
from codigo.api.routes_llm import router_llm

app.include_router(router_llm)
```

Endpoints disponibles:
- `POST /llm/search/rerank` - Búsqueda con re-ranking
- `POST /llm/search/explain` - Explicar relevancia (WIP)
- `GET /llm/health` - Estado del servicio LLM

---

## 📚 Documentación

- `docs/ESCALADO_MODELOS.md` - Cómo escalar a modelos más grandes
- `docs/propuestas_llm.md` - Las 14 propuestas originales (análisis)
- `motor/llm_client.py` - API del cliente genérico
- `motor/llm_reranker.py` - Implementación del re-ranker

## 🎯 Posibles Mejoras con LLM (14 propuestas)

### Categorías de Mejoras

| # | Mejora | Descripción | Complejidad |
|---|--------|-------------|-------------|
| 1 | **Re-ranking inteligente** | LLM reordena resultados del buscador según contexto del usuario | Media |
| 2 | **Explicaciones de relevancia** | Explica por qué un dataset es relevante para la query | Baja |
| 3 | **Interpretación de queries** | Conviere lenguaje natural a parámetros de búsqueda estructurados | Media |
| 4 | **Expansión semántica** | Sugiere sinónimos y términos relacionados automáticamente | Baja |
| 5 | **Detección de datasets complementarios** | Identifica datasets que podrían combinarse | Media |
| 6 | **Evaluación de compatibilidad** | Analiza si dos datasets pueden unirse técnicamente | Alta |
| 7 | **Generación de planes de análisis** | Crea propuestas de análisis basadas en datasets encontrados | Media |
| 8 | **Normalización de conceptos** | Unifica términos diferentes que significan lo mismo | Media |
| 9 | **Perfilado técnico automático** | Genera descripción técnica del contenido del dataset | Alta |
| 10 | **Respuestas a preguntas sobre datasets** | Responde preguntas específicas sobre un dataset encontrado | Media |
| 11 | **Síntesis de múltiples datasets** | Resume información de varios datasets relacionados | Alta |
| 12 | **Validación semántica de queries** | Detecta si la query tiene sentido en el dominio | Baja |
| 13 | **Sugerencias de queries relacionadas** | Propone búsquedas alternativas basadas en el contexto | Baja |
| 14 | **Resumen automático de datasets** | Genera resumen del contenido potencial del dataset | Media |

## 📚 Documentación de Propuestas

**Ver:** [`docs/propuestas_llm.md`](docs/propuestas_llm.md)

Documento completo con las 14 propuestas detalladas, incluyendo:
- Descripción técnica
- Viabilidad (con/sin acceso a datos)
- Coste/beneficio
- Priorización

## 📁 Estructura Prevista

```
08_Sprint6_LLM_Mejora/
├── codigo/
│   ├── api/
│   │   ├── llm_reranking.py        # Re-ranking con LLM
│   │   ├── query_interpreter.py  # Interpretación de queries
│   │   └── explanation_generator.py # Generador de explicaciones
│   ├── frontend/
│   │   └── llm_features.py         # Componentes UI para LLM
│   └── motor/
│       ├── llm_client.py           # Cliente LLM (OpenAI/local)
│       └── semantic_expander.py    # Expansión semántica
├── docs/
│   ├── propuestas_llm.md           # 14 propuestas detalladas
│   ├── arquitectura_llm.md         # Documentación técnica
│   └── priorizacion.md             # Matriz de decisión
└── entregables/
    └── resumen_fase08.md           # Resumen cuando se complete
```

## 🚪 Condiciones de Activación

Se activará esta fase solo si se cumplen TODAS las condiciones:

1. ✅ Fase 05 (Evaluación) completada con precisión > 70%
2. ✅ Fase 07 (Integración) completada
3. ✅ Feedback de usuarios reales solicita mejoras inteligentes
4. ✅ Decisión explícita sobre qué propuestas implementar (ver [propuestas_llm.md](docs/propuestas_llm.md))
5. ✅ Disponibilidad de recursos (API LLM o modelo local)
6. ✅ Presupuesto para costes de API (si se usa servicio cloud)

## 🔗 Relación con Otras Fases

- **Fase 05**: Usa el mismo motor de búsqueda (API REST)
- **Fase 06**: Los resultados de evaluación deciden si merece la pena
- **Fase 07**: Integración debe estar estable antes de añadir LLM
- **Fase 09**: Documentación incluirá las mejoras con LLM implementadas

## 📋 Plan Técnico (Borrador)

### Opciones de LLM Consideradas

| Opción | Pros | Contras | Decisión |
|--------|------|---------|----------|
| **OpenAI GPT-4** | Calidad alta, fácil integración | Coste, dependencia externa | ⚠️ Opción principal si hay presupuesto |
| **Llama 2/3 local** | Sin coste, privacidad | Requiere GPU, más complejo | ⚠️ Alternativa sin dependencia |
| **Modelos español (Beto)** | Optimizado para español | Menor capacidad que GPT-4 | ⚠️ Opción específica |
| **Sin LLM** | Cero coste, determinista | Sin mejoras inteligentes | ❌ Opción por defecto si no se activa |

### Implementación Preferida (cuando se active)

1. **Mismo buscador semántico** como base (Fase 05/07)
2. **Capa de LLM opcional** para mejoras seleccionadas
3. **Fallback graceful**: Si LLM falla, buscador funciona igual
4. **Caching de respuestas LLM** para reducir costes
5. **Límite de tokens** por query para controlar costes

## 📚 Documentación Previa

- Planes originales:
  - [`02_Idear_Prototipar/docs/chatbot_fase2_plan.md`](../02_Idear_Prototipar/docs/chatbot_fase2_plan.md)
  - [`02_Idear_Prototipar/docs/ideas_descartadas/ideas_rechazadas.md`](../02_Idear_Prototipar/docs/ideas_descartadas/ideas_rechazadas.md)

## 💡 Nota de Alcance

**No es un chatbot:** El objetivo no es crear una interfaz conversacional tipo chat. Las 14 propuestas son mejoras incrementales al buscador existente (explicaciones, re-ranking, expansión de queries, etc.) que usan LLM para mejorar la experiencia de búsqueda, no sustituirla.

---

*Fase diferida a post-MVP. Se revisará tras completar fase 07 (Integración) y obtener feedback de usuarios.*
