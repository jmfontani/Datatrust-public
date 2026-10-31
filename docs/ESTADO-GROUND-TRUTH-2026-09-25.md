# Estado del ground truth · punto de continuación

**Fecha:** 25-sep-2026 · **sesión cerrada sin commit** · API health 200

Documento de traspaso para retomar el trabajo sin releer la sesión.

---

## 1. El objetivo, en una frase

Poder decidir **con datos** si un motor de recuperación es mejor que otro
(MiniLM actual vs BGE-M3), sobre el catálogo de datos.gob.es (94.461 fichas).

---

## 2. Lo que está hecho y es sólido

### 2.1 El bug del `top_k` — corregido

`main_v2_final_v07.py` (+76/−17). El ranking dependía de `top_k` porque la
normalización del léxico se hacía dividiendo por el máximo de cada consulta
(un accidente: el máximo de `ts_rank_cd` variaba de 0,0008 a 13,4 según la
consulta). Sustituido por `rank/(rank+0.2)`, con `k` medido sobre la
distribución real. Recorte interno `max(150, top_k*3)`.

- Test de aceptación: primer resultado y top-5 idénticos para todo `top_k`
  → **0/47** (antes 21/47).
- Vuelta atrás: imagen `docker-api:pre-bugfix-2026-09-25` +
  `backup/main_v2_final_v07.py.PRE-ARREGLO` (sha256 `a2fa2a36…`).
- Doc: `docs/BUG-TOP_K-CORREGIDO.md`.

### 2.2 La línea base canónica — **47 consultas**

`entregables/fase_b_CRITERIO.json` (GT v2 con el criterio de ámbito corregido):

| sistema | nDCG@10 | IC95 | cob |
|---|---|---|---|
| actual (0,7/0,3) | **0,6408** | [0,5502 · 0,7314] | 100 % |
| semántico (1,0/0,0) | 0,5801 | [0,4948 · 0,6654] | 100 % |
| léxico (0,0/1,0) | 0,4368 | [0,3269 · 0,5467] | 74 % |

**Comparación pareada (el dato decisivo, medido 25-sep):**

| comparación | diff | IC95 de la diff | veredicto |
|---|---|---|---|
| actual vs semántico | +0,0607 | [+0,0043 · +0,1171] | **DISTINGUIBLE** |
| actual vs léxico | +0,2041 | [+0,0891 · +0,3190] | **DISTINGUIBLE** |
| semántico vs léxico | +0,1433 | [+0,0068 · +0,2799] | **DISTINGUIBLE** |

→ **El híbrido gana a los dos motores por separado, y los tres se distinguen.**
La pregunta original («¿aporta el híbrido?») **ya está respondida con 47 consultas.**

El plan decía que con 47 la mejora detectable era 0,106 y hacían falta 213
consultas; eso valía para una **media aislada**. La diferencia **pareada** detecta
0,0564. Las 216 siguen haciendo falta para mejoras pequeñas (~0,03, la de BGE-M3),
no para lo ya medido.

### 2.3 El criterio de ámbito — corregido

El ámbito va en el **criterio del juez**, no en el texto de la consulta. Las 225
etiquetas de nivel 1 se rejuzgaron: **146 eran en realidad «responde»**.
Control de ida y vuelta: ~45 % efecto del criterio, ~50 % reproducibilidad del
nivel 1 (era 0,45, frente al 0,881 global — era la categoría frágil).
Copia previa: `gt_etiquetas_v2_PRE-CRITERIO.json`.
Docs: `FASE-C-PASO1-HALLAZGO.md`, `FASE-C-PASO1-EJECUTADO.md`.

### 2.4 El GT v3 — juicio hecho, **texto de consulta contaminado**

- **6.722 etiquetas** (v2 intacto: 0 cambiadas, 1.424/1.424 presentes).
- 5.298 pares nuevos juzgados, 0 fallos de lote, 242 min, < 5 €.
- **El juicio es válido como par (consulta, ficha)**; lo que caduca es el *texto*.
- Doc: `docs/FASE-C-PASO3-HALLAZGO-CONTAMINACION.md`.

### 2.5 El hallazgo de la estratificación

Los motores **no se ordenan igual** según el tipo de consulta:

- consulta que **copia** el vocabulario del catálogo → gana el **léxico** (0,7331)
- consulta que **no lo copia** → semántico y léxico **empatan** (0,3517 / 0,3533)
  y **gana el híbrido** (0,4223)

→ El híbrido es la mejor opción de despliegue **no por su media, sino porque es el
único que no pierde en ningún régimen**.

---

## 3. El problema abierto (lo único que bloquea)

**Las 216 consultas NO sirven para comparar motores.** Motivo:

Las 169 nuevas se generaron mostrando al LLM **40 títulos reales** del catálogo, y
el LLM copió su vocabulario. Resultado aparente (FALSO): actual 0,5827 · léxico
0,5802 · semántico 0,4350 → «el léxico empata con el híbrido».

Pruebas de que es artefacto:

| sistema | 47 antiguas | 169 nuevas | delta |
|---|---|---|---|
| semántico | 0,5801 | 0,3947 | **−0,1854** |
| léxico | 0,4368 | **0,6201** | **+0,1834** |

- Se cruzan **solo** en las nuevas. Longitud idéntica (2,8 vs 2,9 palabras).
- Solapamiento con el título del top-1: léxico **+0,208**.
- **Prueba decisiva** (tercios por solapamiento): `semántico − léxico` =
  **−0,0016** con solapamiento bajo y **−0,3816** con solapamiento alto.

→ Un vuelco de 0,38 causado por el **texto de la consulta**, no por el motor.

**Matiz honesto:** las nuevas son también algo más difíciles (8,6 nivel-2
disponibles frente a 11,6). Es un factor real, pero afecta a los tres motores por
igual y no explica el cambio de orden.

---

## 4. La decisión pendiente

Tres opciones, sin ejecutar ninguna:

- **A. Arreglo completo** — regenerar las 169 **sin mostrar títulos al LLM** (solo
  tema y facetas) + medir solapamiento **antes** de juzgar (criterio: bajar de
  **0,571**, el de las 47 humanas) + rehacer pool y juicio (~4 h, <5 €).
  → Deja un instrumento válido para comparar motores y para medir BGE-M3.
- **B. Solo el control** (~15 min) — regenerar y medir solapamiento, sin rejuzgar.
  Confirma la causa, no da resultado utilizable.
- **C. Parar aquí** — la pregunta original ya está respondida con 47.

**Recomendación dada: A**, porque la Fase E (BGE-M3) espera una mejora de ~0,03 y
el conjunto de 47 no la distingue. Si el trabajo se cierra con lo que hay, **C es
defendible** y nada queda mal documentado.

---

## 5. Trampas y lecciones de esta sesión

1. **Nunca mostrar texto del corpus al LLM que genera consultas de evaluación** —
   contamina la comparación entre motores. Medir el solapamiento *antes* de
   juzgar: cuesta segundos y aquí habría ahorrado 4 horas de juicio.
2. **No reimplementar métricas.** El nDCG propio (ganancia exponencial, ideal del
   top-k) no coincidía con el canónico (ganancia lineal, ideal de todos los
   juicios). Se detectó reproduciendo una cifra publicada (0,6408).
3. **Comparar pareado**, no dos medias independientes. Detectable: 0,0464 suelto
   vs **0,0355** pareado, con los mismos datos.
4. **Un validador propio que marca >25 % de la muestra es el sospechoso.** El
   filtro por palabras clave marcó 45/169 consultas como dudosas, todas falsos
   positivos.
5. **Subcadena ≠ palabra**: «nacional» casaba «nacionalidad».
6. **Cambiar el texto de una consulta invalida sus etiquetas.** Medido: 32,2 %
   cambian de nivel, 12 casos reproducibles en la misma dirección.
7. **El contenedor va en UTC** (2 h de desfase con el host) — confunde al
   comparar marcas de tiempo.
8. **`docker compose build` se lleva `/codigo`** del contenedor: hay que volver a
   copiar los scripts y `entregables/`.

---

## 6. Ficheros, estado y vuelta atrás

**Nuevos (todos `??`, sin commit):** scripts `116`–`134` en
`09_Sprint7_RAGAS/codigo/`; docs `BUG-TOP_K-CORREGIDO`, `FASE-C-PASO1-HALLAZGO`,
`FASE-C-PASO1-EJECUTADO`, `FASE-C-PASO2-EJECUTADO`,
`FASE-C-PASO3-HALLAZGO-CONTAMINACION`.

**Modificado:** `08_Sprint6_LLM_Mejora/codigo/api/main_v2_final_v07.py` (+76/−17).

**Entregables clave:** `gt_etiquetas_v2.json` (línea base, 1.424 etiquetas) ·
`gt_etiquetas_v3.json` (6.722) · `fase_b_CRITERIO.json` (cifras canónicas) ·
`fase_c_FINAL_216.json` (**NO usar como resultado**) ·
`control_sesgo_vocabulario.json` · `estratificacion_vocabulario.json`.

**Copia de seguridad de embeddings:** tabla `datasets_emb_backup_20260925`
(94.461 filas, 384 dim, 0 discrepancias).

**Imágenes de vuelta atrás:** `docker-api:pre-bugfix-2026-09-25` ·
`docker-api:pre-pinning-2026-09-24`.

**Git sucio (ojo antes de commitear):** 83 `??`, **77 borrados** sin confirmar del
movimiento `metodología EOI` → `metodologia/` (21-sep), 10 `M`.

---

## 7. Lo que NO está hecho

- **Fase D** — recalcular los 94.461 embeddings (el catálogo es inconsistente: las
  fichas cortas no se reproducen desde la BD; causa raíz no identificada). ~9 min.
  Integrar `88_regresion_embeddings.py` como comprobación tras cada build.
  Invalida las cifras del bugfix → habrá que re-medir.
- **Fase E** (BGE-M3) — bloqueada por el instrumento. Sus dos condiciones (GT
  arreglado, catálogo coherente) **no se cumplen aún**.
- **Commit** — nada está commiteado.
- **Puerta G2** — robustez al prompt 0,780 (por debajo de 0,85). Consecuencia:
  fijar un prompt canónico y no cambiarlo.
