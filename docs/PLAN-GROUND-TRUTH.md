# Plan para que el ground truth sirva al fin perseguido

**Fecha:** 24-sep-2026
**Estado:** propuesta · **sin ejecutar**
**Fin:** poder decidir con datos si un motor es mejor que otro (MiniLM actual vs BGE-M3)

> **Revisado el 24-sep-2026 mediante auditoría adversarial.** Se corrigieron
> cuatro números y se retiró una afirmación sin base. Detalle y justificación de
> cada corrección en `AUDITORIA-DEL-PLAN.md`. Los puntos **modificados** respecto
> a la primera versión van marcados en el texto.

---

## Principio rector

> **No medir nada más hasta que la métrica mida.**

Hoy el criterio de patrón **marca como relevante el 41 % de las fichas que el
juicio del LLM rechaza** (matriz de confusión sobre los 470 juicios: precisión
0,697, 96 falsos positivos de 232 no relevantes). No está invertido: está inflado.
Cualquier medición hecha con ese criterio —incluido el P@5 de 0,6043 que venimos
reportando— no es interpretable.

Por eso la Fase A va primero, y va sola: sin ella, todo lo demás produce números
que no se pueden defender.

---

## Fase A · Arreglar la métrica

**Esfuerzo:** una tarde de trabajo · **Coste:** 0 € (no usa LLM)
**Desbloquea:** todo lo demás

### Qué se hace

1. **Recuperar los 470 juicios existentes indexados por `dataset_id`.**
   Vía fiable: `resultados_reales` **ya trae el `dataset_id`**. El cruce por
   título **no sirve como vía principal**: el catálogo tiene 2.144 grupos de
   títulos duplicados, así que un título puede apuntar a varias fichas y el
   error sería silencioso. Solo 418 de 470 (89 %) son resolubles por título, y
   de forma ambigua.

2. **Sustituir el criterio de relevancia** en `utils/ragas_metrics.py`:
   - actual: `any(patron in titulo for patron in patrones)`
   - nuevo: consulta al fichero de etiquetas por `dataset_id`
   - los no juzgados se marcan **aparte**, no como no relevantes

3. **Cambiar la métrica principal** a **nDCG@10 sobre el juicio**, con P@5 y MRR
   de apoyo (el MRR ya está implementado en el código y sin usar).

4. **Añadir los dos controles que faltan:**
   - **cobertura**: qué % del pool evaluado está juzgado (si es bajo, la métrica
     no es interpretable y debe decirlo)
   - **acuerdo entre jueces**: doble juicio ciego sobre 100 pares

5. **Aplicar de verdad el `no_debe_contener`** que ya está en el fichero
   (`humedales`, `geoparapes`, `BIC`): hoy existe y **nunca se ejecuta**. Basta
   `re.search` en vez de `in`.

### Criterio de aceptación

- La matriz de confusión del nuevo criterio **sube la precisión por encima de
  0,90 sin bajar el recall de 0,90**. (El patrón actual: precisión 0,697,
  recall 0,929. El patrón estricto: 0,904 y 0,630 — sube precisión pero hunde
  recall; el juicio no debe hacer eso.)
- Se aplica de verdad el `no_debe_contener` y se comprueba que reduce los falsos
  positivos sin perder relevantes.
- **Nota:** hay que descartar el test `102_discriminacion_gt.py` como criterio de
  aceptación: su universo mezcla documentos reales con aleatorios y produce un
  artefacto. Ver `AUDITORIA-DEL-PLAN.md` §1.

### Lo que produce

El GT pasa de «inservible para comparar» a «utilizable con reservas», y aparece
la **línea base honesta**. Y no es un número, es un **intervalo**:

| métrica | valor |
|---|---|
| nDCG@10 sobre el juicio | **0,4820** · IC95 % **[0,376 · 0,588]** |
| P@5 sobre el juicio | cota inferior **0,3660** · cota superior **0,7872** |

El intervalo del P@5 es ancho (0,42) porque **99 de las 235 fichas del top-5 no
están juzgadas**. Dar un número suelto sería más precisión de la que los datos
permiten. La Fase B es lo que cierra el intervalo.

---

## Fase B · Completar el pool

**Esfuerzo:** ~1 día · **Coste:** < 5 € de LLM
**Depende de:** Fase A

### El problema que resuelve

| dato | valor |
|---|---|
| documentos en el top-30 de hoy | 1.410 |
| juzgados | **397 (28 %)** |
| sin juzgar → cuentan como no relevantes | **1.013** |
| unión de 3 motores | 583 docs → **448 (77 %) sin juzgar** |

Un motor nuevo que encuentre algo relevante que el viejo no encontraba sería
**penalizado por encontrarlo**. Esto es lo que hay que eliminar antes de comparar
nada.

### Qué se hace

1. **Pool = unión** del top-20 de varios sistemas:
   - motor actual (semántico + léxico)
   - solo léxico (independiente del encoder por construcción)
   - solo semántico
2. **Juzgar solo lo pendiente**, con el prompt de `generar_ground_truth_real.py`
   en **lotes de 20 resultados por llamada**.
3. Escala de **3 niveles** (validada: 90 % de acuerdo, 40/40 con ±1).
4. **Control de duplicados**: agrupar fichas equivalentes (6.564 grupos, 176
   pares relevantes casi idénticos hoy) y contarlas **una sola vez** en la
   métrica.
5. Rejuzgar las **2 consultas que son títulos literales** (`cult_001`,
   `dep_002`) o reformularlas.

### Criterio de aceptación

- Cobertura del pool evaluado **> 90 %** en el top-10 y **> 70 %** en el top-30.
- Acuerdo entre jueces **> 0,80** en el doble juicio ciego.

### Lo que produce

Un GT **justo con motores distintos al actual**: se puede migrar sin que el
propio GT castigue la mejora.

---

## Fase C · Ampliar el conjunto de consultas

**Esfuerzo:** 1-2 días · **Coste:** < 5 € de LLM
**Depende de:** Fase A (para el formato de salida)

### El problema que resuelve

| n | mejora mínima detectable (IC95 %) |
|---|---|
| **47 (hoy)** | **0,106** |
| 150 | 0,060 |
| **213** | **0,050** |
| 300 | 0,042 |

Cálculo sobre la varianza de **nDCG@10 (desv 0,3717)**, que es la métrica que se
va a usar. Si se exige potencia estadística del 80 %, para +0,05 hacen falta
**434** consultas.

Con 47 consultas, la mejora esperada de BGE-M3 (**+0,05**) es **indetectable por
construcción**. La pregunta del fin no se puede responder con este tamaño.

### Qué se hace

1. ~~**Fijar el ámbito en el texto de la consulta.**~~
   **⚠️ EJECUTADO Y DESMENTIDO (25-sep-2026).** Se hizo (38 reescrituras) y se
   midió con ida y vuelta: el texto nuevo degrada 12 de 29 cambios de forma
   reproducible, **11 de ellos de 2 a 1**. Causa: solo el 11,4 % del catálogo es
   de ámbito «España» y País Vasco tiene más fichas que España; exigir ámbito
   nacional castiga al 88,6 %. **El ámbito va en el CRITERIO del juez, no en el
   texto** → `docs/FASE-C-PASO1-HALLAZGO.md`.

   **✅ EJECUTADO (25-sep-2026):** criterio corregido y aplicado. 225 etiquetas de
   nivel 1 rejuzgadas → **146 suben a 2**, 31 siguen, 48 bajan a 0. GT queda
   `{0: 849, 1: 31, 2: 544}` y nDCG@10 pasa a **0,6408** (+0,0043: la corrección
   vale por validez, no por la cifra). Control de ida y vuelta: 45 % efecto del
   criterio, 50 % fragilidad del nivel 1 (55 % no reproducía). Detalle:
   `docs/FASE-C-PASO1-EJECUTADO.md`.
2. **Ampliar a ~215 consultas**, manteniendo el reparto por categoría y la
   distribución de dificultad (el actual calibra bien: 0,727 / 0,600 / 0,467).
   Con 150 solo se detectan mejoras ≥0,06; con 215, ≥0,05.
3. **Reutilizar el juicio de las 47 actuales**: no se repite el trabajo.
   **⚠️ Sólo si NO se cambia el texto de la consulta.** Con el texto reescrito,
   ~190 etiquetas cambian de nivel (§ hallazgo). Con el ámbito movido al
   criterio, sí se puede reutilizar.

### Criterio de aceptación

- ≥ 215 consultas, ≥ 18 por categoría.
  **✅ CUMPLIDO: 216 consultas, 12 categorías × 18 exacto** (25-sep-2026).
  169/169 nuevas respondidas por el catálogo, 0 sin resultados.
  Detalle: `docs/FASE-C-PASO2-EJECUTADO.md`.

  ⚠️ **25-sep-2026 · el paso 3 invalidó la comparación de motores con las 216.**
  El juicio se hizo (5.298 pares, GT v3 con 6.722 etiquetas), pero las consultas
  nuevas heredaron el vocabulario de los títulos del catálogo que se le mostraron
  al LLM, lo que favorece al motor léxico por construcción. La línea base canónica
  siguen siendo las 47. Antes de reutilizar el conjunto hay que **regenerar las 169
  consultas sin acceso a títulos** y verificar que el solapamiento queda por debajo
  de 0,57. Detalle: `docs/FASE-C-PASO3-HALLAZGO-CONTAMINACION.md`.
- La dificultad **sigue calibrando** de forma monótona (control de regresión).

---

## Fase D · Línea base con el motor actual

**Esfuerzo:** 1 hora · **Coste:** 0 €
**Depende de:** Fases A, B, C

### Qué se hace

1. **Recalcular los 94.461 embeddings** con el entorno ya fijado
   (`requirements.txt` + revisión `e8f8c211`). Medido: **8,7 minutos** a 180
   textos/s. Deja el catálogo consistente, que hoy no lo está (§9 del pinning:
   hay fichas cortas cuyo vector no se reproduce).
2. **Ejecutar el GT y guardar la línea base**: P@5, nDCG@10, MRR, cobertura.
3. **Integrar `88_regresion_embeddings.py`** como comprobación tras cada build.

### Criterio de aceptación

- Prueba de regresión `PASA` **en todo el catálogo**, no solo en las últimas 100.
- Línea base guardada con su intervalo de confianza al 95 %.

**Esta es la foto de partida honesta.** Todo lo que se mida después se compara
contra esto.

---

## Fase E · Migrar a BGE-M3

**Esfuerzo:** media jornada · **Coste:** 0 € (solo cómputo local)

### Qué se hace, **en un solo movimiento**

```
1. ampliar la columna:  vector(384) -> vector(1024)
2. recalcular los 94.461 embeddings de documentos   (~45 min estimado)
3. desplegar la API con BGE-M3                      <- mismo paso
4. rehacer la prueba de regresión con el modelo nuevo
```

**Nunca en pasos separados.** Si la API despliega BGE-M3 antes de recalcular los
documentos, durante ese intervalo **todas las búsquedas devuelven basura**:
el coseno entre espacios vectoriales distintos no mide similitud.

### Por qué BGE-M3 y no otro

- primera de las opciones **sin restricción de licencia** (MIT)
- **61,5 en español** (MMTEB) frente a ~52 del actual
- ventana de **8.194 tokens**: elimina el truncamiento a 128 que hoy deja fuera
  `keywords`, `tema` y `territorio` en el 76 % de las fichas
- devuelve denso + **sparse** + multi-vector en una pasada, y el buscador **ya es
  híbrido**: sustituye al expansor léxico sin rehacer nada
- `jina-embeddings-v3` descartado: **CC-BY-NC**, uso comercial de pago

### Criterio de aceptación

- Prueba de regresión con el modelo nuevo **PASA**
- El caso A sigue en el puesto 1

---

## Fase F · Comparación final (la que responde al fin)

**Esfuerzo:** 2 horas · **Coste:** < 2 €
**Depende de:** Fases D y E

### Qué se hace

1. **Medir BGE-M3 con el GT** y comparar contra la línea base de la Fase D.
2. **Juzgar solo lo nuevo que BGE-M3 encuentra** en su top-5 y no estaba juzgado
   (~100-235 pares). Es el *pooling adaptativo*: sin esto, el GT sigue sesgado
   hacia MiniLM aunque se haya ampliado el pool en la Fase B.
3. **Volver a medir** y reportar:
   - nDCG@10 con su **intervalo de confianza**
   - mejora mínima detectable con el tamaño final
   - cobertura del pool
   - decisión explícita: **¿se adopta BGE-M3, sí o no?**

### Criterio de aceptación

- La mejora (o su ausencia) es **mayor que la mejora mínima detectable**.
  Si no lo es, la conclusión honesta es «no se puede decidir con este GT», y eso
  también es un resultado.

---

## Puertas de decisión

| puerta | tras | se decide |
|---|---|---|
| **G1** | Fase A | ¿se publica la línea base como **nDCG@10 = 0,48 · IC95 % [0,38 · 0,59]** con el % de pool sin juzgar declarado, en vez de una cifra única? |
| **G2** | Fase B | ¿el acuerdo entre jueces supera 0,80? Si no, el problema es el prompt de juicio, no el buscador |
| **G3** | Fase C | ¿150 consultas bastan para +0,05, o se amplía más? |
| **G4** | Fase D | línea base fijada. ¿Se procede a migrar? |
| **G5** | Fase F | **¿BGE-M3 mejora?** Decisión de adopción |

---

## Resumen de esfuerzo y coste

| fase | esfuerzo | coste LLM | dependencia |
|---|---|---|---|
| A · métrica | 1 tarde | 0 € | — |
| B · pool | ~1 día | < 5 € | A |
| C · consultas | 1-2 días | < 5 € | A |
| — | (215 consultas, no 150) | | |
| D · línea base | 1 hora | 0 € | A, B, C |
| E · migrar | media jornada | 0 € | — |
| F · comparar | 2 horas | < 2 € | D, E |

**Total: 4-6 jornadas de trabajo, menos de 12 € de LLM.**

Reparto recomendado del calendario:
- **Días 1-2:** Fases A + D con las 47 consultas actuales → ya hay una cifra
  defendible y una línea base
- **Días 3-4:** Fase B (pool) y Fase C (consultas)
- **Día 5:** Fase E (migración) + Fase F (comparación)

Las Fases A y D juntas **caben en un día** y ya dan el resultado principal: una
métrica que mide y un suelo honesto.

---

## Lo que NO se hace

| no se hace | por qué |
|---|---|
| tirar el GT y hacer uno nuevo | la estructura es sólida (calibra, sin duplicados, balanceada). El fallo es la métrica |
| rejuzgar los 470 pares ya juzgados | la etiqueta depende del **documento**, no del ranking. Son válidos |
| juzgar de nuevo sin pooling | repetiría el defecto: el motor se evaluaría contra su propia salida |
| cambiar de modelo antes de arreglar el GT | sería un cambio grande medido con una métrica que ordena al revés |
| subir `max_seq_length` a 512 | **probado y empeora** (P@5 0,0128 → 0,0043). El modelo se entrenó con 128 |
| desplegar BGE-M3 antes de recalcular vectores | mezcla espacios vectoriales: devuelve basura |

---

## Riesgos y cómo se cubren

| riesgo | mitigación |
|---|---|
| la línea base (0,48) se lee como empeoramiento | documentar G1: es un cambio de criterio, no del buscador. Publicar el IC95 %, no un número |
| baja acuerdo entre jueces | puerta G2: rehacer el prompt antes de seguir |
| BGE-M3 no cabe en RAM (6 GB libres) | medirlo en la Fase E antes de comprometerse; 568 M params en CPU ya rinde |
| el recálculo de vectores altera el catálogo | la imagen anterior está etiquetada (`docker-api:pre-pinning-2026-09-24`) y hay copia del arranque previo |
| 150 consultas no bastan | G3 lo decide con números, no con fe |

---

## Arranque propuesto

**Fase A sola, y nada más.** Una tarde, coste cero, y al terminar existe por
primera vez una métrica que mide lo que dice medir.

A partir de ahí, cada fase tiene su puerta y se puede parar sin dejar trabajo a
medias.
