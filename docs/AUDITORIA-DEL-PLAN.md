# Auditoría del plan: errores encontrados

**Fecha:** 24-sep-2026
**Método:** revisión adversarial — se buscaron errores, no confirmaciones
**Resultado:** el plan **acierta en la dirección y falla en cuatro números y una
afirmación**. Todos corregidos en `PLAN-GROUND-TRUTH.md`.

---

## Resumen de hallazgos

| # | lo que decía el plan | realidad medida | gravedad |
|---|---|---|---|
| 1 | «el criterio de patrón ordena al revés: premia a un motor que ordena mal» | **no demostrado**: mi propio test estaba mal diseñado. El criterio tiene precisión 0,697 y F1 0,796 — es defectuoso, no invertido | **alta** — afirmación sin base |
| 2 | «el suelo honesto es P@5 ≈ 0,38 (o 0,44)» | es un **intervalo [0,366 · 0,787]**. Dar un número suelto es incorrecto | **alta** — número mal presentado |
| 3 | «se recuperan los 470 juicios por título (92 %)» | solo 89 %, y **de forma ambigua**: 2.144 grupos de títulos duplicados | **media** — vía equivocada |
| 4 | «hacen falta ~137 consultas para detectar +0,05» | **213** (IC95 %) o **434** (potencia 80 %). Usé la varianza del P@5 de patrón, no del nDCG | **media** — cálculo mal hecho |
| 5 | Fase C: «150-200 consultas» | con 150 la mejora detectable es 0,06; con 200, 0,05. Al límite | **baja** — ajustar |

---

## 1. El error más grave: la afirmación «ordena al revés»

### Lo que dije

> *«El motor INVERTIDO —que pone delante lo que el juicio dice que NO es
> relevante— puntúa 0,5064, muy por encima del ALEATORIO (0,0894). Es decir: el
> criterio de patrón premia a un motor que ordena mal.»*

### Por qué está mal

Viene del test `102_discriminacion_gt.py`, y **ese test tiene un defecto de
diseño**: el universo sobre el que ordenaban los motores mezclaba **30 documentos
reales** (que casan los patrones) con **200 documentos aleatorios del catálogo**
(que casi nunca los casan). En ese montaje, cualquier orden que coloque los
documentos reales delante —incluido el INVERTIDO— supera al aleatorio puro. El
resultado era un **artefacto del diseño**, no una propiedad del criterio.

### Cómo se mide bien: matriz de confusión

Sobre los **470 juicios reales**, comparando el criterio de patrón con el juicio
del LLM, que es la verdad de referencia:

**Criterio actual (cualquier patrón, subcadena)**

| | LLM relevante | LLM no relevante |
|---|---|---|
| **patrón dice sí** | 221 | **96** |
| **patrón dice no** | 17 | 136 |

- precisión **0,697** · recall **0,929** · F1 **0,796** · exactitud 0,760
- de 238 relevantes detecta **221 (93 %)** — buena sensibilidad
- de 232 **no relevantes marca 96 (41 %)** — **aquí está el problema**

**Criterio estricto (exigir 2+ patrones)**

| | LLM relevante | LLM no relevante |
|---|---|---|
| **patrón dice sí** | 150 | 16 |
| **patrón dice no** | 88 | 216 |

- precisión **0,904** · recall **0,630** · F1 0,743

### Conclusión corregida

El criterio de patrón **no está invertido: está inflado**. Marca como relevante el
41 % de lo que el juicio rechaza. Eso basta para invalidar la métrica, pero por
una razón distinta a la que dije: **no distingue bien, y no distingue grados**.

Y aparece un dato nuevo que afecta a la Decisión 1 del Paso 0: **endurecer los
patrones no es gratis.** Exigir 2+ coincidencias sube la precisión de 0,697 a
0,904 pero **hunde el recall de 0,929 a 0,630**: dejaría de detectar 88 de los 238
relevantes. La opción «binario endurecido» tiene un coste medible que no había
cuantificado.

---

## 2. El «suelo honesto» no es un número: es un intervalo

### Lo que dije

> *«el suelo honesto: P@5 ≈ 0,44 en lugar del 0,60 regalado»* (y en la auditoría,
> «0,3830»).

### Por qué está mal

En el top-5 de las 47 consultas hay **235 fichas**: **86 relevantes**, **99 sin
juicio**. Los sin juicio los conté como no relevantes — lo cual **no es el valor,
es una cota**.

| cota | supuesto | P@5 |
|---|---|---|
| **inferior** | los 99 sin juicio son NO relevantes | **0,3660** |
| **superior** | los 99 sin juicio son relevantes | **0,7872** |

**El valor real está entre 0,366 y 0,787.** Ese intervalo de 0,42 de anchura es
la medida exacta del daño que hace el pool incompleto: con 99 de 235 fichas sin
juzgar, el GT no puede dar un número, solo un rango.

**Corrección:** el plan no debe prometer un «nuevo suelo». Debe decir que **hoy no
hay un número**, y que la Fase B es lo que lo produce.

---

## 3. La recuperación de juicios no puede ser por título

### Lo que dije

> *«431 cruzables por título con resultados_reales (92 %)»*

### Por qué está mal

El catálogo tiene **2.144 grupos de títulos duplicados**. Un título puede apuntar
a varias fichas distintas, así que resolver por título es **ambiguo**: se puede
asignar el juicio a la ficha equivocada, y ese error es silencioso.

Medido: **418 de 470 juicios (89 %) resolubles por título**, no 431/92 %.

**Corrección:** usar la vía fiable, que ya existe — **`resultados_reales` trae el
`dataset_id` directamente**. El cruce por título solo como respaldo, y marcando
los casos ambiguos en vez de asignarlos a ciegas.

---

## 4. El cálculo de consultas necesarias estaba hecho sobre la métrica equivocada

### Lo que dije

> *«hacen falta ~137 consultas (hay 47)»*

### Por qué está mal

Usé la desviación del **P@5 de patrón** (0,2848), que es la métrica que
precisamente vamos a abandonar. Sobre la métrica que se va a usar, **nDCG@10 con
el juicio**, la desviación es mayor (0,3717) y el número sube.

| métrica | media | desv | IC95 % | +0,02 (IC95 %) | **+0,05 (IC95 %)** | +0,05 (potencia 80 %) |
|---|---|---|---|---|---|---|
| nDCG@10 (juicio) | **0,4820** | 0,3717 | ±0,1063 | 1.327 | **213** | **434** |
| P@5 (patrón) | 0,6383 | 0,2848 | ±0,0814 | 779 | 125 | 255 |

**Corrección: 213 consultas** (para detectar +0,05 con IC95 %) o **434** si se
exige potencia estadística del 80 %. No 137.

Y de paso queda fijado el valor honesto de partida: **nDCG@10 = 0,4820** sobre los
juicios, con IC95 % [0,376 · 0,588].

---

## 5. Ajuste menor: el tamaño de la Fase C

Con la varianza correcta, «150-200 consultas» queda al límite:

| n | mejora detectable (IC95 %) |
|---|---|
| 47 (hoy) | 0,106 |
| 150 | 0,060 |
| **213** | **0,050** |
| 300 | 0,042 |

**Corrección:** la Fase C debe apuntar a **~215 consultas**, no 150. Con 150 solo
se detectan mejoras ≥0,06.

---

## 6. Lo que la revisión CONFIRMA

Para no caer en el error contrario —destruir el plan entero por sus fallos—,
estos puntos se verificaron y **se sostienen**:

| afirmación del plan | verificación |
|---|---|
| el pool está incompleto | **confirmado**: 99 de 235 fichas del top-5 sin juicio |
| el juicio recuperable es material válido | **confirmado**: 470 juicios, 89 % resolubles |
| la estructura del GT es sólida | **confirmado**: calibra (0,727/0,600/0,467), sin consultas duplicadas |
| la métrica debe cambiar | **confirmado**, por otra razón (41 % de falsos positivos, no inversión) |
| no hay que tirar el GT | **confirmado** |
| subir `max_seq_length` no ayuda | **confirmado** (P@5 0,0128 → 0,0043) |
| BGE-M3 es la mejor opción sin restricción de licencia | **confirmado** (MIT, 61,5 en español) |
| no mezclar vectores al migrar | **confirmado** (error silencioso, devuelve basura) |
| el orden de fases (métrica → pool → consultas → base → migrar → comparar) | **confirmado**: las dependencias son reales |

---

## 7. Veredicto

**El plan es sólido en su estructura y tenía cuatro errores en sus números y una
afirmación sin base.**

- La **dirección** es correcta: arreglar la métrica antes de medir nada, porque la
  métrica actual marca como relevante el 41 % de lo que el juicio rechaza.
- El **orden de las fases** se sostiene: las dependencias son reales, no
  inventadas.
- Las **puertas de decisión** son útiles y ahora tienen umbrales bien calculados.

Lo que estaba mal y ya está corregido:

1. Retirar «ordena al revés» y sustituirlo por la matriz de confusión.
2. Retirar el «nuevo suelo ≈0,44»: no hay número, hay un intervalo **[0,366 · 0,787]**.
3. Recuperar juicios por `dataset_id`, no por título (2.144 títulos duplicados).
4. **213 / 434** consultas para +0,05, no 137.
5. Fase C: objetivo **~215 consultas**, no 150.

**Un apunte sobre el método.** Los errores 1 y 4 tienen la misma raíz: **calculé
propiedades de la métrica nueva usando datos de la métrica vieja.** El test de
discriminación usó un universo mixto y el cálculo de potencia usó la varianza del
P@5 de patrón. Es exactamente el error que el propio plan pretende evitar; conviene
tenerlo presente.

---

## Nota para la puerta G1

El plan proponía en G1 «¿se acepta el nuevo suelo (≈0,44) como cifra oficial?».

**Debe formularse así:**

> ¿Se acepta publicar la línea base como **nDCG@10 = 0,48 con IC95 % [0,38 · 0,59]
> y un pool con 42 % sin juzgar**, declarando el intervalo en lugar de un número?

Porque presentar 0,44 como cifra oficial sería **repetir el error anterior**: dar
un número con más precisión de la que los datos permiten.
