# Frontend del Buscador - Modo Público y Modo Avanzado

## 📋 Resumen

El frontend tiene **dos modos** accesibles desde un único punto de entrada:

1. **Modo Público** (`/?mode=public` o `/`) - Por defecto
   - Interfaz limpia, rápida y amigable
   - Sin controles técnicos visibles
   - Búsquedas populares
   - Filtros visuales (chips)
   - Resultados con estrellas de relevancia
   - TL;DR, datasets complementarios y chat bajo demanda

2. **Modo Avanzado** (`/?mode=advanced`) - Demostrador técnico
   - Controles de pesos semántico/léxico
   - Sliders de configuración (score mínimo, coincidencia léxica)
   - Panel de estado de API
   - Acceso a capacidades LLM del backend
   - Sirve como laboratorio/demostrador, no como interfaz principal

---

## 🚀 Cómo acceder

### Modo Público (por defecto)

```bash
http://localhost:8501
```

### Modo Avanzado

```bash
http://localhost:8501?mode=advanced
```

---

## 📁 Estructura

| Archivo / Carpeta | Propósito |
|-------------------|-----------|
| `app.py` | **Entrypoint unificado**. Detecta `?mode=advanced` y carga el modo correspondiente. |
| `public/app.py` | Modo público: interfaz rápida y visual. |
| `public/components.py` | Componentes UI del modo público (tarjetas, filtros, chat, TL;DR). |
| `advanced/app.py` | Modo avanzado: demostrador técnico con controles y diagnósticos. |
| `common/utils.py` | Utilidades compartidas (llamadas a API, facetas, formateo). |
| `legacy/` | Versiones antiguas y demos archivadas (app_router, app_original, demos Sprint 6). |

---

## 🐳 Docker

El contenedor ejecuta directamente el entrypoint unificado:

```bash
docker-compose up frontend
```

La URL con parámetro `?mode=advanced` carga el modo avanzado sin necesidad de variables de entorno ni contenedores adicionales.

---

## 🎨 Características del Modo Público

### Diseño
- Header minimalista
- Barra de búsqueda estilo Google
- Filtros como chips clicables
- Resultados en tarjetas limpias
- Footer minimalista

### Funcionalidad
- **Búsquedas populares**: chips rápidos (Empleo, Educación, etc.)
- **Filtros visuales**: Territorio y Categoría como botones
- **Relevancia visual**: estrellas ⭐⭐⭐⭐⭐
- **TL;DR inline**: resumen generado por LLM en cada tarjeta
- **Datasets complementarios**: expander opcional por dataset
- **Chat sobre dataset**: expander opcional para preguntar sobre un dataset

### UX
- Respuesta rápida (<1s para búsquedas sin LLM)
- Las funciones LLM (TL;DR, complementarios, chat) no interfieren en el flujo habitual
- Estados vacíos amigables

---

## ⚙️ Características del Modo Avanzado

- Sliders de peso semántico/léxico
- Configuración de score mínimo
- Checkbox "requerir coincidencia léxica"
- Panel de estado de API
- Dropdowns de filtros completos
- Scores numéricos exactos
- Acceso a endpoints de demostración LLM (re-ranking, explicaciones, query preprocessor, sugerencias)

---

## 📝 Notas para desarrolladores

### Añadir nuevas búsquedas populares
Editar `public/components.py`, función `render_popular_searches()`.

### Modificar pesos por defecto (público)
Editar `public/app.py`, función `execute_search()`.

### Añadir una nueva demo técnica al modo avanzado
Editar `advanced/app.py` y añadir una nueva pestaña o sección. Reutilizar componentes de `public/components.py` si es posible.

---

## ✅ Estado

- ✅ Entrypoint unificado (`app.py`)
- ✅ Modo público refactorizado en `public/`
- ✅ Modo avanzado disponible en `advanced/`
- ✅ Utilidades compartidas en `common/`
- ✅ Archivos antiguos archivados en `legacy/`
- ✅ Docker apunta al entrypoint unificado
