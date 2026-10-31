# Frontend del Buscador Semántico de Datasets

## 🎯 Características

- **Interfaz visual intuitiva** con Streamlit
- **Búsqueda en tiempo real** conectada a la API REST
- **Controles de pesos** ajustables (semántico vs léxico)
- **Filtros facetados** desplegables (territorio, tema, formato, publisher)
- **Tarjetas de resultados** con scores coloreados y explicaciones
- **Estadísticas de búsqueda** (tiempo, resultados, pesos utilizados)

---

## 🚀 Ejecución (Automática)

### Opción recomendada: Script único

Desde la raíz del Sprint 3:
```bash
cd ~/datos/PFM/Datatrust/05_Sprint3_Busqueda_UI/codigo
./lanzar_sistema.sh
```

Este script automáticamente:
1. ✅ Activa el virtualenv
2. ✅ Verifica dependencias (las instala si faltan)
3. ✅ Libera puertos ocupados
4. ✅ Inicia el Backend (API FastAPI) en puerto 8000
5. ✅ Espera a que la API esté lista (health check)
6. ✅ Inicia el Frontend (Streamlit) en puerto 8501
7. ✅ Verifica que ambos servicios respondan
8. 📋 Muestra logs en tiempo real

## 🚀 Ejecución Manual (si prefieres control total)

### Requisitos previos

1. **Virtualenv activado**

### Acceso

- Local: http://localhost:8501
- Red: http://servidor1.local:8501

---

## 📁 Estructura

```
frontend/
├── __init__.py          # Inicialización del módulo
├── app.py               # Aplicación principal Streamlit
├── components.py        # Componentes visuales reutilizables
├── utils.py             # Funciones utilitarias (API, formatting)
└── README.md            # Esta documentación
```

---

## 🎨 Componentes Visuales

### Header Principal
- Título con gradiente de colores
- Descripción del sistema híbrido

### Barra de Búsqueda
- Campo de texto amplio con placeholder
- Selector de número de resultados (1-50)

### Panel Lateral (Sidebar)

#### Controles de Pesos
- Slider para peso semántico (0.0 - 1.0)
- Slider para peso léxico (0.0 - 1.0)
- Barra de progreso mostrando proporción
- Validación automática de totales

#### Filtros Facetados
- Dropdown de territorios
- Dropdown de temas
- Dropdown de formatos
- Dropdown de publishers
- Opción "Todos" en cada filtro

#### Información de Ayuda
- Leyenda de colores de score
- Explicación de búsqueda híbrida

### Tarjetas de Resultado
- Score visual con color codificado
- Título del dataset
- Metadatos (publisher, territorio, tema, formato)
- Descripción truncada
- Explicación de relevancia (💡)
- Enlace al dataset original

### Estadísticas
- Resultados mostrados / totales
- Tiempo de búsqueda (ms)
- Pesos semántico y léxico utilizados

---

## 🔧 Personalización

### Cambiar URL de la API

Editar `utils.py`:
```python
API_URL = "http://localhost:8000"  # Cambiar si es necesario
```

### Añadir nuevos filtros

1. Añadir al endpoint `/facets/{nuevo_facet}` en la API
2. Actualizar `render_filters()` en `components.py`
3. Añadir al payload en `search_datasets()` en `utils.py`

### Modificar estilos

Los estilos CSS están en `components.py` en cada función `render_*()`.

---

## 🐛 Solución de Problemas

### Error: "Connection refused"
**Causa**: La API no está corriendo.
**Solución**: Iniciar la API primero.

### Error: "Module not found: streamlit"
**Causa**: Streamlit no instalado.
**Solución**: `pip install streamlit`

### Filtros no cargan
**Causa**: API no responde o facets vacíos.
**Solución**: Verificar que la API está corriendo y tiene datos indexados.

### Resultados vacíos
**Causa**: Query muy específica o filtros restrictivos.
**Solución**: Probar con query más general o quitar filtros.

---

## 📸 Capturas de Pantalla

### Estado Inicial
```
┌─────────────────────────────────────────┐
│  🔍 Buscador Semántico de Datasets     │
│  Búsqueda híbrida: semántica + léxica │
└─────────────────────────────────────────┘

┌──────────┐  ┌──────────────────────────┐
│ Sidebar  │  │     🔍 Empieza tu       │
│          │  │        búsqueda          │
│ Pesos    │  │                          │
│ Filtros  │  │  Escribe una consulta... │
│ Ayuda    │  │                          │
└──────────┘  └──────────────────────────┘
```

### Con Resultados
```
┌─────────────────────────────────────────┐
│  Resultados: 5/42  Tiempo: 145ms      │
│  Semántico: 70%    Léxico: 30%        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 🟢 [0.892] Accidentalidad en tráfico  │
│ 🏛️ Comunidad de Madrid | 🌍 Madrid     │
│ 🏷️ Transporte | 📄 CSV, JSON          │
│ Estadísticas de accidentalidad en...   │
│ 💡 Alta similitud semántica; territorio │
│    coincidente: Comunidad de Madrid    │
│ 🔗 Ver dataset →                       │
└─────────────────────────────────────────┘
```

---

*Generado el 2026-05-23*
