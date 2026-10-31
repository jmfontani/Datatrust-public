# Fase B ejecutada · pool completo y acuerdo entre jueces

**Fecha:** 24-sep-2026
**Estado:** **ejecutada**. La cobertura está cerrada; la puerta G2 queda **parcialmente superada** (ver §5).
**Premisa:** G1 adoptada (criterio del juicio como criterio oficial).

---

## 1. Qué se ha hecho

| fichero | qué es |
|---|---|
| `108_construir_pool.py` | pool = unión del top-20 de 3 sistemas (uno **léxico puro**) |
| `entregables/pool_a_juzgar.json` | 1.358 fichas, 1.007 sin juzgar |
| `109_juzgar_pool.py` | juez en lotes de 10, temperatura 0, reanudable |
| `entregables/gt_etiquetas_v2.json` | **el GT ampliado: 1.413 etiquetas** |
| `110_acuerdo_v2.py` | acuerdo (corregido: ver §5.1) |
| `111_rejuzgar_muestra.py` | rejuzgado ciego para medir el acuerdo |
| `112_evaluar_fase_b.py` | medición de cierre |
| `113_sensibilidad_umbral.py` | ¿cuenta el nivel 1 como acierto? |
| `114_reproducibilidad_api.py` | ¿es determinista el motor? |
| `entregables/fase_b_comparacion.json` | la medición |

---

## 2. El pool: por qué la unión y no un solo motor

El pool de junio cubría solo el 28 % del top-30. Consecuencia medida: **240
documentos que otro motor encuentra nunca se juzgaron**, y por tanto contaban
como no relevantes.

| aportación | fichas | sin juzgar |
|---|---|---|
| solo el motor léxico | **338** | — |
| solo el semántico | 87 | — |
| solo el actual | 33 | — |

**338 fichas las trae únicamente el motor léxico.** Ese era el sesgo: un motor
distinto al de junio quedaba penalizado *por encontrar* documentos que el de
junio no encontraba. Se corrigió juzgando la unión.

La vía léxica **no usa embeddings**: es la garantía estructural de que el GT no
queda atado al encoder actual. Es lo que hace posible comparar mañana BGE-M3 con
el MiniLM de hoy.

---

## 3. El juicio

| dato | valor |
|---|---|
| fichas juzgadas | **1.007** |
| consultas | 47 de 47 |
| lotes fallidos | 2 (de ~140), recuperados |
| etiquetas totales | **1.413** (406 de junio + 1.007 nuevas) |
| fichas del pool sin juicio | **0** |

Distribución final:

| nivel | fichas | % |
|---|---|---|
| 0 · no responde | 794 | 56,2 % |
| **1 · mismo tema, otro alcance** | **225** | **15,9 %** |
| 2 · responde | 394 | 27,9 % |

El nivel intermedio aparece en **225 casos**. La escala de 3 niveles no es
decorativa: está cargando con una sexta parte del GT.

---

## 4. El resultado: la cobertura cambia las conclusiones

Con el pool completo (cobertura 98 %):

| sistema | nDCG@10 | IC95 % | P@5 | cobertura |
|---|---|---|---|---|
| **actual (0,7/0,3)** | **0,6083** | [0,528 · 0,688] | **0,4809** | **98 %** |
| semántico (1,0/0,0) | 0,5926 | [0,515 · 0,670] | 0,4511 | 98 % |
| léxico (0,0/1,0) | 0,4095 | [0,307 · 0,512] | 0,3362 | 74 % |

Comparación con la línea base (pool de junio):

| sistema | nDCG base | nDCG ahora | delta | cobertura |
|---|---|---|---|---|
| actual | 0,5324 | 0,6083 | **+0,0759** | 57 % → **98 %** |
| semántico | 0,5441 | 0,5926 | +0,0485 | 59 % → 98 % |
| léxico | 0,0954 | 0,4095 | **+0,3141** | 9 % → 74 % |

### 4.1 Tres lecturas

**1. La mezcla 0,7/0,3 y el semántico puro han invertido su orden.**
Con el pool incompleto parecía ganar el semántico puro (0,5441 vs 0,5324). Con el
pool completo gana la mezcla (0,6083 vs 0,5926). Era **sesgo de pooling**, justo
lo que la Fase B venía a corregir. La diferencia (0,016) sigue por debajo de la
mejora detectable (0,080), así que **tampoco ahora se puede afirmar cuál es
mejor** — pero ya no se afirma lo contrario.

**2. El motor léxico sube 0,315 y no ha mejorado nada.**
Su cobertura era del **9 %**: el 91 % de lo que encontraba contaba como no
relevante por no estar juzgado. El sesgo castigaba precisamente al motor más
distinto del que generó el GT.

**3. El intervalo se estrecha.** La mejora mínima detectable baja de 0,0996 a
**0,0799**: con más juicios, la misma diferencia se vuelve distinguible.

**4. 180 fichas nuevas marcadas «responde».** De las 1.007 etiquetas nuevas, 180
son nivel 2 y 225 nivel 1. Antes contaban como no relevantes y penalizaban al
motor que las encontraba.

### 4.2 Un bug del motor descubierto al cerrar la cobertura

La cobertura no llegaba al 100 % por una razón que resultó ser **un bug del motor
de producción**: el ranking **cambia según el `top_k`**. La misma consulta da
cuatro primeros resultados distintos con `top_k` 5, 10, 20 y 30.

Medido: el **primer** resultado cambia en **9/47 consultas (19 %)**, el **top-5**
en **21/47 (45 %)**. La causa está en `main_v2_final_v07.py`: los dos motores
recuperan `top_k * 3` y **normalizan por el máximo del conjunto recuperado**, así
que cambiar el corte cambia todos los scores.

**El GT no está afectado** (su unidad es `(consulta, dataset_id)`, no una
posición) — pero **arreglarlo es requisito para que las Fases D-F signifiquen
algo**. Detalle en `docs/BUG-RANKING-DEPENDE-DE-TOP_K.md`.

---

## 5. Control de calidad del juicio (puerta G2)

Tres comparaciones, que miden **cosas distintas** y no se pueden reducir a un
número:

| comparación | qué mide | resultado |
|---|---|---|
| mismo prompt, dos pasadas | reproducibilidad | **0,881** exacto · 1,000 con ±1 · kappa 0,793 |
| prompt con otra redacción | robustez | 0,729 exacto · **0,780** binarizado |
| junio vs nuevo (binarizado) | acuerdo entre jueces distintos | **0,847** · kappa 0,697 |

### 5.1 Corrección de un artefacto propio

El primer control dio **1,000** de «acuerdo interno» y **era falso**: el script
109 guarda un único juicio por ficha, sobrescribiendo la misma clave, así que
comparaba el dato **consigo mismo**. Detectado antes de usarlo como evidencia;
`110_acuerdo_v2.py` ahora se niega a reportar ese número y remite a `111`.

Además, `111` etiquetaba como «reproducibilidad» una comparación entre el juicio
de junio y el nuevo: **jueces distintos, escalas distintas**. Corregido.

### 5.2 Veredicto

- **Reproducibilidad 0,881 ≥ 0,80 → superada.** El juez es determinista:
  el nivel 1 aparece 19 veces en una pasada y 18 en la siguiente.
- **Acuerdo entre jueces 0,847 ≥ 0,80 → superada.** El juez de junio y el nuevo
  coinciden. El GT es consistente entre tandas.
- **Robustez 0,780 < 0,80 → NO superada, pero no invalida nada.** El nivel 1
  aparece 19 veces con un prompt y **26 con la redacción alternativa**; el prompt
  alternativo marca un 63 % de relevantes frente al 44 % del canónico. Es un
  juez **sistemáticamente más generoso**, no un juez ruidoso.

**Consecuencia práctica:** hay que **fijar un prompt canónico y no cambiarlo**.
Mezclar juicios de redacciones distintas rompería la comparabilidad. El prompt de
`109` queda como canónico.

### 5.3 El aviso que esto deja

El acuerdo «exacto» entre junio y el nuevo es 0,559, y **está topado por
construcción**: junio no tiene nivel 1, así que no puede coincidir en los 19
casos donde el nuevo sí lo usa. El número comparable es el binarizado (0,847).
Confundir ambos fue el error que la auditoría del plan ya había señalado en otro
sitio: **calcular propiedades de una escala con datos de otra.**

---

## 6. Dos controles independientes

### 6.1 ¿Es determinista el motor? **Sí**

Antes de creerse ninguna comparación:

| configuración | rankings distintos en 2 pasadas de 47 consultas |
|---|---|
| actual | **0/47** |
| léxico | **0/47** |
| semántico | **0/47** |

**0 diferencias en 141 pares.** Las mediciones son comparables.

### 6.2 El motor léxico devuelve vacío en 12 de 47 consultas

| configuración | consultas sin resultados | media de resultados |
|---|---|---|
| actual | 0/47 | 10,0 |
| semántico | 0/47 | 10,0 |
| **léxico** | **12/47** | **6,1** |

El motor léxico **no encuentra nada** en 12 de las 47 consultas (palabras como
«datos de empleo juvenil en España» no casan con `ts_rank_cd` sobre los títulos).
Sus cifras bajas (0,41) no son un artefacto de medición: son su comportamiento.

### 6.3 Un bug de medición corregido

`113` calculaba la media **excluyendo las consultas sin resultados**, lo que
inflaba al léxico (0,4107 → 0,5515 según se filtrara o no). Una consulta que
devuelve vacío es un **fallo del motor** y debe contar como 0. Corregido: ahora
el léxico reporta **0,4107 con 12 vacías declaradas**, y coinciden las dos
mediciones.

---

## 7. Decisión pendiente: ¿cuenta el nivel 1 como acierto?

El 16 % del GT está en el nivel 1. Que cuente o no cambia las cifras:

| sistema | política severa (solo «responde») | política amplia (nivel 1 cuenta) | efecto |
|---|---|---|---|
| actual | P@5 **0,4809** · MRR 0,6962 | P@5 0,5660 · MRR 0,7545 | +0,0851 |
| semántico | 0,4511 · 0,6792 | 0,5319 · 0,7381 | +0,0808 |
| léxico | 0,3362 · 0,4457 | 0,5319 · 0,6294 | +0,1957 |

**El efecto está entre +0,08 y +0,20 en P@5, y es 0 en nDCG** (el nDCG es gradado:
usa el nivel, no un umbral).

**Consecuencia:** las comparaciones *entre* sistemas no dependen de la elección
(el orden se mantiene). Las cifras *absolutas* sí, así que hay que declararla.

**Recomendación:** publicar la política **severa** como principal (responde a
«¿me da la respuesta?») y la **amplia** como secundaria (mide si acierta el tema
aunque falle el ámbito).

---

## 8. Estado y siguiente paso

**Fase B: completada**, con estos flecos:

- **Los 2 lotes fallidos están recuperados**: el pool queda 100 % juzgado
  (verificado: 0 fichas del pool sin etiqueta).
- **Residuo: 10 fichas del top-10 evaluado (2,1 %) sin juicio**, ambas de
  `medio_004`. No es un fallo del juicio: es consecuencia directa del bug de
  `top_k` (§4.2) — el pool se construyó con top-20 sobre un ranking que cambió.
- **La puerta G2 se cierra con matiz**: reproducibilidad y acuerdo superados;
  robustez al prompt no, con la consecuencia de fijar el prompt canónico.
- **Decisión de umbral** pendiente (§7).

**Siguiente fase prevista:** Fase C (ampliar consultas). Con 47 consultas la
mejora detectable es 0,0801; para detectar +0,05 hacen falta **~213 consultas**.
Es la fase más costosa en criterio, porque obliga a fijar el ámbito en el texto
de las consultas.
