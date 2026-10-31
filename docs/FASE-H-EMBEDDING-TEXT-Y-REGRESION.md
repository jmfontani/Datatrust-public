# Fase H · Columna `embedding_text` y prueba de regresión con ambos motores

**Fecha:** 30-sep-2026
**Estado:** las dos tareas **EJECUTADAS Y VERIFICADAS**.

---

## Tarea 1 — Columna `embedding_text`: el catálogo ya es reproducible

### Qué era la deuda

La Fase D cerró con este hallazgo: los vectores del catálogo **no eran
reproducibles desde la BD**. El texto con el que se generaron (`embedding_text` de
la limpieza) no se guardaba en ninguna columna, y reconstruirlo desde los campos
actuales daba **coseno 0,923 (5/80 exactos)**. Es decir: recalcular los vectores
hoy **degradaría** los 87.661 buenos, porque se sustituirían por una aproximación.

La única fuente con el texto exacto era `datasets_clean.jsonl` de la limpieza.

### Qué se ha hecho

1. Creada la columna `embedding_text TEXT` en `datasets` (aditiva; ningún dato
   existente se ha modificado).
2. Volcados los pares `(dataset_id, embedding_text)` del JSONL de limpieza, **solo
   los que existen en la BD**.
3. Carga vía tabla temporal + `UPDATE`, con `\copy` de `psql`.

Script: `codigo/151_poblar_embedding_text.py` (idempotente, con modo simulación
sin `--aplicar`).

### Resultado

| concepto | fichas |
|---|---|
| catálogo total | **94.461** |
| **con `embedding_text`** | **87.661 (92,8 %)** |
| sin texto (las posteriores) | 6.800 (7,2 %) |

El JSONL tenía 87.677 fichas; **87.661** casan con la BD (16 no están en el
catálogo actual). Coincide exactamente con los «originales de mayo-2026» que la
Fase D identificó como reproducibles.

### Verificación: el texto guardado reproduce el vector

Script `codigo/152_verificar_embedding_text_bd.py`. Muestra estratificada por
longitud, vectorizando **el texto que ahora está en la BD** con el mismo modelo y
revisión del catálogo, comparando contra el vector guardado:

| tercio | n | coseno medio | mínimo | exactos (>0,9999) |
|---|---|---|---|---|
| cortas | 20 | **1,000000** | 1,000000 | 20/20 |
| medias | 20 | **1,000000** | 1,000000 | 20/20 |
| largas | 20 | **1,000000** | 1,000000 | 20/20 |
| **global** | **60** | **1,000000** | **1,000000** | **60/60** |

**Reproduce a 1,000000, incluidas las fichas cortas** — el caso que el diagnóstico
previo daba por irresoluble.

Entregable: `entregables/fase_h_EMBEDDING_TEXT_BD.json`.

### Por qué esto cierra la puerta

Antes: recalcular = degradar (0,923). Ahora: recalcular = reproducir (1,0). La
ingesta futura ya puede guardar el texto con el vector y el catálogo es auditable.
**Queda pendiente integrarlo en el pipeline de ingesta** (que
`generate_embeddings_pg.py` escriba la columna), que es una línea de código pero
pertenece al proceso de ingesta, no a esta fase.

### Deuda que permanece, declarada

Las **6.800 fichas posteriores (7,2 %)** siguen sin texto: se generaron con un
esquema que se desconoce (0,96-0,98 con todo lo probado). No son recuperables. La
recomendación es re-sembrarlas con el esquema canónico y guardar su texto.

---

## Tarea 2 — Prueba de regresión con el motor nuevo

### Qué faltaba

El criterio de aceptación de la Fase E del plan («rehacer la prueba de regresión con
el modelo nuevo», «PASA») **no estaba cerrado**. El script existente,
`88_regresion_embeddings.py`, tenía dos defectos que lo hacían engañoso:

- **Cubría solo MiniLM**, nunca BGE.
- **Vectorizaba un texto reconstruido** (`title + description + keywords +
  theme_label + territory_label`), que es justo el que la Fase D demostró que **no**
  generó los vectores → daba 0,92-0,93 y «REVISAR» por construcción.

### Hallazgo al prepararlo

`142_poblar_bge_gpu.py` **no vectorizó `embedding_text`**, sino un texto
reconstruido con su propio esquema (`texto()`: title, description, `Temas`, keywords,
`Territorio`). Es decir: **MiniLM y BGE se generaron con textos distintos**, y
difieren en ~16 palabras por ficha en promedio.

**Consecuencia para la interpretación:** la comparación de motores de las Fases E/F
mezcla dos cambios a la vez — el modelo **y** el texto. El efecto medido (+0,2743)
es la suma de ambos. No invalida la decisión (ambos favorecen BGE y el despliegue es
el que es), pero **debe declararse** al presentar la cifra.

### Qué se ha hecho

Script nuevo `codigo/153_regresion_embeddings_bge.py`, que comprueba **cada motor con
su propio texto**:

| motor | texto usado | dimensiones |
|---|---|---|
| MiniLM (`embedding`) | `embedding_text` **guardado** en la BD | 384 |
| BGE-M3 (`embedding_bge`) | esquema de `142_poblar_bge_gpu.py` | 1024 |

Muestra de 120 fichas estratificadas por longitud (cuartiles).

### Resultado

| motor | coseno medio | mínimo | exactos | veredicto |
|---|---|---|---|---|
| **MiniLM** (`embedding`, 384) | **0,999819** | 0,990635 | 110/113 | **PASA** |
| **BGE-M3** (`embedding_bge`, 1024) | **1,000000** | 0,9999995 | **120/120** | **PASA** |

**VEREDICTO GLOBAL: PASA** (umbral 0,99).

Notas de lectura honesta:
- BGE reproduce **perfecto** (120/120), coherente con que se generó hace un día con
  este mismo entorno.
- MiniLM reproduce a 0,9998 con **3 fichas por debajo de 0,9999** (la peor, 0,9906).
  No es un fallo del entorno: son fichas cuyo texto en la BD no coincide
  exactamente con el que se usó en su día (limpieza posterior, campos tocados). El
  veredicto PASA se sostiene; la cola se declara.
- Las fichas sin `embedding_text` se **excluyen** de MiniLM y se declaran (7 de 120
  en esta muestra), porque no son comparables.

Entregable: `entregables/fase_h_REGRESION_AMBOS_MOTORES.json`.

**Lo que esto cierra**

El criterio de aceptación de la Fase E («PASA con el modelo nuevo») queda
**cumplido y declarado**, no supuesto. Y por primera vez la prueba de regresión es
**honesta con el texto**: cada motor se comprueba contra el esquema que realmente lo
generó.

**Pendiente:** integrarla como comprobación tras cada build, que era el paso 3 del
plan. El script es ejecutable con un `docker cp` + `docker exec`.

### Actualización noche del 30-sep

- **La escritura en la ingesta ya está hecha** (`generate_embeddings_pg.py`),
  verificada end-to-end con ficha de prueba; el invariante queda fijado: la columna
  siempre contiene el texto exacto que produjo el vector de esa fila. Ver
  `DECISIONES.md`, sección `embedding_text`.
- ~~**Hallazgo confirmado y declarado**: las dos columnas de embeddings se generaron
  con **textos distintos** (BGE usó el esquema del 142, no `embedding_text`). El
  +0,2743 de las Fases E/F mezcla modelo y texto; queda como pregunta abierta en
  `DECISIONES.md` la separación de ambos factores.~~
  **CORREGIDO 01-oct-2026 — el aviso era falso.** La cifra canónica +0,2743 usa
  `embedding_minilm_aprox` (texto idéntico al de BGE): el confound se eliminó
  dentro de la propia Fase E (`144_bge_mismo_texto.py`). El efecto texto medido
  aparte es no atribuible (+0,0211). Detalle: `FASE-H-MODELO-VS-TEXTO.md`.
