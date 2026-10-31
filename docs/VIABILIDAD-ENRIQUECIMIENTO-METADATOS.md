# Evaluación de viabilidad · Reconstruir metadatos en la ingesta

**Fecha:** 28-sep-2026 · **Estado:** evaluación, sin implementar
**Propuesta evaluada:** reescribir/aumentar metadatos (título más descriptivo,
descripción ampliada, inferir formato del enlace) en la fase de ingesta.

---

## 1. Veredicto corto

**Viable, pero con techo bajo y una parte mal dirigida.** Y no es una hipótesis:
**ya se probó**, con controles, el 24-sep-2026 (`~/datos/informes/
ENRIQUECIMIENTO-LLM-DESCRIPCIONES-RESULTADO-2026-09-24.md`).

- La reescritura de descripciones **funciona y se mide**: +0,0245 de similitud
  (t = +2,53), superando cuatro controles, incluido el decisivo de meter texto
  ajeno de la misma longitud (−0,022).
- **Pero no mejora el nDCG/P@5, y no puede**: acerca relevantes y no relevantes
  *por igual*. El informe lo dice con precisión: **mejora el orden, no la
  discriminación**. La primera ficha relevante sube 5,9 puestos, y el top-5 no
  se mueve.
- Lo que **sí** falta no es calidad de metadatos, es que **tres de cada cuatro
  fichas tienen los metadatos estructurados truncados fuera del vector**
  (`max_seq_length = 128`).

**Recomendación:** no abrir esta vía como línea principal. Hay una acción más
barata y de más efecto (reordenar el texto vectorizado), y la solución natural
al truncamiento es la Fase E que ya está en el plan.

---

## 2. Estado real de los metadatos (medido hoy)

Sobre 94.461 fichas:

| Metadato | Cobertura | Lectura |
|---|---|---|
| `title` | 94.461 · ninguno vacío | longitud media **93 caracteres** |
| `description` | 94.461 · ninguno vacío | longitud media **275 caracteres** |
| `keywords` | **84.463** (89,4 %) | el mejor metadato libre |
| `theme_label` | 94.460 | |
| `territory_label` | **37.842** (40 %) | |
| `format` (columna) | 83.288 (88 %) | **32.947 vacías** |
| `license` | 1.240 (1,3 %) | |
| `frequency` | 32.457 (34 %) | |
| `temporal_coverage` | 15.056 (16 %) | |
| **`download_url`** | **0** | vacío en el catálogo entero |
| **`tags`** | **0** | vacío en el catálogo entero |
| `dataset_formats` | 61.514 fichas con algún formato | 168.787 filas |

### 2.1 El problema no es la brevedad: es la duplicación

- **20.959 descripciones son literalmente iguales al título.**
- **24.936 empiezan por el título.**
- 17.806 descripciones tienen **menos de 80 caracteres** (18,8 %).
- 34.704 tienen menos de 200 (36,7 %).

Ejemplos reales del caso degenerado:

```
Título:      "Porcentaje de contratos 2020 - Ayuntamiento de Málaga"
Descripción: "Porcentaje de contratos 2020 - Ayuntamiento de Málaga"

Título:      "Consumo de agua"
Descripción: "Total de agua suministrada en baja para su consumo en el municipio."

Título:      "Previsión de voto para Elecciones Generales"
Descripción: "Datos en formato SAV (SPSS, PSPP) y CSV."     <- ¡la descripción es el FORMATO!
```

**Consecuencia de diseño importante:** ampliar el título en esos 21.000 casos
sería *duplicar texto que ya está duplicado*. El diagnóstico correcto no es
«faltan palabras», es **«falta información distinta»**.

---

## 3. Viabilidad pieza por pieza

### 3.1 Inferir el formato del enlace — **poco viable como se plantea**

La idea (deducir CSV de la URL) no se sostiene: las URLs del catálogo son
**páginas de catálogo, no enlaces a ficheros**.

Medido sobre los 32.947 sin formato declarado y con URL:

- **0** terminan en `.csv`, `.xlsx`, `.json`, `.xml`, `.pdf` o `.zip`
- **32.873** no tienen ninguna extensión reconocible (el resto son parámetros)
- Solo **74** serían resolubles por extensión

**Pero hay una vía mejor y sí viable: re-parsear el origen.**
`raw_metadata` conserva el campo `distribution` en **94.459 de 94.461 fichas**,
y **4.502 traen `format` explícito** que no llegó a la columna. Cruzando:
**10.977 fichas sin formato declarado sí tienen `distribution` en el origen**,
recuperable sin salir a la red.

Ejemplo del origen (las distribuciones son URLs a *resources*):

```json
"distribution": [
  "https://datos.gob.es/catalogo/<id>/resource/167f58af-63a7-4ce0-bc99-1d33b3b18cf6",
  "https://datos.gob.es/catalogo/<id>/resource/21509f4f-f9c2-4323-8de2-699e91ae8674"
]
```

⚠️ El formato **no está en ese campo**, solo el enlace al recurso. Para sacarlo
hay que **visitar la página del recurso** (una petición por distribución, decenas
de miles). Eso convierte la tarea en un scraping con ritmo limitado, no en un
cálculo local.

**Matiz que cambia la prioridad:** el formato **no entra en el texto vectorizado**.
Enriquecerlo **no mejora la recuperación**; mejora los **filtros del frontend**.
Es valor de producto, no de motor.

### 3.2 Ampliar el título — **no recomendado**

- En el 22 % de los casos el título y la descripción son el mismo texto: ampliar
  el título ahí es rellenar con redundancia.
- Reescribir 94.461 títulos con LLM sobre registros públicos introduce riesgo de
  **alterar el significado de un dato oficial** (un título es un identificador,
  no un campo descriptivo).
- El efecto medible esperado es el mismo que el de las descripciones: mejora el
  orden, no la discriminación.

### 3.3 Ampliar la descripción con LLM — **ya probado; efecto real pero insuficiente**

Resultado del experimento (39 queries, 11.215 pares, mismo encoder):

| variante | similitud | delta |
|---|---|---|
| base (descripción vieja) | 0,3042 | — |
| **nueva (LLM)** | **0,3117** | **+0,0074** |
| longitud (vieja repetida) | 0,2547 | −0,0495 |
| título repetido ×3 | 0,2624 | −0,0418 |
| ajena (misma longitud) | 0,2820 | −0,0223 |

La ganancia viene del **contenido**, no del volumen de texto. **Pero**:

- El efecto máximo cabe en **11 huecos de 235** del top-5 (4,7 %): no hay dónde
  manifestarse.
- Mejora los casi duplicados: en 96 grupos con el mismo título y distinto año, la
  similitud mutua baja de 0,9618 a 0,8934 y los pares indistinguibles (>0,95)
  caen de **2.882 a 859**. Ese sí es un beneficio real y de producto.

### 3.4 Los dos metadatos vacíos — **trabajo pendiente real, pero fuera del motor**

`download_url` y `tags` están **vacíos en las 94.461 fichas**. Son mejoras
evidentes del catálogo (permitirían descargar el dato y navegar por etiquetas),
pero **no entran en el vector**, así que no afectan a la comparación de motores.

---

## 4. El obstáculo que la propuesta no tiene en cuenta

**Solo lo que está en el texto vectorizado puede afectar a la recuperación.** El
texto es `título + descripción + keywords + theme_label + territory_label`, y el
modelo **trunca a 128 tokens** (≈500 caracteres).

Medido: **3.063 de 4.015 fichas (76 %)** tienen el texto por encima de la ventana.
Es decir, en tres de cada cuatro fichas **`keywords`, `theme_label` y
`territory_label` nunca llegan al vector**.

De ahí se deduce lo que tiene efecto y lo que no:

| acción | ¿llega al vector? | ¿puede mejorar la recuperación? |
|---|---|---|
| ampliar descripción | sí | sí, pero el efecto no discrimina |
| ampliar título | sí | sí, con el mismo límite |
| inferir formato | **no** | **no** |
| rellenar `download_url`, `tags` | **no** | **no** |
| **reordenar el texto** | **sí** | **sí, y es gratis** |
| **subir la ventana (Fase E)** | **sí** | **sí** |

---

## 5. Qué haría yo, por orden

1. **Reordenar el texto vectorizado** (coste ~0, sin LLM). Si el truncamiento
   corta, que corte la *cola de la descripción* y no los metadatos estructurados,
   que son justamente la señal que distingue una ficha de otra. **Medir antes y
   después.** Es la acción de mejor relación efecto/coste de toda la lista.
2. **Fase E (BGE-M3)**: ventana de 8.194 tokens → el truncamiento desaparece por
   construcción. Es la solución *estructural*, y ya está en el plan.
3. **Enriquecimiento de descripciones: solo si (1) y (2) no bastan,** y limitado
   a las ~21.000 fichas degeneradas (donde el texto es el título repetido). En el
   resto, el experimento demuestra que el efecto no se ve.
4. **Formato, `download_url`, `tags`: como línea de producto**, no de motor. Y el
   formato por la vía de re-parsear `raw_metadata` (10.977 recuperables sin red),
   no por la extensión de la URL (74).

**Cuándo esta vía pasaría a ser la principal:** si la Fase F concluye que BGE-M3
**no** mejora lo suficiente. Entonces la calidad de los metadatos sería la
siguiente palanca — pero conviene saber que su techo medido es +0,0074 de
similitud, no una mejora de décimas en nDCG.

---

## 6. Lo que sostiene esta evaluación

- **Medición propia, hoy:** cobertura y longitudes de todos los metadatos sobre
  las 94.461 fichas; 20.959 descripciones idénticas al título; 0 URLs con
  extensión resoluble; 10.977 recuperables desde `raw_metadata`.
- **Experimento ya hecho (24-sep):** 11.215 pares, 4 controles, t = +2,53.
- **Hallazgo del truncamiento:** 76 % de las fichas con metadatos fuera del vector.
- Plan previo del proyecto: `docs/PLAN_ENRIQUECIMIENTO_METADATOS.md` (246 líneas).

**No se ha modificado nada del proyecto para escribir esta evaluación.**
