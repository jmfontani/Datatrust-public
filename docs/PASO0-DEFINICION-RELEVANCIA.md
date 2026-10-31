# Paso 0 · Definición de relevancia

**Fecha:** 24-sep-2026
**Estado:** validado con juicios reales · **pendiente de tu decisión**
**Decide:** qué significa «relevante» antes de reconstruir el ground truth

---

## 1. Punto de partida

El GT actual etiqueta **binario**: `relevante` / `no_relevante`. Y el evaluador
no usa esas etiquetas, sino patrones de texto en el título.

Al revisar los **470 juicios** del LLM que ya están dentro del fichero:

| observación | medida |
|---|---|
| juicios totales | 470 |
| distribución | 238 relevante / 232 no relevante |
| longitud media de la razón | 75 caracteres |
| con indicio de nivel intermedio | **1 de 470** |

Es decir: el juicio existente es **binario de verdad**, no un binario que oculta
una escala. El nivel intermedio no está en los datos: hay que crear el criterio.

---

## 2. La escala propuesta y su validación

### 2.1 Definición

| nivel | significado | ganancia nDCG |
|---|---|---|
| **2** | **RESPONDE.** El fenómeno y el ámbito coinciden | 2 |
| **1** | **TEMA CORRECTO, OTRO ALCANCE.** Mismo fenómeno, distinto ámbito geográfico o desglose | 1 |
| **0** | **NO RESPONDE.** Otro fenómeno, o solo comparte una palabra | 0 |

### 2.2 Validación empírica (hecha, no supuesta)

Prueba: 40 pares reales (consulta, ficha) del top-30 de hoy, juzgados **dos veces**
con `deepseek-v4.1-flash`, temperatura 0.

| prueba | resultado |
|---|---|
| pares sin error de parseo | **40/40** |
| **acuerdo en el nivel exacto** | **36/40 (90 %)** |
| acuerdo con tolerancia ±1 | **40/40 (100 %)** |
| nivel 1 usado en pasada 1 / 2 | 8 / 10 (20-25 %) |
| distribución | {0: 19, 1: 8, 2: 13} vs {0: 20, 1: 10, 2: 10} |

**La escala es utilizable.** El nivel intermedio no es una casilla de refugio: se
usa en 1 de cada 4-5 casos, de forma estable.

### 2.3 El nivel 1 captura casos reales

Ejemplos literalmente producidos por el juez:

| consulta | ficha | nivel | razón |
|---|---|---|---|
| paro registrado por comunidades | «Paro registrado… por nacionalidad. Municipios» | **1** | «trata del paro registrado, pero desglosado por municipios, no por comunidades» |
| pirámide poblacional Andalucía | «Pirámide de población (tramos cada 5 años)» | **1** | «es pirámide poblacional… pero de un municipio, no de Andalucía» |
| bibliotecas públicas | «Directorio de bibliotecas de Castilla-La Mancha» | **1** | «mismo fenómeno, pero ámbito autonómico, no red municipal» |
| calidad del aire ciudades | «FGC · Calidad del aire por paradas» | **1** | «misma contaminación atmosférica, pero por paradas, no por ciudades» |

**Estos son exactamente los casos que en binario son una moneda al aire.** El
nivel 1 los resuelve sin discusión.

### 2.4 Las discrepancias, examinadas

De los 4 desacuerdos, **todos** implican al nivel intermedio (1 vs 2, o 1 vs 0).
Ejemplo:

- «Tráfico de pasajeros en aeropuertos de Canarias», consulta `pasajeros aeropuerto`
  - pasada 1 → **2**: «fenómeno solicitado coincide»
  - pasada 2 → **1**: «mismo fenómeno, pero limitado a Canarias»

Es un caso genuinamente ambiguo: la consulta no fija ámbito. Que el desacuerdo se
concentre **solo** en la frontera es la señal esperada de una escala bien
construida; si aparecieran desacuerdos 0 vs 2, sería un problema de prompt.

**Recomendación derivada:** en las consultas del GT, **fijar el ámbito explícito**
en el texto de la consulta. «pasajeros aeropuerto» → «pasajeros en aeropuertos
españoles». Elimina la ambigüedad en la fuente.

---

## 3. Consecuencia sobre la métrica

Con el criterio honesto, el P@5 medido sobre el top-5 de hoy:

| criterio | P@5 |
|---|---|
| patrones actuales | **0,6043** |
| juicio del LLM (binario) | **0,3830** |

**El número baja un 37 %.** No es un empeoramiento del buscador: es que el
criterio anterior contaba como relevante fichas que el propio juicio razonado
rechaza (49 casos medidos).

**Hay que asumirlo y contarlo así.** Un P@5 de 0,38 con criterio defendible vale
más que un 0,60 con criterio que premia coincidencias de una palabra.

---

## 4. Cobertura actual: el arreglo es más barato de lo previsto

| dato | valor |
|---|---|
| fichas en el top-5 de hoy (47 × 5) | 235 |
| **ya juzgadas por el LLM en junio** | **145 (62 %)** |
| sin juzgar | **90** |

Y 8 consultas no tienen **ningún** resultado juzgado en su top-5 de hoy:
`empleo_001`, `demo_002`, `demo_003`, `econ_001`, `trans_004`, `cult_005`,
`san_003`, `amb_002`.

Esas 8 son las que hay que juzgar completas. El resto, completar huecos.

**Consecuencia:** con los juicios existentes + **90 pares nuevos** + el completo
de 8 consultas, el GT queda operativo. Son **~50 llamadas al LLM**, no miles.

---

## 5. El límite que hay que reconocer: potencia estadística

Este punto es independiente del criterio y hay que decidirlo también.

Con 47 consultas y P@5 ≈ 0,38:

| n | error estándar | intervalo de confianza 95 % |
|---|---|---|
| 47 | 0,071 | **[0,24 · 0,52]** |

Consultas necesarias para detectar una mejora (prueba pareada):

| mejora a detectar | consultas necesarias |
|---|---|
| 0,02 | ~1.177 |
| **0,05** | **~189** |
| 0,10 | ~48 |
| 0,15 | ~21 |

**Traducción directa:**

- Con **47** consultas solo se detectan mejoras **≥ 0,10**.
- Para detectar **+0,05** (lo que se espera de BGE-M3) hacen falta **~190 consultas**.
- El efecto del enriquecimiento (**−0,021**) es **indetectable** con este GT, con
  cualquier criterio. No fue un fallo de la medición: fue falta de resolución.

**Recomendación:** en paralelo al arreglo del criterio, **ampliar el conjunto a
~200 consultas** (las 47 actuales + ~150 nuevas por categoría). Sin eso, cualquier
comparación de modelos seguirá siendo ininterpretable.

---

## 6. Lo que hay que decidir

### Decisión 1 · Escala (recomendada: 3 niveles)

- **Opción A — 3 niveles** (validado: 90 % de acuerdo, nivel 1 usado en 20-25 %, captura los casos frontera). Permite nDCG gradado.
- **Opción B — binario endurecido**: mantener 0/1 pero con patrones arreglados (aplicar `re` de verdad y exigir 2+ coincidencias). Más barato, pero mantiene las monedas al aire.
- **Opción C — 4 niveles**, añadiendo «tema relacionado pero distinto fenómeno». **No recomendada:** con 4 niveles el acuerdo bajaría y no se ha medido.

### Decisión 2 · Métrica principal

- **Opción A — nDCG@10 gradado** como principal, con P@5 y MRR de apoyo. Aprovecha la escala. (MRR ya está implementado en el código y sin usar.)
- **Opción B — P@5 binario** (nivel 2 como relevante). Comparable con lo publicado.

**Recomendación: A, reportando ambos.** El nDCG distingue «acertar el orden» de
«acertar la presencia», que es justo lo que se quiere medir.

### Decisión 3 · Ámbito

¿Se fija el ámbito explícito en las consultas del GT? **Recomendado sí**: elimina
la ambigüedad en la fuente en vez de discutirla al juzgar.

### Decisión 4 · Tamaño del conjunto

**Recomendado ampliar a ~190-200 consultas.** Sin ello, el GT arreglado seguirá
sin poder detectar la mejora que se busca.

---

## 7. Recomendación conjunta

```
Decisión 1: 3 niveles                        (validado)
Decisión 2: nDCG@10 principal + P@5 y MRR    (aprovecha la escala)
Decisión 3: sí, fijar ámbito en la consulta  (quita ambigüedad)
Decisión 4: ampliar a ~200 consultas         (sin esto, no hay resolución)
```

Coste: ~90 pares nuevos + 8 consultas completas (~50 llamadas) + ~150 consultas
nuevas generadas. Con `deepseek-v4.1-flash` en off-peak, **por debajo de 5 €**.

Con esto, el GT pasa de un IC95 % de ±0,14 a uno de aproximadamente **±0,07**, y
se vuelve capaz de detectar la mejora que se busca.

---

## Anexo · evidencia

| script | qué mide | resultado |
|---|---|---|
| `97_cobertura_gt.py` | cobertura de juicios sobre el top-5 de hoy | 145/235 (62 %) |
| `98_escala_juicio.py` | acuerdo de la escala de 3 niveles | 36/40 exacto · 40/40 ±1 |
| `99_extrae_pares.py` | pares reales para el juicio | 20 consultas, 3 puestos cada una |
| `96_ventana_vs_calidad.py` | efecto de subir la ventana | no mejora (contexto) |

Modelo juez: `deepseek-v4.1-flash`, temperatura 0, dos pasadas independientes.
