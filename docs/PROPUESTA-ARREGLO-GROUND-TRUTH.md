# Cómo arreglar el ground truth

**Fecha:** 24-sep-2026
**Estado:** propuesta, sin ejecutar
**Pregunta:** ¿cómo arreglar el GT?

---

## 1. El diagnóstico en una frase

El fichero `ground_truth_48.jsonl` **no es un ground truth de recuperación**.
Es el residuo de tres generaciones distintas de generación automática, y el
evaluador actual usa **la peor de las tres partes** en lugar de la mejor.

Y la mejor parte ya está dentro del fichero, sin usar.

---

## 2. Los cinco defectos, con números medidos

### 2.1 El criterio de relevancia es `any` con patrones de una palabra

Cada consulta trae `patrones_palabras_clave` como lista de frases cortas, y el
evaluador marca relevante si **cualquiera** de ellas aparece en el título.

Medido sobre el catálogo (94.461 fichas), cuántos títulos casa el patrón **más
amplio** de cada consulta:

| consulta | patrón más amplio | títulos que casa |
|---|---|---|
| `demo_001` | `población` | **17.162** (18 % del catálogo) |
| `trans_003` | `intervalo` | 12.211 |
| `econ_002` | `media` | 9.621 |
| `empleo_004` | `sexo` | 7.844 |
| `cult_001` | `registro` | 4.585 |
| `cult_005` | `España` | 2.476 |

**Mediana: 703 títulos.** Y con `any`, basta el más amplio.

Además, `intervalo` y `media` son **artefactos ya documentados** del generador
del GT: palabras que el LLM metió como «patrón» y que no describen ninguna
temática.

### 2.2 La relevancia se decide solo por el título

```python
titulo = resultado.get("title", "").lower()
return any(patron in titulo for patron in patrones_validos)
```

No se lee la descripción, ni el contenido, ni el tema, ni el territorio.

**Es exactamente el campo que las fichas degeneradas repiten.** El experimento de
enriquecimiento mejora la *descripción* — un campo que el evaluador **no mira**.
Eso explica por qué el P@5 no se movía.

### 2.3 Los patrones son regex, pero se evalúan como texto literal

Todas las entradas tienen `datasets_esperados` con expresiones regulares:

```
"INE.*empleo.*joven"     "SEPE.*juvenil"     "juventud.*empleo"
```

Los **95 patrones** de las 47 consultas son regex (100 %). Pero el evaluador hace
`patron in titulo` — búsqueda de subcadena literal. La cadena
`"INE.*empleo.*joven"` **nunca** aparece en ningún título.

Consecuencia: **la evaluación real no mide nada de eso.** Y el
`criterios_evaluacion.no_debe_contener` (`humedales`, `geoparques`, `BIC`) existe
en el fichero y **no se aplica nunca**.

### 2.4 Hay juicios del LLM con razones, y no se usan para puntuar

Dentro de `ground_truth.resultados_clasificados` hay un juicio por resultado y
consulta, con su razón:

```json
{"title": "Humedales de importancia internacional en Canarias",
 "relevancia": "no_relevante",
 "razon": "Trata sobre humedales Ramsar, no sobre Patrimonio Mundial de la UNESCO."}
```

| dato | valor |
|---|---|
| juicios totales | **470** |
| cruzables por título con `resultados_reales` (que sí tiene `dataset_id`) | **431 (92 %)** |
| marcados `relevante` | **238 (51 %)** |

**Esto es material de ground truth de verdad**, con identificador recuperable, y
el evaluador lo ignora en favor de los patrones.

### 2.5 Los patrones sobreestiman; el LLM es más estricto

Comparando ambos criterios sobre el mismo resultado:

| caso | n |
|---|---|
| coinciden | 93 |
| **el patrón dice «relevante» y el LLM dice «no»** | **49** |

El patrón marca relevante y el juicio razonado dice que no. La métrica está
premiando lo que el propio GT considera incorrecto.

---

## 3. La propuesta

Cinco pasos, del más barato al más caro. **Ninguno exige reescribir el fichero
desde cero.**

### Paso 0 · Fijar la definición de relevancia (decisión, no código)

Antes de tocar nada hay que acordar **qué significa relevante**. Propuesta:
escala **gradada de 3 niveles** en lugar de binaria.

| nivel | significado | ejemplo (consulta «PIB por comunidades») |
|---|---|---|
| **2** | responde a la consulta | «Principales resultados del PIB. Comunidades autónomas» |
| **1** | tema correcto, ámbito o desglose distinto | «PIB per cápita por provincia» |
| **0** | mismo tema, otro fenómeno | «Hogares según umbral de pobreza por comunidad» |

Motivo: el P@5 binario obliga a decidir en casos límite que la propia escala
delata. Con ganancia gradada, `nDCG` discrimina mejor y desaparecen las
discusiones de frontera.

**Este paso requiere tu decisión.** Todo lo demás se apoya en él.

### Paso 1 · Recuperar las etiquetas que ya existen (coste 0)

Construir un fichero de etiquetas **por identificador**, no por patrón:

```
dataset_id | consulta | relevancia (0/1/2) | razon | juez
```

A partir de los `resultados_clasificados` cruzados con `resultados_reales`
(92 % de cobertura). **Sin llamadas al LLM.**

### Paso 2 · Completar el juicio con pooling (coste bajo, ~940 pares)

Las 470 etiquetas solo cubren el top-10 de una ejecución concreta de junio.
Faltan los documentos que **hoy** entran en el top-5 pero no estaban entonces.

Diseño tipo TREC:

1. Ejecutar cada consulta y tomar el **top-30**.
2. Juzgar **solo los pares no juzgados** (~940 de 1.410).
3. Juzgar con el prompt de `generar_ground_truth_real.py`, **en lotes de 20**
   resultados por llamada.
4. **Fondo multi-sistema**: juzgar la unión del top-20 de (a) motor actual,
   (b) búsqueda léxica pura, (c) motor con otro modelo. Así ningún sistema se
   auto-beneficia: si un motor encuentra algo relevante que otro no, ese
   documento también queda juzgado.

Coste estimado: **50-90 llamadas**, menos de 1 dólar con `deepseek-v4.1-flash`.

### Paso 3 · Cambiar el evaluador (esto es el arreglo real)

Tres cambios en `utils/ragas_metrics.py`:

| actual | propuesto |
|---|---|
| relevancia por patrón en el título | relevancia por `dataset_id` contra etiquetas |
| `any(patron in titulo)` | consulta al fichero de etiquetas; si no está juzgado, se marca aparte |
| P@5, P@10 binarios | P@5, nDCG@10 gradado y **MRR** (ya está implementado, sin usar) |

Y añadir dos controles que hoy no existen:

- **Cobertura**: qué porcentaje del pool evaluado está juzgado. Si es bajo, la
  métrica no es interpretable y hay que decirlo.
- **Fiabilidad**: doble juicio ciego sobre 100 pares, midiendo el acuerdo entre
  jueces. Si el acuerdo es bajo, el problema es el prompt de juicio, no el
  buscador.

### Paso 4 · Validar el propio GT (antes de creer cualquier métrica)

1. Doble juicio ciego sobre 100 pares → acuerdo esperado > 0,80. Si no, rehacer
   el prompt de juicio.
2. Comprobar el sesgo de pooling: ¿cuántos relevantes encuentra la búsqueda
   léxica que el motor semántico no encontraba? Si son muchos, el pool está
   sesgado hacia el motor actual.
3. Ampliar consultas (opcional pero recomendable): con 47 consultas, el error
   estándar de un P@5 de 0,60 es **±0,07**. Para detectar mejoras de 0,02 hacen
   falta del orden de **300 consultas**. Con 47, cualquier mejora pequeña queda
   dentro del ruido por construcción.

---

## 4. Qué NO hacer

- **No borrar el fichero actual.** Los patrones siguen sirviendo para una cosa:
  verificar el `no_debe_contener` (`humedales`, `geoparques`, `BIC`). Basta
  aplicar `re` de verdad en vez de `in`.
- **No juzgar de nuevo los 470 pares ya juzgados.** Son válidos: la etiqueta
  depende del documento, no del ranking.
- **No generar un GT nuevo desde cero con el LLM sin pooling.** Repetiría el
  defecto: solo juzgaría lo que el motor actual encuentra, y el motor se
  evaluaría contra su propia salida.

---

## 5. Orden recomendado y dependencias

```
Paso 0 (decisión)  ──►  Paso 1 (barato, 0 coste)  ──►  Paso 2 (pooling ~940 pares)
                                                              │
                                                              ▼
                                        Paso 3 (evaluador)  ──►  Paso 4 (validación)
```

Sin el **Paso 3**, cualquier medición posterior —incluido el cambio de modelo a
BGE-M3— seguirá siendo ininterpretable. Por eso el Paso 3 es el que desbloquea
todo lo demás.

**Dato que abarata el conjunto:** 470 de los ~1.410 pares ya están juzgados y son
reutilizables. El trabajo restante son decenas de llamadas, no miles.
