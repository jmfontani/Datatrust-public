# Fase C, paso 3 · El juicio está hecho, y apareció un problema en mi propio método

**Fecha:** 25-sep-2026
**Estado:** ✅ juicio completado · ❌ la comparación de motores con estas 216 consultas **no es válida**

---

## 1. Lo que pedía el plan y lo que salió

El paso 3 era cerrar la Fase C: ampliar a 216 consultas para tener potencia
estadística y volver a medir los tres motores. Se hizo:

- **5.298 pares juzgados**, 0 fallos de lote, 242 min, < 5 €.
- **GT v3: 6.722 etiquetas**, con el criterio de ámbito corregido.
- Integridad verificada: el GT v2 sigue **intacto** (0 etiquetas cambiadas,
  1.424/1.424 presentes) y las 5.298 son nuevas.
- Control de comparabilidad superado: el script nuevo reproduce **exactamente**
  las cifras del anterior (0,6408 / 0,5801 / 0,4368) sobre las 47 consultas.

Y el resultado pareció un vuelco:

| sistema | nDCG@10 | IC95 |
|---------|---------|------|
| actual (0,7/0,3) | 0,5827 | [0,5363 · 0,6290] |
| **léxico (0,0/1,0)** | **0,5802** | [0,5290 · 0,6315] |
| semántico (1,0/0,0) | 0,4350 | [0,3893 · 0,4808] |

El **semántico puro se hunde** y el **léxico empata con el híbrido**. Comparación
pareada: `actual vs léxico` **+0,0024**, no distinguible del ruido. Si esto fuera
cierto, el hallazgo sería enorme: el motor semántico no aporta nada y bastaría con
buscar palabras.

**No es cierto. Es un artefacto que introduje yo al generar las consultas.**

---

## 2. El control que lo destapa

Las 169 consultas nuevas se generaron dando al LLM **40 títulos reales del catálogo**
de cada tema, para que las consultas pudieran responderse. Eso fue deliberado y
está documentado. El riesgo que no vi: **el LLM reutilizó el vocabulario de esos
títulos**. Y una consulta escrita en el idioma del catálogo favorece al motor que
casa palabras literales.

### 2.1 La caída está concentrada en las consultas nuevas

| sistema | nDCG (47 antiguas) | nDCG (169 nuevas) | delta |
|---------|--------------------|-------------------|-------|
| actual | 0,6408 | 0,5665 | −0,0744 |
| semántico | 0,5801 | 0,3947 | **−0,1854** |
| léxico | 0,4368 | **0,6201** | **+0,1834** |

El semántico y el léxico se cruzan **solo** en las nuevas. En las antiguas el orden
es el de siempre. Si la causa fuera el modelo de embeddings, la caída aparecería en
los dos grupos.

### 2.2 El solapamiento de vocabulario lo confirma

Fracción de palabras significativas de la consulta que están **literalmente** en el
título/descripción del primer resultado:

| sistema | 47 antiguas | 169 nuevas | delta |
|---------|-------------|------------|-------|
| actual | 0,514 | 0,627 | +0,113 |
| semántico | 0,450 | 0,391 | −0,059 |
| **léxico** | 0,426 | **0,634** | **+0,208** |

El léxico gana +0,208 de solapamiento en las nuevas. **La longitud de las consultas
es idéntica** (2,8 vs 2,9 palabras significativas), así que no es que las nuevas sean
más cortas: es que usan las mismas palabras que los títulos.

### 2.3 Y lo decisivo: el ranking entre motores depende del solapamiento

Partiendo las 169 nuevas en tercios por solapamiento:

| tercio | n | solap. | actual | semántico | léxico | gana |
|--------|---|--------|--------|-----------|--------|------|
| **BAJO** | 56 | 0,271 | **0,4223** | 0,3517 | 0,3533 | **actual** |
| medio | 56 | 0,929 | 0,7307 | 0,4817 | 0,7720 | léxico |
| **ALTO** | 57 | 1,000 | 0,5468 | 0,3515 | **0,7331** | léxico |

`semántico − léxico`:
- con solapamiento **bajo**: **−0,0016** (empatados)
- con solapamiento **alto**: **−0,3816** (el léxico arrasa)

**Un vuelco de 0,38 puntos causado por una propiedad del TEXTO de la consulta, no del
motor.** En las consultas que no copian el vocabulario del catálogo, el semántico y
el léxico están empatados; el que gana es el **híbrido** (0,4223 frente a 0,35).

### 2.4 El control de dificultad (aquí me equivoqué al predecir)

Escribí en el script que si las nuevas tenían *más* nivel-2 disponibles, no serían más
díficiles. Salió al revés: **11,6 nivel-2 disponibles en las antiguas frente a 8,6 en
las nuevas**. Así que las nuevas **sí** son algo más difíciles de responder — es un
factor real y hay que reconocerlo.

Pero no explica el vuelco: la dificultad afecta a los tres motores por igual, y lo que
se mide en el apartado 2.3 es el **cambio de orden entre motores según el
solapamiento**, que la dificultad no puede producir.

---

## 3. Qué queda en pie y qué no

**No es válido:**
- Comparar motores con las 216 consultas como si fueran un instrumento neutro.
- Concluir que el léxico iguala al semántico, ni que el semántico no aporta nada.
- La cifra 0,5827 / 0,5802 / 0,4350 como resultado final del sistema.

**Sigue siendo válido:**
- La línea base de las **47 consultas** (0,6408 / 0,5801 / 0,4368) y todas las
  cifras históricas. Las consultas se escribieron antes de este trabajo y no copian
  el vocabulario del catálogo (solapamiento 0,571, el tercio bajo).
- El **GT v3** y sus 6.722 etiquetas: el juicio no depende de cómo se escribió la
  consulta, solo del par (consulta, ficha). Reutilizable íntegro.
- Las correcciones anteriores: el bug del `top_k`, el criterio de ámbito.
- **El hallazgo de la estratificación**, que es nuevo y tiene valor propio.

---

## 4. El hallazgo que sí vale

Los motores **no se ordenan igual según el tipo de consulta**:

- consulta que **copia el vocabulario** del catálogo → gana el léxico (0,7331)
- consulta que **no lo copia** → semántico y léxico **empatan** (0,3517 / 0,3533)
  y **gana el híbrido** (0,4223)

Esto explica por qué el híbrido es la mejor opción de despliegue: **no es que sea el
mejor en promedio, es que es el único que no pierde en ninguno de los dos regímenes.**
Y da un criterio operativo: el peso léxico debería depender de si la consulta comparte
vocabulario con el catálogo.

---

## 5. Cómo se arregla

1. **Regenerar las 169 consultas sin mostrar títulos reales al LLM.** En su lugar,
   darle solo la descripción del tema y las facetas, y comprobar *a posteriori* que
   el solapamiento queda por debajo del de las 47 originales (objetivo: < 0,57).
2. **Añadir el solapamiento como control obligatorio** en cualquier generación de
   consultas: medirlo antes de juzgar, no después. Es una medición barata (segundos)
   que ahora sé que invalida 4 horas de juicio.
3. **Rejuzgar solo lo nuevo** (el GT v3 aprovechable son las 169 fichas ya juzgadas
   por pares; si cambia el texto de la consulta, hay que rejuzgar — lección §32).
4. Las 47 originales se mantienen como línea base canónica.

**Nota sobre §32:** la lección decía que cambiar el texto de la consulta invalida sus
etiquetas. Este episodio es la misma lección desde el otro lado: **escribir el texto
con el vocabulario del catálogo invalida la comparación entre motores.**

---

## 6. Estado de ficheros

- `entregables/gt_etiquetas_v3.json` — 6.722 etiquetas (v2 intacto)
- `entregables/_checkpoint_nuevas.json` — 5.298 juicios con título y razón
- `entregables/pool_nuevas.json` — 5.298 pares con metadatos
- `entregables/fase_c_FINAL_216.json` — métricas de 216 (**no usar como final**)
- `entregables/control_sesgo_vocabulario.json` — desglose 47 vs 169
- `entregables/estratificacion_vocabulario.json` — tercios y ranking
- `codigo/130_construir_pool_v2.py`, `131_juzgar_nuevas.py`, `132_evaluar_216.py`,
  `133_control_sesgo_vocabulario.py`, `134_estratificar_por_vocabulario.py`
