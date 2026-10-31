#!/usr/bin/env python3
"""
Frontend del Buscador Semántico de Datasets.

Ejecutar:
    streamlit run app.py --server.port 8501

Requiere:
    - API corriendo en http://localhost:8000
    - Dependencias: streamlit, requests
"""
import sys
from pathlib import Path

import streamlit as st

# Añadir directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from components import (
    render_header,
    render_search_bar,
    render_weight_controls,
    render_filters,
    render_result_card,
    render_stats,
    render_empty_state,
    render_no_results,
)
from utils import (
    get_facet_values,
    search_datasets,
    check_api_health,
    API_URL,
)


# Configuración de la página
_LOGO = str(Path(__file__).parent / "assets" / "logo_buscador_semantico.png")

st.set_page_config(
    page_title="Buscador Semántico de Datasets",
    page_icon=_LOGO,
    layout="wide",
    initial_sidebar_state="expanded",
)


# Inicializar estado de sesión
if "territorios" not in st.session_state:
    st.session_state.territorios = []
if "temas" not in st.session_state:
    st.session_state.temas = []
if "formatos" not in st.session_state:
    st.session_state.formatos = []
if "publishers" not in st.session_state:
    st.session_state.publishers = []
if "has_searched" not in st.session_state:
    st.session_state.has_searched = False
if "last_results" not in st.session_state:
    st.session_state.last_results = None
if "api_status" not in st.session_state:
    st.session_state.api_status = None


def check_api_status():
    """Verifica estado de la API y muestra diagnóstico."""
    health = check_api_health()
    st.session_state.api_status = health is not None
    return health


def load_facets():
    """Carga valores de facetas al inicio."""
    # Solo cargar si no están ya cargadas y la API está disponible
    if not st.session_state.territorios and st.session_state.api_status:
        with st.spinner("Cargando filtros..."):
            st.session_state.territorios = get_facet_values("territorio", limit=50)
            st.session_state.temas = get_facet_values("tema", limit=50)
            st.session_state.formatos = get_facet_values("formato", limit=30)
            st.session_state.publishers = get_facet_values("publisher", limit=50)


def render_api_status_panel():
    """Muestra panel de estado de la API."""
    # Verificar estado de la API
    health = check_api_status()
    
    if health is None:
        st.error(f"""
## ❌ API No Disponible

No se pudo conectar a la API en: `{API_URL}`

### Pasos para resolver:

1. **Verifica que la API esté corriendo:**
   ```bash
   cd ~/datos/PFM/Datatrust/05_Sprint3_Busqueda_UI/codigo/api
   source ../../../venv/bin/activate
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **Verifica la URL en `utils.py`:**
   - URL actual: `{API_URL}`
   - Si usas HTTPS: edita la variable `API_URL`

3. **Prueba manualmente:**
   ```bash
   curl -k {API_URL}/health
   ```

### Si usas el script automático:
```bash
cd ~/datos/PFM/Datatrust/05_Sprint3_Busqueda_UI/codigo
./lanzar_sistema.sh
```
        """)
        return False
    
    # Mostrar estado OK
    datasets_count = health.get('datasets_count', 0)
    st.success(f"✅ API Conectada | Datasets cargados: {datasets_count:,}")
    return True


def main():
    """Aplicación principal."""
    render_header()
    
    # Panel de estado de la API (antes del sidebar)
    api_ok = render_api_status_panel()
    
    # Sidebar: Filtros y configuración
    with st.sidebar:
        st.markdown("---")
        
        if api_ok:
            # Cargar facetas solo si la API está OK
            load_facets()
            
            # Controles de pesos
            semantic_weight, lexical_weight = render_weight_controls()
            
            st.markdown("---")
            
            # Umbral de calidad
            st.subheader("⚙️ Calidad Mínima")
            min_score = st.slider(
                "Score mínimo",
                min_value=0.0,
                max_value=1.0,
                value=0.20,
                step=0.05,
                help="Filtra resultados irrelevantes. Valor recomendado: 0.20+"
            )
            
            # Filtro de coincidencia léxica
            require_lexical = st.checkbox(
                "🔤 Requerir coincidencia léxica",
                value=True,
                help="Descarta resultados que no contengan palabras de la búsqueda"
            )
            
            if min_score > 0.3:
                st.info("🔒 Modo estricto")
            elif min_score < 0.1:
                st.warning("⚠️ Modo permisivo")
            
            st.markdown("---")
            
            # Filtros facetados
            filters = render_filters()
            
            st.markdown("---")
            
            # Botón de búsqueda en sidebar
            search_button = st.button("🔍 Buscar", type="primary", use_container_width=True)
            
            st.markdown("---")
            
            # Información adicional
            st.markdown("""
            ### ℹ️ Ayuda
            
            **Búsqueda Híbrida:**
            - **Semántica**: Entiende el significado
            - **Léxica**: Busca palabras exactas
            
            **Filtros:**
            Reduce resultados por metadatos
            
            **Score:**
            - 🟢 Excelente (>= 0.8)
            - 🟡 Bueno (>= 0.6)
            - 🟠 Regular (>= 0.4)
            - 🔴 Bajo (< 0.4)
            """)
        else:
            st.warning("⚠️ Conecta la API para usar filtros y búsqueda")
            search_button = False
            filters = {}
            semantic_weight, lexical_weight = 0.7, 0.3
    
    # Área principal: Barra de búsqueda
    query, top_k = render_search_bar()
    
    # Ejecutar búsqueda solo si API está OK
    if api_ok and search_button and query.strip():
        with st.spinner("🔍 Buscando..."):
            result_data = search_datasets(
                query=query,
                top_k=top_k,
                semantic_weight=semantic_weight,
                lexical_weight=lexical_weight,
                min_score=min_score,
                require_lexical=require_lexical,
                **filters,
            )
            st.session_state.last_results = result_data
            st.session_state.has_searched = True
    
    # Mostrar resultados
    if not st.session_state.has_searched:
        if api_ok:
            render_empty_state()
        else:
            st.info("👆 Conecta la API arriba para comenzar a buscar")
    elif st.session_state.last_results is None:
        st.error("❌ Error al realizar la búsqueda.")
        st.info("💡 Verifica que la API esté respondiendo correctamente")
    else:
        result_data = st.session_state.last_results
        results = result_data.get("results", [])
        
        if not results:
            render_no_results()
        else:
            # Estadísticas
            render_stats(result_data)
            
            st.markdown("---")
            
            # Lista de resultados
            st.markdown(f"### 📊 Resultados para: *{result_data['query']}*")
            
            for i, result in enumerate(results, 1):
                render_result_card(result, i)


if __name__ == "__main__":
    main()
