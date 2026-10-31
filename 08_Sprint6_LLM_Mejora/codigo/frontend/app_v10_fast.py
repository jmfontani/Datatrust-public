#!/usr/bin/env python3
"""
Frontend Streamlit V10 - Búsqueda Rápida + Explicaciones Bajo Demanda

Arquitectura optimizada:
- Búsqueda rápida sin LLM (<100ms)
- Explicaciones solo bajo demanda (click en "🤖 ¿Por qué es relevante?")
- Sin re-ranking automático

Uso:
    streamlit run app_v10_fast.py --server.port 8503
"""

import streamlit as st
import requests
import time
from typing import Optional

# Configuración de API
API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Buscador Semántico V10 - Rápido",
    page_icon="⚡",
    layout="wide"
)

# CSS personalizado
st.markdown("""
<style>
    .dataset-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #e9ecef;
    }
    .dataset-title {
        font-size: 1.1em;
        font-weight: bold;
        color: #1a73e8;
        margin-bottom: 10px;
    }
    .dataset-meta {
        font-size: 0.85em;
        color: #666;
        margin-bottom: 10px;
    }
    .explanation-box {
        background-color: #e8f4fd;
        border-left: 4px solid #1a73e8;
        padding: 15px;
        margin-top: 10px;
        border-radius: 5px;
    }
    .speed-badge {
        display: inline-block;
        background-color: #e6f4ea;
        color: #137333;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.75em;
        font-weight: bold;
        margin-left: 10px;
    }
</style>
""", unsafe_allow_html=True)


def fast_search(query: str, top_k: int = 10, semantic_weight: float = 0.75, lexical_weight: float = 0.25) -> Optional[dict]:
    """Búsqueda rápida sin LLM."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/llm/search/fast",
            json={
                "query": query,
                "limit": top_k,
                "semantic_weight": semantic_weight,
                "lexical_weight": lexical_weight
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error en búsqueda: {e}")
        return None


def get_explanation(query: str, dataset_id: str) -> Optional[dict]:
    """Obtener explicación bajo demanda."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/llm/explain",
            json={
                "query": query,
                "dataset_id": dataset_id
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None


def render_dataset_card(result: dict, query: str, index: int) -> None:
    """Renderizar tarjeta de dataset con explicación bajo demanda."""

    col1, col2 = st.columns([5, 1])

    with col1:
        st.markdown(f"""
        <div class="dataset-card">
            <div class="dataset-title">
                #{index} {result.get('title', 'Sin título')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.metric("Score", f"{result.get('score', 0):.3f}")

    # Metadatos
    col_meta1, col_meta2, col_meta3 = st.columns(3)
    with col_meta1:
        st.caption(f"📁 Tema: {result.get('theme', 'N/A')}")
    with col_meta2:
        st.caption(f"📍 Territorio: {result.get('territory', 'N/A')}")
    with col_meta3:
        st.caption(f"🏢 Publisher: {result.get('publisher', 'N/A')}")

    # Descripción
    st.markdown(f"**Descripción**: {result.get('description', 'Sin descripción')[:300]}...")

    # Botón para explicación bajo demanda
    explanation_key = f"explain_{result.get('dataset_id', index)}"

    if st.button("🤖 ¿Por qué es relevante?", key=explanation_key, type="secondary"):
        with st.spinner("Generando explicación con LLM..."):
            start = time.time()
            explanation = get_explanation(query, result.get('dataset_id', ''))
            elapsed = time.time() - start

            if explanation:
                st.markdown(f"""
                <div class="explanation-box">
                    <strong>📊 Relevancia:</strong> {explanation.get('relevance_score', 0)}/10<br><br>
                    <strong>💡 Explicación:</strong> {explanation.get('explanation', '')}<br><br>
                    <strong>🔍 Factores:</strong>
                    <ul>
                """, unsafe_allow_html=True)

                for factor in explanation.get('factors', []):
                    st.markdown(f"  - **{factor.get('factor', '')}** ({factor.get('score', 0):.1f}): {factor.get('description', '')}")

                st.markdown(f"""
                    </ul>
                    <small>⏱️ Generado en {elapsed:.1f}s (modelo: {explanation.get('metadata', {}).get('model', 'unknown')})</small>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("No se pudo generar la explicación. Inténtalo de nuevo.")

    st.divider()


def main():
    st.title("⚡ Buscador Semántico V10")
    st.markdown("""
    **Arquitectura optimizada**: Búsqueda rápida (<100ms) + Explicaciones bajo demanda.

    - ✅ Sin re-ranking automático
    - ✅ Explicaciones solo cuando las pides
    - ✅ Resultados instantáneos
    """)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")

        top_k = st.slider("Resultados", 5, 20, 10)
        semantic_weight = st.slider("Peso semántico", 0.0, 1.0, 0.75, 0.05)
        lexical_weight = st.slider("Peso léxico", 0.0, 1.0, 0.25, 0.05)

        st.info("""
        ### 📊 Comparativa
        | Modo | Tiempo | Calidad |
        |------|--------|---------|
        | V10 Fast | <0.1s | Base |
        | V09 + LLM | ~40s | Similar |
        """)

    # Input de búsqueda
    query = st.text_input(
        "🔍 Buscar datasets",
        placeholder="Ej: paro juvenil Canarias 2023",
        key="query_input"
    )

    # Estado en session
    if "last_results" not in st.session_state:
        st.session_state.last_results = None
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""
    if "search_time" not in st.session_state:
        st.session_state.search_time = 0

    # Ejecutar búsqueda
    if query:
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            search_btn = st.button("🔍 Buscar", type="primary", use_container_width=True)

        if search_btn or st.session_state.last_query == query:
            with st.spinner("Buscando..."):
                start = time.time()
                results = fast_search(
                    query,
                    top_k=top_k,
                    semantic_weight=semantic_weight,
                    lexical_weight=lexical_weight
                )
                elapsed = time.time() - start

                if results and results.get('results'):
                    st.session_state.last_results = results['results']
                    st.session_state.last_query = query
                    st.session_state.search_time = elapsed

                    # Mostrar resultados
                    st.success(f"✅ {len(results['results'])} resultados encontrados en {elapsed*1000:.0f}ms")

                    # Speed badge
                    if elapsed < 0.1:
                        st.markdown('<span class="speed-badge">⚡ Ultra rápido</span>', unsafe_allow_html=True)
                    elif elapsed < 0.5:
                        st.markdown('<span class="speed-badge">🚀 Rápido</span>', unsafe_allow_html=True)

                    # Renderizar tarjetas
                    st.markdown("---")
                    for i, result in enumerate(results['results'], 1):
                        render_dataset_card(result, query, i)
                else:
                    st.warning("No se encontraron resultados.")
                    st.session_state.last_results = None

    # Mostrar resultados previos si existen
    elif st.session_state.last_results:
        st.info(f"📊 Última búsqueda: '{st.session_state.last_query}' - {len(st.session_state.last_results)} resultados")
        for i, result in enumerate(st.session_state.last_results, 1):
            render_dataset_card(result, st.session_state.last_query, i)


if __name__ == "__main__":
    main()
