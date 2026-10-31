#!/usr/bin/env python3
"""
Frontend Avanzado del Buscador Semántico de Datasets.
Demostrador técnico con controles de pesos, filtros detallados,
diagnósticos de API y acceso a las capacidades LLM del backend.

Se carga desde el entrypoint principal (app.py) con mode=advanced.
"""
import sys
from pathlib import Path

import streamlit as st

# Añadir directorio padre al path para imports absolutos
sys.path.insert(0, str(Path(__file__).parent.parent))

from legacy.components_v2 import (
    render_header,
    render_search_bar_v2,
    render_weight_controls,
    render_filters,
    render_result_card,
    render_stats,
    render_empty_state,
    render_no_results,
)
from common.utils import (
    get_facet_values,
    search_datasets,
    check_api_health,
    API_URL,
)


# Configuración de la página (solo si se ejecuta directamente)
if __name__ == "__main__":
    _logo = str(Path(__file__).parent.parent / "assets" / "logo_buscador_semantico.png")
    st.set_page_config(
        page_title="Datatrust - Modo Avanzado",
        page_icon=_logo,
        layout="wide",
        initial_sidebar_state="expanded",
    )


def init_session_state():
    """Inicializar estado de sesión de Streamlit."""
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

    # Estado para filtros reactivos
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""
    if "last_filters" not in st.session_state:
        st.session_state.last_filters = {}
    if "pending_filter_update" not in st.session_state:
        st.session_state.pending_filter_update = False
    if "filter_update_message" not in st.session_state:
        st.session_state.filter_update_message = None


def check_api_status():
    """Verifica estado de la API y muestra diagnóstico."""
    health = check_api_health()
    st.session_state.api_status = health is not None
    return health


def load_facets():
    """Carga valores de facetas al inicio."""
    if not st.session_state.territorios and st.session_state.api_status:
        with st.spinner("Cargando filtros..."):
            st.session_state.territorios = get_facet_values("territorio", limit=50)
            st.session_state.temas = get_facet_values("tema", limit=50)
            st.session_state.formatos = get_facet_values("formato", limit=30)
            st.session_state.publishers = get_facet_values("publisher", limit=50)


def render_api_status_panel():
    """Muestra panel de estado de la API."""
    health = check_api_status()
    
    if health is None:
        st.error(f"""
## ❌ API No Disponible

No se pudo conectar a la API en: `{API_URL}`

### Pasos para resolver:

1. **Verifica que la API esté corriendo:**
   ```bash
   cd codigo/api && uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **Verifica la URL en `utils_v2.py`:**
   - URL actual: `{API_URL}`

3. **Prueba manualmente:**
   ```bash
   curl {API_URL}/health
   ```
        """)
        return False
    
    datasets_count = health.get('datasets_count', 0)
    st.success(f"✅ API Conectada | Datasets cargados: {datasets_count:,}")
    return True


def execute_search(query, top_k, semantic_weight, lexical_weight, min_score, require_lexical, filters):
    """Ejecutar búsqueda y guardar resultados."""
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
        # Guardar query y filtros para actualizaciones reactivas
        st.session_state.last_query = query
        st.session_state.last_filters = filters.copy()


def main():
    """Aplicación principal."""
    # Inicializar estado de sesión primero
    init_session_state()

    # Enlace a modo público
    st.markdown(
        "<div style='text-align: right; margin-bottom: 1rem;'>"
        "<a href='/?mode=public' target='_self' style='color: #64748b; text-decoration: none; font-size: 0.875rem;'>"
        "🏠 Volver a modo público</a></div>",
        unsafe_allow_html=True
    )

    render_header()

    # Panel de estado de la API
    api_ok = render_api_status_panel()
    
    # Sidebar: Filtros y configuración
    with st.sidebar:
        st.markdown("---")
        
        if api_ok:
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
        else:
            st.warning("⚠️ Conecta la API para usar filtros y búsqueda")
            filters = {}
            semantic_weight, lexical_weight = 0.7, 0.3
            min_score = 0.20
            require_lexical = True
    
    # Área principal: Barra de búsqueda con soporte Enter
    query, top_k = render_search_bar_v2()
    
    # Detectar cambios en filtros para búsqueda reactiva
    filters_changed = False
    if api_ok:
        current_filters = filters.copy()
        last_filters = st.session_state.last_filters
        if current_filters != last_filters:
            filters_changed = True
            st.session_state.pending_filter_update = True

    # Ejecutar búsqueda cuando se presiona Enter o se hace clic en el botón
    if api_ok and query.strip() and st.session_state.get('search_triggered', False):
        execute_search(
            query=query,
            top_k=top_k,
            semantic_weight=semantic_weight,
            lexical_weight=lexical_weight,
            min_score=min_score,
            require_lexical=require_lexical,
            filters=filters,
        )
        # Resetear el trigger
        st.session_state.search_triggered = False
        st.rerun()

    # Ejecutar búsqueda automática cuando cambian filtros
    elif api_ok and filters_changed:
        # Usar la última query si existe, si no, query vacía (solo filtros)
        effective_query = st.session_state.last_query if st.session_state.last_query else ""
        st.session_state.filter_update_message = (
            f"🔄 Búsqueda actualizada con filtro"
            + (f": '{st.session_state.last_query}'" if st.session_state.last_query else "")
        )
        execute_search(
            query=effective_query,
            top_k=top_k,
            semantic_weight=semantic_weight,
            lexical_weight=lexical_weight,
            min_score=min_score,
            require_lexical=require_lexical,
            filters=filters,
        )
        st.session_state.pending_filter_update = False
        st.rerun()

    # Mostrar mensaje de actualización por filtro
    if st.session_state.filter_update_message:
        st.success(st.session_state.filter_update_message)
        st.session_state.filter_update_message = None

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
            render_stats(result_data)
            
            st.markdown("---")
            
            st.markdown(f"### 📊 Resultados para: *{result_data['query']}*")
            
            for i, result in enumerate(results, 1):
                render_result_card(result, i)


if __name__ == "__main__":
    main()
