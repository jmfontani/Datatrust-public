# Fase C, paso 1 · Fijar el ámbito: hallazgo y reversión

**Fecha:** 25-sep-2026
**Qué se hizo:** reescribir las 47 consultas para que el ámbito quedara explícito
(38 reescritas, 6 ya lo tenían, 3 intocables por ser ambiguas a propósito).
**Resultado:** **la premisa del paso 1 es incorrecta para este catálogo.**
El paso se mantiene como *mejora de redacción*, pero **la justificación hay que
reescribirla** y **no se puede usar para reutilizar las etiquetas sin más**.

---

## 1. Lo que el plan daba por supuesto

`PLAN-GROUND-TRUTH.md`, Fase C, paso 1:

> **Fijar el ámbito en el texto de la consulta** (`pasajeros aeropuerto` →
> `pasajeros en aeropuertos españoles`). Elimina la ambigüedad en la fuente: fue
> el origen de **todas** las discrepancias medidas en la escala.

Y el paso 3:

> **Reutilizar el juicio de las 47 actuales**: no se repite el trabajo.

Ambas cosas se dieron por buenas **sin medirlas**. Las he medido, y la segunda es
falsa, y la primera está mal planteada.

---

## 2. Primero: el cambio de texto NO invalida las etiquetas masivamente

Control `121_efecto_ambito_en_etiquetas.py`, sobre 90 pares ya etiquetados
rejuzgados con el texto nuevo:

| métrica | valor |
|---|---|
| acuerdo (mismo nivel) | **0,678** |
| kappa de Cohen | 0,517 |
| cambian de nivel | 29/90 (32,2 %) |
| cambios peligrosos 0↔2 | 3/90 (3,3 %) |

Un 0,678 parece alarmante, pero **incluye el ruido del juez**. La
reproducibilidad medida del juez es 0,881, así que hay que separar.

---

## 3. El test que separa efecto de ruido

Control `122_test_ambito_controlado.py` — ida y vuelta sobre los 29 pares que
cambiaron: juicio histórico → con «España» → texto viejo otra vez.

| categoría | n |
|---|---|
| **cambio atribuible al texto** (reproduce y cambia) | **12/29** |
| inestable (no reproduce el nivel histórico) | 17/29 |

Y de los 12 cambios reales, **11 van de 2 a 1** (92 %), uno sube. Es decir: el
único efecto reproducible es **degradar de «responde» a «mismo tema, otro
ámbito»**, y va en una sola dirección.

Transiciones completas:

```
2 -> 1 -> 2    12   EFECTO TEXTO      <- el unico patron sistematico
2 -> 1 -> 1     7   inestabilidad
0 -> 1 -> 1     2   inestabilidad
2 -> 0 -> 0     2   inestabilidad
1 -> 0 -> 1     1   efecto texto
1 -> 2 -> 1     1   efecto texto
1 -> 2 -> 2     1   inestabilidad
0 -> 2 -> 1     1   inestabilidad
2 -> 1 -> 0     1   inestabilidad
0 -> 1 -> 2     1   inestabilidad
```

---

## 4. Por qué ocurre: el catálogo NO es de ámbito nacional

Tabla de territorios del catálogo real:

| territorio | fichas |
|---|---|
| *(vacío)* | 56.619 |
| **País Vasco** | **12.437** |
| **España** | **10.749** |
| Aragón | 2.253 |
| Comunidad Foral de Navarra | 1.869 |
| Cataluña | 1.550 |
| Málaga | 1.283 |
| Madrid | 1.179 |

**Solo el 11,4 % del catálogo tiene ámbito «España».** Y el mayor territorio
individual es **País Vasco, con más fichas que España**.

El territorio de las fichas degradadas lo confirma: Zaragoza, Álava, País Vasco,
y metadatos geográficos de la UE.

### 4.1 El error de fondo

`datos.gob.es` **no es un portal de estadística nacional**: es el catálogo de las
administraciones públicas españolas, y por tanto **mayoritariamente autonómico y
municipal**.

El usuario que pregunta por «empleo juvenil» **no rechaza** la versión de su
comunidad: probablemente la prefiere. Tratar «España» como el único ámbito
válido convierte en nivel 1 todo lo que venga de una comunidad — que es el
88,6 % del catálogo.

### 4.2 Y el motor no puede satisfacer esa exigencia

El buscador devuelve lo que es relevante, con independencia del ámbito declarado.
Con la consulta «empleo juvenil España», las fichas de País Vasco **siguen
apareciendo** en el top-10 (son relevantes), pero ahora cuentan como nivel 1.
Es decir: **la métrica empeoraría sin que el motor haya hecho nada peor.** Se
estaría midiendo el catálogo, no el recuperador.

---

## 5. Magnitud del daño si se reutilizan las etiquetas sin revisarlas

| | |
|---|---|
| pares afectados por el texto | 12/90 = **13,3 %** |
| extrapolado a las 1.424 etiquetas | **~190 etiquetas** |
| de ellas, degradadas (2→1) | **~163** |

163 etiquetas degradadas en un GT de 1.424 no es ruido: es el 11,4 % del GT, y
concentrado en un lado (castiga sistemáticamente al catálogo autonómico). Eso
movería el nDCG y, peor, **en una dirección que no tiene que ver con la calidad
del motor**.

---

## 6. Lo que se ha hecho con el artefacto

`entregables/consultas_v2.jsonl` contiene las 47 consultas con `query_original`
preservado. **Está bien construido** — el problema no es el fichero, es la
justificación. Se conserva, pero cambia de papel:

1. **No se usa** como base para reutilizar las 1.424 etiquetas.
2. Sirve como **mejora de redacción** en los casos donde el ámbito sí estaba
   ausente y no había ambigüedad entre territorios.
3. Las consultas de la categoría `ambigua` se dejaron intactas (correcto).

---

## 7. Propuesta: el ámbito debe entrar en el CRITERIO, no en el texto

En vez de forzar el ámbito en la consulta, declararlo como **criterio de
relevancia** que el juez aplica:

> La consulta pide un fenómeno. Un conjunto de datos **responde** (2) si mide ese
> fenómeno, con independencia del territorio, siempre que el territorio sea
> español. Marca 1 solo si el ámbito es **incompatible** con la intención (otro
> país, otro periodo, otro desglose).

Así:
- se elimina la ambigüedad sin cambiar el texto de la consulta (el juicio
  histórico **sí** se puede reutilizar);
- no se castiga al catálogo autonómico, que es la mayoría real;
- sigue distinguiendo lo que importa (un dataset de Francia es 1, no 0 ni 2).

Esto **invierte la dirección del paso 1** del plan: la ambigüedad se resuelve en
el criterio, no en el texto.

---

## 8. Estado de las fases

| fase | estado |
|---|---|
| A (etiquetas por `dataset_id`) | ✅ ejecutada |
| B (pool TREC + juicio) | ✅ ejecutada, 1.424 etiquetas, cobertura 100 % |
| Bug de `top_k` | ✅ corregido y verificado (0/47) |
| C · paso 1 (fijar ámbito) | ⚠️ **ejecutado, hallazgo: premisa incorrecta** |
| C · paso 2 (ampliar a ~215 consultas) | pendiente, **no afectado** por este hallazgo |
| C · paso 3 (reutilizar juicio) | **bloqueado** hasta decidir el criterio (§7) |
| D (recalcular 94.461) | pendiente, ~9 min |
| E (BGE-M3) | pendiente |

El paso 2 sigue siendo válido y es el que da la potencia estadística. Lo que
cambia es que las consultas nuevas deben nacer **con el ámbito en el criterio**,
no forzado en el texto.

---

## 9. Controles ejecutados

```bash
# reescribir las 47 consultas fijando ambito (38 reescritas, 0 fallos)
119_fijar_ambito.py

# auditar las reescrituras (37 solo anaden ambito, 1 perdida de termino: "fp")
120_auditar_reescrituras.py

# ¿el texto nuevo cambia el juicio?   -> 32 % cambia, 3,3 % peligroso
121_efecto_ambito_en_etiquetas.py --n 90

# ida y vuelta: separar efecto de ruido -> 12 efecto, 17 inestabilidad
122_test_ambito_controlado.py
```

**Coste:** ~200 juicios LLM en total, < 0,20 €.

---

## 10. Regla que se lleva este episodio

El plan decía «fijar el ámbito elimina la ambigüedad» y «reutilizar el juicio».
Las dos afirmaciones eran **razonables y ninguna estaba medida**. Al medirlas,
una resultó falsa y la otra contraproducente.

Es la tercera vez en este trabajo que una propiedad dada por buena en el plan no
sobrevive a la medición (antes: el sesgo del pool, la cobertura del juicio). El
patrón es constante: **el plan acierta en la dirección y falla en las cifras**.
Auditar los pasos del plan antes de ejecutarlos es lo que lo detecta.
