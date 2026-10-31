# Decisiones adoptadas

Registro de las puertas de decisión del plan de ground truth. Cada entrada fija
un criterio para que no se reinterprete después.

---

## G1 · Criterio de medición y línea base

**Fecha:** 24-sep-2026
**Decisión:** **ADOPTADA** — se adopta el criterio del juicio como criterio oficial
de medición del TFM.

### Qué se adopta

| concepto | valor adoptado |
|---|---|
| **criterio de relevancia** | juicio del LLM indexado por `dataset_id`, no patrones de texto |
| **métrica principal** | **nDCG@10** con ganancia gradada |
| **métricas de apoyo** | P@5 y MRR |
| **línea base oficial** | **nDCG@10 = 0,5324 · IC95 % [0,4328 · 0,6320]** |
| **P@5 oficial** | **0,3574 · IC95 % [0,2636 · 0,4513]** |
| **MRR oficial** | **0,5591 · IC95 % [0,4340 · 0,6842]** |
| **cobertura del pool** | **57 %** — se declara como limitación |
| **mejora mínima detectable** | **0,0996** con n=47 |

### Qué se retira

El P@5 = **0,6043** calculado con patrones de texto sobre el título **deja de ser
la cifra oficial**. Motivo medido: ese criterio marca como relevante el **41 %**
de las fichas que el juicio rechaza (precisión 0,697 · 96 falsos positivos de 232
no relevantes).

### Cómo debe citarse

> Línea base del buscador: **nDCG@10 = 0,53 (IC95 % 0,43–0,63)** sobre 47 consultas,
> con el 43 % del pool del top-10 sin juicio humano.

**Siempre con el intervalo.** Nunca «0,53» a secas: el intervalo es parte del
resultado, no un adorno.

### Consecuencias asumidas

1. La cifra es más baja y menos vistosa que la anterior. **Se asume** porque la
   anterior tenía una precisión de 0,697.
2. Hay que declarar la limitación de cobertura en cada informe.
3. Exige explicar por qué baja, y la explicación está medida, no argumentada.

### Efecto sobre el plan

**Desbloquea la Fase B.** El pool incompleto (43 % del top-10 sin juicio) es la
causa del intervalo ancho, y cerrarlo es lo que da una cifra defendible con
precisión real.

---

## G2 · Calidad del juicio y prompt canónico

**Fecha:** 24-sep-2026
**Decisión:** **SUPERADA CON MATIZ** — el juicio es válido; se fija el prompt.

| comparación | mide | resultado | umbral 0,80 |
|---|---|---|---|
| mismo prompt, dos pasadas | reproducibilidad | **0,881** | superado |
| junio vs nuevo (binarizado) | acuerdo entre jueces | **0,847** | superado |
| prompt con otra redacción | robustez | 0,780 | **no superado** |

### Qué se decide

1. **El juicio es válido.** Un juez determinista (0,881) que coincide con el de
   junio (0,847) es material utilizable.
2. **Se fija el prompt de `109_juzgar_pool.py` como CANÓNICO.** El nivel 1
   aparece 19 veces con el prompt canónico y **26** con una redacción alternativa;
   la alternativa marca un 63 % de relevantes frente al 44 %. Es un juez
   sistemáticamente más generoso, no ruidoso.
3. **No se mezclan juicios de redacciones distintas.** Una tanda nueva debe usar
   el mismo prompt, o no es comparable.

### Cómo debe citarse

> 1.413 juicios sobre 47 consultas, con la escala 0/1/2 y el prompt canónico de
> `109_juzgar_pool.py`. Reproducibilidad 0,881, acuerdo con el juicio previo 0,847.

---

## G2b · Política de umbral para el nivel 1

**Fecha:** 24-sep-2026
**Decisión:** **ADOPTADA la doble publicación** (pendiente de confirmación del
interesado, recomendada).

| sistema | severa (solo «responde») | amplia (nivel 1 cuenta) | efecto |
|---|---|---|---|
| actual | P@5 0,4809 · MRR 0,6962 | P@5 0,5660 · MRR 0,7545 | +0,0851 |
| semántico | 0,4511 · 0,6792 | 0,5319 · 0,7381 | +0,0808 |
| léxico | 0,3362 · 0,4457 | 0,5319 · 0,6294 | +0,1957 |

**Efecto en nDCG: cero** (es gradado, usa el nivel, no un umbral).

**Se publica la severa como principal** (responde a «¿me da la respuesta?») y la
**amplia como secundaria** (mide si acierta el tema aunque falle el ámbito). La
elección se declara junto a cada cifra.

---

## Bug del motor: el ranking depende de `top_k`

**Fecha:** 24-sep-2026
**Estado:** **diagnosticado, NO arreglado** (cambia el motor de producción).

El ranking cambia según `top_k`: el primer resultado cambia en **9/47 consultas**
y el top-5 en **21/47**. Causa: los motores recuperan `top_k*3` y normalizan por
el máximo del conjunto recuperado.

**No afecta al GT** (su unidad es el par consulta-documento, no la posición), pero
**bloquea la validez de las Fases D-F**: sin ranking estable no se puede comparar
dos motores.

**Consecuencia:** el arreglo pasa a ser **requisito previo** de la Fase D.
Detalle en `docs/BUG-RANKING-DEPENDE-DE-TOP_K.md`.

---

---

## Bug de `top_k` · ARREGLADO Y VERIFICADO

**Fecha:** 25-sep-2026
**Decisión:** **corregido** por indicación del usuario («Corrige bug y continúa»).

| qué | antes | ahora |
|---|---|---|
| escala léxica | dividir por el máximo del conjunto | `rank/(rank+0.2)` |
| cuándo se aplicaba | solo si el máximo > 1,0 | siempre |
| recorte interno | `top_k * 3` | `max(150, top_k * 3)` |

**Test de aceptación: `ranking(k)[:5]` invariante a `k` → 21/47 fallos antes,
0/47 después.** El score ya no se mueve con `top_k`.

**Efecto:** híbrido 0,6083 → **0,6365** (+0,0282), semántico 0,5926 → 0,5834,
léxico 0,4095 → 0,4069. La brecha híbrido-vs-semántico se triplica (0,0157 →
0,0531), aunque sigue por debajo de la mejora detectable (0,0821).

**Cobertura cerrada:** 100 % (11 pares nuevos juzgados con el prompt canónico,
1.424 etiquetas totales).

**Vuelta atrás:** imagen `docker-api:pre-bugfix-2026-09-25` y copia del original
en `ssd/experimentos/enriquecimiento/backup/main_v2_final_v07.py.PRE-ARREGLO`
(sha256 `a2fa2a36…`). Documento: `docs/BUG-TOP_K-CORREGIDO.md`.

**Desbloquea la Fase D** (recalcular los 94.461 embeddings), que era el
requisito previo.

---

## Fase C, paso 1 · la premisa del plan era incorrecta

**Fecha:** 25-sep-2026
**Hallazgo:** el paso 1 del plan («fijar el ámbito en el texto de la consulta»)
se ejecutó y **el resultado lo desmiente**.

Medido con ida y vuelta sobre 90 pares etiquetados
(`121_efecto_ambito_en_etiquetas.py`, `122_test_ambito_controlado.py`):

| | |
|---|---|
| efecto atribuible al texto | **12/29 cambios** (11 de ellos 2→1, 92 %) |
| inestabilidad del juez | 17/29 |
| extrapolado al GT | **~190 etiquetas**, ~163 degradadas |

**Causa:** `datos.gob.es` es mayoritariamente autonómico y municipal. Solo el
**11,4 %** del catálogo tiene ámbito «España», y **País Vasco tiene más fichas
(12.437) que España (10.749)**. Exigir «España» convierte en nivel 1 el 88,6 %
del catálogo, y el motor no puede satisfacerlo porque devuelve lo relevante con
independencia del territorio declarado: **empeoraría la métrica sin que el motor
haya empeorado.**

**Decisión:** el ámbito entra en el **criterio de relevancia**, no en el texto de
la consulta. Así se elimina la ambigüedad sin invalidar las 1.424 etiquetas.
Documento: `docs/FASE-C-PASO1-HALLAZGO.md`.

**Estado:** `consultas_v2.jsonl` se conserva pero **no se usa** para reutilizar
etiquetas. El paso 2 (ampliar a ~215 consultas) **no se ve afectado**.

### ✅ EJECUTADO (25-sep-2026)

Criterio de ámbito corregido y **aplicado al GT**. Las 225 etiquetas de nivel 1
rejuzgadas (225/225, 0 fallos):

| destino | n |
|---|---|
| **suben a nivel 2** (eran ámbito autonómico/municipal) | **146** |
| siguen en 1 (desglose o periodo incompatible) | 31 |
| bajan a 0 (era otro fenómeno) | 48 |

**Distribución del GT:** `{0: 849, 1: 31, 2: 544}`.

**Control de ida y vuelta** (40 pares, `127_control_criterio_ambito.py`): el cambio
tiene **dos causas, ambas correcciones**:
- **45 %** efecto del criterio (el nivel 1 se reproduce y el criterio lo mueve),
- **50 %** el nivel 1 original **no se reproducía** (55 % de ese nivel era frágil,
  frente al 0,881 global) y el juicio nuevo sí es consistente,
- 5 % inestable.

**Efecto en la métrica: +0,0043** (0,6365 → **0,6408**). La corrección **vale por
validez, no por la cifra**: el criterio anterior describía mal qué es relevante, no
deformaba el ranking.

**Vuelta atrás:** `cp entregables/gt_etiquetas_v2_PRE-CRITERIO.json entregables/gt_etiquetas_v2.json`
(trazabilidad: las 225 llevan `nivel_previo: 1` y `origen`).
Documento: `docs/FASE-C-PASO1-EJECUTADO.md`.

---

## Fase C, paso 2 · 216 consultas

**Fecha:** 25-sep-2026 · **estado:** ✅ ejecutado

47 → **216 consultas** (12 categorías × 18, exacto). Mejora mínima detectable:
**0,106 → ~0,050**.

**Diseño:** cada llamada al LLM recibió **40 títulos reales** del tema, para que
cada consulta nazca con material que pueda responderla (una consulta sin respuesta
mide la ausencia de datos, no el recuperador). El **ámbito no se fuerza en el
texto** (0/169 lo incluyen) y la `descripcion` que ve el juez describe fenómeno y
faceta, nunca ámbito nacional.

**Validación:** las 169 nuevas contra el motor → **169/169 con resultados, 0 sin
respuesta**; 11 con similitud top-1 < 0,45 que **se conservan** (decide el juicio
del pool, no un umbral propio).

**Error de método corregido:** el primer validador filtraba por **solapamiento de
palabras clave** y marcó **45/169 como dudosas** — falsos positivos masivos
(«mujeres en puestos directivos» daba tema 0 % porque ninguna ficha contiene
literalmente «empleo»). Es el **mismo error de medir con patrones** ya corregido
dos veces aquí. Sustituido por una señal del motor.

Documento: `docs/FASE-C-PASO2-EJECUTADO.md`.

---

## Fase C, paso 3 · el juicio está hecho, la comparación no vale

**Fecha:** 25-sep-2026 · **estado:** ⚠️ juicio OK, comparación de motores INVALIDADA

5.298 pares juzgados (0 fallos, 242 min). GT v3 con 6.722 etiquetas, v2 intacto.
Control de comparabilidad superado (reproduce 0,6408/0,5801/0,4368 en las 47).

**Resultado aparente:** actual 0,5827 · léxico 0,5802 · semántico 0,4350 → el
léxico empata con el híbrido y el semántico se hunde.

**Es un artefacto que introdujo nuestra propia generación de consultas.** Las 169
nuevas se generaron mostrando 40 títulos reales al LLM, y el LLM copió su
vocabulario:

| sistema | 47 antiguas | 169 nuevas | delta |
|---|---|---|---|
| semántico | 0,5801 | 0,3947 | −0,1854 |
| léxico | 0,4368 | 0,6201 | +0,1834 |

Solapamiento con el título del top-1: léxico +0,208 en las nuevas. Longitud de
consulta idéntica (2,8 vs 2,9 palabras) → no es longitud, es vocabulario.

**Prueba decisiva** (169 nuevas partidas en tercios por solapamiento):
`semántico − léxico` = **−0,0016** con solapamiento bajo y **−0,3816** con
solapamiento alto. Un vuelco de 0,38 causado por el texto de la consulta.

**Decisión:**
- ❌ NO usar las 216 para comparar motores (ni la cifra 0,5827 como resultado).
- ✅ La línea base de las **47** sigue siendo la canónica.
- ✅ El GT v3 (6.722 etiquetas) es válido y reutilizable: el juicio depende del par
  (consulta, ficha), no de cómo se escribió la consulta.
- ✅ Control nuevo obligatorio: medir el solapamiento **antes** de juzgar.

**Hallazgo que sí vale:** los motores no se ordenan igual según el tipo de consulta
— léxico gana si la consulta copia el vocabulario (0,7331); si no lo copia, semántico
y léxico empatan (0,3517/0,3533) y **gana el híbrido** (0,4223). El híbrido es la
mejor opción de despliegue no por su media, sino porque **es el único que no pierde
en ningún régimen**.

**Corrección de mi propia predicción:** escribí que las nuevas no serían más
difíciles si tenían más nivel-2 disponibles; tienen **8,6 frente a 11,6**. Son algo
más difíciles — factor real, aunque no explica el vuelco (afecta a los tres motores
por igual).

Documento: `docs/FASE-C-PASO3-HALLAZGO-CONTAMINACION.md`.

---

## G5 · Adopción de BGE-M3 y pesos del híbrido

**Fecha:** 30-sep-2026
**Estado:** **G5 APROBADA y DESPLEGADA. Pesos: sin cambio (0,7/0,3).**

### Motor: BGE-M3 adoptado

Medido sobre **el buscador en servicio** (no un clon), 214 consultas, GT v5 e
instrumento canónico:

| métrica | MiniLM (antes) | BGE-M3 (después) |
|---|---|---|
| nDCG@10 | 0,4249 | **0,5575** |
| P@5 | 0,3458 | **0,4224** |
| P@10 | 0,2977 | **0,3879** |
| MRR | 0,4932 | **0,5895** |

Contraste pareado **+0,1326** IC95 [+0,0929 · +0,1741] — no cruza cero.
Mejora en 94 consultas, empeora 37, empata 83. Entregable:
`entregables/fase_h_VERIFICACION.json`.

**Control de instrumento:** las cifras de producción **reproducen exactamente** las
del clon experimental de la Fase G (P@5 0,4224 · P@10 0,3879 · nDCG 0,5575), y el
«antes» reproduce la Fase F al cuarto decimal. Dos implementaciones independientes
coincidiendo descarta que el despliegue introdujera desviación.

**Costes asumidos, declarados:**
- **Latencia ~2,5 s por consulta** (dominada por vectorizar en ollama). El índice
  HNSW no es el cuello de botella. Pendiente estudiado: caché de embeddings.
- **Cobertura de juicio 100 % → 92,6 %** (BGE recupera fichas sin juzgar), lo que
  **penaliza** la métrica: +0,1326 es un **límite inferior**.

**Reversibilidad:** imagen `docker-api:pre-bge-20260930`; o sin rebuild, arrancar
con `EXPERIMENTO_MOTOR=minilm` (el default sin variables es MiniLM). La columna
`embedding` (384) está intacta con su índice.

**Hallazgo que condicionó el despliegue:** `embedding_bge` **no tenía índice HNSW**,
y sin él cada consulta tardaba **1.850 ms** frente a **4,5 ms** con índice (**411×**).
Creado (717 MB). Sin él, BGE habría ganado en calidad y perdido en uso.

### Pesos del híbrido: se mantiene 0,7 / 0,3

Medido con BGE sobre las 214 consultas (`fase_h_PESOS.json`), convención
**(semántico/léxico)**:

| pesos | nDCG@10 | IC95 | vs actual |
|---|---|---|---|
| **0,7 / 0,3** (actual) | **0,5575** | [0,5113 · 0,6038] | — |
| 1,0 / 0,0 (solo semántico) | 0,5672 | [0,5206 · 0,6138] | +0,0097 · empate |
| 0,3 / 0,7 (invertido) | 0,5400 | [0,4942 · 0,5858] | −0,0175 · empate |

**Los tres repartos empatan** (los dos intervalos cruzan cero).

**Decisión: no cambiar.** El orden de las medias favorece a 1,0/0,0, pero el
intervalo cruza cero y no se cita un ranking como resultado. Además, con MiniLM el
canal léxico **sí** aportaba (+0,0537 significativo); con BGE ese aporte se
desvanece, y el léxico en solitario sigue siendo malo (nDCG 0,3269, cobertura
0,6822). Se conserva porque el híbrido es *el único que no pierde en ningún régimen*
(Fase C), hallazgo **pendiente de re-verificar con BGE**.

Documento: `docs/FASE-H-PESOS-HIBRIDO.md`.

**Nota de despliegue:** los pesos viven en **tres sitios con valores distintos** —
`main_v2_final_v07.py` (0,7/0,3, solo si el llamante no los envía),
`routes_v10.py` (0,75/0,25, endpoint `/llm/search/fast`) y `/app/public/app.py`
(0,75/0,25, **la UI pública, que los envía explícitos**). Cambiar el default de la
API **no altera lo que ve un usuario de la web**.

---

## Columna `embedding_text` — el catálogo ya es reproducible

**Fecha:** 30-sep-2026 (**antes: propuesta sin autorizar; ahora: EJECUTADA y verificada**)
**Estado:** **RESUELTA.** Columna creada y poblada; reproducibilidad comprobada.

La Fase D cerró con una deuda estructural: los vectores del catálogo **no eran
reproducibles desde la BD**, porque el texto que los generó (el `embedding_text` de
la limpieza) no se guardaba en ninguna columna. Reconstruirlo desde los campos
actuales daba **0,923 (5/80 exactos)**, así que recalcular **degradaría** los 87.661
vectores buenos.

**Hecho:**
1. Columna `embedding_text TEXT` creada en `datasets` (aditiva, sin tocar datos).
2. Poblada desde `datasets_clean.jsonl` (la limpieza), la única fuente con el texto
   exacto.
3. Verificado sobre vectores reales, muestra estratificada por longitud:

| muestra | coseno medio | mínimo | exactos |
|---|---|---|---|
| 60 fichas (cortas/medias/largas) | **1,000000** | **1,000000** | **60/60** |

**Reproduce a 1,0, incluidas las cortas** — el caso que el diagnóstico previo daba
por irresoluble.

**Cobertura:** 87.661 de 94.461 fichas (**92,8 %**). Las **6.800 posteriores (7,2 %)**
siguen sin texto: se generaron con un esquema desconocido y no son recuperables.

**Antes:** recalcular = degradar (0,923). **Ahora:** recalcular = reproducir (1,0).
El catálogo es auditable y la ingesta futura puede guardar el texto con el vector.

**✅ Cerrada también la ingesta futura (30-sep, noche):** `generate_embeddings_pg.py`
**escribe ahora la columna** en cada UPDATE del vector (mismo texto usado en la
generación — exacto si `--fuente-jsonl` lo tiene, el esquema canónico si no).
Verificado **end-to-end**: ficha de prueba insertada sin vector ni texto → script →
vector 384-dims + texto guardado → texto reproduce el vector (coseno 1,0) → ficha
eliminada, catálogo íntegro en 94.461. El invariante queda fijado: **la columna
siempre contiene el texto exacto que produjo el vector de esa fila**.

Documento: `docs/FASE-H-EMBEDDING-TEXT-Y-REGRESION.md`.
Entregable: `entregables/fase_h_EMBEDDING_TEXT_BD.json`.

---

## Prueba de regresión con el motor nuevo — PASA

**Fecha:** 30-sep-2026
**Estado:** **criterio de la Fase E cumplido y declarado** (antes: no cerrado).

Script nuevo `codigo/153_regresion_embeddings_bge.py`. Comprueba **cada motor con su
propio texto**, 120 fichas estratificadas:

| motor | coseno medio | mínimo | exactos | veredicto |
|---|---|---|---|---|
| MiniLM (`embedding`, 384) | 0,999819 | 0,990635 | 110/113 | **PASA** |
| BGE-M3 (`embedding_bge`, 1024) | 1,000000 | 0,9999995 | 120/120 | **PASA** |

El script anterior (`88_regresion_embeddings.py`, fuera del repo) **no servía de
criterio**: cubría solo MiniLM y vectorizaba un texto reconstruido que la Fase D
demostró que no generó los vectores (daba «REVISAR» por construcción).

### Hallazgo que hay que declarar al presentar la comparación de motores

`142_poblar_bge_gpu.py` **no vectorizó `embedding_text`**, sino un texto reconstruido
con su propio esquema, y difiere del de MiniLM en **~16 palabras por ficha**.

**Los dos motores se generaron con textos distintos.** Por tanto el efecto medido en
las Fases E/F (**+0,2743** semántico, **+0,1372** híbrido) es la suma de **dos
cambios a la vez**: el modelo **y** el texto. No invalida la decisión —ambos
favorecen a BGE y el despliegue ya está hecho— pero **la cifra no es atribuible solo
al modelo**. Debe decirse así en la memoria.

Entregable: `entregables/fase_h_REGRESION_AMBOS_MOTORES.json`.

---

## Bug de determinismo del motor

**Fecha:** diagnosticado 25-sep-2026 · **corregido y desplegado 30-sep-2026**
**Estado:** **ARREGLADO en producción** (`main_v2_final_v07.py`, `sorted(expanded)`).

Ordenar el texto expandido antes de vectorizar. Sin el arreglo el orden dependía de
`PYTHONHASHSEED`, así que **producción no era reproducible entre reinicios**: 14 de
214 consultas afectadas (coseno 0,978-0,994, no cambio de resultados pero sí de
posición). Verificado tras el despliegue: dos llamadas idénticas devuelven rankings
idénticos.

---

## Pendientes de decisión

| puerta | tras | pregunta |
|---|---|---|
| G3 | Fase C | ¿213 consultas bastan para +0,05? |
| G4 | Fase D | línea base con vectores recalculados: ¿se migra? |
| — | Fase H | ~~columna `embedding_text`~~ **RESUELTA 30-sep-2026** (87.661 fichas pobladas + ingesta ya escribe la columna; end-to-end verificado). |
| — | Fase H | ~~¿se re-verifica con BGE el hallazgo de la Fase C?~~ **DESMENTIDO 30-sep-2026**: con BGE el régimen lexico-copia **desaparece** (léxico pierde −0,25 pareada en los tres tercios, no gana ninguno) y el híbrido empata-perdería vs semántico (+0,7/0,3). Cambiar el argumento de la memoria: ahora el fundamento del 0,3/0,7 es el red de seguridad + empates globales, no «no pierde en ningún régimen». |
| — | Fase H | ~~el efecto +0,2743 mezcla modelo **y** texto~~ **RESUELTO 01-oct-2026**: NO lo mezcla — la cifra canónica ya usa la columna anti-confound (`embedding_minilm_aprox`, misma función `texto()` que BGE). Efecto texto medido aparte: +0,0211 IC95 [−0,0061 · +0,0484], cruza cero. Doc: `FASE-H-MODELO-VS-TEXTO.md`. Re-vectorización de 5-6 h cancelada (innecesaria). |
| — | Fase H | **latencia: probado el fix HNSW en producción y RETIRADO** (01-oct). La SQL del handler impide el índice (×75); al reescribirla, la calidad **baja −0,0315** [−0,0517 · −0,0114] con `ef_search` 500 y el solape con el exacto no es idéntico. Para ganarlo de verdad: reindexar con `ef_construction` mayor (horas) + validar contra el exacto. Doc: `FASE-H-LATENCIA-PROBADA-Y-REVERTIDA.md`. |
| — | Fase H | el primer golpe tras reiniciar la API es ollama frío (+6 s); el resto, la SQL exacta (~2,3 s). Opción declarada: reindexado HNSW. La caché de vector de consulta solo ahorra 116 ms — descartada. |

