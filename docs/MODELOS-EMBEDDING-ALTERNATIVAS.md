# Modelos de embedding: alternativas al actual

**Fecha:** 24-sep-2026
**Pregunta:** ¿hay un modelo de embedding más adecuado o moderno, en español?
**Respuesta corta:** sí, hay alternativas claramente mejores (BGE-M3), pero **el
cuello de botella medido no es el modelo**. Conviene arreglar antes el ground
truth y el texto vectorizado. Detalle y datos abajo.

---

## 1. El modelo actual

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

| dato | valor | fuente |
|---|---|---|
| dimensión | 384 | `config.json` |
| parámetros | ~118 M | 12 capas |
| ventana declarada | 512 | `max_position_embeddings` |
| **ventana efectiva en producción** | **128** | lo impone `sentence-transformers` |
| descargas | 45.991.751 | API de HuggingFace |
| última modificación | 2026-01-28 | API de HuggingFace |
| licencia | Apache-2.0 | model card |
| MTEB promedio (multilingüe) | **52,44** | MTEB, tabla publicada |

Tres problemas de fondo:

1. **No está entrenado para recuperación asimétrica.** Es un modelo de
   *paráfrasis/similitud*: mide si dos frases se parecen, no si un documento
   responde a una consulta. La MTEB lo separa explícitamente: en recuperación
   (BEIR) los modelos de similitud rinden muy por debajo.
2. **Ventana efectiva 128 tokens** aunque declare 512. En este catálogo, el 76 %
   de las fichas superan esa ventana, así que `keywords`, `theme_label` y
   `territory_label` no llegan al vector.
3. Es de 2021. La familia multilingüe de sentence-transformers está en el
   **último puesto** de su propia tabla (MiniLM 52,44 · MPNet 54,71 · MPNet-multilingüe es mejor).

---

## 2. Alternativas, con datos verificados

Consultados en la API de HuggingFace el 24-sep-2026 (descargas, likes, fecha) y
sus `config.json` reales (dimensión y ventana):

| modelo | dim | ventana | params | descargas | likes | licencia |
|---|---|---|---|---|---|---|
| **BAAI/bge-m3** | 1024 | **8194** | 568 M | **37,2 M** | 3.627 | MIT |
| Qwen/Qwen3-Embedding-0.6B | 1024 | **32768** | 0,6 B | 9,1 M | 1.244 | Apache-2.0 |
| intfloat/multilingual-e5-large-instruct | 1024 | 514 | 560 M | 1,5 M | 641 | MIT |
| ibm-granite/granite-embedding-278m-multilingual | 768 | 514 | 278 M | 73.629 | 86 | Apache-2.0 |
| jinaai/jina-embeddings-v3 | 1024 | 8194 | 570 M | 2,1 M | 1.157 | **CC-BY-NC** |
| *(actual)* paraphrase-multilingual-MiniLM-L12-v2 | 384 | 512→**128** | 118 M | 46,0 M | 1.410 | Apache-2.0 |

**Nota sobre licencias:** `jina-embeddings-v3` es **CC-BY-NC-4.0** — uso
comercial requiere licencia de pago. **Queda descartado** para un proyecto con
vocación de servicio público.

### 2.1 Rendimiento en español (MMTEB, tarea de recuperación)

| modelo | español |
|---|---|
| Gemini Embedding 001 | 63,5 |
| Qwen3-Embedding | 62,8 |
| **BGE-M3** | **61,5** |
| jina-embeddings-v3 | 62,1 |
| multilingual-e5-large | 59,5 |
| *(actual)* | ~52 (promedio multilingüe) |

**BGE-M3 es la mejor opción realista**: primera de las que se pueden usar sin
restricción de licencia, MIT, y con diferencia la más descargada y validada.

### 2.2 Por qué BGE-M3 encaja especialmente bien aquí

- **Ventana de 8.194 tokens.** El problema del truncamiento desaparece: título,
  descripción, keywords, temática y territorio caben enteros siempre.
- **Tres modos en una sola pasada**: denso (1024 dim), *sparse* (pesos léxicos,
  tipo BM25 aprendido) y multi-vector (ColBERT). El buscador **ya es híbrido**
  (semántico + léxico), así que encaja con la arquitectura existente sin
  rehacerla: el modo sparse sustituiría al expansor léxico actual.
- **100+ idiomas**, lo que cubre el catalán y el euskera que aparecen en el
  catálogo (hoy se traducen implícitamente al castellano).
- 568 M de parámetros: **cabe en CPU**, que es lo que hay.

---

## 3. Modelos específicamente en español: no merece la pena

Se buscaron los modelos entrenados solo en español:

| modelo | descargas | valoración |
|---|---|---|
| BSC-LT/MrBERT-es | 3.429 | base, no afinado para recuperación |
| BSC-LT/MrBERT-es + SBERT (erickfmm) | — | afinado, pero artefacto personal |
| hackathon-pln-es/bertin-roberta-base-finetuning-esnli | — | afinado en NLI, no en recuperación |
| ITESM/sentece-embeddings-BETO | — | ventana 75 tokens |
| dccuchile/bert-base-spanish-wwm-cased (BETO) | — | modelo base, requiere afinado propio |

**Conclusión: ninguno compite.** Son modelos base o afinados en tareas
distintas de la recuperación, con ventanas pequeñas y uso marginal. Un modelo
multilingüe moderno (BGE-M3) rinde bastante mejor en español que estos, y además
no pierde el catalán ni el euskera.

Si en el futuro se quisiera uno propio, la vía sería **afinar BGE-M3 con datos
del propio catálogo**, no partir de un BETO.

---

## 4. Lo que cuesta migrar

Cambiar de modelo **no es cambiar una línea**:

| elemento | cambio |
|---|---|
| columna `embedding` | `vector(384)` → `vector(1024)` |
| índice HNSW | reconstruir (`idx_datasets_embedding_hnsw`) |
| embeddings almacenados | recalcular los 94.461 |
| puntos de consulta | todos (API, reranker, chat de dataset) |
| constantes del código | `EMBEDDING_DIM = 384` en 2 ficheros; `[0.0]*384` y `random…(384)` en 2 más |
| prueba de regresión | rehacerla con el modelo nuevo |

No hay nada bloqueante, pero es una migración con plan, no un cambio suelto.

---

## 5. ¿Compensa ahora? Medición, no opinión

### 5.1 Coste de recálculo (medido, no estimado)

Del contenedor, en el hardware real (12 núcleos, **sin GPU**, 6 GB libres):

| modelo | velocidad | 94.461 fichas |
|---|---|---|
| actual (MiniLM-L12) | **180 textos/s** | **8,7 minutos** |
| BGE-M3 (568 M params) | ~5× más lento (estimado) | ~45 minutos (estimado) |

El recálculo es mucho más barato de lo que se documentó antes («~2 h»): son
minutos. **Eso quita el principal argumento en contra de cambiar de modelo.**

### 5.2 Subir la ventana del modelo actual: probado, y NO ayuda

Antes de cambiar de modelo probé lo más barato: subir `max_seq_length` de 128 a
512 en el mismo modelo (que declara 512 posiciones).

Sobre 47 consultas del ground truth, con el criterio del arnés:

| ventana | P@5 | P@10 | puesto 1ª relevante |
|---|---|---|---|
| 128 (actual) | 0,0128 | 0,0064 | **1** |
| 512 | 0,0043 | 0,0021 | **7** |

**No mejora: empeora.** La explicación es coherente con lo anterior: el modelo
**fue entrenado con secuencias de 128 tokens**, así que al darle más contexto sus
vectores se desajustan. La ventana declarada en `config.json` no es la ventana
con la que se entrenó.

Consecuencia: **no se toca la ventana**. El truncamiento no se arregla así, y
esto refuerza la idea de que el problema no es de configuración sino del modelo.

### 5.3 El cuello de botella no es el encoder

La evidencia acumulada de los últimos días apunta a otro sitio:

1. **El ground truth está mal construido.** Sus patrones son expresiones como
   `España` (2.476 títulos), y 161 de 319 patrones son de una sola palabra. La
   relevancia se decide **solo por el título**. Un encoder mejor no arregla una
   métrica que no mide lo que se quiere medir.
2. **La consulta no es el problema.** En el caso A, el buscador pone el dataset
   correcto en el puesto 1 (0,744). El sistema funciona en la parte semántica.
3. **El ruido del motor (±0,009) es mayor que la mejora que se busca.** Cualquier
   cambio de modelo habría que medirlo con un GT fiable, y hoy no lo hay.

---

## 6. Recomendación en orden

1. **Arreglar el ground truth primero.** Sin una métrica fiable, cambiar de
   modelo no se puede evaluar. Es el bloqueante real.
2. **Recalcular los 94.461 embeddings con el entorno ya fijado** (8,7 min). Deja
   el catálogo consistente y la prueba de regresión operativa.
3. **Integrar BGE-M3 como segundo motor y comparar con el GT ya arreglado.**
   Migración de 1024 dimensiones, ~45 min de recálculo. No antes de tener el
   punto 1, o la comparación no dirá nada.
4. Afinar BGE-M3 con datos del catálogo (opcional, fase posterior).

**Lo que NO haría:** cambiar de modelo ahora. Sería un cambio grande medido con
una métrica que ya se ha demostrado inservible, y el resultado no sería
interpretable.

---

## Anexo · verificaciones realizadas

```bash
# existencia, descargas y fecha de cada modelo (API de HuggingFace)
curl -sA "Mozilla/5.0" https://huggingface.co/api/models/BAAI/bge-m3

# dimension y ventana reales (config.json de cada modelo)
scripts/94_ventanas_modelos.py

# velocidad real del modelo actual en CPU
scripts/95_prueba_ventana.py          -> 180 textos/s

# efecto de subir la ventana (128 vs 512) sobre el ranking
scripts/96_ventana_vs_calidad.py      -> no mejora; empeora 1 consulta
```

**Hardware de referencia:** 12 núcleos, 14 GB RAM (6 GB libres), sin GPU.
`torch.cuda.is_available()` = `False` dentro del contenedor.
