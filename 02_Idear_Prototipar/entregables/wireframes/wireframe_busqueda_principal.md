# Wireframe: Pantalla Principal de Búsqueda

## Proyecto: Buscador Semántico de Datasets Públicos
**Fase:** 02 - Idear y Prototipar
**Versión:** 1.0 (post-Fase 01: lista de resultados, NO chatbot)

---

## 🎯 Principios de diseño (basados en entrevistas)

1. **Simplicidad primero:** Los usuarios quieren resultados, no conversación
2. **Velocidad:** <2s desde query a resultados
3. **Metadatos visibles:** Preview sin descargar
4. **Control:** Filtros facetados accesibles
5. **Trazabilidad:** Link directo a datos.gob.es

---

## 📱 Pantalla Principal

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔍 Buscador Semántico de Datasets Públicos          [?] [⚙️]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Busca datasets por intención...                         │   │
│  │  Ej: "pueblos que se vacían", "calidad del aire Madrid" │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [🔍 Buscar]  [🎲 Descubrir datasets relacionados]              │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │ 📊 Temas        │  │ 📍 Territorio   │  │ 📅 Actualización│    │
│  │ [Todos ▼]      │  │ [Todos ▼]      │  │ [Cualquiera ▼] │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│                                                                  │
│  Resultados: 1.247 datasets encontrados (0.8 segundos)          │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 📊 Censo de población por municipios (2023)            │   │
│  │                                                         │   │
│  │ ⭐ Relevancia: 96%  │  Instituto Nacional de Estadística │   │
│  │ 📍 España          │  🏷️ Demografía, Población, Censo  │   │
│  │ 📅 Última actualización: 15/06/2024                    │   │
│  │ 📁 Formato: CSV (45 MB)  │  📥 Descargar  │  🔗 Ver en datos.gob.es │
│  │                                                         │   │
│  │ 📝 Descripción: Población empadronada por municipio,    │   │
│  │    sexo, edad y nacionalidad. Datos anuales desde 1996. │   │
│  │                                                         │   │
│  │ 💡 ¿Por qué es relevante? Contiene datos de población   │   │
│  │    por municipio con series temporales, ideal para      │   │
│  │    analizar tendencias de despoblación.                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 📊 Movimiento natural de la población por provincias    │   │
│  │                                                         │   │
│  │ ⭐ Relevancia: 89%  │  Ministerio de Sanidad            │   │
│  │ 📍 España          │  🏷️ Demografía, Natalidad, Defunción│  │
│  │ 📅 Última actualización: 30/04/2024                    │   │
│  │ 📁 Formato: XLSX (12 MB)  │  📥 Descargar  │  🔗 Ver en datos.gob.es│
│  │                                                         │   │
│  │ 📝 Descripción: Estadísticas de nacimientos, defunciones │  │
│  │    y migraciones por provincia. Serie temporal 2000-2023│  │
│  │                                                         │   │
│  │ 💡 ¿Por qué es relevante? Muestra el balance migratorio  │   │
│  │    que explica el vaciamiento de pueblos.                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 📊 Indicadores de sostenibilidad territorial            │   │
│  │                                                         │   │
│  │ ⭐ Relevancia: 82%  │  Ministerio de Política Territorial│   │
│  │ 📍 Castilla y León │  🏷️ Territorio, Despoblación, Rural │   │
│  │ 📅 Última actualización: 10/03/2024                    │   │
│  │ 📁 Formato: CSV (8 MB)   │  📥 Descargar  │  🔗 Ver en datos.gob.es│
│  │                                                         │   │
│  │ 📝 Descripción: Conjunto de indicadores para el análisis │   │
│  │    territorial y la lucha contra la despoblación.      │   │
│  │                                                         │   │
│  │ 💡 ¿Por qué es relevante? Incluye índices específicos   │   │
│  │    de despoblación, envejecimiento y dependencia.        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [◀ Anterior]  Página 1 de 125  [Siguiente ▶]                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎨 Especificaciones de componentes

### Barra de búsqueda
- **Placeholder:** "Busca datasets por intención... Ej: pueblos que se vacían"
- **Ancho:** 100% del contenedor
- **Autocompletar:** Sugerencias de queries populares (debounce 300ms)
- **Histórico:** Guardar últimas 10 búsquedas (localStorage)

### Botones de acción
- **🔍 Buscar:** Principal, submit del formulario
- **🎲 Descubrir:** Sugerir datasets aleatorios relevantes (para descubrimiento)

### Filtros facetados (visibles siempre, colapsables en móvil)
- **Temas:** Checkboxes jerárquicas (Demografía, Economía, Salud, Medio ambiente...)
- **Territorio:** Selector jerárquico (País → CCAA → Provincia → Municipio)
- **Formato:** CSV, XLSX, JSON, RDF, XML, GeoJSON...
- **Frecuencia:** Diaria, Semanal, Mensual, Anual, Histórico...
- **Organismo:** Buscador + autocomplete de organismos

### Tarjeta de resultado (dataset)

| Elemento | Tipo | Descripción |
|----------|------|-------------|
| 📊 Icono | Visual | Emoji según tema (📊 estadísticas, 🏥 salud, 🌍 medio ambiente...) |
| Título | Link | Nombre del dataset, clickable a datos.gob.es |
| Relevancia | Badge | Porcentaje (0-100%), color-coded |
| Organismo | Metadata | Quién publica el dataset |
| Territorio | Metadata | Cobertura geográfica |
| Tags | Chips | Temas DCAT + keywords |
| Actualización | Metadata | Fecha última modificación |
| Formato/Tamaño | Metadata | Tipo de archivo + tamaño |
| Descripción | Texto | Truncada a 2 líneas, expandible |
| Acciones | Botones | Descargar archivo, Ver en datos.gob.es |
| Explicación | Callout | Por qué este dataset es relevante para la query |

### Footer de paginación
- 10 resultados por página (configurable)
- Total de resultados + tiempo de respuesta
- Navegación rápida a página específica

---

## 📋 Variantes de pantalla

### 1. Estado inicial (sin búsqueda)
- Barra de búsqueda centrada grande
- Debajo: datasets destacados/recientes + temas populares
- Ejemplos de queries clickeables

### 2. Búsqueda con resultados (principal)
- Layout de dos columnas: filtros (izq) + resultados (der)
- Filtros pueden colapsarse en móvil

### 3. Búsqueda sin resultados
- Mensaje amigable: "No encontramos datasets para esta búsqueda"
- Sugerencias: queries alternativas, datasets similares
- Botón "Notificar cuando haya resultados" (opcional)

### 4. Dataset individual (detalle)
- Modal o página dedicada
- Metadatos completos + preview de columnas/tipos
- Distribuciones (URLs descarga por formato)
- Datasets relacionados (recomendación)

---

## 📱 Responsive

### Desktop (>1024px)
- Layout 2 columnas: filtros (25%) + resultados (75%)
- Barra de búsqueda ancha, filtros expandidos

### Tablet (768-1024px)
- Layout 2 columnas con filtros colapsables
- Tarjetas de resultado compactas

### Móvil (<768px)
- Layout 1 columna
- Filtros en drawer lateral
- Tarjetas apiladas verticalmente
- Paginación simplificada

---

## 🔄 Flujo de interacción

```
Usuario escribe query
        ↓
Sistema genera embedding de la query
        ↓
Búsqueda híbrida (semántica + léxica)
        ↓
Ranking de resultados por score combinado
        ↓
Aplicar filtros facetados (si los hay)
        ↓
Mostrar tarjetas con metadatos + explicación
        ↓
Usuario puede: filtrar más, ordenar, paginar,
               descargar, o ver detalle completo
```

---

## ✅ Checklist de validación

- [x] Simplificado: lista de resultados, no chatbot
- [x] Metadatos visibles sin descargar
- [x] Filtros facetados accesibles
- [x] Explicaciones de relevancia incluidas
- [x] Links verificables a datos.gob.es
- [ ] Validado con 2+ usuarios de los perfiles definidos

---

*Wireframe creado tras decisión de Fase 01: NO chatbot, SÍ lista de resultados*
