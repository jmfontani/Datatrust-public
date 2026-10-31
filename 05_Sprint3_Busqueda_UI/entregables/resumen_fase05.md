# Entregables Fase 05 – Sprint 3: Motor de Búsqueda Híbrida

## Resumen Ejecutivo

Se ha implementado un motor de búsqueda híbrida que combina similitud semántica (embeddings) con búsqueda léxica (BM25) y filtros facetados.

## Componentes Entregados

### 1. Motor de Búsqueda (`codigo/motor/search_engine.py`)

| Característica | Descripción |
|----------------|-------------|
| Búsqueda semántica | Similitud coseno con embeddings normalizados L2 |
| Búsqueda léxica | BM25 sobre títulos y descripciones |
| Combinación | Ponderación configurable (default: 70% semántico, 30% léxico) |
| Filtros facetados | Territorio, tema, formato, publisher |
| Explicaciones | Texto explicando por qué cada resultado es relevante |
| Normalización | Min-max de scores antes de combinar |

**API del motor:**
```python
engine.search(
    query="educación primaria",
    top_k=10,
    semantic_weight=0.7,
    lexical_weight=0.3,
    explain=True,
    territorio="Comunidad de Madrid",  # opcional
    tema="educación",                   # opcional
    formato="CSV",                      # opcional
    publisher="Ministerio",           # opcional
)
```

### 2. API REST (`codigo/api/main.py`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Info de la API |
| `/health` | GET | Estado del motor |
| `/search` | POST | Búsqueda híbrida con filtros |
| `/facets/{facet}` | GET | Valores disponibles de una faceta |

**Ejemplo de petición:**
```json
POST /search
{
  "query": "datos de tráfico",
  "top_k": 10,
  "semantic_weight": 0.7,
  "lexical_weight": 0.3,
  "territorio": "Comunidad de Madrid",
  "explain": true
}
```

### 3. Tests (`codigo/tests/test_search.py`)

Tests implementados:
- ✅ Búsqueda básica
- ✅ Búsqueda semántica pura
- ✅ Búsqueda léxica pura
- ✅ Filtros facetados
- ✅ Explicaciones de relevancia
- ✅ Rendimiento (tiempo medio < 5s)

### 4. Queries de Ejemplo (`datos/queries/test_queries.json`)

10 queries representativas para evaluación:
1. Datos de tráfico en Madrid (con filtro territorial)
2. Educación primaria (con tema)
3. Población por municipios (sin filtros)
4. Presupuestos (con formato)
5. Calidad del aire (territorio + tema)

### 5. Documentación del Algoritmo (`docs/algoritmo/ranking.md`)

Incluye:
- Pipeline completo de búsqueda
- Fórmula de combinación de scores
- Complejidad computacional
- Optimizaciones futuras (FAISS, caché, paralelización)

## Métricas de la Fase

| Métrica | Valor |
|---------|-------|
| Tiempo de búsqueda (medio) | ~200-500ms CPU |
| Resultados por query | 10-100 configurables |
| Pesos combinación | 70% semántico / 30% léxico (default) |
| Filtros facetados | 4 (tema, territorio, formato, publisher) |

## Dependencias de Fases Anteriores

- Embeddings: `04_Sprint2_Embeddings/datos/processed/embeddings.npy`
- Índices: `04_Sprint2_Embeddings/datos/indices/`
- Datasets: `03_Sprint1_Ingesta/datos/processed/datasets_clean.jsonl`

## Estado: ✅ COMPLETADA

*Generado: 2026-05-22*
