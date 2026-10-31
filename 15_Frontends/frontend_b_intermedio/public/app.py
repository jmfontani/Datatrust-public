#!/usr/bin/env python3
"""
Frontend Público del Buscador Semántico de Datasets.
Versión limpia, rápida y amigable para usuarios finales.

Se carga desde el entrypoint principal (app.py) con mode=public.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from public.components import (
    render_public_header,
    render_search_bar_public,
    render_popular_searches,
    render_filters_dropdown,
    render_result_card_public,
    render_empty_state_public,
    render_no_results_public,
    render_results_header_public,
    render_public_footer,
    render_active_filters,
)
from common.utils import (
    get_facet_values,
    search_datasets,
    check_api_health,
    API_URL,
)


def init_session_state():
    """Inicializa el estado de sesión de Streamlit."""
    if "territorios" not in st.session_state:
        st.session_state.territorios = []
    if "temas" not in st.session_state:
        st.session_state.temas = []
    if "has_searched" not in st.session_state:
        st.session_state.has_searched = False
    if "last_results" not in st.session_state:
        st.session_state.last_results = None
    if "current_filters" not in st.session_state:
        st.session_state.current_filters = {}
    if "search_id" not in st.session_state:
        st.session_state.search_id = 0
    # Query persistente: se guarda aquí para no perderla al cambiar filtros
    if "active_query" not in st.session_state:
        st.session_state.active_query = ""


def load_facets():
    """Carga valores de facetas al inicio."""
    if not st.session_state.territorios:
        st.session_state.territorios = get_facet_values("territorio", limit=50)
        st.session_state.temas = get_facet_values("tema", limit=50)


def check_api_status():
    """Verifica el estado de la API (cacheado para evitar llamadas repetidas)."""
    if 'api_status_cached' in st.session_state:
        return st.session_state['api_status_cached']
    health = check_api_health()
    st.session_state['api_status_cached'] = health is not None
    return health is not None


def execute_search(query, filters=None, top_k=25):
    """Ejecuta búsqueda con parámetros optimizados para usuarios finales."""
    # Incrementar search_id para invalidar todas las claves de widgets de búsquedas anteriores
    st.session_state.search_id += 1

    with st.spinner("Buscando datasets..."):
        result_data = search_datasets(
            query=query,
            top_k=top_k,
            semantic_weight=0.75,  # Optimizado para calidad
            lexical_weight=0.25,
            min_score=0.15,  # Más permisivo para no perder resultados
            require_lexical=False,  # Permitir resultados semánticos puros
            **(filters or {})
        )
        st.session_state.last_results = result_data
        st.session_state.has_searched = True


def on_popular_search(term: str):
    """Callback para búsquedas populares.
    Activa el filtro de categoría (tema) correspondiente.
    Si el filtro ya está activo, lo desactiva (toggle)."""
    # `term` es el VALOR real de `theme` en la BD (slug), no la etiqueta visible
    current_tema = st.session_state.current_filters.get('tema', '').lower()
    if current_tema == term.lower():
        # Ya activo → desactivar
        st.session_state.current_filters.pop('tema', None)
    else:
        # Activar filtro de categoría
        st.session_state.current_filters['tema'] = term
    
    # Si ya hay una búsqueda activa, re-ejecutar con el nuevo filtro
    if st.session_state.has_searched and st.session_state.active_query.strip():
        execute_search(
            st.session_state.active_query,
            st.session_state.current_filters,
            st.session_state.get('top_k_value', 10)
        )
    elif st.session_state.has_searched:
        # Hay búsqueda sin query (solo filtros) → re-ejecutar
        execute_search(
            st.session_state.active_query,
            st.session_state.current_filters,
            st.session_state.get('top_k_value', 10)
        )
    else:
        # No hay búsqueda previa → ejecutar con query vacía + filtro
        st.session_state.has_searched = True
        execute_search(
            '',
            st.session_state.current_filters,
            st.session_state.get('top_k_value', 10)
        )
    st.rerun()


def main():
    """Aplicación principal pública."""
    # Inicializar estado de sesión primero
    init_session_state()

    render_public_header()

    # Verificar API
    api_ok = check_api_status()

    # Cargar facetas
    if api_ok:
        load_facets()

    # Enlace a modo avanzado (esquina superior derecha)
    col1, col2 = st.columns([6, 1])
    with col2:
        st.markdown(
            "<div style='text-align: right;'>"
            "<a href='/?mode=advanced' target='_self' style='color: #585857; text-decoration: none; font-size: 0.875rem;'>"
            "⚙️ Modo Avanzado</a></div>",
            unsafe_allow_html=True
        )

    # Barra de búsqueda
    st.markdown("<div class='search-wrapper'>", unsafe_allow_html=True)
    query, top_k = render_search_bar_public()
    st.markdown("</div>", unsafe_allow_html=True)

    # Sincronizar: si el usuario escribe en la barra, actualizar active_query
    if query.strip() and query.strip() != st.session_state.active_query:
        st.session_state.active_query = query.strip()

    # Guardar top_k en session_state para que on_popular_search lo tenga
    st.session_state.top_k_value = top_k

    active_query = st.session_state.active_query

    # Auto-ejecutar búsqueda si hay query activa y no se ha buscado aún
    if active_query.strip() and not st.session_state.has_searched:
        execute_search(active_query, st.session_state.current_filters, top_k)

    # Detectar Enter en el formulario
    if st.session_state.get('enter_pressed'):
        st.session_state.enter_pressed = False
        if active_query.strip():
            execute_search(active_query, st.session_state.current_filters, top_k)
            st.rerun()

    # Botón de búsqueda (opcional, Enter ya funciona)
    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 2])
    with col_btn2:
        if st.button("🔍 Buscar", type="primary", use_container_width=True):
            if active_query.strip():
                execute_search(active_query, st.session_state.current_filters, top_k)
                st.rerun()

    # Búsquedas populares (siempre visibles — actúan como filtros de categoría toggle)
    render_popular_searches(on_popular_search)

    # Filtros desplegables (mostrar siempre que haya datos)
    if api_ok and st.session_state.territorios:
        new_filters = render_filters_dropdown(
            st.session_state.territorios,
            st.session_state.temas,
            st.session_state.current_filters
        )

        # Los filtros se persisten en current_filters desde el on_change del
        # desplegable; aquí solo se relanza la búsqueda si cambiaron.
        st.session_state.current_filters = new_filters
        if st.session_state.pop('_refilter', False) and st.session_state.has_searched:
            execute_search(active_query, st.session_state.current_filters, top_k)
            st.rerun()

    # Mostrar filtros activos como chips visuales
    if st.session_state.current_filters:
        render_active_filters(st.session_state.current_filters, active_query)

    # Mostrar resultados o estado vacío
    if not st.session_state.has_searched:
        if not api_ok:
            st.error("⚠️ No se puede conectar al servidor de búsqueda. Por favor, inténtalo más tarde.")
        else:
            render_empty_state_public()
    elif st.session_state.last_results is None:
        st.error("❌ Error al realizar la búsqueda. Por favor, inténtalo de nuevo.")
    else:
        result_data = st.session_state.last_results
        results = result_data.get("results", [])

        if not results:
            render_no_results_public()
        else:
            render_results_header_public(
                result_data.get('query', ''),
                result_data.get('total_results', 0),
                result_data.get('returned_results', 0)
            )

            search_id = st.session_state.search_id
            for i, result in enumerate(results, 1):
                render_result_card_public(result, i, search_id)

    # Footer
    render_public_footer()


if __name__ == "__main__":
    st.set_page_config(
        page_title="Datatrust - Buscador Semántico",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    main()
