# Fase C cerrada · El instrumento queda limpio y el orden se restaura

**Fecha:** 28-sep-2026 · **Estado:** ✅ Fase C cerrada · comparación de motores válida

---

## 1. El resultado

**214 consultas** (47 humanas + 167 regeneradas sin títulos), GT v4 con **6.114
etiquetas**, juicio de **4.690 pares** (0 fallos tras recuperar 1 lote).

| sistema | nDCG@10 | IC95 | P@5 | MRR | cobertura |
|---|---|---|---|---|---|
| **actual (0,7/0,3)** | **0,4831** | [0,4338 · 0,5324] | 0,3449 | 0,4908 | 100 % |
| semántico (1,0/0,0) | 0,4235 | [0,3774 · 0,4697] | 0,2869 | 0,4328 | 100 % |
| léxico (0,0/1,0) | 0,3623 | [0,3117 · 0,4129] | 0,3129 | 0,4047 | 68 % |

**Comparación pareada:**

| comparación | diff | IC95 de la diff | veredicto |
|---|---|---|---|
| actual vs semántico | +0,0596 | [+0,0367 · +0,0825] | **DISTINGUIBLE** |
| actual vs léxico | +0,1208 | [+0,0680 · +0,1736] | **DISTINGUIBLE** |
| semántico vs léxico | +0,0612 | [+0,0008 · +0,1216] | **DISTINGUIBLE** |

**El orden es el mismo que el de las 47 consultas humanas:**

```
47 humanas:    actual 0,6408  >  semántico 0,5801  >  léxico 0,4368
214 limpias:   actual 0,4831  >  semántico 0,4235  >  léxico 0,3623
```

Esto es lo que valida la comparación: **el conjunto ampliado reproduce la
conclusión del conjunto escrito por personas.** Con las 169 contaminadas ese orden
**se rompía** (el léxico empataba con el híbrido y el semántico se hundía).

---

## 2. Qué cambió respecto a la versión contaminada

| conjunto | actual | semántico | léxico | ¿orden correcto? |
|---|---|---|---|---|
| 47 humanas | 0,6408 | 0,5801 | 0,4368 | ✅ |
| 169 contaminadas | 0,5827 | 0,4350 | **0,5802** | ❌ léxico empata con el híbrido |
| **167 limpias** | **0,4831** | **0,4235** | **0,3623** | ✅ |

Los valores absolutos **bajan** al limpiar (0,58 → 0,48). No es un empeoramiento
del buscador: es que las consultas limpias **comparten menos vocabulario con el
catálogo**, así que son más difíciles. El léxico era el principal beneficiado del
vocabulario prestado, y al quitarlo **cae 0,22 puntos** (0,5802 → 0,3623).

---

## 3. La potencia: lo que se gana

| conjunto | mejora detectable (diferencia pareada) |
|---|---|
| 47 humanas | 0,0564 |
| **214 (limpias)** | **0,0229** |

Mejora de **2,5×**. Y es determinante para lo que viene: la mejora esperada de
BGE-M3 es del orden de **0,03**, que con 47 consultas era **indetectable** y ahora
**está por encima del umbral**.

**La Fase E ya se puede medir.** Antes no.

---

## 4. Cómo se arregló

1. **No mostrar títulos del catálogo al LLM.** Se le da el tema y las facetas.
2. **Sí mostrarle las consultas humanas del mismo tema**, como *ejemplo de
   registro*: así escribe como una persona y no como un catálogo. Es el movimiento
   que llevó el solapamiento de 0,735 a **0,438**, por debajo del 0,514 de las
   humanas.
3. **Validar contra el motor después**, no primando el texto. 167/167 devuelven
   resultados; ninguna se descartó por similitud baja (el único descarte legítimo
   es «no devuelve nada»).

---

## 5. Incidencias de esta sesión (y qué se aprendió)

- **Se mató un proceso sano.** La comprobación de «¿sigue vivo?» buscaba la cadena
  `131.py` en los procesos, y **esa misma orden contenía la cadena**, así que el
  `grep` se encontraba a sí mismo. Regla: **filtrar por intérprete** (`case
  "$cmd" in python*`), no por nombre de fichero.
- **El progreso parecía congelado.** Python **bloquea stdout al redirigir a
  fichero**: sin `python -u` no se ve nada hasta que termina. Explicó dos
  diagnósticos falsos de «atascado». Regla: `-u` en cualquier job largo.
- **Faltó copiar el fichero al host** tras recuperar el lote fallido: la
  evaluación leyó 6.104 etiquetas en vez de 6.114. Se detectó **porque el número
  no cuadraba**. Regla: verificar el conteo contra el esperado, no contra el
  fichero que se acaba de leer.
- **Los ids se materializaron leyéndolos del pool**, no por convención de orden
  (script 136). Si se hubieran asignado «por orden del fichero», un cambio futuro
  desalinearía consultas y juicios **en silencio**.
- **Un duplicado entre categorías** (`competencias digitales docentes`) por
  reinicializar el conjunto de deduplicación dentro del bucle. 168 → 167.

---

## 6. Ficheros

- `entregables/consultas_limpias.jsonl` — 167 consultas con id verificado
- `entregables/control_solapamiento_limpias.json` — el control que valida el conjunto
- `entregables/pool_limpias.json` — 4.690 pares (1.011 solo del motor léxico)
- `entregables/_checkpoint_limpias.json` — 4.690 juicios
- `entregables/gt_etiquetas_v4.json` — **6.114 etiquetas** (v2 intacto: 0 cambiadas)
- `entregables/fase_c_FINAL_LIMPIAS.json` — **el resultado válido de la Fase C**
- `codigo/135_generar_consultas_limpias.py`, `136_materializar_ids.py`
- `codigo/130`, `131`, `132` parametrizados para reutilizarse con cualquier pool

---

## 7. Qué sigue

**Fase D — línea base con el motor actual.** Recalcular los 94.461 embeddings
(~9 min). No se ha hecho **a propósito** antes de esta evaluación: recalcular
cambia los resultados de búsqueda y la medición habría mezclado la mejora del
instrumento con la del motor. Ahora es el momento de hacerla y **volver a medir
las 214** para fijar la foto de partida.

⚠️ Nota técnica: `generate_embeddings_pg.py` está escrito para **rellenar nulos**, y
no hay ninguno (0 de 94.461): necesita un modo `--forzar`. Además, 35.767 fichas
tienen el texto truncado a 128 tokens, así que el recálculo **sí cambia el
ranking**.

**Fase E — BGE-M3**, ya medible: la mejora esperada (~0,03) supera el umbral
detectable (0,0229).
