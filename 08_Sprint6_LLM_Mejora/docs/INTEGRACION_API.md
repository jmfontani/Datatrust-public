# Guía de Integración con API Sprint 7

Esta guía explica cómo integrar el re-ranking con LLM (Sprint 8) con la API REST existente del Sprint 7.

## Opción 1: Integrar Router LLM (Recomendado)

Esta opción añade endpoints específicos para funcionalidades LLM manteniendo la API existente intacta.

### Paso 1: Copiar archivos necesarios

```bash
# Desde directorio del proyecto
cd proyecto/PFM/Datatrust

# Copiar cliente LLM y re-ranker al Sprint 7
cp 08_Sprint6_LLM_Mejora/codigo/motor/llm_client.py \
   07_Sprint5_Integracion/codigo/motor/
   
cp 08_Sprint6_LLM_Mejora/codigo/motor/llm_reranker.py \
   07_Sprint5_Integracion/codigo/motor/

# Copiar rutas API
cp 08_Sprint6_LLM_Mejora/codigo/api/routes_llm.py \
   07_Sprint5_Integracion/codigo/api/
```

### Paso 2: Modificar API principal

Editar `07_Sprint5_Integracion/codigo/api/main.py`:

```python
from fastapi import FastAPI
from motor.search_engine_pgvector import SearchEnginePgvector

# Importar router LLM
try:
    from api.routes_llm import router_llm
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

app = FastAPI(title="Buscador Semántico de Datasets")

# Router existente
# app.include_router(router_search, prefix="/search")

# Añadir router LLM si está disponible
if LLM_AVAILABLE:
    app.include_router(router_llm)
    print("✅ LLM features disponibles en /llm/*")
else:
    print("⚠️  LLM no disponible (faltan dependencias)")

@app.get("/")
def root():
    return {
        "message": "Buscador Semántico de Datasets",
        "version": "2.0",
        "llm_available": LLM_AVAILABLE
    }
```

### Paso 3: Instalar dependencias (si es necesario)

```bash
cd 07_Sprint5_Integracion/codigo
source .venv/bin/activate

# Verificar que requests está instalado (para llamadas a Ollama)
pip install requests
```

### Paso 4: Verificar Ollama

Asegurar que Ollama está corriendo:

```bash
# Verificar conexión
curl http://localhost:11434/api/tags

# Si no está corriendo, iniciar:
docker start big-bear-ollama-amd
```

### Paso 5: Probar integración

```bash
# Iniciar API
cd 07_Sprint5_Integracion/codigo
python -m uvicorn api.main:app --reload --port 8000

# En otra terminal, testear:
curl http://localhost:8000/
# Debería retornar: {"llm_available": true}

# Test re-ranking:
curl -X POST http://localhost:8000/llm/search/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "query": "paro juvenil Madrid",
    "limit": 5,
    "rerank_top_n": 10,
    "use_llm": true
  }'
```

## Opción 2: Endpoint Híbrido (Modificar búsqueda existente)

Si prefieres que la búsqueda normal ya incluya re-ranking:

### Modificar endpoint `/search`

Editar `07_Sprint5_Integracion/codigo/api/main.py`:

```python
from fastapi import Query
from motor.llm_reranker import LLMReranker

# Instancia del re-ranker (lazy loading)
_reranker = None

def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = LLMReranker()
    return _reranker

@app.post("/search")
async def search(
    query: str,
    use_llm_rerank: bool = Query(False, description="Activar re-ranking con LLM"),
    limit: int = 10
):
    """
    Búsqueda híbrida con opción de re-ranking LLM.
    """
    # Búsqueda base
    engine = SearchEnginePgvector()
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    embedding = model.encode(query, normalize_embeddings=True).tolist()
    
    results, time_ms = engine.search_hybrid(query, embedding, limit=limit*2 if use_llm_rerank else limit)
    
    # Re-ranking opcional
    if use_llm_rerank:
        reranker = get_reranker()
        results, llm_meta = reranker.rerank(query, results, top_n=limit)
        return {
            "query": query,
            "results": results,
            "llm_enhanced": True,
            "llm_model": llm_meta.get("model")
        }
    
    return {"query": query, "results": results}
```

## Opción 3: Frontend Directo (Sin modificar API)

Si solo quieres usar re-ranking desde el frontend Streamlit:

### En `07_Sprint5_Integracion/codigo/frontend_v2/app_public.py`

```python
import sys
sys.path.insert(0, '../motor')

from llm_reranker import LLMReranker

# Inicializar re-ranker (lazy)
@st.cache_resource
def get_reranker():
    return LLMReranker()

# En la sección de búsqueda
if st.button("🔍 Buscar con IA"):
    with st.spinner("Buscando..."):
        # Búsqueda normal
        results = search_datasets(query, limit=20)
        
        # Re-ranking con LLM
        reranker = get_reranker()
        reranked, meta = reranker.rerank(query, results, top_n=10, verbose=True)
        
        # Mostrar resultados con badges de IA
        for r in reranked:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{r.title}**")
                st.caption(r.description[:200])
            with col2:
                st.badge(f"⭐ {r.llm_relevance_score:.1f}")
                st.caption(f"_{r.explanation[:50]}_")
```

## Comparación de Opciones

| Opción | Ventajas | Desventajas | Cuándo usar |
|--------|----------|-------------|-------------|
| **1: Router LLM** | Limpio, separado, no toca código existente | Más endpoints | Recomendado siempre |
| **2: Endpoint híbrido** | Un solo endpoint, transparente | Mezcla responsabilidades | Si quieres simplificar UI |
| **3: Frontend directo** | Sin tocar backend | Más carga en frontend | Prototipado rápido |

## Troubleshooting

### "Ollama no disponible"

```bash
# Verificar contenedor
docker ps | grep ollama

# Si no está corriendo:
docker start big-bear-ollama-amd

# Verificar modelo:
curl http://localhost:11434/api/tags
```

### "ModuleNotFoundError: llm_client"

```bash
# Asegurar que los archivos están en motor/
ls 07_Sprint5_Integracion/codigo/motor/llm_*.py

# Si no están, copiar:
cp 08_Sprint6_LLM_Mejora/codigo/motor/llm_*.py \
   07_Sprint5_Integracion/codigo/motor/
```

### Timeout en re-ranking

```python
# Aumentar timeout en LLMReranker
reranker = LLMReranker(timeout=120)  # segundos
```

### Respuesta vacía del LLM

```python
# Cambiar a modelo más estable
reranker = LLMReranker(model="deepseek-v4-pro:cloud")
```

## Variables de Entorno

```bash
# .env file
OLLAMA_URL=http://localhost:11434
LLM_DEFAULT_MODEL=deepseek-v4-flash:cloud
LLM_TIMEOUT=60
LLM_VERBOSE=false
```

Cargar en la app:

```python
from dotenv import load_dotenv
import os

load_dotenv()

reranker = LLMReranker(
    ollama_url=os.getenv("OLLAMA_URL"),
    model=os.getenv("LLM_DEFAULT_MODEL"),
    timeout=int(os.getenv("LLM_TIMEOUT", 60))
)
```

---

## Próximos Pasos

Una vez integrado el re-ranking, considerar:

1. **Añadir toggle en UI**: Checkbox "Usar IA para mejorar resultados"
2. **Caching**: Cachear resultados de LLM para queries repetidas
3. **Métricas**: Trackear cuántos usuarios activan re-ranking
4. **Fallback**: Si LLM falla, volver a resultados originales automáticamente
