# Experimento A/B — ¿El LLM responde mejor con los datos?

Modelo: `deepseek-v4-flash:0731-cloud` · temp 0.2 · 10 preguntas

| # | Pregunta | A (metadatos) | B (metadatos+datos) | Columnas citadas A | B |
|---|---|---|---|---|---|
| 1 | paro registrado | 0/7 cols | 2/7 cols | — | Ańo, Valor |
| 2 | museos | 1/8 cols | 8/8 cols | Año | Año, Concepto, Tipo territorio |
| 3 | accidentes | 0/11 cols | 2/11 cols | — | Unnamed: 2, Unnamed: 9 |
| 4 | residuos | 0/13 cols | 0/13 cols | — | — |
| 5 | energía solar | 0/11 cols | 6/11 cols | — | CENTRO, Latitud, POTENCIA KWP |
| 6 | población | 0/5 cols | 4/5 cols | — | zona_basica_salud, casos_confirmados_P60mas_ultimos_14dias, tasa_incidencia_acumulada_P60mas_ultimos_14dias |
| 7 | bibliotecas | 0/12 cols | 12/12 cols | — | prbarc, prprsu, prcolp |
| 8 | pensiones | 0/8 cols | 0/8 cols | — | — |
| 9 | turismo | 0/22 cols | 0/22 cols | — | — |
| 10 | natalidad | 2/8 cols | 0/8 cols | Año, Valor | — |

## Respuestas completas

### 1. paro registrado
**Dataset**: Evolución  del porcentaje de paro registrado. Municipios
**Pregunta**: ¿Este dataset permite conocer la evolución mensual del paro por municipio? ¿Con qué granularidad temporal?

**A (metadatos)** (7.5s):


**B (metadatos+datos)** (3.4s):
No, este dataset **no permite conocer la evolución mensual** del paro por municipio. La única columna temporal es **`Ańo`** (ej. 2007, 2008), y la descripción indica que los datos corresponden al **paro registrado a 31 de marzo de cada año**. Por tanto, la granularidad temporal es **anual**, no mensual. Aunque la descripción menciona "último día del mes", el valor de muestra solo refleja un dato por año y municipio (ej. `Acebeda (La)` con `Valor` 1.75 en 2007). No existe ninguna columna como `Mes` o `Fecha` que permita desglosar por meses. Si necesitas evolución mensual, este dataset no es adecuado.

---

### 2. museos
**Dataset**: Visitantes de museos por titularidad
**Pregunta**: ¿Qué información tiene cada museo: horarios, tipo, dirección? ¿Podría filtrar por provincia?

**A (metadatos)** (2.7s):
El dataset **"Visitantes de museos por titularidad"** no contiene la información que buscas. Su contenido se limita a cifras de visitantes (probablemente columnas como `museo`, `año` y `numero_visitantes`), sin incluir campos como `horario`, `tipo` (más allá de la titularidad pública/privada) o `dirección`. Tampoco dispone de una columna explícita de `provincia`, aunque podrías inferirla a partir del nombre del museo (ej. "Museo Nacional de Antropología" está en Madrid), pero no es un dato estructurado. Por tanto, no podrás filtrar por provincia de forma fichear

**B (metadatos+datos)** (2.2s):
El dataset **no contiene información sobre horarios, tipo de museo ni dirección**, ya que sus columnas son: `Año`, `Concepto`, `Tipo territorio`, `Código territorio`, `Territorio`, `Valor`, `Unidad` y `Estado dato`.  
La columna `Concepto` solo incluye el nombre del museo (ej. "Visitantes del Museo Cerralbo"), pero no describe sus características.  
Tampoco es posible **filtrar por provincia**, porque la columna `Territorio` aparece vacía en los valores de muestra y `Tipo territorio` es siempre "Otros".  
Lo único que ofrece el fichero son **cifras de visitantes en miles** (columna `Valor`) por año y museo, como el ejemplo de 2.7 para el Museo Cerralbo en 1985.  
Por tanto, este dataset solo responde a preguntas sobre **evolución de visitantes**, no sobre datos descriptivos de los museos.

---

### 3. accidentes
**Dataset**: Accidentes de trabajo con baja acumulados en el periodo por gravedad y
**Pregunta**: ¿Permite saber cuántos accidentes con víctimas hubo por tipo de vía y año? ¿Qué columnas lo permiten?

**A (metadatos)** (6.4s):
No, este dataset no responde a tu pregunta. Se centra exclusivamente en **accidentes de trabajo con baja** en el País Vasco durante el año **2023**, clasificados por **gravedad** y **actividad económica (divisiones CNAE)**, no por tipo de vía. No incluye ninguna columna relativa a "tipo de vía" (como carretera, urbana, etc.) ni tampoco una columna de "año", ya que el dato es fijo para 2023. Las variables que encontrarás serán del estilo de "gravedad" (leve, grave, mortal) y "actividad" (códigos CNAE), pero no hay información sobre el lugar del accidente en términos de vía. Por tanto, no es posible obtener el desglose que buscas con estos datos.

**B (metadatos+datos)** (2.9s):
No, este dataset no permite responder a esa pregunta. Las columnas existentes (como "Unnamed: 2" a "Unnamed: 9") se refieren a la gravedad (Leve, Grave, Mortal) y al tipo de jornada (En Jornada Laboral, In Itinere), no al tipo de vía. Tamp

---

### 4. residuos
**Dataset**: Clasificación de la Lista Europea de Residuos (ISTAC: CL_LER)
**Pregunta**: ¿Puedo saber cuántas toneladas de residuos se recogieron por municipio y año? ¿Qué variables hay?

**A (metadatos)** (2.3s):
No, este dataset no puede responder a tu pregunta. Se trata de la **Clasificación de la Lista Europea de Residuos (CL_LER)**, que es un catálogo de códigos de residuos (de 2, 4 y 6 cifras) y sus descripciones, no un registro de cantidades recogidas. No contiene variables como toneladas, municipio ni año, ya que su estructura se limita a identificar tipos de residuos (por ejemplo, códigos de capítulo y subcapítulo). Para saber toneladas por municipio y año necesitarías un dataset de estadísticas de generación o recogida de residuos, que no es este. Por tanto, no dispongo de información sobre columnas de cantidad o territorio en este recurso.

**B (metadatos+datos)** (6.9s):


---

### 5. energía solar
**Dataset**: Generación de energía solar fotovoltaica en edificios y centros munici
**Pregunta**: ¿Qué variables incluye: potencia instalada, energía generada, número de instalaciones? ¿Desglose municipal?

**A (metadatos)** (6.4s):
No tengo acceso al contenido exacto del dataset, solo a sus metadatos, por lo que no puedo confirmar los nombres reales de las columnas ni sus valores de muestra. Basándome en la descripción, es muy probable que incluya variables como **potencia instalada** y **energía generada** por instalación, pero no puedo asegurarlo. Tampoco puedo confirmar si existe una columna específica para el **número de instalaciones** o si se agrega por edific

**B (metadatos+datos)** (4.6s):
El dataset incluye la columna **POTENCIA KWP** (potencia instalada, ej. 2,5 o 10) y **ENERGÍA PRODUCIDA KWh** (energía generada, ej. 251,1 o 1004,4). El número de instalaciones se puede contar a partir de la columna **CENTRO** (ej. "AULA DE LA NATURALEZA DEHESA DE LA VILLA"), aunque cada fila combina centro, año y mes. No existe una columna explícita de municipio, pero el dataset es del Ayuntamiento de Madrid (territorio geonames 3117735), por lo que no hay desglose municipal interno. Sí dispone de **Latitud**

---

### 6. población
**Dataset**: Covid 19 -TIA para población de 60 y más años de edad por Zonas Básica
**Pregunta**: ¿Tiene desglose por sexo y edad? ¿A nivel de municipio o provincia?

**A (metadatos)** (2.3s):
No, el dataset no tiene desglose por sexo; solo agrega la información para el grupo de edad de **60 y más años** en su conjunto. La unidad territorial no es municipio ni provincia, sino **Zonas Básicas de Salud (ZBS)**, definidas por el Decreto 52/2010 de la Comunidad de Madrid. Por tanto, los datos se publican a nivel de ZBS, que es una división sanitaria inferior al municipio. Las columnas principales que encontrarás son **casos confirmados** y **tasa de incidencia acumulada (TIA)** a 14 días, siempre referidas a ese grupo de edad. No se incluyen variables como sexo, edad desagregada (p. ej., 60-69, 70-79) ni códigos de municipio o provincia. Si necesitas ese nivel de detalle, este dataset no es suficiente.

**B (metadatos+datos)** (4.3s):
No, el dataset no tiene desglose por sexo ni por grupos de edad más allá de la población de 60 y más años. Las únicas columnas relacionadas son `casos_confirmados_P60mas_ultimos_14dias` y `tasa_incidencia_acumulada_P60mas_ultimos_14dias`, que agregan a todo ese grupo. Tampoco hay desglose por municipio o provincia: el nivel geográfico es la Zona Básica de Salud (columna `zona_basica_salud`), con un código en `codigo_geometria`. Aunque algunos nombres de zona coinciden con municipios (ej. "Algete", "Aranjuez"), no es un dato municipal oficial. Por tanto, solo podrás obtener valores agregados por ZBS para el conjunto de mayores de 60 años.

---

### 7. bibliotecas
**Dataset**: Bibliotecas públicas de Madrid. Histórico de préstamos
**Pregunta**: ¿Qué datos tiene cada biblioteca: dirección, horario, teléfono? ¿Puedo filtrar por comunidad autónoma?

**A (metadatos)** (1.7s):
No, este dataset no contiene dirección, horario ni teléfono de las bibliotecas. Se centra exclusivamente en datos de préstamos (ejemplares prestados) con información mensual, probablemente con columnas como `biblioteca`, `fecha` y `número de préstamos`. Tampoco permite filtrar por comunidad autónoma, ya que el ámbito territorial es únicamente la ciudad de Madrid (según el enlace a GeoNames). Para obtener esos datos de contacto, necesitarías consultar otro dataset, como el catálogo de equipamientos municipales.

**B (metadatos+datos)** (6.9s):
No, este dataset no contiene dirección, horario ni teléfono de las bibliotecas. Las columnas disponibles son códigos de préstamo (prbarc, prprsu, prcolp, prcocp, prlebi, prlesu, pradul, prfpre, prcocs) y datos bibliográficos (tititu, tiauto, tiisxn), pero ninguna incluye información de contacto o ubicación física. Tampoco existe una columna de comunidad autónoma; los códigos como "BP02" o "BPM" son identificadores internos de bibliotecas o secciones, no direcciones. Por tanto, no puedes filtrar por comunidad autónoma con estos datos. El dataset se centra exclusivamente en el histórico de préstamos de ejemplares, no en los datos administrativos de las bibliotecas. Si necesitas esa información, deberías buscar otro dataset específico de equipamientos o directorio de bibliotecas.

---

### 8. pensiones
**Dataset**: Pensiones contributivas en vigor del sistema de la Seguridad Social po
**Pregunta**: ¿Permite calcular la pensión media por régimen y provincia? ¿Qué periodos cubre?

**A (metadatos)** (7.6s):


**B (metadatos+datos)** (7.5s):


---

### 9. turismo
**Dataset**: Datos de turismo sobre casas rurales en la Comunitat Valenciana
**Pregunta**: ¿Puedo saber el número de viajeros o pernoctaciones por mes y provincia? ¿Qué columnas hay?

**A (metadatos)** (8.8s):


**B (metadatos+datos)** (6.9s):


---

### 10. natalidad
**Dataset**: Indicadores de natalidad y fecundidad
**Pregunta**: ¿Tiene desglose por provincia y año de la madre? ¿Permite calcular tasas si lo cruzo con población?

**A (metadatos)** (2.6s):
Según los metadatos, la descripción solo menciona tasas agregadas (tasa bruta de natalidad, tasa general de fecundidad e índice sintético), pero **no especifica desglose por provincia ni por edad/año de la madre**. No se indican nombres de columnas ni valores de muestra, por lo que no puedo confirmar si existe una variable geográfica o de edad materna. Para saber si permite calcular tasas cruzando con población, necesitaría conocer el formato y las variables reales del archivo, pero el campo "Formato" es **None**, lo que impide verificar su estructura. En resumen, **no hay información suficiente** en los metadatos para responder afirmativamente a ninguna de tus dos preguntas. Te recomiendo consultar el recurso publicado directamente o contactar al publicador (datos.gob.es) para obtener el detalle de columnas y cobertura territorial.

**B (metadatos+datos)** (7.6s):


---
