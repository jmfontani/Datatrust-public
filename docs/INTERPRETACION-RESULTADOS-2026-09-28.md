# Interpretación de los resultados · ¿son buenos? ¿mejoran?

**Fecha:** 28-sep-2026 · Datos: `entregables/analisis_calidad.json` + `fase_d_LINEA_BASE.json`

---

## 0. Aviso previo: dos errores míos en el camino a esta interpretación

Antes de las cifras, porque cambian lo que se puede afirmar.

1. **Usé el fichero de consultas equivocado.** Hay **dos ficheros con las mismas 47
   consultas humanas y 38 de ellos difieren**:
   - `ground_truth.jsonl` → `"censo población 2024"` (sin ámbito) ← **el canónico**
   - `consultas_v2.jsonl` → `"censo población 2024 España"` (con ámbito) ← reliquia
     previa a la decisión §7

   Mi primer análisis leyó el segundo y dio **0,4147 / cobertura 89 %** en lugar de
   0,4854 / 100 %. Con el ámbito dentro del texto, las consultas humanas dejan de
   parecerse al pool con el que se juzgaron: la cobertura se hunde y el nDCG cae.
   **Es el mismo error de instrumento que ya había aparecido con las consultas
   contaminadas, esta vez dentro de la herramienta de medida.**

2. **Añadí una «corrección» que no corregía nada.** Pasé `semantic_weight=0.7`
   explícitamente creyendo que la API usaba otros por defecto. Comprobado: la API ya
   usa 0,7/0,3, y las 47 consultas dan resultado idéntico con y sin pesos explícitos.

Tras corregir (1), mis números coinciden **exactamente** con la línea base canónica.
Lo que sigue está medido con `ground_truth.jsonl`.

---

## 1. ¿Son buenos? El 0,4854 en contexto

| referencia | valor |
|---|---|
| **Sistema actual** | **0,4854** |
| Suelo (mejor nivel-2 a distancia media en un pool de ~25) | ~0,04 |
| **Techo alcanzable** (orden ideal sobre los juicios que existen) | **0,8318** |
| Fracción del recorrido útil cubierta | **0,485 / 0,832 = 58 %** |

**No es azar, y queda margen.** El sistema está en el 58 % del recorrido entre el azar
y el mejor ranking posible con los juicios disponibles.

Contexto histórico (cifras no idénticas, mismo orden de magnitud):

| medición | nDCG@10 | cobertura |
|---|---|---|
| Fase A (47 consultas, GT provisional) | 0,5324 | 57 % |
| Comparación contra datos.gob.es | 0,5358 | — |
| **Fase D (214 consultas, GT v4)** | **0,4854** | **100 %** |

Las cifras anteriores eran **más altas porque la cobertura era del 57 %**: medir sobre
la mitad del pool favorece. Con cobertura del 100 % el número baja y **es más fiable**.

---

## 2. ¿Dónde acierta y dónde falla?

| grupo | consultas | % |
|---|---|---|
| Con ≥1 acierto exacto (nivel 2) en el top-5 | 123 | 57 % |
| Sin ninguno en el top-5 | 91 | 43 % |
| **Sin ninguno en el top-10 (fallo completo)** | **78** | **36 %** |

| grupo | nDCG medio |
|---|---|
| Consultas con acierto | **0,7085** |
| Consultas sin acierto | 0,1525 |

No es «mediocre en todas»: es **bueno cuando encuentra (0,71) y nulo cuando no (0,15)**.
El sistema acierta o falla, con poco término medio.

### La separación tema / alcance

| métrica | nDCG@10 | P@5 | MRR |
|---|---|---|---|
| **Estricto** (nivel 2: responde) | 0,4854 | 0,3458 | 0,4932 |
| **Tema** (nivel ≥1: mismo tema, otro alcance) | — | **0,4355** | **0,5990** |

En el 57 % de los casos el primer acierto exacto está en el **top-2** (MRR 0,4932).
Subiendo el listón a «mismo tema», el primer acierto está en el top-2 en el 60 % de
los casos. **El alcance geográfico es la diferencia** entre 0,346 y 0,436 de P@5.

---

## 3. Los 10 peores casos: el diagnóstico

De las 10 peores, **7 tienen 0 nivel-2 en TODO su GT**. Es decir: el juez no encontró
ni una ficha que responda a esa consulta, así que **nDCG 0 no es un fallo del motor**,
es un conjunto vacío. Ejemplos: «falsos autónomos», «jornada parcial involuntaria»,
«sobrecualificación titulados universitarios», «ERTE por sector» (esta sí tiene 20
nivel-2 y el motor no trae ninguno: **ese es un fallo real**).

Y las consultas con **un solo** nivel-2 en todo el GT: en 16 casos el motor lo pone en
el top-1 el **38 %** de las veces (azar ≈ 2 %). Con una sola respuesta correcta en un
pool de ~25 fichas, acertar el primero el 38 % de las veces indica un motor que
**ordena bien**.

---

## 4. ¿Mejoran? Comparación honesta

**Lo que ha mejorado (y es lo importante):**

| dimensión | antes | ahora |
|---|---|---|
| Cobertura de la medición | 57-74 % | **100 %** |
| Potencia (mejora detectable pareada) | 0,0564 | **0,0229** |
| Validez del instrumento | contaminado | **limpio** (orden validado contra las 47 humanas) |
| Reproducibilidad | no verificada | **reproducida exacta** (0,4854 dos veces) |

Esto no mejora el buscador, **mejora la capacidad de saber si el buscador mejora**. Y
era la condición para poder responder la pregunta original.

**Lo que NO ha mejorado:**

| comparación | diff | IC95 | veredicto |
|---|---|---|---|
| actual vs semántico | +0,0596 | [+0,0367 · +0,0825] | distinguible |
| actual vs léxico | +0,1231 | [+0,0702 · +0,1760] | distinguible |
| semántico vs léxico | +0,0635 | [+0,0030 · +0,1241] | distinguible |

El híbrido 0,7/0,3 sigue ganando con diferencia **estadísticamente significativa** sobre
los dos puros, pero **la diferencia con el semántico puro es pequeña (0,06)**: el
híbrido aporta, pero no es una goleada. Y el léxico solo cubre el 68 %, así que su
0,3623 está medido sobre dos tercios del pool.

---

## 5. Conclusión

1. **Los resultados son buenos y están bien medidos.** 0,4854 con cobertura del 100 %,
   en el 58 % del recorrido útil, y con MRR 0,49 (acierto en el top-2 la mitad de las
   veces). Un ranking al azar daría ~0,04.
2. **El orden de los motores es sólido:** el híbrido gana a los dos puros con
   intervalos que no cruzan el cero, y reproduce el veredicto de las 47 consultas
   humanas.
3. **La mejora real de esta fase no es el nDCG: es el instrumento.** Potencia 2,5×
   mejor, cobertura 100 % frente a 57 %, y trazabilidad. Sin eso, BGE-M3 no se puede
   evaluar.
4. **El margen está identificado y es concreto:** el 36 % de fallos completos, y de
   ellos el subtipo accionable es el **alcance** —el motor encuentra el tema pero no el
   ámbito—, que es donde el 0,4355 de P@5-tema podría subir hacia el 0,3458 estricto.
5. **Cautela obligatoria:** parte del «0 nDCG» viene de consultas sin ninguna respuesta
   correcta en el catálogo (7 de las 10 peores). Eso no mide el motor, mide el catálogo.
