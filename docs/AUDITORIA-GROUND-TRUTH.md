# Auditoría del ground truth: calidad y adecuación

**Fecha:** 24-sep-2026
**Fin perseguido:** comparar motores de recuperación (MiniLM actual vs BGE-M3)
**Veredicto:** la **estructura** del GT es buena; la **métrica** está rota y el
**pool** es demasiado superficial. No hay que tirarlo: hay que corregir dos cosas.

---

## 1. Resumen en una tabla

| dimensión | valor | veredicto |
|---|---|---|
| consultas: número | 47 | **insuficiente** (se necesitan ~140) |
| consultas: longitud | media 3,1 palabras | correcto (realista) |
| consultas: duplicidad | 0 pares con solapamiento ≥0,5 | **correcto** |
| consultas: atajo | 2 coinciden con un título literal | defecto menor |
| balance por categoría | 10 categorías, 4-5 cada una | **correcto** |
| balance por dificultad | 11 fácil / 27 media / 9 difícil | correcto |
| **calibración de dificultad** | 0,727 > 0,600 > 0,467 | **correcto (monótono)** |
| profundidad del pool | 10 docs de 94.461 (**0,0106 %**) | **muy insuficiente** |
| cobertura del top-30 actual | 397/1.410 (**28 %**) | **insuficiente** |
| cobertura de la unión de motores | 135/583 (**23 %**) | **insuficiente** |
| **discriminación con el juicio LLM** | ordena correctamente | **correcto** |
| **discriminación con el criterio de patrón** | **ordena al revés** | **ROTO** |
| potencia estadística | IC95 % ±0,086 | insuficiente |

---

## 2. Lo que está bien (y conviene no tocar)

### 2.1 Las consultas son realistas

- Media de **3,1 palabras** (mediana 3, máximo 5). Es la longitud típica de una
  consulta real, no de una consulta de laboratorio.
- **Cero pares duplicados**: ningún par de consultas comparte más del 50 % del
  vocabulario. No hay relleno.
- Balance correcto: **10 categorías** con 4-5 consultas cada una, y **3 marcadas
  como «ambigua»** deliberadamente.

### 2.2 La etiqueta de dificultad CALIBRA

| dificultad | n | P@5 medio |
|---|---|---|
| fácil | 11 | **0,7273** |
| media | 27 | **0,6000** |
| difícil | 9 | **0,4667** |

Es monótona y con separación clara. **Esto es una señal de que el GT tiene
gradiente real**: no es un conjunto de consultas intercambiables. Un GT mal
construido no calibraría.

### 2.3 El juicio del LLM discrimina correctamente

Prueba decisiva para el fin perseguido: se construyen **motores sintéticos de
calidad conocida** y se comprueba si la métrica los ordena bien.

| motor | nDCG@10 (juicio LLM) |
|---|---|
| PERFECTO (relevantes delante) | **0,7751** |
| REAL (motor actual) | **0,4377** |
| ALEATORIO | 0,0325 |
| INVERTIDO (no relevantes delante) | 0,0000 |

**Orden correcto.** El juicio del LLM produce una métrica capaz de distinguir un
motor perfecto del azar (separación **+0,7426**) y con recorrido útil: el motor
real está en 0,438, lo que deja margen de mejora hasta 0,775.

**Esto responde a la pregunta del fin:** *sí*, el GT puede comparar motores —
**si se usa el juicio del LLM como criterio**.

---

## 3. Lo que está roto

### 3.1 El criterio actual de medición no discrimina: ordena al revés

Con el criterio de patrón en título (el que usa el código):

| motor | P@5 (patrón) |
|---|---|
| PERFECTO | 0,7362 |
| REAL | 0,6596 |
| **INVERTIDO** | **0,5064** |
| **ALEATORIO** | **0,0894** |

**El motor INVERTIDO —que pone delante lo que el juicio dice que NO es
relevante— puntúa 0,5064, muy por encima del ALEATORIO (0,0894).**

Es decir: el criterio de patrón **premia a un motor que ordena mal**. La
separación PERFECTO−INVERTIDO es de solo **0,2298**, contra 0,7751 del juicio.

Confirmado de forma independiente a lo ya medido: el criterio de patrón mide
coincidencia de vocabulario en el título, no relevancia.

### 3.2 El pool es 20.000 veces más superficial de lo necesario

| dato | valor |
|---|---|
| documentos juzgados por consulta | **10** |
| catálogo | 94.461 |
| cobertura del juicio | **0,0106 %** |

Y sobre los resultados de **hoy**:

| dato | valor |
|---|---|
| documentos en el top-30 de las 47 consultas | 1.410 |
| ya juzgados | **397 (28 %)** |
| **sin juzgar (cuentan como no relevantes)** | **1.013** |

### 3.3 La unión de motores deja fuera el 77 % de lo que se encuentra

Sobre 20 consultas, unión del top-20 de tres motores (actual, semántico puro,
léxico puro):

| dato | valor |
|---|---|
| documentos distintos | 583 |
| nunca juzgados | **448 (77 %)** |

**Este es el riesgo directo para el fin:** un motor nuevo que encuentre un
documento relevante que el motor viejo no encontraba será **penalizado** por
encontrarlo, porque ese documento no está juzgado y cuenta como no relevante.

### 3.4 Duplicados casi idénticos inflan la métrica

El catálogo tiene **6.564 grupos** de títulos con prefijo común, que afectan a
**64.547 fichas (68,3 %)**. Ejemplos: 259 fichas que empiezan igual
(«distribució de la població total i de la població en risc de…»), 168, 161…

Dentro de los juicios: **176 pares de fichas relevantes casi idénticas en la
misma consulta**. Ocupan varios puestos del top-5 con contenido equivalente, así
que **suben el P@5 sin mejorar la experiencia del usuario**.

### 3.5 La potencia estadística no alcanza para el fin

| dato | valor |
|---|---|
| P@5 medio | 0,6043 |
| desviación | 0,2989 |
| error estándar (n=47) | 0,0436 |
| **intervalo de confianza 95 %** | **±0,0855** |
| **mejora mínima detectable** | **0,171** |
| consultas necesarias para detectar +0,05 | **~137** |

**Con 47 consultas, el GT solo detecta mejoras ≥0,17.** La mejora que se busca
con BGE-M3 es de ~0,05, y la del enriquecimiento fue 0,021: **ambas son
indetectables**, con cualquier criterio.

### 3.6 Dos consultas son literalmente títulos de datasets

`cult_001` y `dep_002`. Son consultas que copian el título, así que se resuelven
por coincidencia léxica exacta: no miden recuperación semántica.

---

## 4. Veredicto de adecuación para el fin

El fin es **comparar motores** y decidir si BGE-M3 mejora al MiniLM actual. La
pregunta es si este GT puede responderla.

| pregunta | respuesta |
|---|---|
| ¿Mide relevancia de verdad? | **Sí, con el juicio del LLM.** Con patrones, no. |
| ¿Distingue un motor bueno de uno malo? | **Sí, con nDCG sobre el juicio** (0,775 de rango) |
| ¿Detecta una mejora de +0,05? | **No:** necesita ~137 consultas, hay 47 |
| ¿Es justo con un motor distinto al actual? | **No:** 77 % de la unión sin juzgar |
| ¿Puede reutilizarse al migrar de modelo? | **Sí:** el juicio es independiente del encoder |

### Conclusión

**El GT es estructuralmente sólido y métricamente inadecuado.** Las consultas, el
balance por categoría, la calibración de dificultad y el juicio del LLM son
material válido. Lo que falla es:

1. **La métrica** — el criterio de patrón está roto (ordena al revés). Cambiarlo
   por nDCG sobre el juicio del LLM es obligatorio, no opcional.
2. **La profundidad del pool** — sin ampliarlo, el GT penaliza la mejora.
3. **El tamaño** — 47 consultas no tienen resolución para la pregunta que se
   quiere responder.

**No hay que tirar el GT.** Hay que cambiar la métrica, ampliar el pool y
multiplicar las consultas por tres.

---

## 5. Trabajo mínimo para que el GT sirva al fin

| paso | qué | coste |
|---|---|---|
| 1 | Cambiar la métrica a nDCG sobre el juicio del LLM | **1 tarde**, sin LLM |
| 2 | Juzgar los 1.013 sin juzgar del top-30 + unión de motores | ~1.100 pares, ~60-80 llamadas |
| 3 | Añadir BGE-M3 al pool antes de juzgar | depende de la migración |
| 4 | Ampliar de 47 a ~150 consultas | generación + juicio |
| 5 | Control de duplicados: agrupar fichas equivalentes y contarlas una vez | medible en SQL |

**El paso 1 es el de mayor rendimiento por esfuerzo:** cambia el GT de
«inservible para comparar» a «utilizable con reservas», sin coste de LLM.
