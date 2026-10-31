# Fase C · paso 1 ejecutado: el ámbito en el criterio

**Fecha:** 25-sep-2026
**Qué se ha hecho:** aplicar el criterio de ámbito corregido al ground truth,
rejuzgando las 225 etiquetas de nivel 1. Ejecutado y verificado con control de
ida y vuelta.
**Estado del GT:** 1.424 etiquetas · `{0: 849, 1: 31, 2: 544}`

---

## 1. Lo que se ha cambiado, en una línea

El prompt del juez definía el nivel 1 como *«tema correcto, otro alcance»*
enumerando como equivalentes **«otra comunidad, otro municipio, otro país, otro
periodo, o el desglose»**. Para este catálogo, meter «otra comunidad» en esa lista
es incorrecto: solo el 11,4 % de las fichas es de ámbito nacional, y el juez estaba
penalizando al 88,6 % del catálogo.

El criterio nuevo separa los tres motivos que estaban mezclados:

| nivel | cuándo | antes |
|---|---|---|
| **2** «responde» | mismo fenómeno, territorio **español o sin especificar**, desglose coincide | exigía ámbito español *nacional* |
| **1** «alcance incompatible» | territorio de **otro país**, **desglose** pedido ausente, o **periodo** que no sirve | mezclaba territorio autonómico con desglose y periodo |
| **0** «no responde» | otro fenómeno | igual |

**La consulta no se ha tocado.** Se usó `ground_truth.jsonl` (texto original), no
`consultas_v2.jsonl`, para que las etiquetas sigan siendo comparables con las de
junio.

---

## 2. Resultado del rejuicio

Las 225 etiquetas de nivel 1, rejuzgadas con el criterio nuevo (225/225, 0 fallos):

| destino | n |
|---|---|
| **suben a nivel 2** (eran ámbito autonómico/municipal) | **146** |
| siguen en nivel 1 (desglose o periodo incompatible) | 31 |
| bajan a nivel 0 (era otro fenómeno) | 48 |

**Solo se rejuzgó el nivel 1: es el único que podía moverse.** El criterio nuevo
es *más permisivo* en territorio, así que un 2 ya satisfacía la exigencia estricta
y un 0 lo es por otro fenómeno, donde el territorio no interviene. Rejuzgar 0 y 2
habría gastado llamadas sin poder cambiar nada.

### 2.1 Los 48 que bajan no son un error del criterio

Leyendo sus razones, son casos donde el nivel 1 del prompt viejo **tapaba un
juicio más limpio**: el conjunto mide otro fenómeno, y el juez viejo lo clasificó
como «mismo tema, otro alcance» en vez de «otro fenómeno». Ejemplos:

- «Lista de cines con programación en catalán; **no mide taquilla** ni industria cinematográfica»
- «Mide **densidad urbana**, no densidad de municipios pequeños/rurales»
- «Mide **medallas obtenidas**, no competiciones internacionales celebradas»

El criterio nuevo los separa correctamente.

---

## 3. El control que separa criterio de ruido

El rejuicio usó un prompt distinto, así que el cambio mezcla dos causas: el
criterio (lo que se quiere medir) y la inestabilidad del juez (0,881 de
reproducibilidad, ya medida). Control `127_control_criterio_ambito.py`, ida y
vuelta sobre 40 pares: *texto original → criterio nuevo → prompt viejo otra vez*.

| categoría | n | % | IC95 % |
|---|---|---|---|
| **A) efecto del criterio** (el nivel 1 se reproduce y el criterio lo mueve) | 18 | 45 % | ±15,4 pp |
| **B) el nivel 1 original no se reproduce, y el juicio nuevo es consistente** | 20 | 50 % | ±15,4 pp |
| C) inestable (los dos juicios discrepan) | 2 | 5 % | ±6,8 pp |

### 3.1 Las dos correcciones van en la misma dirección

**A) El criterio mueve el juicio: 45 %.** Confirmado el efecto buscado, en la
dirección prevista (12 casos `1→2→1`, 6 casos `1→0→1`).

**B) El nivel 1 era la categoría frágil del juicio: 50 %.** El nivel 1 **no se
reproduce**: al rejuzgar con el prompt viejo, 22 de 40 (55 %) **no** vuelven a 1.
Y ahí el juicio con el criterio nuevo es **consistente** (da lo mismo con los dos
prompts) en 20 de esos 22. Es decir: el «1» original era la parte inestable, y el
juicio nuevo lo corrige de forma estable.

Esto **encaja con el diseño del prompt viejo**: el nivel 1 era un cajón de sastre
(«otro alcance» cubría ocho situaciones distintas), y una categoría con criterios
múltiples es donde un juez oscila. El criterio nuevo, al obligar a decir *cuál* de
los tres motivos aplica, reduce la ambigüedad del propio prompt.

**Reproducibilidad del nivel 1: 45 %** (frente al 0,881 global). La categoría era
mucho más frágil que la media.

---

## 4. Efecto sobre las métricas

| sistema | nDCG@10 antes del criterio | después | efecto | cobertura |
|---|---|---|---|---|
| **actual (0,7/0,3)** | 0,6365 | **0,6408** | **+0,0043** | 100 % |
| semántico puro | 0,5834 | 0,5801 | −0,0033 | 100 % |
| léxico puro | 0,4069 | 0,4368 | **+0,0299** | 74 % |

**El número apenas se mueve: +0,0043.** Y eso es el resultado importante:

> La corrección **vale por validez, no por la cifra**. El criterio anterior no
> estaba *deformando* el ranking, estaba **describiendo mal** lo que es relevante.
> El motor no mejora; lo que mejora es lo que se está midiendo.

El efecto que sí aparece es en el léxico (+0,0299): sus 146 etiquetas ascendidas a
«responde» incluyen fichas de ámbito autonómico que antes contaban en su contra.
Tiene sentido: el motor léxico devuelve fichas muy literales, muchas de ellas
autonómicas.

---

## 5. Trazabilidad y vuelta atrás

- Copia previa: `entregables/gt_etiquetas_v2_PRE-CRITERIO.json`
- Cada una de las 225 etiquetas tocadas lleva `"nivel_previo": 1` y
  `"origen": "criterio_ambito_2026-09-25"` → auditable caso por caso.
- Revertir: `cp gt_etiquetas_v2_PRE-CRITERIO.json gt_etiquetas_v2.json`

---

## 6. Lo que queda del hallazgo original

El informe `FASE-C-PASO1-HALLAZGO.md` concluía: *«el ámbito va en el criterio, no
en el texto»*. Ejecutado, la conclusión se sostiene, **con un matiz que la medición
ha añadido**:

1. El criterio **sí** era el sitio correcto: 146 etiquetas pasan a «responde» sin
   tocar el texto de ninguna consulta, así que las etiquetas antiguas siguen siendo
   comparables.
2. Pero el daño era **mayor de lo que sugería el primer test**: la premisa
   «reutilizar las etiquetas» tampoco valía para el nivel 1, porque **el 55 % de
   ese nivel no se reproducía**. No hacía falta reescribir las consultas para
   tener que rejuzgar; bastaba con que la categoría fuera frágil.
3. `consultas_v2.jsonl` sigue **sin usarse** para las etiquetas. Su papel queda
   como redacción de referencia para las consultas nuevas del paso 2.

---

## 7. Controles ejecutados

```bash
123_impacto_criterio_ambito.py    # coste 0: clasifica las razones -> 84/225 territoriales
124_rejuzgar_nivel1.py            # rejuicio de las 225 -> 146 suben, 31 siguen, 48 bajan
125_recuperar_nivel1.py           # recupera 8 fichas de un lote fallido -> 225/225
126_aplicar_criterio_ambito.py    # aplica al GT + copia de seguridad + trazabilidad
127_control_criterio_ambito.py    # ida y vuelta: separa criterio (45%) de fragilidad (50%)
112_evaluar_fase_b.py             # metricas -> 0,6408
```

**Coste:** ~30 llamadas LLM para el rejuicio + 6 para el control. < 1 €.

---

## 8. Estado del plan

| fase | estado |
|---|---|
| A (etiquetas por `dataset_id`) | ✅ |
| B (pool TREC + juicio) | ✅ 1.424 etiquetas |
| Bug de `top_k` | ✅ corregido, 0/47 |
| C · paso 1 (ámbito) | ✅ **ejecutado**, criterio corregido y aplicado |
| C · paso 2 (ampliar a ~215 consultas) | **siguiente** |
| D (recalcular 94.461 embeddings) | pendiente, ~9 min |
| E (BGE-M3) | pendiente; la copia de vectores ya está hecha |

El paso 2 no se ve afectado: las consultas nuevas nacen **con el criterio ya
corregido**, y el ámbito no se fuerza en el texto.
