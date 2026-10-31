# Fase H · Modelo vs texto — el +0,2743 ya separaba los factores

**Fecha:** 30-sep/01-oct-2026
**Estado:** **el confound de texto que declaré ayer NO existe en la cifra canónica.**
Fue eliminado dentro de la propia Fase E. Queda medido el residuo del texto, que es
pequeño y no atribuible.

---

## Qué se averiguó (y corrección de mi aviso de ayer)

Al preparar la descomposición 2×2 se revisó `143_comparar_motores.py` y el
entregable canónico, y aparece esto en `fase_e_FINAL_v5.json`:

```
"columna_minilm": "embedding_minilm_aprox"
```

Es decir: la comparación canónica **ya usa la columna anti-confound**. La Fase E
hizo el trabajo en dos tandas (documentado en `FASE-E-BGE-M3-RESULTADO.md`, §3):

1. Primera medición (`143`): MiniLM con su texto de origen vs BGE con el esquema
   del 142. **GT v4 → 0,3539 vs 0,3657, +0,0118, no concluyente** — porque además
   sufría el sesgo de cobertura (que sí era el defecto grave).
2. Corrección (`144_bge_mismo_texto.py`): MiniLM recalculado sobre el **mismo
   texto** que BGE (20,9 min, 75/s), columna `embedding_minilm_aprox`, y luego el
   pool conjunto con el GT v5. La cifra **+0,2743 sale de ahí** — texto idéntico en
   ambos brazos, modelo como única variable.

El 2×2 completo (GT v5 canónico):

| MODELO \ TEXTO | esquema limpieza (`embedding_text`) | esquema 142 (reconstruido) |
|---|---|---|
| **MiniLM** | 0,3212 — *columna `embedding`* | *0,3423 — `embedding_minilm_aprox`* |
| **BGE-M3** | no medida (no hay columna) | *0,6157 — `embedding_bge`* |

Las celdas en cursiva son el texto constante: **el efecto MODELO es +0,2734**
(BGE 0,6157 vs MiniLM-aprox 0,3423), casi idéntico al canónico +0,2743 porque ambos
brazos del canónico ya compartían texto.

*Nota de honestidad*: la celda MiniLM-limpieza del cuadro de arriba la acabo de medir
sobre el GT v5 (0,3212); en el doc de la Fase E la cifra análoga con GT v4 era
0,3539. No es contradictoria: distinto GT y distinto top-k de referencia.

## Efecto del texto (modelo constante, GT v5, medido hoy)

Script nuevo `155_efecto_texto_gt_v5.py` — comparación pareada de MiniLM con sus dos
textos, con IC95, sobre el GT v5 canónico. Nunca se había hecho con este GT (el
control de la Fase E era con el v4 y sin IC).

| texto de MiniLM | nDCG@10 | IC95 |
|---|---|---|
| esquema limpieza | 0,3212 | [0,2763 · 0,3660] |
| esquema del 142 | 0,3423 | [0,2990 · 0,3856] |

**Pareada: +0,0211 · IC95 [−0,0061 · +0,0484] — cruza cero: EMPATE.**

Es decir: cambiar el texto de la limpieza por el esquema del 142 mueve la métrica
±0,02 como mucho, no atribuible. El **conflound texto es pequeño y no influye** en
la historia de la migración.

## Lo que esto cierra y corrige

1. **El aviso de ayer retirado.** En
   `FASE-H-EMBEDDING-TEXT-Y-REGRESION.md` y en `DECISIONES.md` declaré que «el
   +0,2743 mezcla modelo y texto». No es cierto: ese número es de la comparación
   con texto constante (`embedding_minilm_aprox` vs `embedding_bge`), y el
   docstring del `144` así lo declara. Se corrige y queda documentado aquí.
2. **La historia para la memoria queda limpia.** Se puede escribir: *«el efecto
   modelo medido con texto constante es +0,2743; el efecto texto, medido aparte
   con el modelo constante, es no atribuible (±0,02)»*. Eso responde de forma
   completa la pregunta «¿ganasteis por el modelo o por cómo preparabais el
   texto?».
3. **No hace falta la re-vectorización de 5-6 h.** Se canceló antes de lanzarla:
   la celda BGE-sobre-embedding_text no aporta nada a la pregunta y las celdas
   relevantes ya estaban medidas.

## Caveats

- BGE se vectorizó con `texto()` del 142. Ese esquema **no** es
  `embedding_text`; pero la cifra canónica enfrenta `embedding_bge` contra
  `embedding_minilm_aprox` — **ambos con el esquema del 142** — así que el texto
  no confunde.
- El efecto texto se mide con MiniLM como anfitrión (única columna par con dos
  textos disponibles). No se puede descartar que en BGE el efecto texto sea
  distinto; es la limitación estándar del diseño con una columna por par.
- La primera medición del 155 al correrla dentro del contenedor usó la copia del
  GT v5; el JSON entregado ha sido verificado byte a byte contra el del repo.

## Artefactos

- `codigo/155_efecto_texto_gt_v5.py`
- `entregables/fase_h_EFECTO_TEXTO.json`
- Columna ya existente que hace posible el control: `embedding_minilm_aprox` (Fase E)