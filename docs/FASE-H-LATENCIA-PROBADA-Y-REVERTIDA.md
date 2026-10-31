# Fase H · Latencia: lo probado y por qué se quedó como estaba

**Fecha:** 01-oct-2026
**Estado:** **fix de latencia probado en producción y RETIRADO por degradar calidad.**
La decisión queda documentada con números — no volver a intentarlo «a ojo».

---

## 1. El diagnóstico (verificado, correcto)

Los 94.461 vectores de fichas **ya están en Postgres** (`embedding_bge`); por
consulta solo se vectoriza la frase del usuario (ollama, **116 ms** en caliente,
6,2 s el primer golpe tras un reinicio). El desglose real de la latencia de
`/search`:

| pieza | tiempo |
|---|---|
| ollama embed consulta (warm) | 116 ms |
| SQL semántica con el índice HNSW | 7 ms |
| **SQL del handler** (con `JOIN + GROUP BY`) | **2.346 ms** |
| léxico + ensamblado | ~12 ms |

Causa: la forma `LEFT JOIN dataset_formats + GROUP BY` **impide el uso del índice
HNSW**, así que Postgres hace un *seq scan exacto* de los 94.461 vectores en cada
consulta. Reescrita con una subquery en `SELECT` cae al índice: **30 ms** (×75).

## 2. Pero el índice tampoco era equivalente — lo medido

Calibración sobre 40 consultas del GT, contra el resultado exacto (seq scan):

| `hnsw.ef_search` | solape medio top-10 | rankings idénticos | nDCG@10 (40 cons.) |
|---|---|---|---|
| 40 (default) | 6,65/10 | 12/40 | 0,5810* |
| 100 | 7,88/10 | 23/40 | — |
| 200 | 8,35/10 | 25/40 | 0,6391 |
| 500 | 9,47/10 | 30/40 | **0,7111** |
| 1000 | — | — | 0,7113 |
| **exacto (seq scan)** | 10/10 | 40/40 | **(0,7565 en la misma muestra)** |

*el 0,5810 de ef40 venía de una primera pasada; la calibración fina es la de la
segunda tabla.

## 3. El experimento en producción (honesto: se desplegó y se midió)

Se desplegó la SQL reescrita con `ef_search = 500` y se re-midieron **las 214
consultas** con el instrumento canónico:

| | nDCG@10 (GT v5, 214 consultas) |
|---|---|
| exacto (lo servido hasta hoy) | **0,5575** |
| HNSW ef500 | **0,5260** |
| **pareada (ahora − antes)** | **−0,0315** · IC95 [−0,0517 · −0,0114] → **DISTINGUIBLE, BAJA** |

**La latencia baja (0,16 s media, de 2,5 s) pero la calidad cae −0,0315** — cinco
veces la mejora mínima detectable del instrumento. Con `ef_search` 1000 el nDCG
apenas sube (0,7113 vs 0,7111 en la muestra) y el solape con el exacto sigue sin
ser idéntico.

**Decisión: revertir.** El fix estaba desplegado ~40 minutos. Revertido con el
código original (JOIN + GROUP BY, seq scan exacto), re-desplegado y **verificado:
214/214 rankings idénticos** al snapshot anterior.

## 4. Qué queda

- **Producción: sin cambios.** La SQL del handler sigue siendo la exacta — es la
  que sirvió todos los números de la Fase H y la que mide 2,3-2,5 s.
- **Hallazgo nuevo para el libro de decisiones:** el índice HNSW construido
  (`m=16, ef_construction=64`) **no alcanza equivalencia con el exacto** con
  `ef_search` razonables: a 500 recupera 9,47/10 y su nDCG es −0,03 bajo el exacto.
  Para que la aceleración ×75 sea gratuita habría que **reindexar con
  `ef_construction` mayor** (p. ej. 200 con `m=32`), que son horas de construcción
  y hay que validarlo contra el exacto como hoy. Queda como opción declarada, no
  ejecutada.
- El primer golpe tras reiniciar la API (ollama frío, +6 s) no es la latencia de
  servicio: es el calentamiento del modelo. No se toca.

## 5. La lección

«El índice parece más rápido» no basta: el índice de pgvector es **aproximado**, y
la calidad de un buscador se mide, no se supone. La prueba honesta es la que se
hizo: desplegar, re-medir las 214 con el instrumento canónico, y revertir si la
pareada baja. Sin ese paso, el fix habría cambiado los resultados de la web en
silencio — y los números publicados de la Fase H ya no significarían lo mismo.

Artefactos: `main_v2_final_v07.py` (revertido, con notas de por qué), esta
documentación. La calibración de ef_search vive en el transcript y los números están
en la sección 2.