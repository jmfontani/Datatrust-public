# Escalado de Modelos LLM en el Buscador Semántico

## Resumen

El sistema de mejoras con LLM está diseñado para escalar fácilmente desde modelos pequeños/rápidos (flash) hasta modelos grandes/potentes (pro), permitiendo equilibrar coste/latencia vs calidad según el caso de uso.

---

## Modelos Disponibles

### Actualmente Configurados

| Modelo | Tamaño | Caso de Uso | Latencia | Coste |
|--------|--------|-------------|----------|-------|
| `deepseek-v4-flash:cloud` | ~8B activos | Re-ranking, explicaciones | ~1-3s | Bajo |
| `deepseek-v4-pro:cloud` | ~32B activos | Análisis complejo, expansión | ~3-8s | Medio |

### Futuros (añadir cuando se necesiten)

| Modelo | Tamaño | Caso de Uso |
|--------|--------|-------------|
| `granite-4.1:8b` | 8B | Re-ranking local (sin cloud) |
| `qwen-3.5:72b` | 72B | Razonamiento profundo |
| `claude-sonnet-4` | - | Análisis muy complejo (vía API Anthropic) |

---

## Arquitectura de Escalado

### Presets Configurables

El sistema usa **presets** que agrupan configuración óptima por caso de uso:

```python
# Presets definidos en llm_client.py
PRESETS = {
    "reranking": {
        "model": "deepseek-v4-flash:cloud",  # Rápido, económico
        "temperature": 0.1,
        "num_predict": 1500,
        "timeout": 60
    },
    "explanation": {
        "model": "deepseek-v4-flash:cloud",
        "temperature": 0.2,
        "num_predict": 800,
        "timeout": 30
    },
    "analysis": {
        "model": "deepseek-v4-pro:cloud",  # Grande para análisis
        "temperature": 0.3,
        "num_predict": 4000,
        "timeout": 120
    },
    "query_expansion": {
        "model": "deepseek-v4-flash:cloud",
        "temperature": 0.4,
        "num_predict": 500,
        "timeout": 30
    }
}
```

### Cambiar de Modelo (Ejemplos)

#### Opción 1: Por Preset (Recomendado)

```python
from llm_client import create_llm_client

# Re-ranking rápido (flash)
client = create_llm_client(use_case="reranking")

# Análisis complejo (pro)
client = create_llm_client(use_case="analysis")
```

#### Opción 2: Sobrescribir Modelo

```python
from llm_client import LLMClient

# Usar preset pero cambiar modelo
client = LLMClient(preset="reranking", model="deepseek-v4-pro:cloud")
```

#### Opción 3: Configuración Manual

```python
# Control total
client = LLMClient(
    model="deepseek-v4-pro:cloud",
    temperature=0.2,
    num_predict=2000,
    timeout=90
)
```

---

## Cuándo Usar Qué Modelo

### Usar FLASH (`deepseek-v4-flash:cloud`) Para:
- ✅ Re-ranking de resultados (tarea simple, estructurada)
- ✅ Explicaciones breves de relevancia
- ✅ Validación de queries
- ✅ Expansión semántica simple

### Usar PRO (`deepseek-v4-pro:cloud`) Para:
- 🔶 Análisis de compatibilidad entre datasets complejos
- 🔶 Generación de planes de análisis detallados
- 🔶 Interpretación de consultas ambiguas
- 🔶 Detección de datasets complementarios multi-fuente

### Considerar Modelo Local (Granite/Llama) Para:
- 🏠 Demo sin conexión a internet
- 🏠 Entornos con restricciones de datos sensibles
- 🏠 Coste cero operacional

---

## Integración con Re-ranker

El re-ranker por defecto usa el preset `reranking` (flash). Para cambiar:

```python
from llm_reranker import LLMReranker

# Re-ranker con flash (default)
reranker = LLMReranker()

# Re-ranker con pro (para queries complejas)
reranker_pro = LLMReranker(model="deepseek-v4-pro:cloud")

# O crear con verbose para debug
reranker_debug = LLMReranker(verbose=True)
```

---

## Métricas de Comparación (Benchmark)

Resultados esperados al cambiar de modelo:

| Métrica | Flash | Pro | Diferencia |
|---------|-------|-----|------------|
| Latencia re-ranking | 1-3s | 3-8s | 2-3x |
| Calidad explicaciones | 7/10 | 9/10 | +28% |
| Coherencia JSON | 95% | 99% | +4% |
| Coste/tokens | $0.001 | $0.01 | 10x |

---

## Fallback y Robustez

Si el modelo grande falla o timeout:

```python
from llm_reranker import LLMReranker

reranker = LLMReranker()

try:
    # Intentar con pro
    reranker.llm.model = "deepseek-v4-pro:cloud"
    results = reranker.rerank(query, results, top_n=10)
except:
    # Fallback a flash
    reranker.llm.model = "deepseek-v4-flash:cloud"
    results = reranker.rerank(query, results, top_n=10)
```

---

## Configuración para Producción

Variables de entorno recomendadas:

```bash
# .env
OLLAMA_URL=http://localhost:11434
LLM_DEFAULT_MODEL=deepseek-v4-flash:cloud
LLM_ANALYSIS_MODEL=deepseek-v4-pro:cloud
LLM_TIMEOUT_RERANK=60
LLM_TIMEOUT_ANALYSIS=120
LLM_VERBOSE=false
```

Cargar en el cliente:

```python
import os
from llm_client import LLMClient

client = LLMClient(
    ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
    model=os.getenv("LLM_DEFAULT_MODEL", "deepseek-v4-flash:cloud"),
    verbose=os.getenv("LLM_VERBOSE", "false").lower() == "true"
)
```

---

## Roadmap de Mejoras con LLM

| Fase | Mejora | Modelo | Prioridad |
|------|--------|--------|-----------|
| **Actual** | Re-ranking | Flash | ✅ Implementado |
| **Next** | Explicaciones | Flash | 🔄 Próximo |
| **Next** | Query expansion | Flash | 🔄 Próximo |
| **Future** | Análisis de compatibilidad | Pro | 📋 Planificado |
| **Future** | Detección complementarios | Pro | 📋 Planificado |
| **Future** | Generación planes | Pro+ | 💡 Idea |

---

## Notas sobre Coste

Con el modelo Flash:
- ~1000 tokens por re-ranking (top 10)
- ~1-2 llamadas por búsqueda
- Coste marginal en suscripción cloud

Con modelo Pro:
- ~2000-4000 tokens por análisis complejo
- Recomendado: caching de respuestas
- Considerar limitar a usuarios premium

---

## Documentación Relacionada

- `llm_client.py` - Cliente genérico
- `llm_reranker.py` - Implementación de re-ranking
- `routes_llm.py` - Endpoints API
- `INTEGRACION_API.md` - Cómo integrar con API existente
