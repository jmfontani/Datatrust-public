# Frontend V2 - Buscador Semántico de Datasets

## 🎯 Mejoras Principales

### 1. Búsqueda con Tecla Enter
- ✅ Ahora puedes presionar **Enter** para ejecutar la búsqueda directamente
- ✅ También funciona el botón "Buscar" como alternativa
- ✅ Indicador visual que muestra que se puede usar Enter

### 2. Diseño Personalizable
- ✅ **Temas de colores**: Personaliza colores primarios, secundarios y de acento
- ✅ **Tamaños de fuente**: Configura tamaños para títulos, textos y metadatos
- ✅ **Estilo de tarjetas**: Personaliza bordes, sombras y espaciado

## 🚀 Cómo Usar

### Ejecutar el Frontend
```bash
cd codigo/frontend_v2
streamlit run app.py --server.port 8501
```

### Personalizar el Tema
Edita `components_v2.py` y modifica las variables de configuración:

```python
# Colores del tema (personalizable)
THEME_COLORS = {
    'primary': '#667eea',      # Color principal
    'secondary': '#764ba2',    # Color secundario
    'accent': '#48bb78',       # Color de acento
    'danger': '#f56565',       # Color de error
    'warning': '#ed8936',      # Color de advertencia
    'info': '#4299e1',         # Color de información
}

# Tamaños de fuente (personalizable)
FONT_SIZES = {
    'header_title': '2.5rem',
    'header_subtitle': '1.1rem',
    'card_title': '1.2rem',
    'card_text': '0.95rem',
}

# Estilo de tarjetas (personalizable)
CARD_STYLE = {
    'border_radius': '10px',
    'padding': '1.2rem',
    'shadow': '0 2px 8px rgba(0,0,0,0.1)',
}
```

## 📁 Estructura

```
frontend_v2/
├── app.py              # Aplicación principal
├── components_v2.py    # Componentes visuales personalizables
├── utils_v2.py         # Utilidades y conexión a API
└── README.md           # Este archivo
```

## 🎨 Personalización Avanzada

### Cambiar Colores Dinámicamente
```python
from components_v2 import apply_theme_colors

# Aplicar tema personalizado
apply_theme_colors(
    primary='#e74c3c',    # Rojo
    secondary='#c0392b',
    accent='#f39c12'
)
```

### Modificar Estilos CSS
Los estilos están definidos en la función `get_custom_css()` en `components_v2.py`. Puedes:
- Cambiar gradientes del header
- Modificar sombras de tarjetas
- Ajustar espaciados y márgenes
- Personalizar animaciones hover

## 🔧 Características Implementadas

| Característica | Frontend V1 | Frontend V2 |
|---|---|---|
| Búsqueda con botón | ✅ | ✅ |
| Búsqueda con Enter | ❌ | ✅ |
| Temas personalizables | ❌ | ✅ |
| Fuentes configurables | ❌ | ✅ |
| Estilo de tarjetas customizable | ❌ | ✅ |
| Responsive design | ✅ | ✅ |
| Filtros facetados | ✅ | ✅ |
| Pesos de búsqueda | ✅ | ✅ |

## 📋 Dependencias

```
streamlit >= 1.28.0
requests >= 2.31.0
```

## 🔗 API Requerida

El frontend se conecta a la API REST en `http://localhost:8000`. Asegúrate de que la API esté corriendo antes de iniciar el frontend.
