# Fase D · Hallazgo: el «desajuste de embeddings» era un error de diagnóstico

**Fecha:** 28-sep-2026 · **Estado:** diagnóstico cerrado · línea base fijada · bug latente corregido

---

## 1. Resumen en tres frases

1. El «desajuste de embeddings» que el plan y el pinning daban por hecho **era un
   error de diagnóstico**: se comparaba el vector guardado contra un texto que no
   era el que se usó para generarlo.
2. El catálogo **sí tiene un problema real de reproducibilidad**, pero su causa es
   otra: la limpieza vectorizó un `embedding_text` construido con campos que la BD
   **ya no conserva**, así que el texto **no es reconstruible** desde la BD.
3. Se ha corregido un **bug latente real** en el script de embeddings (roto, además:
   habría fallado en la próxima ingesta) y se ha **fijado la línea base**.

---

## 2. Cómo se llegó hasta aquí (en orden)

### 2.1 La sospecha inicial no se sostenía

`137_medir_discrepancia_embeddings.py` (400 fichas estratificadas) comparó el vector
guardado contra el texto que vectoriza `generate_embeddings_pg.py`:

| grupo | coseno medio | mínimo | < 0,999 |
|---|---|---|---|
| cortas (desc <80) | 0,8616 | 0,6700 | 96 % |
| medias (80-300) | 0,9354 | 0,7710 | 94 % |
| largas (>300) | 0,9876 | 0,8876 | 47 % |
| **global** | **0,9349** | **0,6135** | **70,5 %** |

### 2.2 No era cuestión de combinar campos

`138_diagnosticar_texto_embeddings.py` probó **15 combinaciones** de campos. Ninguna
pasó de 0,86. Descartado: `tags`, `url`, `license`, `content_text`.

### 2.3 La respuesta estaba en el repo

Los vectores **no los generó `generate_embeddings_pg.py`**, sino
`generate_embeddings.py` (Sprint1), que vectoriza el campo **`embedding_text`**
construido por `clean_datasets.py:468-477`:

```
title_es \n title_en \n description_es_clean
         \n Temas: <temas> \n Palabras clave: <keywords> \n Territorio: <territorio>
```

`139_verificar_embedding_text_original.py` lo confirma sobre los vectores guardados:

| grupo | coseno | exactos |
|---|---|---|
| 40 aleatorias | **0,999979** | 39/40 |
| cortas (<80) | 0,999746 | 28/29 |
| medias (80-300) | 0,999454 | 27/29 |
| largas (>300) | 0,999902 | 26/27 |

**Reproduce a ~1.0 en todos los grupos, incluidas las cortas** — justo el caso
patológico que el diagnóstico previo señalaba como irresoluble.

---

## 3. El problema real: el texto no es reconstruible

Reconstruyendo el mismo esquema **desde la BD** (que es lo que puede hacer la
ingesta futura), la reproducción **falla**:

| texto usado | coseno (80 fichas cortas) | exactos |
|---|---|---|
| esquema reconstruido desde la BD | 0,923 | 5/80 |
| `embedding_text` original | **0,999963** | 55/56 |

**Causa raíz, verificada:** la limpieza construyó el `embedding_text` con campos que
la BD ya no conserva tal cual:

- `title_es` **y** `title_en` — la BD guarda `title` fusionado
- `description_es_clean` — limpiada y truncada a 1000 chars
- **temas normalizados**: `theme` guarda la etiqueta (`demografia`) y **`theme_label`
  guarda el URI** (`http://datos.gob.es/kos/...`) en **89.958 fichas (95 %)**. Usar
  `theme_label` hunde el coseno a 0,897
- territorio **inferido** por la limpieza, puede no coincidir con `territory_label`

**Conclusión de diseño:** la única forma de que un vector sea reproducible es
**guardar el texto con el que se generó**. La BD no lo guarda. Eso sí es un problema
real, y no se arregla recalculando: el texto no está.

### Los dos regímenes del catálogo

| grupo | fichas | texto de origen | ¿reproduce? |
|---|---|---|---|
| originales (mayo-2026) | **87.661** | `embedding_text` de la limpieza | ✅ ~1,0 con el texto exacto |
| posteriores | **6.800** | desconocido (0,96-0,98 con todo lo probado) | ❌ |

---

## 4. Dos bugs reales encontrados y corregidos

### 4.1 Bug latente: se vectorizaba un texto distinto

La versión anterior vectorizaba `title + description + keywords + theme_label +
territory_label`. Por dos motivos eso era incorrecto:

- No es el esquema que generó el 92,8 % del catálogo.
- **Usaba `theme_label`, que contiene el URI** en el 95 % de las fichas: metía
  `http://datos.gob.es/kos/sector-publico/sector/demografia` en el texto vectorizado.

Toda ficha nueva quedaba vectorizada en otro régimen, **en silencio**.

### 4.2 Bug que habría roto la próxima ingesta

Al reescribir el guardado con `execute_values` apareció un fallo real, cazado por una
**prueba end-to-end** (insertar una ficha sin embedding y ejecutar el script):

```
psycopg2.errors.InvalidTextRepresentation: malformed vector literal:
"{-0.0236...,0.0047...}"
DETAIL: Vector contents must start with "[". 
```

Pasar una lista de Python produce `{...}` y pgvector exige `[...]`. El vector **no se
guardaba**. Corregido con el literal explícito y **verificado**: 384 dimensiones
escritas correctamente, ficha de prueba eliminada, catálogo en 94.461 y 0 nulos.

---

## 5. Línea base fijada (Fase D)

214 consultas (47 humanas + 167 limpias), GT v4 (6.114 etiquetas), `top_k`=10:

| sistema | nDCG@10 | IC95 | P@5 | MRR | cob |
|---|---|---|---|---|---|
| **actual (0,7/0,3)** | **0,4854** | [0,4363 · 0,5345] | 0,3458 | 0,4932 | 100 % |
| semántico (1,0/0,0) | 0,4259 | [0,3799 · 0,4718] | 0,2879 | 0,4351 | 100 % |
| léxico (0,0/1,0) | 0,3623 | [0,3117 · 0,4129] | 0,3129 | 0,4047 | 68 % |

Pareada: actual vs semántico **+0,0596** [+0,0367·+0,0825] · actual vs léxico
**+0,1231** [+0,0702·+0,1760] · semántico vs léxico **+0,0635** [+0,0030·+0,1241].

Los tres **DISTINGUIBLES**. Mejora detectable (diferencia pareada): **0,0229**.

Guardado en `entregables/fase_d_LINEA_BASE.json`.

---

## 6. Por qué NO se ejecutó el recálculo masivo

El plan decía «recalcular los 94.461 embeddings (8,7 min)». Los datos dicen que:

1. **No arregla la reproducibilidad**: el 92,8 % ya reproduce con su texto original.
2. Reconstruir el texto desde la BD da **0,923**, no 1,0 — recalcular **degradaría**
   los 87.661 vectores buenos, cambiándolos por una aproximación.
3. Movería el ranking justo antes de fijar la línea base.

**Recalcular hoy sería empeorar el catálogo.** Decisión: no ejecutarlo.

---

## 7. ⚠️ Corrección a `docs/PINNING-DEPENDENCIAS.md` §9

La sección **§9 «Diagnóstico del desajuste de embeddings (corregido)»** contiene una
afirmación **incorrecta**:

> «cuando el texto se trunca, el vector se reproduce […] cuando el texto es corto y
> entra entero, no coincide»

Ese patrón era un **artefacto de comparar contra el texto equivocado**: con textos
largos el truncamiento a 128 tokens hacía que ambos textos coincidieran en el prefijo
(y por eso «reproducía»); con textos cortos entraba todo y la diferencia se veía. No
era una propiedad del catálogo, sino de la comparación.

Con el texto correcto, **las fichas cortas reproducen a 0,9997**. La afirmación debe
retirarse y sustituirse por la §3 de este documento.

---

## 8. Ficheros

- `codigo/137_medir_discrepancia_embeddings.py` · `entregables/discrepancia_embeddings.json`
- `codigo/138_diagnosticar_texto_embeddings.py` · `entregables/diagnostico_texto_embeddings.json`
- `codigo/139_verificar_embedding_text_original.py` · `entregables/verificacion_embedding_text.json`
- `entregables/fase_d_LINEA_BASE.json`
- `03_Sprint1_Ingesta/codigo/limpieza/generate_embeddings_pg.py` — **corregido**
- Evidencia de origen: `clean_datasets.py:468-477`, `generate_embeddings.py:47`,
  `conectores/ingest_datos_gob_v2.py:216-221`

---

## 9. Deuda conocida y recomendación

**Deuda:** las 6.800 fichas posteriores (7,2 %) tienen vectores de origen desconocido,
y el texto de las 87.661 no está almacenado (solo reconstruible al 0,923).

**Recomendación:**
1. **Añadir una columna `embedding_text`** a `datasets` y poblarla en la ingesta.
   Es la corrección estructural: a partir de ahí todo vector es reproducible y
   auditable. Coste bajo, beneficio permanente.
2. Usar `--fuente-jsonl` (ya implementado) para re-sembrar las 87.661 con su texto
   exacto si alguna vez se recalculan.
3. **Fase E (BGE-M3)**: ya medible — la mejora esperable (~0,03) supera el umbral
   detectable (0,0229), que con 47 consultas era 0,0564.
