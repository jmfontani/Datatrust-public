# Auditoría Impeccable — datatrust.ejemplo.com

**Fecha:** 4-nov-2026 · **Alcance:** frontend público (`frontend_b_intermedio/public`) sobre la app viva · **Herramientas:** Impeccable 4.8.0 (URL, dos viewports) + sonda propia `live_app_probe.js` (Puppeteer sobre la app real)

**Solo diagnóstico.** No se ha modificado ni el frontend ni el motor.

---

## 1. Resumen

| Gravedad | Nº | Qué |
|---|---|---|
| **P0** bloqueante | 0 | Nada impide buscar ni leer resultados |
| **P1** accesibilidad rota | 2 | Subtítulo del header 3,23:1 · aviso naranja 2,55:1 |
| **P2** calidad y coherencia | 4 | `lang="en"`, salto h1→h3, logo sin `alt`, placeholder al límite |
| **P3** estética y detalle | 3 | Foco de 1 px, 8 controles pequeños, sin `<nav>` |

**Comparación con la portada de proyectos:** allí el detector dio **43 avisos**; aquí da **2 en escritorio y 3 en móvil**. El frontend de DataTrust está en mucho mejor estado: tema claro con texto a 14,38:1, sin desbordamiento horizontal en ningún ancho y las fichas de resultado con contraste correcto.

## 2. Método

1. `IMPECCABLE_BROWSER=<chrome> npx impeccable detect --json --viewport {1280x800,390x844} https://datatrust.ejemplo.com` → 62 reglas deterministas.
2. `node live_app_probe.js`: overflow a 390/768/1280, contraste recalculado contra **las paradas del degradado** (no contra el color de fondo de la página), foco con teclado real, `lang`, imágenes sin `alt`, y una **búsqueda real** (teclea `basura que generamos en casa` y pulsa Enter) para medir también el estado de resultados: 10 fichas.
3. Tema leído de `15_Frontends/frontend_b_intermedio/.streamlit/config.toml`.

## 3. P1 — accesibilidad rota

### 1. El subtítulo del header no se lee sobre la parte clara del degradado

`.public-header` pinta `linear-gradient(135deg, #080066, #1F7CFF)` y el subtítulo va en `rgba(255,255,255,0.85)` a 1.125 rem con `font-weight: 400` (`public/components.py:60` y `:73-78`).

Compuesto real sobre la parada clara: **`#ddebff` sobre `#1F7CFF` = 3,23:1**; el detector mide 3,9:1 porque usa blanco puro. A 18 px y peso normal el umbral es 4,5:1. Afecta a «Buscador semántico de datasets públicos», en escritorio y en móvil.

Arreglo (dos líneas, sin tocar la identidad):

| Opción | Cambio | Ratio |
|---|---|---|
| A | subtítulo `#ffffff` + parada final `#1A6FE8` | **4,68:1** |
| B | subtítulo `#ffffff` + parada final `#1665D8` | **5,40:1** |
| C | mantener 85 % de opacidad y bajar la parada a `#1259C4` | 5,12:1 |

El `h1` («Datatrust», 36 px en negrita) sí pasa: el umbral de texto grande es 3:1 y da 3,9:1.

### 2. El aviso «⚠️ Página web» es naranja claro sobre blanco

`public/components.py:854`: `color: #ed8936`, `font-size: 0.8rem` sobre la tarjeta blanca → **2,55:1** (necesita 4,5:1). Aparece en las fichas cuyo recurso es una página web en lugar de un fichero: en la búsqueda de la demo, **3 de las 10 fichas**.

Arreglo: `#b45309` → **5,02:1** (misma familia naranja, sin cambiar el significado). Alternativa `#a34a00` → 5,94:1.

## 4. P2 — calidad y coherencia

### 3. La página se declara en inglés

`<html lang="en">` con todo el contenido en español. No lo pone el proyecto: es la plantilla de Streamlit (`site-packages/streamlit/static/index.html`) dentro de la imagen. Un lector de pantalla pronuncia el español con reglas inglesas y el navegador ofrece traducir. `st.set_page_config` **no** lo cambia: hay que parchear la plantilla en la imagen (o servir un `index.html` propio en el `Dockerfile`).

### 4. Salto de jerarquía: `h1` → `h3`

«Datatrust» (h1) va seguido de «Busca entre 94.461 datasets públicos» (h3), sin h2. Aviso `skipped-heading` del detector en ambos viewports. Arreglo: pasar ese subtítulo a `h2` o a un `<p>` con clase.

### 5. El logo no tiene texto alternativo

Hay un único `<img>` (el logo, en data URI) y ninguno lleva `alt`. Arreglo: `alt="DataTrust"` o `alt=""` si el `h1` ya lo nombra.

### 6. Placeholder del buscador al límite

`#777876` sobre blanco = **4,44:1** frente a 4,5 exigidos: falla por 0,06. Es un placeholder, no contenido, pero el detector lo marca (advisory). Arreglo trivial: `#6f706e` o el `#585857` que ya usa la app en otros textos.

## 5. P3 — estética y detalle

7. **Foco del buscador**: `outline: none` y borde de 1 px `#1F7CFF` al enfocar (3,35:1 sobre el fondo pálido). Cumple el 3:1 de componentes, pero no el grosor de 2 px del nivel AAA. Subir a 2 px con `outline-offset` no cambia nada visual en reposo.
8. **8 controles con área táctil menor de 40×32 px**: los botones de categoría de la portada. En móvil se pulsan con el pulgar.
9. **Sin `<nav>`**: sólo hay un `<main>`. Las categorías y los filtros podrían ser una región navegable.

## 6. Lo que está bien (no tocar)

- **0 px de desbordamiento horizontal** a 390, 768 y 1280: la respuesta de Streamlit está bien resuelta.
- Tema: texto `#1D1E1B` sobre `#f0ecf6` = **14,38:1**; primario `#080066` sobre el mismo fondo = **15,0:1**; blanco sobre primario = 17,47:1.
- Las fichas de resultado: cuerpo y TL;DR con contraste correcto, y el TL;DR del dataset de residuos domésticos aparece ya redactado en la primera ficha.
- La búsqueda devuelve lo esperado en la demo: «Residuos domésticos generados…» y «Generación de residuos urbanos» en las dos primeras posiciones.

## 7. Si quieres que lo arregle

Los dos P1 son **tres líneas** en `public/components.py` (color del subtítulo, parada del degradado, color del aviso) y no tocan el motor ni la API. El P2 del `lang` requiere rebuild de la imagen del frontend (la plantilla va dentro). Coste: 10 minutos los P1, 20 más el `lang` con rebuild y verificación.

Verificación después: volver a pasar el detector en los dos viewports (debe quedar 0 o sólo el advisory del placeholder) y la sonda con la búsqueda real, comparando el ratio del subtítulo y del aviso.


---

## 8. Estado: mejoras implementadas y desplegadas el 5-nov-2026 a las 07:45

Aplicadas en `15_Frontends/frontend_b_intermedio/public/components.py` (10 cambios) y `07_Sprint5_Integracion/codigo/docker/Dockerfile.frontend` (1 cambio). Imagen `docker-frontend` reconstruida y contenedor recreado; `health` en 200 y sitio público en 200.

| Comprobación | Antes | Después |
|---|---|---|
| Avisos del detector (1280×800) | 2 | **0** |
| Avisos del detector (390×844) | 3 | **0** |
| Fallos de contraste en portada | 1 | **0** |
| Fallos de contraste en resultados | 1 | **0** |
| Subtítulo del header | 3,23:1 | **4,68:1** (`#1A6FE8` + blanco puro) |
| Aviso «Página web» | 2,55:1 | **5,02:1** (`#b45309`) |
| `lang` del documento | `en` | **`es`** |
| Jerarquía de encabezados | h1 → h3 | **h1 → h2** |
| Imágenes sin `alt` | 1 | **0** |
| Foco (teclado) | sin outline, borde 1 px | **outline 2 px `#080066`** (17,47:1) |
| Placeholder del buscador | 4,44:1 | **#585857** |
| Botones (área táctil) | 8 por debajo de 40×32 | **mínimo 40 px de alto** |
| Desbordamiento horizontal | 0 px | **0 px** |

Detalle de los cambios:

1. Nuevo token `primary_light_header = #1A6FE8` para la **parada final del degradado del header**; `primary_light` (#1F7CFF) se mantiene para bordes.
2. Subtítulo del header a **blanco puro** y peso 500.
3. Aviso «⚠️ Página web» de `#ed8936` a **`#b45309`**.
4. Logo con `alt="DataTrust"`.
5. Estado vacío y «sin resultados»: `h3` → **`h2`** (y el CSS `.empty-state-public` cubre ambos).
6. `outline` de 2 px en `:focus-visible` del buscador.
7. `::placeholder` a `#585857`.
8. `min-height: 2.5rem` en todos los botones de Streamlit.
9. Plantilla de Streamlit parcheada en la imagen: `<html lang="en">` → **`<html lang="es">`** con verificación en el propio `RUN`.

**Copias de seguridad:** `07_Sprint5_Integracion/codigo/docker/backup/components.py-20261105-074017` y `.../Dockerfile.frontend-20261105-074017`.

**Revertir:** restaurar esos dos ficheros y volver a construir y recrear el frontend (`docker compose build frontend && docker compose up -d --no-deps frontend`).

**Pendiente y no tocado:** el `<title>` sigue siendo «Datos Abiertos - Buscador Semántico» (no dice DataTrust) y no hay `<nav>`. Ninguno afecta a la lectura.
