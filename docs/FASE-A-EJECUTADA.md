# Fase A ejecutada · métrica basada en el juicio

**Fecha:** 24-sep-2026
**Estado:** **ejecutada y verificada**
**Autorizado:** «Empieza el plan. Siempre podremos volver atrás»

---

## 1. Qué se ha hecho

Cuatro piezas nuevas, **ninguna modifica el funcionamiento del buscador**.

| fichero | qué es |
|---|---|
| `codigo/104_construir_etiquetas.py` | extrae los 470 juicios y los indexa por `dataset_id` |
| `entregables/gt_etiquetas.json` | **el índice**: 406 etiquetas (consulta, dataset) → nivel |
| `codigo/utils/gt_metrics.py` | métricas sobre el juicio: P@5, nDCG@10, MRR, cobertura |
| `codigo/105_evaluar_v2.py` | evaluador: ejecuta la API y aplica las métricas |
| `codigo/106_test_invariantes.py` | 12 invariantes matemáticos de las métricas |
| `codigo/107_acuerdo_jueces.py` | control de fiabilidad del juicio |
| `entregables/fase_a_baseline.json` | **la línea base** |

**La API de producción no se ha tocado.** Verificado: el servicio no importa
`ragas_metrics` ni el evaluador. Todo lo anterior sigue intacto.

---

## 2. El índice de etiquetas

| dato | valor |
|---|---|
| juicios leídos | 470 |
| anclados por `dataset_id` | **434 (92 %)** |
| sin anclar | 36 |
| fichas distintas etiquetadas | 393 |
| etiquetas en el índice | **406** |
| distribución | nivel 2 → 214 · nivel 0 → 192 |

Los **36 sin anclar quedan SIN ETIQUETA**, no como no relevantes. Es deliberado:
son casos donde el título del juicio no casa con ningún `dataset_id`, y
resolverlos por título sería ambiguo (el catálogo tiene 2.144 grupos de títulos
duplicados).

---

## 3. La línea base

Medición sobre las 47 consultas, con el criterio del juicio:

| sistema | P@5 | IC95 % | nDCG@10 | IC95 % | MRR | cobertura |
|---|---|---|---|---|---|---|
| **actual (0,7/0,3)** | **0,3574** | [0,264 · 0,451] | **0,5324** | [0,433 · 0,632] | 0,5591 | 57 % |
| semántico (1,0/0,0) | 0,3617 | [0,265 · 0,458] | 0,5441 | [0,443 · 0,645] | 0,5492 | 59 % |
| léxico (0,0/1,0) | 0,0979 | [0,046 · 0,150] | 0,0954 | [0,044 · 0,147] | 0,1479 | 9 % |

**Mejora mínima detectable: 0,0996** en nDCG@10 con 47 consultas.

### 3.1 Lectura de estos números

1. **El motor real funciona:** nDCG@10 de 0,53 frente a 0,095 del léxico puro.
   La parte semántica aporta, y mucho.

2. **La mezcla 0,7/0,3 es razonable pero no óptima:** el semántico puro da 0,5441
   frente a 0,5324. La diferencia (**0,012**) es **muy inferior** a la mejora
   mínima detectable (**0,0996**): **no se puede concluir** que uno sea mejor.
   Los intervalos se solapan ampliamente.

3. **La cobertura es del 57 %:** 4,3 de cada 10 fichas del top-10 no tienen
   juicio. La métrica es **utilizable pero no plenamente interpretable**, y el
   propio evaluador lo avisa en pantalla. Es la Fase B.

4. **Comparación con las cifras anteriores:** el P@5 baja de 0,6043 (patrón) a
   0,3574 (juicio). No es un empeoramiento: el criterio anterior marcaba como
   relevante el 41 % de lo que el juicio rechaza.

---

## 4. Verificación de la implementación

12 invariantes matemáticos sobre datos **sintéticos de control** (5 nivel-2, 3
nivel-1, 7 nivel-0):

| invariante | resultado |
|---|---|
| orden ideal → nDCG = 1,000 | **1,0000** |
| orden invertido → nDCG bajo | **0,1312** |
| orden aleatorio → intermedio | **0,5392** |
| P@5 con relevantes en cabeza | **1,0000** |
| P@5 con relevantes al final | **0,0000** |
| MRR con relevante primero | **1,0000** |
| MRR con relevante al final | **0,0909** |
| ganancia gradada (2,1,0) > (1,2,0) | **1,0000 > 0,8369** |
| monotonía: subir un relevante no baja la métrica | **0 violaciones** |
| fichas sin juicio → ganancia 0 | **0,0000** |
| cobertura = juzgados/total | **0,25 con 1 de 4** |

**Los 12 se cumplen.** La implementación es correcta.

### 4.1 Una corrección de método en el propio test

La primera pasada falló en «P@5 con relevantes al final». **El fallo estaba en el
test, no en la métrica:** usaba una consulta real (`empleo_001`) con 9 relevantes
y 1 no relevante, así que el «orden invertido» aún dejaba 4 relevantes en cabeza.
Se reescribió con datos sintéticos de composición conocida. Es la misma clase de
error detectada en la auditoría del plan: **sacar conclusiones de datos cuya
distribución no controlas.**

---

## 5. Control de fiabilidad del juicio existente

Antes de confiar en las métricas hay que saber si el juicio de junio es sólido:

| control | resultado |
|---|---|
| coherencia razón ↔ etiqueta (casos positivos) | **1 de 470 (0,2 %)** |
| coherencia razón ↔ etiqueta (casos negativos) | **7 de 470 (1,5 %)** |
| razones distintas / totales | 437 / 470 |
| **razones repetidas tipo plantilla** | **15** |
| razones vacías de contenido | **8** («Idem.», «Irrelevante.») |

**Veredicto: el juicio es sustancialmente fiable.** 470 etiquetas con un 0,2-1,5 %
de incoherencia interna. Las 8 razones vacías están todas en dos consultas
(`econ_002`: 5, `amb_002`: 2), así que el ruido está localizado, no repartido.

Las 12 «contradicciones» entre consultas (mismo título con etiquetas opuestas) son
**esperadas**: el juicio depende de la consulta. «Estadística de prestaciones por
desempleo» responde a `amb_001` («paro») y no a `empleo_002` («paro registrado por
comunidades»). Eso es criterio, no ruido.

---

## 6. Cómo volver atrás

Nada de lo anterior es destructivo. **Tres vías:**

**1. No usar el evaluador nuevo.** El original sigue en su sitio:
```bash
# el de siempre, sin cambios
python eval_ragas_core.py --mode basic --output ../entregables/ragas_scores_basic.json
```

**2. Descartar el trabajo de la Fase A** — los ficheros son nuevos, ninguno
sobrescribe algo existente:
```bash
cd ~/datos/PFM/Datatrust
git status --short -- 09_Sprint7_RAGAS/     # ver qué hay de nuevo
rm 09_Sprint7_RAGAS/entregables/gt_etiquetas.json
rm 09_Sprint7_RAGAS/entregables/fase_a_baseline.json
# y los scripts 104-107 si se quiere
```

**3. Volver al estado del último commit:**
```bash
git log -1 --format=%h -- 09_Sprint7_RAGAS/   # b3f9096
git checkout b3f9096 -- 09_Sprint7_RAGAS/
```

**El directorio estaba limpio antes de empezar** (verificado con `git status`):
no había cambios pendientes, así que la reversión es exacta.

Y lo más importante: **el producto no ha cambiado**. La API, los embeddings, el
catálogo y el frontend están exactamente igual. Lo único nuevo es una forma
distinta de **medir**, que convive con la anterior.

---

## 7. Puerta G1: decisión pendiente

Formulada según la corrección de la auditoría del plan:

> ¿Se adopta esta línea base como la cifra oficial del TFM, publicando
> **nDCG@10 = 0,53 con IC95 % [0,43 · 0,63]** y declarando que el **43 % del pool
> no está juzgado**, en lugar del P@5 = 0,6043 calculado con patrones?

**Argumentos a favor:**
- el criterio nuevo usa los 470 juicios razonados que ya existían, no coincidencias de vocabulario
- la implementación está verificada con 12 invariantes
- el juicio de origen es fiable (0,2-1,5 % de incoherencia)
- se publica con intervalo, no con un número con falsa precisión

**Argumentos en contra:**
- el número es más bajo y menos vistoso
- la cobertura del 57 % obliga a declarar la limitación
- exige explicar por qué baja

**Mi recomendación:** adoptarlo. Un 0,53 defendible con su intervalo vale más que
un 0,60 que premia coincidencias de vocabulario y que, medido contra el propio
juicio del GT, tiene una precisión de 0,697.

---

## 8. Estado y siguiente paso

**Fase A: completada.** Quedan dos controles de la Fase A sin ejecutar, ambos
opcionales porque el juicio ha resultado fiable:

- **doble juicio ciego** sobre 100 pares con un juez independiente
  (`108_doble_juicio.py`), para medir el acuerdo entre jueces. Sería lo riguroso.
- **aplicar el `no_debe_contener`** en las métricas. Hoy el campo existe en el GT
  y no se ejecuta.

**Siguiente fase prevista:** Fase B (completar el pool), que cierra el 43 % sin
juzgar y con ello el intervalo de la línea base.

Antes de seguir conviene el visto bueno en **G1**, porque la Fase B depende de que
se acepte este criterio de medición.
