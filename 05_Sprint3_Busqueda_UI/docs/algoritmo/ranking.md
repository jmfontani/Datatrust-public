# Algoritmo de Ranking Híbrido

## Visión General

El motor de búsqueda combina tres señales de relevancia:

1. **Similitud Semántica** (embeddings): Entiende el significado de la consulta
2. **Similitud Léxica** (BM25): Encuentra coincidencias exactas de palabras
3. **Filtros Facetados** (metadatos): Refina por territorio, tema, formato, publisher

## Pipeline de Búsqueda

```
Query del usuario
      ↓
[1] Generar embedding de la query
      ↓
[2] Buscar top-k por similitud coseno (semántica)
[3] Buscar top-k por BM25 (léxica) 
      ↓
[4] Combinar y normalizar scores
      ↓
[5] Aplicar filtros facetados
      ↓
[6] Generar explicaciones de relevancia
      ↓
Resultados ordenados
```

## Fórmula de Combinación

```
score_final = w_semántico × score_semántico_norm + w_léxico × score_léxico_norm
```

Donde:
- `score_semántico_norm`: Normalizado min-max de similitudes coseno
- `score_léxico_norm`: Normalizado min-max de scores BM25
- Pesos por defecto: `w_semántico = 0.7`, `w_léxico = 0.3`

## Normalización Min-Max

```python
score_norm = (score - min_score) / (max_score - min_score)
```

Si todos los scores son iguales (caso degenerado), se asigna 0.

## Búsqueda Semántica

- **Modelo:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Dimensiones:** 384
- **Normalización:** L2 (producto escalar = coseno)
- **Texto vectorizado:** `title + " — " + description`
- **Complejidad:** O(n) con n = número de datasets (búsqueda lineal por ahora)

## Búsqueda Léxica (BM25)

- **Tokenización:** Palabras en minúscula, sin stopwords
- **Parámetros BM25:** Default (k1=1.5, b=0.75)
- **Campos indexados:** Título y descripción
- **Ventaja:** Encuentra palabras exactas incluso si el embedding no las captura

## Filtros Facetados

Los índices invertidos permiten filtrar eficientemente:

| Faceta | Fuente | Ejemplo |
|--------|--------|---------|
| Territorio | `spatial_name` | "Comunidad de Madrid" |
| Tema | `theme_labels` | "educación", "transporte" |
| Formato | `format_labels` | "CSV", "JSON", "XML" |
| Publisher | `publisher_name` | "Ayuntamiento de Madrid" |

**Implementación:** Intersección de sets en memoria (O(min(|A|, |B|)))

## Explicaciones de Relevancia

Para cada resultado se genera una explicación textual:

```
"Alta similitud semántica con la consulta; términos aparecen en 
título/descripción; territorio coincidente: Madrid."
```

**Reglas:**
- Si score semántico > 0.5 → "alta similitud semántica"
- Si score léxico > 0.5 → "términos de la consulta aparecen"
- Si territorio en query coincide → "territorio coincidente"
- Si tema en query coincide → "tema coincidente"

## Complejidad Computacional

| Operación | Complejidad | Notas |
|-----------|-------------|-------|
| Generar embedding | O(d) | d = dimensión del modelo |
| Búsqueda semántica | O(n × d) | n = 87.677 datasets |
| Búsqueda BM25 | O(n × avg_doc_length) | |
| Filtrado facetado | O(k) | k = candidatos post-ranking |
| **Total** | **O(n × d)** | ~200-500ms en CPU |

## Optimizaciones Futuras

1. **FAISS/Annoy:** Reducir búsqueda semántica a O(log n) con índices aproximados
2. **Caché de embeddings:** Pre-computar embeddings de queries frecuentes
3. **Paralelización:** Usar múltiples cores para búsqueda BM25
4. **Índice invertido en PostgreSQL:** Para filtrado más escalable

## Referencias

- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
- [Sentence Transformers](https://www.sbert.net/)
- [FAISS - Facebook AI Similarity Search](https://github.com/facebookresearch/faiss)
