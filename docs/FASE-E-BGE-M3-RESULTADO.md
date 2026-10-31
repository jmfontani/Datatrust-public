# FASE E — BGE-M3 frente a MiniLM: resultado y dos defectos de instrumento

Fecha: 2026-09-29
Estado: **cerrada**. Veredicto: **BGE-M3 es mejor, y la diferencia es grande.**

---

## 1. Resumen en una frase

Con un instrumento que por fin mide a los dos motores con las mismas
oportunidades, BGE-M3 obtiene nDCG@10 **0,6157** frente a **0,3414** de MiniLM
(diferencia pareada **+0,2743**, IC [+0,2284 · +0,3202]), muy por encima del
umbral de mejora detectable (0,0459).

El resultado anterior (+0,0118, «no concluyente») **no era un resultado**: era
un artefacto de dos defectos del instrumento. Se documentan abajo porque el
diagnóstico vale más que la cifra.

---

## 2. Defecto 1 — la cobertura asimétrica (el grave)

Los 6.114 juicios existentes se construyeron con el **motor actual** y sus
variantes (semántico, léxico). BGE-M3 **nunca participó** en la construcción del
pool. Consecuencia medida:

| motor | cobertura sobre los juicios existentes |
|---|---|
| MiniLM | 71-85 % |
| BGE-M3 | **34 %** |

Solapamiento de los top-10 entre ambos: **~1 %** (el azar sería 0,001 %).

Cuando un motor devuelve una ficha que nunca se juzgó, el nDCG la puntúa como 0.
Eso **no mide que el motor falle**: mide que al juez no se le preguntó por esa
ficha. BGE-M3 aparecía peor de lo que es, y el sesgo entero era en su contra.

**Corrección:** pool conjunto — la unión del top-20 de los dos motores.
Resultado: cobertura simétrica **99,5 % / 99,9 %** y 4.539 juicios nuevos
(la unión aportó **1.137 fichas de nivel 2** que nunca se habían juzgado: casi
duplica el nivel 2 disponible).

**Lección general:** *antes de comparar dos motores, medir la cobertura de
juicios de cada uno*. Si son asimétricas, el nDCG mide la historia del pool, no
la calidad del motor. Un pool construido con un solo motor no puede medir a otro.

## 3. Defecto 2 — el confound de texto

La primera comparación enfrentó:

- MiniLM → columna `embedding`, generada desde el `embedding_text` de la limpieza
- BGE-M3 → texto reconstruido por el script (`texto()` en `142`)

Es decir, se cambiaron **dos cosas a la vez**: modelo y texto. Cualquier
diferencia mezclaba las dos. El texto reconstruido es además una aproximación
(reproduce el vector guardado a coseno 0,923, no a 1,0).

**Corrección:** recálculo de MiniLM sobre **exactamente el mismo texto** que usó
BGE-M3 → columna paralela `embedding_minilm_aprox vector(384)` (20,9 min, 75/s).
Así la comparación modelo-contra-modelo tiene el texto **constante** y la única
variable es el modelo. La columna `embedding` original no se toca.

Efecto del confound: pequeño pero real → MiniLM 0,3539 (texto de la limpieza) vs
0,3497 (mismo texto que BGE).

## 4. Resultado final (GT v5, 10.653 juicios, 214 consultas)

### CONTROL DE INSTRUMENTO (antes de interpretar)

```
minilm : cobertura 99.5 % (2130 juzgados, 10 SIN juzgar)
bge    : cobertura 99.9 % (2137 juzgados,  3 SIN juzgar)
```

Cobertura simétrica → la comparación es interpretable.

### MÉTRICAS (mismo texto, mismo GT, mismas consultas, mismo top_k)

| motor | nDCG@10 | IC95 | P@5 | MRR | cobertura |
|---|---|---|---|---|---|
| MiniLM (candidato retirado) | 0,3414 | [0,2980 · 0,3848] | 0,2822 | 0,4022 | 99,5 % |
| **BGE-M3** | **0,6157** | [0,5699 · 0,6615] | **0,4813** | **0,6490** | 99,9 % |

### COMPARACIÓN PAREADA

```
BGE-M3 - MiniLM : +0.2743  IC95 [+0.2284 · +0.3202]
mejora minima detectable (n=214): 0.0459
VEREDICTO: BGE-M3 ES MEJOR (la diferencia supera lo detectable)

consultas donde BGE-M3 gana : 146
consultas donde empata      :  41
consultas donde MiniLM gana :  27
```

El reparto 146/27 no es una moneda al aire: es un motor ganando de forma
consistente. El contraste con el reparto anterior (80/74/60) es la prueba de que
aquel empate era un artefacto del instrumento.

**Comprobación de sanidad:** fichas de nivel 2 en los top-10 → MiniLM 504,
BGE-M3 934 (**1,85×**).

### Verificación independiente

La fórmula de nDCG se reimplementó desde cero, sin usar `utils/gt_metrics.py`,
sobre el JSON guardado. Resultado idéntico al cuarto decimal:
0,3414 / 0,6157, pareada +0,2743. No es un artefacto del evaluador.

---

## 5. Coste real de la Fase E (y el error de estimación del plan)

El plan estimaba **45 minutos**. La realidad: **4,75 h** para BGE-M3 + 21 min
para el control de MiniLM.

El error venía de medir con textos de prueba en vez del catálogo real. Longitudes
reales: media **136 tokens**, mediana 100, p90 203, **máximo 1.135** (y hasta
156.973 caracteres en el campo crudo).

| vía | velocidad medida | catálogo |
|---|---|---|
| sentence-transformers, textos de prueba | 46,7/s | 34 min (irreal) |
| sentence-transformers, textos reales | 3,3-7,6/s | 3,5-8 h |
| ollama con GPU ROCm, textos reales | 3,5-5,5/s | **4,75 h** |

Se eligió **ventana 1024** (cubre el **99 %** de las fichas sin truncar; la 128
cubriría solo el 65 %, heredando la limitación del modelo viejo y anulando el
argumento de migrar; la 2048 cuesta 3 h extra para el 1 % restante).

Equivalencia verificada antes de usar la GPU: ollama vs sentence-transformers
→ **coseno 0,999902** (mismo modelo).

---

## 6. Qué NO dice este resultado

1. **No es el número del buscador en producción.** Esto es comparación
   *semántica pura* (vector contra vector). El sistema en producción es
   **híbrido** (0,7 semántico + 0,3 léxico) y su nDCG con el motor actual es
   0,4854. Migrar el modelo dentro del híbrido es otra medición, todavía no
   hecha; el número comparable sería *híbrido+MiniLM* frente a *híbrido+BGE-M3*.
2. **No se ha tocado producción.** BGE-M3 vive en la columna paralela
   `embedding_bge vector(1024)`. `embedding` (384) está intacta y el buscador
   sirve con normalidad. La vuelta atrás es `DROP COLUMN`.
3. La ventaja medida es sobre **este** catálogo y **estas** 214 consultas.
4. MiniLM aquí aparece como *semántico puro* (0,3414), no como el sistema
   híbrido (0,4854). No comparar esas dos cifras entre sí: son objetos distintos.

---

## 7. Decisiones de método registradas

1. **Columna paralela, nunca `ALTER` de la existente.** Permite medir sin
   desplegar, y la reversión es un `DROP COLUMN`.
2. **Mismo texto para los dos motores** al comparar modelos. Cambiar texto y
   modelo a la vez invalida la comparación.
3. **Ventana nativa explícita** (`num_ctx`), no el valor por defecto del
   servidor: un ajuste oculto es justo lo que invalida una comparación.
4. **Reanudable** vía `WHERE ... IS NULL` y checkpoint cada 10 consultas.
5. **Consultar la cobertura antes de interpretar cualquier nDCG.** Si los
   motores no tienen el mismo porcentaje de resultados juzgados, la comparación
   no es válida por construcción.
6. **Verificar la equivalencia de dos implementaciones** del mismo modelo
   (coseno ≥ 0,9999) antes de sustituir una por otra aunque sea «más rápida».

---

## 8. Artefactos

**Scripts** (`09_Sprint7_RAGAS/codigo/`):
- `141_poblar_embeddings_bge.py` — primera versión (CPU), ventana configurable
- `142_poblar_bge_gpu.py` — **usado**: BGE-M3 vía ollama, columna paralela, reanudable
- `143_comparar_motores.py` — comparación con control de instrumento; `--col-minilm`, `--etiquetas`
- `144_bge_mismo_texto.py` — MiniLM sobre el texto constante (elimina el confound)
- `145_construir_pool_conjunto.py` — pool = unión del top-20 de ambos motores

**Entregables** (`09_Sprint7_RAGAS/entregables/`):
- `gt_etiquetas_v5.json` — **10.653** juicios (v4 6.114 + 4.539 del pool conjunto)
- `pool_conjunto.json` — 4.551 pares a juzgar (214/214 consultas)
- `fase_e_FINAL_v5.json` — **resultado definitivo** (texto constante, cobertura simétrica)
- `fase_e_MISMO_TEXTO.json` — control del confound (GT v4)
- `fase_e_BGE_vs_MiniLM.json` — primera medición, **no válida** (cobertura asimétrica)

**Columnas nuevas** (paralelas, producción intacta):
- `embedding_bge vector(1024)` — 94.461/94.461
- `embedding_minilm_aprox vector(384)` — 94.461/94.461
- `embedding vector(384)` — intacta

**Copia de seguridad previa:** `datasets_emb_backup_20260925` (94.461 filas).
