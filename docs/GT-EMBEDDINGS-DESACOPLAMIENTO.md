# ¿El nuevo ground truth se evalúa contra los embeddings actuales?

**Fecha:** 24-sep-2026
**Respuesta corta:** No debe evaluarse *contra* los embeddings, y hay que
**desacoplarlos**. Pero el juicio ya recogido **es reutilizable** cuando se cambie
de modelo. Los detalles y la prueba, abajo.

---

## 1. Qué significa «evaluar contra los embeddings», en tres piezas distintas

Hay que separar tres cosas que suelen ir juntas:

| pieza | qué es | ¿depende del encoder? |
|---|---|---|
| **el juicio** | el par (consulta, dataset) → nivel 0/1/2 | **NO** |
| **el pool** | qué documentos se someten a juicio | **SÍ** |
| **la consulta ejecutada** | el texto de la consulta | no, pero su *vector* sí |

El juicio humano o del LLM sobre «¿responde este conjunto de datos a esta
consulta?» es **independiente de qué motor lo encontró**. Ese es el activo
reutilizable.

---

## 2. El problema real: sesgo de pooling

Si el GT se construye juzgando **solo el top-30 del motor actual**, quedan sin
juzgar los documentos que ese motor no encuentra pero otro sí. Y un documento sin
juzgar cuenta como no relevante → **el GT penalizaría al motor nuevo por
encontrar cosas buenas.**

### 2.1 Medido, no supuesto

Comparación del top-30 sobre 20 consultas, entre:

- motor actual (semántico 0,7 / léxico 0,3)
- solo semántico (0,7→1,0)
- **solo léxico** (0,0 / 1,0) — *no usa embeddings en absoluto*

| dato | valor |
|---|---|
| documentos distintos en el pool del **motor actual** | 598 |
| documentos distintos en la **unión** de los tres | **838** |
| que el motor actual **no** encuentra | **240** |
| cobertura del pool actual sobre la unión | **71,4 %** |
| solapamiento medio por consulta | **0,764** |

Umbral de referencia: por debajo de 0,80 hay sesgo. Estamos en 0,764.

### 2.2 El caso más claro

Consulta `empleo_004`: el motor actual y el semántico devuelven 30 documentos
**idénticos**; el léxico devuelve 5, de los cuales **solo 2 coinciden**. Es decir,
hay **3 documentos que solo aparecen por vía léxica**.

**Consecuencia directa:** un GT construido solo sobre el top-30 del motor actual
dejaría 240 documentos sin juzgar en 20 consultas. Si alguno es relevante, el
motor que lo encuentre será penalizado por encontrarlo.

### 2.3 La solución

El pool debe ser la **unión** del top-20/30 de varios sistemas:

1. motor actual (semántico + léxico)
2. **solo léxico** (independiente de embeddings por construcción)
3. solo semántico
4. y, cuando exista, **BGE-M3**: su top-20 también entra al pool

Esto es el diseño estándar de TREC. Además da una garantía importante: **la parte
léxica del pool no depende del encoder**, así que el GT nunca queda completamente
atado al modelo de embeddings.

---

## 3. El error que sí hay que evitar: mezclar embeddings

Esto es lo que hay que vigilar técnicamente, y es un error silencioso.

El buscador compara **el vector de la consulta** con **los vectores guardados de
los documentos**. Si los dos lados vienen de modelos distintos:

```python
# la consulta se vectoriza EN VIVO, en la API
EMBEDDING_MODEL = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)
# los documentos ya estan vectorizados en la BD (columna embedding)
```

…la comparación **carece de sentido**. Dos modelos distintos producen espacios
vectoriales distintos; el coseno entre ellos no mide similitud.

### 3.1 Estado actual tras la validación de hoy

| lado | modelo |
|---|---|
| documentos (columna `embedding`) | MiniLM-L12, revisión `e8f8c211` |
| consulta (en la API) | MiniLM-L12, revisión `e8f8c211` |

**Coinciden:** hoy no hay mezcla. La revisión fijada hoy garantiza que si mañana
se reconstruye la imagen, sigue siendo el mismo modelo.

### 3.2 Al migrar a BGE-M3, hay que hacerlo en un solo paso

Migración correcta:

```
1. ampliar la columna:  vector(384) -> vector(1024)
2. recalcular los 94.461 embeddings de documentos        (~45 min)
3. desplegar la API con el modelo nuevo  <-- en el mismo paso
4. rehacer la prueba de regresión con el modelo nuevo
```

**Nunca** en pasos separados: si se despliega la API con BGE-M3 antes de
recalcular los documentos, durante ese intervalo **todas las búsquedas devuelven
basura** (coseno entre espacios distintos).

---

## 4. Entonces, ¿el juicio del GT sirve tras cambiar de modelo?

**Sí.** El juicio es un par (consulta, dataset) con un nivel. No depende de qué
encoder lo encontró ni de qué posición ocupaba.

Lo que cambia al migrar es:

| elemento | ¿se reutiliza? |
|---|---|
| el juicio (consulta, dataset) → nivel | **sí, íntegro** |
| los patrones de texto (`datasets_esperados`) | sí, para el filtro `no_debe_contener` |
| el **pool** | hay que **ampliarlo** con BGE-M3 |
| los **vectores** | no: se recalculan los dos lados |
| las posiciones y el ranking | no: son la medición, no el GT |

Por eso el Paso 1 (recuperar los 470 juicios por `dataset_id`) tiene el valor que
tiene: convierte el GT en algo **independiente del motor**.

---

## 5. Ventaja adicional del diseño por `dataset_id`

Indexar el GT por identificador en vez de por patrón resuelve de paso un problema
que hoy está sin resolver: **la estabilidad del propio GT**.

Hoy, si cambia la descripción de una ficha, cambia su vector, cambia su posición,
y cambia el juicio *aunque el documento sea el mismo*. Es lo que ocurrió con el
experimento de enriquecimiento: se reescribieron 4.015 descripciones y el P@5 se
movió por eso, no porque el buscador empeorara.

Con el GT por `dataset_id`, el juicio **no se mueve** cuando se reescribe una
descripción. Solo se mueve la posición. Eso separa las dos cosas que hoy están
confundidas: *calidad del ranking* y *contenido del documento*.

---

## 6. Resumen

| pregunta | respuesta |
|---|---|
| ¿El GT debe evaluarse contra los embeddings actuales? | **No.** El juicio debe ser independiente del encoder |
| ¿Se puede reutilizar el juicio al cambiar a BGE-M3? | **Sí, íntegro** (pares consulta-dataset) |
| ¿Qué hay que rehacer al migrar? | los vectores (ambos lados) y el pool |
| ¿Hay sesgo en el pool actual? | **Sí: cubre el 71,4 % de la unión** |
| ¿Cómo se evita? | pool = **unión** de varios sistemas (incluido el léxico, que no usa embeddings) |
| ¿Qué error hay que evitar? | mezclar vectores de documentos (modelo viejo) y de consulta (modelo nuevo) |

**Recomendación operativa, en orden:**

1. Construir el GT con **pool unión** (motor actual + léxico puro + semántico), y
   añadir BGE-M3 al pool cuando esté disponible.
2. Indexar el GT **por `dataset_id`**, no por patrón.
3. Desplegar el GT y **medir con los embeddings actuales** para tener la línea
   base.
4. Migrar a BGE-M3 **por pasos 1-4 del apartado 3.2**, en un solo movimiento.
5. Volver a medir: la diferencia entre (3) y (5) es la mejora **real** del
   cambio de modelo, sin contaminación.

---

## Anexo · evidencia

| script | qué mide | resultado |
|---|---|---|
| `100_sesgo_pool.py` | solapamiento top-30 entre sistemas | actual cubre 71,4 % de la unión |
| `88_regresion_embeddings.py` | reproducibilidad de vectores guardados | 100/100 en las últimas fichas |
| `87_validar_revision.py` | coherencia de la revisión fijada | coseno 0,99999994 → mismo vector |

**Verificado en el código:** la búsqueda léxica usa
`ts_rank_cd(search_vector, ...)` sobre PostgreSQL y **no toca la columna
`embedding`**. Es, por tanto, independiente del encoder por construcción.
