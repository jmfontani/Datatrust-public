# Fase C, paso 2 ejecutado · 216 consultas

**Fecha:** 25-sep-2026
**Qué se ha hecho:** ampliar el conjunto de consultas de 47 a **216**, con el
criterio de ámbito ya corregido.
**Objetivo que cumple:** bajar la mejora mínima detectable de **0,106** (con 47)
a **~0,050**, que es la condición para que la Fase E (MiniLM vs BGE-M3) pueda
concluir algo.

---

## 1. Resultado

| | antes | ahora |
|---|---|---|
| consultas | 47 | **216** |
| categorías | 10 | **12** (18 cada una) |
| mejora detectable (IC95 %) | 0,106 | **~0,050** |

**Reparto: 18 por categoría, exacto.** Se conservaron las 10 categorías
existentes y se añadieron dos con masa real en el catálogo
(`ciencia y tecnología`, `sociedad y bienestar`), que también aparecen en el
temario de los temas 3-5 de la oposición.

**Dificultad:** fácil 46 · media 111 · difícil 59 (23 / 57 / 19 %, manteniendo la
proporción del GT original para que siga calibrando).

---

## 2. Cómo se generaron (y por qué así)

Dos decisiones de diseño, ambas derivadas de hallazgos anteriores:

### 2.1 Anclar en material real del catálogo

Cada llamada al LLM recibió **40 títulos reales** de ese tema sacados de la base
de datos, con la instrucción de que las consultas **deben poder responderse con
material como ese**. Además se le dio la lista de consultas existentes de la
categoría para que no las repitiera.

Motivo: una consulta que el catálogo no puede responder **no mide al
recuperador**, mide la ausencia de datos. Aportaría un nDCG cercano a 0 para todos
los motores por igual, ensanchando el intervalo sin aportar información.

### 2.2 El ámbito NO se fuerza en el texto

Es la conclusión del paso 1 (`FASE-C-PASO1-HALLAZGO.md`). Se aplica en las dos
direcciones:

- **A la consulta:** el prompt prohíbe meter «España», «nacional» o comunidades.
  Verificado: **0 de 169** lo incluyen.
- **A la `descripcion`** (la intención que ve el juez): describe el **fenómeno** y
  la **faceta**, nunca exige ámbito nacional. Así la ambigüedad no llega al juez.

Comprobación de que la prohibición se cumplió — y un falso positivo del propio
chequeo: la primera pasada marcó dos consultas por contener «nacional», que en
realidad eran **«nacionalidad»**. Detectar la subcadena como si fuera la palabra
convertía un término legítimo en una violación. Corregido a comparación por
palabras completas.

---

## 3. Validación contra el catálogo real

`129_validar_consultas.py` lanzó las 169 nuevas contra el motor:

| | n |
|---|---|
| **con resultados** | **169 (100 %)** |
| sin resultados | **0** |
| con similitud top-1 < 0,45 | 11 (se conservan) |

**Cero consultas sin respuesta.** El anclaje en títulos reales funcionó.

### 3.1 Un error de método que había que corregir

La primera versión del validador filtraba por **solapamiento de palabras clave**
con el tema, y marcó **45 de 169 como «dudosas» (tema < 30 %)**. Al revisarlas,
eran falsos positivos masivos:

- «mujeres en puestos directivos» → tema 0 %
- «afiliados por actividad económica» → tema 20 %
- «aguas residuales COVID-19» → tema 0 %

El motivo es que **ninguna ficha contiene literalmente** «empleo», «paro» o
«laboral» en esos casos. Es exactamente **el error de medir con patrones** que ya
se había corregido dos veces en este trabajo (el GT original, y el test de
ventana). Repetirlo aquí habría descartado 45 consultas perfectamente válidas.

**Se sustituyó por una señal del propio motor** (similitud del top-1) y, sobre
todo, **se dejó de descartar**: las 11 de similitud baja también pasan. El único
descarte legítimo es «no devuelve nada» (0 casos). Quién decide si una consulta
tiene respuesta es el **juicio del pool**, no un umbral mío: descartar por
heurística sería volver a sustituir la medición por una aproximación.

---

## 4. Los ficheros

| fichero | contenido |
|---|---|
| `entregables/consultas_nuevas.jsonl` | las 169 generadas, con `descripcion` y `criterios_relevancia` |
| `entregables/consultas_validadas.jsonl` | las 169 con las señales de validación (`_n_resultados`, `_sim_top1`) |
| `entregables/_checkpoint_consultas.json` | checkpoint de la generación (permite reanudar sin repetir llamadas) |
| `entregables/consultas_v2.jsonl` | del paso 1; **no se usa** para etiquetas |

### 4.1 Un hueco recuperado

La categoría `sanidad` falló por timeout en la primera pasada (13 consultas). El
checkpoint permitió reanudar pidiendo **solo lo que faltaba** en vez de repetir
las 156 ya generadas. 0 fallos en la segunda.

---

## 5. Coste y controles

| | |
|---|---|
| llamadas LLM (generación) | 13 (una por categoría, +1 repetición por el timeout) |
| llamadas al motor (validación) | 169 |
| coste | < 1 € |
| ficheros nuevos | 3 + 1 checkpoint |
| modificaciones a producción | **ninguna** |

```bash
128_generar_consultas.py    # 12 llamadas, 169 consultas, checklist de ambito
129_validar_consultas.py    # 169 consultas contra el motor: 0 sin respuesta
```

---

## 6. Lo que falta para cerrar la Fase C

El paso 3 del plan decía «reutilizar el juicio de las 47 actuales». Tras el paso 1
sabemos que **eso no es automático**: el nivel 1 era frágil y ya hubo que
rejuzgarlo. Lo que queda:

1. **Construir el pool de las 216 consultas** (unión semántico + léxico, igual que
   el 108).
2. **Juzgar las 169 nuevas** con el prompt canónico + el criterio de ámbito
   corregido. Estimación: ~1.700 pares, del orden de 2 horas de reloj y < 5 €.
3. **Re-medir** con las 216 y recalcular la mejora mínima detectable real (no la
   teórica de 0,050: se calcula sobre la varianza observada).

---

## 7. Estado

| fase | estado |
|---|---|
| A, B, bug de `top_k`, C·paso 1 | ✅ |
| **C · paso 2 (216 consultas)** | ✅ **ejecutado** |
| C · paso 3 (pool + juicio de las nuevas) | **siguiente** |
| D (recalcular 94.461) | pendiente, ~9 min |
| E (BGE-M3, copia de vectores ya hecha) | pendiente |
