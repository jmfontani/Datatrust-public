# Manual de Uso del Buscador Semántico de Datasets

## Tabla de contenidos

1. [Introducción](#introducción)
2. [Acceso y modos](#acceso-y-modos)
3. [Frontend Básico (Modo Público)](#frontend-básico-modo-público)
   - [Barra de búsqueda](#barra-de-búsqueda)
   - [Categorías](#categorías)
   - [Filtros desplegables](#filtros-desplegables)
   - [Resultados](#resultados)
   - [Chat sobre un dataset](#chat-sobre-un-dataset)
4. [Frontend Avanzado (Modo Demostrador)](#frontend-avanzado-modo-demostrador)
   - [Barra de búsqueda](#barra-de-búsqueda-1)
   - [Configuración de búsqueda](#configuración-de-búsqueda)
   - [Filtros facetados](#filtros-facetados)
   - [Resultados](#resultados-1)
5. [Diferencias entre modos](#diferencias-entre-modos)
6. [Solución de problemas](#solución-de-problemas)

---

## Introducción

El Buscador Semántico de Datasets es una aplicación web que permite buscar conjuntos de datos públicos del portal **datos.gob.es** usando búsqueda híbrida (semántica + léxica). Combina la comprensión del significado de las palabras con la coincidencia exacta de términos para ofrecer resultados relevantes.

La aplicación dispone de dos interfaces:

- **Frontend Básico**: interfaz sencilla y visual, pensada para usuarios finales.
- **Frontend Avanzado**: interfaz técnica con controles detallados, pensada para demostración y análisis.

---

## Acceso y modos

La aplicación se sirve en un único endpoint:

| Modo | URL | Descripción |
|---|---|---|
| Básico | `http://<host>:8501/` | Interfaz pública por defecto |
| Avanzado | `http://<host>:8501/?mode=advanced` | Modo demostrador técnico |

Se puede cambiar entre modos con los enlaces de la esquina superior derecha:

- En el modo básico: enlace **⚙️ Modo Avanzado**
- En el modo avanzado: enlace **🏠 Volver a modo público**

---

## Frontend Básico (Modo Público)

Interfaz limpia y visual diseñada para usuarios finales. Prioriza la facilidad de uso sobre el control técnico.

### Barra de búsqueda

- Campo de texto grande con placeholder *"¿Qué datos buscas? Ej: educación Madrid, paro juvenil..."*
- **Pulsar Enter** o hacer clic en **🔍 Buscar** para ejecutar la búsqueda.
- Selector de número de resultados: **10 / 25 / 50** (por defecto 10).
- La consulta escrita se mantiene en la barra aunque se apliquen filtros o se re-ejecuten búsquedas.

### Categorías

Debajo de la barra de búsqueda hay una fila de botones de categorías:

| Botón | Filtro que aplica |
|---|---|
| 📊 Empleo | `tema = Empleo` |
| 🏫 Educación | `tema = Educación` |
| 🌍 Medio Ambiente | `tema = Medio Ambiente` |
| 🏥 Sanidad | `tema = Sanidad` |
| 🚗 Transporte | `tema = Transporte` |
| 💰 Economía | `tema = Economía` |
| 🏛️ Administración | `tema = Administración` |
| 👥 Demografía | `tema = Demografía` |

**Comportamiento tipo toggle:**

- **Un toque** → activa el filtro de categoría. El botón se resalta en **azul oscuro** con sombra. La búsqueda se ejecuta automáticamente mostrando los datasets de esa categoría.
- **Otro toque** → desactiva el filtro. El botón vuelve a blanco con borde gris.
- Si hay una búsqueda de texto activa, los resultados se filtran por la categoría seleccionada manteniendo la consulta.
- Solo puede haber una categoría activa a la vez.

### Filtros desplegables

Dos desplegables bajo la sección de categorías:

- **📍 Territorio**: filtra por comunidad autónoma, provincia o municipio. Los valores se limpian automáticamente (sin duplicados ni entradas inválidas).
- **🏷️ Categoría**: filtra por tema. Está sincronizado con los botones de categoría: si pulsas "Educación", el desplegable muestra "Educación" seleccionado, y viceversa.

**Comportamiento:**

- Al seleccionar un valor en cualquier desplegable, la búsqueda se re-ejecuta automáticamente con los filtros aplicados.
- Al cambiar a "Selecciona territorio..." o "Selecciona categoría..." se elimina el filtro.
- Los cambios en los desplegables se reflejan en los botones de categoría y viceversa.

### Filtros activos

Cuando hay filtros o consulta activos, aparece una barra visual bajo los desplegables:

- **🔍 empleo** (chip azul oscuro) — la consulta de búsqueda activa
- **📍 Madrid** (chip azul claro) — filtro de territorio activo
- **🏷️ Educación** (chip azul claro) — filtro de categoría activo

### Resultados

Cada resultado se muestra como una tarjeta con:

- **Título** del dataset (clicable, enlace al dataset original)
- **Metadatos**: publisher (publicador), territorio, fecha de actualización
- **Descripción** resumida
- **TL;DR**: resumen automático generado por LLM (si está disponible)
- **Etiquetas de formato**: CSV, XLS, JSON, PDF, API, WEB
- **Enlace de descarga** (rojo si es archivo directo, azul si es página web)
- **Estrellas de relevancia**: ⭐ a ⭐⭐⭐⭐⭐ según el score

### Chat sobre un dataset

Cada tarjeta de resultado tiene un botón **💬 Preguntar sobre este dataset** que despliega un chat interactivo:

- Permite hacer preguntas sobre el dataset en lenguaje natural.
- El asistente responde usando los metadatos del dataset.
- Las preguntas y respuestas se mantienen durante la sesión.

### Resultados complementarios

Debajo de cada resultado hay un expander **🔗 Datasets complementarios** que sugiere otros datasets que podrían combinarse con el actual para análisis conjunto.

---

## Frontend Avanzado (Modo Demostrador)

Interfaz técnica con controles detallados para ajustar los parámetros de búsqueda. Pensado para demostraciones técnicas y análisis de calidad.

### Barra de búsqueda

- Campo de texto con placeholder *"Ej: datos de tráfico en Madrid, educación primaria..."*
- **Pulsar Enter** o hacer clic en **🔍 Buscar** para ejecutar.
- Selector numérico de resultados: **1 a 50** (por defecto 10).

### Configuración de búsqueda

En el sidebar izquierdo:

#### ⚖️ Pesos semántico / léxico

Dos sliders que controlan la proporción de cada tipo de búsqueda:

- **Peso Semántico** (0.0 - 1.0, por defecto 0.7): mayor valor da más importancia a la similitud de significado.
- **Peso Léxico** (0.0 - 1.0, por defecto 0.3): mayor valor da más importancia a la coincidencia exacta de palabras.
- Los pesos se normalizan automáticamente. Se muestra una barra de progreso con la proporción.

#### ⚙️ Calidad mínima

- **Score mínimo** (0.0 - 1.0, por defecto 0.20): filtra resultados con score inferior al umbral.
  - Por encima de 0.3: modo estricto 🔒
  - Por debajo de 0.1: modo permisivo ⚠️
- **🔤 Requerir coincidencia léxica**: si está activado, descarta resultados que no contengan ninguna palabra de la búsqueda.

### Filtros facetados

En el sidebar izquierdo, cuatro desplegables:

| Filtro | Descripción |
|---|---|
| 🌍 Territorio | Filtra por comunidad autónoma, provincia o municipio |
| 🏷️ Tema | Filtra por categoría temática |
| 📄 Formato | Filtra por formato de datos (CSV, JSON, XLS, PDF, API...) |
| 🏛️ Publisher | Filtra por organismo publicador |

**Comportamiento:**

- Cada desplegable incluye la opción **"Todos"** como valor por defecto (sin filtro).
- Al seleccionar un valor, la búsqueda se re-ejecuta automáticamente con el filtro aplicado.
- Si no hay búsqueda de texto previa, se muestran todos los datasets que cumplan el filtro.
- Se pueden combinar múltiples filtros simultáneamente.
- Los valores de los filtros se limpian automáticamente (sin duplicados ni entradas inválidas).

### Resultados

Cada resultado incluye:

- **Score numérico** con código de color (verde = excelente, amarillo = bueno, naranja = regular, rojo = bajo)
- **Título** del dataset
- **Metadatos**: publisher, territorio, tema, formato
- **Descripción** resumida
- **Explicación** de por qué el resultado es relevante (si está disponible)
- **Enlace** al dataset original

#### Estadísticas de búsqueda

Barra superior con 4 métricas:

| Métrica | Descripción |
|---|---|
| Resultados | Nº mostrados / Nº total encontrados |
| Tiempo | Milisegundos de la búsqueda |
| Peso Semántico | Porcentaje aplicado |
| Peso Léxico | Porcentaje aplicado |

---

## Diferencias entre modos

| Característica | Básico | Avanzado |
|---|---|---|
| Interfaz | Limpia y visual | Técnica con sidebar |
| Búsqueda | Enter o botón | Enter o botón |
| Top K | Selector 10/25/50 | Numérico 1-50 |
| Pesos semántico/léxico | Fijos (75%/25%) | Ajustables con sliders |
| Score mínimo | Fijo (0.15) | Ajustable (0.0-1.0) |
| Coincidencia léxica | Desactivada | Configurable |
| Categorías | Botones toggle con feedback visual | Desplegable en sidebar |
| Filtros | Territorio + Categoría | Territorio + Tema + Formato + Publisher |
| Chat sobre dataset | ✅ Sí | ❌ No |
| TL;DR | ✅ Sí | ❌ No |
| Resultados complementarios | ✅ Sí | ❌ No |
| Explicación de relevancia | ❌ No | ✅ Sí |
| Estadísticas de búsqueda | ❌ No | ✅ Sí |
| Identidad visual | Infancia Digital | Tema genérico |

---

## Solución de problemas

### La API no responde

- Verificar que los contenedores Docker estén corriendo:
  ```bash
  docker ps --filter name=buscador
  ```
- Si la API no está disponible, el frontend básico muestra *"⚠️ No se puede conectar al servidor de búsqueda"*.

### No aparecen resultados

- Probar con términos más generales.
- En modo avanzado, bajar el **Score mínimo** (ej: 0.10).
- En modo avanzado, desactivar **Requerir coincidencia léxica**.
- Comprobar que los filtros no sean demasiado restrictivos.

### Los filtros no se aplican

- En modo básico: los filtros se aplican automáticamente al seleccionarlos.
- En modo avanzado: los filtros se aplican automáticamente al cambiarlos. Si no hay búsqueda de texto, se muestra todo lo que cumpla el filtro.

### El botón de categoría no se resalta

- El botón activo se muestra en **azul oscuro** con sombra.
- Si no se resalta, recargar la página (F5) y pulsar de nuevo.
- Comprobar que no haya errores en la consola del navegador (F12).

---

*Manual generado para el PFM Buscador Semántico de Datasets Abiertos — EOI 2026*