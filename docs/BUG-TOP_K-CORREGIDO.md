# Bug de `top_k` · corregido y verificado

**Fecha:** 25-sep-2026
**Estado:** **CORREGIDO Y VERIFICADO** en el motor de producción.
**Autorizado por:** «Corrige bug y continúa».

---

## 1. Qué se ha cambiado

Un solo fichero: `08_Sprint6_LLM_Mejora/codigo/api/main_v2_final_v07.py`
(**+76 líneas, −17**). Ningún otro componente tocado.

| qué | antes | ahora |
|---|---|---|
| escala del score léxico | `r['rank'] / max(rank del conjunto)` | `r['rank'] / (r['rank'] + 0.2)` |
| cuándo se aplicaba | solo si `max_rank > 1.0` | siempre |
| recorte interno de cada motor | `LIMIT top_k * 3` | `LIMIT max(150, top_k * 3)` |
| recorte visible | `top_k` | `top_k` (sin cambio) |

Las tres piezas están en `normalizar_rank_lexico()` y en las dos constantes
`LEXICAL_RANK_K = 0.2` y `DEFAULT_INTERNAL_LIMIT = 150`, con el comentario que
explica el porqué.

---

## 2. De dónde sale el 0,2 (no es un número elegido a ojo)

Se midió la distribución real de `ts_rank_cd` sobre las 47 consultas antes de
tocar nada (script `116_medir_ts_rank.py`):

| estadístico | mediana entre consultas |
|---|---|
| máximo | **0,7395** |
| p90 | 0,3391 |
| mediana | 0,0536 |

**El máximo va de 0,0008 a 13,40 según la consulta** — un factor de 16.000. Eso
es la raíz del bug: el divisor no era una magnitud, era un accidente de cada
consulta.

Con `k = 0,2`: el máximo típico queda en **0,79** y la mediana en **0,21**. Es
decir, se conserva la escala relativa que el motor ya tenía, sin heredar su
dependencia del corte. Elegir `k` a ojo habría anulado el peso léxico (0,3) sin
que nada lo delatara.

### 2.1 Un defecto añadido que salió al medir

La normalización estaba guardada tras `if max_rank > 1.0`. Como el máximo de
`ts_rank_cd` **suele quedarse por debajo de 1** (mediana 0,74), la normalización
se aplicaba **solo a algunas consultas**. El comportamiento era inconsistente por
consulta, no solo por `top_k`. Eso explica por qué en las muestras anteriores
unas consultas tenían los cuatro primeros resultados idénticos y otras no.

---

## 3. Verificación: el test de aceptación

Definido en `BUG-RANKING-DEPENDE-DE-TOP_K.md` §5.1: para cada consulta,
`ranking(k)[:5]` debe ser igual para todo `k`.

| | antes del arreglo | después |
|---|---|---|
| el **primer** resultado cambia según `top_k` | 9/47 (19 %) | **0/47** |
| el **top-5** cambia según `top_k` | 21/47 (45 %) | **0/47** |
| el top-5 no está contenido en el top-10 | 1/47 | **0/47** |

Y el score ya no se mueve: `empleo_001` da **0,6742** con `top_k` 5, 10, 20 y 30
(antes 0,5033 con 5 y 0,7019 con 10).

**El test pasa al 100 %.** Es la primera vez que el motor tiene un orden estable.

---

## 4. Efecto sobre las métricas

La línea base cambia, y la dirección del cambio no era predecible:

Medición final, con la cobertura ya cerrada al 100 %:

| sistema | nDCG@10 antes | nDCG@10 después | efecto | cobertura |
|---|---|---|---|---|
| **actual (0,7/0,3)** | 0,6083 | **0,6365** | **+0,0282** | **100 %** |
| semántico puro | 0,5926 | 0,5834 | −0,0092 | 100 % |
| léxico puro | 0,4095 | 0,4069 | −0,0026 | 74 % |

IC95 % del híbrido: **[0,554 · 0,719]**.

### 4.1 Por qué el híbrido sube y los puros no

El arreglo **no mejora la recuperación de ningún motor**: cambia la *escala* en
que los dos motores se combinan. El híbrido sube porque estaba mezclando dos
magnitudes incomparables:

- la similitud coseno siempre estuvo bien escalada ([0,1]);
- el score léxico estaba escalado de forma arbitraria **por consulta**.

Al fijar la escala léxica con una función del score, el peso 0,3 pasa a
significar lo mismo en todas las consultas. El híbrido es el único que usa los
dos componentes, así que es el único que se beneficia. Los puros no cambian
porque su escala interna no se combina con nada.

### 4.2 Consecuencia sobre el orden de los sistemas

Con el motor ya estable, **el híbrido gana por 0,0531** sobre el semántico puro
(0,6365 vs 0,5834). Antes del arreglo la diferencia era 0,0157, y con el pool
incompleto la conclusión estaba *invertida*. La mejora mínima detectable es
**0,0821**, así que el margen (0,0531) sigue sin superarla: la afirmación honesta
es que **el híbrido no es demostrablemente peor y es la opción por defecto
razonable** — pero la brecha se ha triplicado y ahora apunta en un sentido claro.

---

## 5. Cierre del hueco de cobertura

Al cambiar el orden aparecieron fichas en el top-10 que nunca entraron al pool.
Se midió y se cerró (scripts `117` y `118`):

| configuración | cobertura tras el arreglo | pendientes |
|---|---|---|
| actual | **100 %** | 0 |
| semántico | 98,7 % | 6 pares |
| léxico | **100 %** | 0 |

Los **11 pares** (4 consultas: `medio_004` 6, `dep_003` 3, `edu_001` 1,
`amb_003` 1) se juzgaron con **el prompt canónico**, el mismo de la Fase B —
mezclar redacciones rompería la comparabilidad. Resultado: 7 nivel 0, 4 nivel 2,
sin fallos.

**Etiquetas totales: 1.424** (406 de junio + 1.007 de la Fase B + 11 post-arreglo).
Distribución: 801 nivel 0 · 225 nivel 1 · 398 nivel 2.

Cobertura final del pool: **100 %** en el híbrido y en el semántico, 74 % en el
léxico (sus 12 consultas sin resultados son un límite del motor léxico, no del
juicio).

---

## 6. Cómo volver atrás

**La imagen anterior está etiquetada y el fichero original guardado:**

```bash
# opción 1: volver a la imagen previa (10,1 GB, sin el arreglo)
cd ~/datos/PFM/Datatrust/07_Sprint5_Integracion/codigo/docker
docker tag docker-api:pre-bugfix-2026-09-25 docker-api:latest
docker compose up -d --force-recreate api

# opción 2: volver al fichero original y reconstruir
cp ~/ssd/experimentos/enriquecimiento/backup/main_v2_final_v07.py.PRE-ARREGLO \
   08_Sprint6_LLM_Mejora/codigo/api/main_v2_final_v07.py
docker compose build api && docker compose up -d --force-recreate api
```

El original está guardado con sha256 `a2fa2a36…` (verificado idéntico al que
estaba en el contenedor antes de tocar nada). Etiquetas de imagen disponibles:
`docker-api:pre-pinning-2026-09-24`, `docker-api:pre-bugfix-2026-09-25`.

**Y el ground truth no se ve afectado en absoluto**: sus etiquetas son pares
`(consulta, dataset_id)`, independientes de cualquier orden. Volver atrás en el
motor no invalida una sola etiqueta.

---

## 7. Lo que queda pendiente

- **Fase C** (ampliar consultas): con 47 consultas la mejora detectable es
  **0,0805**; para detectar +0,05 hacen falta ~213.
- **Fase D** (recalcular los 94.461 embeddings): ahora **desbloqueada**, era
  requisito tener el ranking estable. Es el siguiente paso natural y cuesta
  ~9 minutos.
- **Re-medir con el motor arreglado** las cifras que se citen en el TFM: las
  anteriores a esta corrección mezclan el bug con la calidad del motor.
