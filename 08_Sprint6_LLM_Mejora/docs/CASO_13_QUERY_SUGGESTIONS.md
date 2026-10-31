# Caso #13: Sugerencias de Queries Relacionadas

**Estado:** ✅ IMPLEMENTADO  
**Fecha:** 2026-06-06  
**Latencia:** <5ms (léxico) + ~3-5s (LLM background)  
**Tipo:** Híbrido asíncrono

---

## 📋 Descripción

Genera sugerencias de queries alternativas que un ciudadano podría usar para buscar datos similares en datos.gob.es.

### Ejemplo

```
Usuario: "paro juvenil Canarias"

Sugerencias:
  1. [sinonimo] desempleo juvenil Canarias
  2. [territorial] paro juvenil España
  3. [temporal] paro últimos 5 años
  4. [tecnica] EPA jóvenes Canarias
  5. [especificacion] paro por municipio
```

---

## 🏗️ Arquitectura

### Enfoque Híbrido Asíncrono

```
┌─────────────┐
│   Usuario   │
│  escribe... │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  POST /enhanced/query/suggest               │
│  ───────────────────────────────            │
│  1. Léxico (<5ms) → Retorna inmediato       │
│  2. LLM (~3-5s) → Background (fire-forget)  │
│  3. Poll URL → /suggest/{cache_key}/result  │
└─────────────────────────────────────────────┘
       │
       ├── [0ms] → Renderizar 5 sugerencias léxicas
       │
       └── [~3s] → Poll → +5 sugerencias LLM
                      → Merge + dedupe
                      → Total: 8-10 sugerencias
```

### Categorías de Sugerencias

| Categoría | Descripción | Ejemplo |
|-----------|-------------|---------|
| **sinonimo** | Reemplazo con sinónimos | "paro" → "desempleo" |
| **temporal** | Variaciones de año/periodo | "2023" → "2022", "últimos 5 años" |
| **territorial** | Cambio de ámbito geográfico | "Canarias" → "España", "por isla" |
| **tecnica** | Términos técnicos del dominio | "paro" → "EPA", "tasa de desempleo" |
| **especificacion** | Desgloses adicionales | "por municipio", "por edad" |

---

## 📁 Archivos

### Motor

| Archivo | Descripción |
|---------|-------------|
| `motor/query_suggester.py` | Clase `QuerySuggester` con métodos `suggest_lexical()` y `suggest_llm()` |
| `motor/sinonimos.json` | Diccionario de sinónimos (50+ términos) |
| `motor/TERMINOS_TECNICOS` | Términos técnicos por dominio (embebido en código) |

### API

| Endpoint | Método | Descripción | Latencia |
|----------|--------|-------------|----------|
| `/enhanced/query/suggest` | POST | Sugerencias híbridas (léxico + LLM background) | <5ms + poll |
| `/enhanced/query/suggest/{cache_key}/result` | GET | Polling para resultados completos | ~3-5s |
| `/enhanced/query/suggest/lexical` | GET | Solo léxico (rápido) | <5ms |
| `/enhanced/query/suggest/llm` | POST | Solo LLM (síncrono) | ~3-5s |
| `/enhanced/query/suggest/health` | GET | Estado del servicio | <1ms |

### Tests

| Archivo | Descripción |
|---------|-------------|
| `tests/test_query_suggester.py` | 20 tests unitarios (léxico, categorías, edge cases) |

---

## 🔧 Uso

### Desde Python

```python
from motor.query_suggester import get_query_suggester

suggester = get_query_suggester()

# Solo léxico (<5ms)
result = suggester.suggest_lexical("paro juvenil Canarias", n=5)
for sug in result.suggestions:
    print(f"[{sug.category}] {sug.text}")

# Híbrido (léxico + LLM background)
lexical_result, llm_task = suggester.suggest_combined("paro juvenil", n_lexical=3, n_llm=3)
llm_result = await llm_task
```

### Desde API REST

```bash
# 1. Petición inicial (retorna léxico + poll URL)
curl -X POST http://localhost:8000/enhanced/query/suggest \
  -H "Content-Type: application/json" \
  -d '{"query": "paro juvenil Canarias", "n": 5}'

# Response:
{
  "query_original": "paro juvenil Canarias",
  "suggestions": [...],
  "llm_pending": true,
  "poll_url": "/enhanced/query/suggest/bf37cfcfc002c40886e3364d3cc12d28/result",
  "lexical_count": 5
}

# 2. Polling (después de ~3s)
curl http://localhost:8000/enhanced/query/suggest/bf37cfcfc002c40886e3364d3cc12d28/result

# Response:
{
  "query_original": "paro juvenil Canarias",
  "suggestions": [...],
  "llm_pending": false,
  "lexical_count": 5,
  "llm_count": 5,
  "total_count": 8
}
```

### Desde Frontend (JavaScript)

```javascript
async function fetchSuggestions(query) {
    // Paso 1: Obtener sugerencias léxicas inmediatas
    const response = await fetch('/enhanced/query/suggest', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query, n: 5})
    });
    
    const data = await response.json();
    
    // Renderizar sugerencias léxicas inmediatamente
    renderSuggestions(data.suggestions);
    
    // Paso 2: Polling para resultados LLM
    if (data.llm_pending && data.poll_url) {
        setTimeout(async () => {
            const complete = await fetch(data.poll_url);
            const completeData = await complete.json();
            
            // Actualizar UI con sugerencias completas
            updateSuggestions(completeData.suggestions);
        }, 3000);
    }
}
```

---

## 📊 Métricas

### Rendimiento

| Métrica | Valor |
|---------|-------|
| Latencia léxico | <5ms |
| Latencia LLM | ~3-5s |
| Sugerencias por query | 5-10 |
| Diversidad categorías | 2-4 categorías/query |
| Cache hit rate | ~80% (queries repetidas) |

### Calidad (Tests Manuales)

| Query | Sugerencias | Categorías |
|-------|-------------|------------|
| "paro juvenil Canarias 2023" | 8 | sinonimo, temporal, territorial |
| "vulnerabilidad económica" | 5 | sinonimo, temporal, territorial |
| "turismo Barcelona 2023" | 5 | sinonimo, temporal, territorial |
| "población mayor 65" | 5 | sinonimo, temporal, territorial |

---

## 🧪 Tests

### Ejecutar Tests

```bash
cd 08_Sprint6_LLM_Mejora/codigo
python tests/test_query_suggester.py
```

### Cobertura

- ✅ 20 tests unitarios
- ✅ Tests de categorías (sinonimo, temporal, territorial, tecnica, especificacion)
- ✅ Edge cases (query vacía, desconocida, larga, con especiales)
- ✅ Integración con QueryPreprocessor
- ✅ API endpoints

---

## 🔗 Integración con Otros Casos

| Caso | Relación |
|------|----------|
| **#3 (Interpretación)** | Usa estructura extraída para sugerencias contextuales |
| **#4 (Expansión)** | Comparte diccionario de sinónimos |
| **#12 (Validación)** | QueryPreprocessor valida antes de sugerir |

---

## ⚠️ Limitaciones

1. **LLM puede fallar** → Silencioso, el usuario ya tiene sugerencias léxicas
2. **Timeout 45s** → Tiempo máximo para polling del LLM
3. **Cache 5 min** → Resultados LLM expiran rápido para ahorrar recursos
4. **Diccionario limitado** → 50 términos, puede ampliarse
5. **Copiar al portapapeles** → Streamlit no permite copiado directo por seguridad. El usuario debe seleccionar el texto del cuadro `st.code()` y usar Ctrl+C.

### Pendiente de Verificación

| Feature | Estado | Notas |
|---------|--------|-------|
| Botón copiar funcional | ⚠️ Pendiente test | Usa st.button() + st.code() para mostrar texto copiado |
| Búsqueda con Enter | ✅ Implementado | st.form() permite submit con Enter |
| UI unificada | ✅ Implementado | Sin duplicados léxico/LLM |

---

## 🚀 Futuras Mejoras

| Mejora | Prioridad | Esfuerzo |
|--------|-----------|----------|
| Ampliar diccionario a 100+ términos | Alta | Bajo |
| Sugerencias basadas en historial | Media | Medio |
| Sugerencias "tendencias" (queries populares) | Baja | Alto |
| Integración UI (mostrar sugerencias al hacer click) | Alta | Bajo |

---

## 📝 Notas de Implementación

### Decisiones de Diseño

1. **Híbrido asíncrono** → Mejor UX: usuario ve sugerencias inmediatas, LLM enriquece después
2. **Máximo 2 por categoría** → Evita que sinónimos dominen todas las sugerencias
3. **Cache 5 min** → Balance entre frescura y ahorro de tokens
4. **Polling simple** → Más fácil que SSE/WebSocket para MVP

### Problemas Resueltos

| Problema | Solución |
|----------|----------|
| Sinónimos dominan sugerencias | Límite 2 por categoría |
| LLM lento bloquea respuesta | Fire-and-forget + polling |
| Duplicados léxico vs LLM | Dedupe por texto lowercase |
| Estructura no se usa | Debug + fix en `_get_structure()` |

---

*Documento creado: 2026-06-06*  
*Implementación completada: 2026-06-06*
