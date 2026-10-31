#!/usr/bin/env python3
"""
Frontend Streamlit para Caso #13 - Sugerencias de Queries Relacionadas
Fase 08: Sprint 6 - Mejoras con LLM

Permite probar interactivamente:
- Sugerencias léxicas instantáneas (<5ms)
- Sugerencias LLM en background (~3-5s)
- Enfoque híbrido asíncrono con polling

Uso:
    source venv/bin/activate
    streamlit run app_v13_query_suggestions.py --server.port 8501
"""

import sys
import os
from pathlib import Path
import time
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import streamlit as st

# Configuración
API_URL = "http://localhost:8000"

# Configuración de página
st.set_page_config(
    page_title="#13 Query Suggestions - Demo",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar y mostrar logo
ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_PATH = ASSETS_DIR / "logo_buscador_semantico.png"

if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), use_container_width=True)
    st.sidebar.divider()

# CSS personalizado
st.markdown("""
<style>
    .suggestion-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        border-left: 4px solid #007bff;
    }
    .suggestion-card:hover {
        background-color: #e9ecef;
        cursor: pointer;
    }
    .suggestion-lexical {
        border-left-color: #28a745;
    }
    .suggestion-llm {
        border-left-color: #6f42c1;
    }
    .category-badge {
        display: inline-block;
        background-color: #e3f2fd;
        color: #1565c0;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: bold;
        margin-right: 6px;
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #007bff;
    }
    .metric-label {
        font-size: 0.9em;
        color: #6c757d;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """Verificar estado de la API y sugerencias."""
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5, verify=False)
        api_ok = resp.status_code == 200

        resp_suggest = requests.get(f"{API_URL}/enhanced/query/suggest/health", timeout=5, verify=False)
        suggest_ok = resp_suggest.status_code == 200

        return {"api_ok": api_ok, "suggest_ok": suggest_ok}
    except Exception as e:
        return {"api_ok": False, "suggest_ok": False, "error": str(e)}


def get_lexical_suggestions(query: str, n: int = 5) -> dict:
    """Obtener sugerencias léxicas (rápido)."""
    try:
        resp = requests.get(
            f"{API_URL}/enhanced/query/suggest/lexical",
            params={"query": query, "n": n},
            timeout=10,
            verify=False
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def get_combined_suggestions(query: str, n: int = 5) -> tuple:
    """
    Obtener sugerencias combinadas (léxico + LLM con polling).

    Returns:
        tuple: (lexical_data, complete_data)
    """
    try:
        # Paso 1: Petición inicial (retorna léxico + poll_url)
        resp = requests.post(
            f"{API_URL}/enhanced/query/suggest",
            json={"query": query, "n": n},
            timeout=10,
            verify=False
        )
        resp.raise_for_status()
        initial_data = resp.json()

        poll_url = initial_data.get("poll_url")
        if not poll_url:
            return initial_data, initial_data

        # Paso 2: Polling (esperar hasta 45s - LLM puede tardar 6-15s en primera llamada)
        max_attempts = 90
        for i in range(max_attempts):
            time.sleep(0.5)

            resp_poll = requests.get(
                f"{API_URL}{poll_url}",
                timeout=5,
                verify=False
            )

            if resp_poll.status_code == 200:
                complete_data = resp_poll.json()
                if not complete_data.get("llm_pending", True):
                    return initial_data, complete_data

        # Timeout: retornar lo que hay
        return initial_data, initial_data

    except Exception as e:
        return {"error": str(e)}, {"error": str(e)}


def render_suggestion_card(suggestion: dict, index: int, is_llm: bool = False):
    """Renderizar una tarjeta de sugerencia con botón de copiar funcional."""
    category = suggestion.get("category", "desconocida")
    text = suggestion.get("text", "")
    reason = suggestion.get("reason", "")
    confidence = suggestion.get("confidence", 0)

    # Badge de categoría con color
    category_colors = {
        "sinonimo": "#28a745",
        "temporal": "#17a2b8",
        "territorial": "#fd7e14",
        "tecnica": "#6f42c1",
        "especificacion": "#e83e8c",
        "llm": "#6610f2",
        "generalizacion": "#007bff",
        "relacionada": "#6c757d",
    }
    color = category_colors.get(category, "#6c757d")

    # Usar columnas para layout
    col_text, col_copy = st.columns([6, 1])

    with col_text:
        # Badge de categoría
        st.markdown(f"""
        <div class="suggestion-card" style="border-left: 4px solid {color}; padding-left: 10px;">
            <span style="display: inline-block; background-color: {color}20; color: {color}; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; font-weight: bold; margin-right: 6px;">
                {category.upper()}
            </span>
            <strong>{text}</strong>
        </div>
        """, unsafe_allow_html=True)

    with col_copy:
        # Botón funcional de copiar
        if st.button("💾", key=f"copy_{index}_{text[:20]}", help=f"Copiar: {text}"):
            st.code(text, language=None)
            st.success(f"✅ Copiado: `{text}`")

    # Razón y confianza
    st.markdown(f"""
    <div style="margin-left: 10px; margin-top: 8px;">
        <div style="font-size: 0.85em; color: #495057;">
            💡 {reason}
        </div>
        <div style="width: 100%; background-color: #e9ecef; border-radius: 4px; height: 6px; margin-top: 6px;">
            <div style="width: {confidence*100}%; background-color: {color}; height: 6px; border-radius: 4px;"></div>
        </div>
        <div style="font-size: 0.75em; color: #6c757d; margin-top: 2px;">
            Confianza: {confidence:.0%}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==================== SIDEBAR ====================

st.sidebar.header("Configuración")

num_suggestions = st.sidebar.slider(
    "Número de sugerencias",
    min_value=3,
    max_value=10,
    value=5
)

use_llm = st.sidebar.checkbox(
    "Activar LLM (background)",
    value=True,
    help="Si está activado, se mostrarán sugerencias adicionales del LLM después de ~3-5s"
)

st.sidebar.divider()

st.sidebar.header("Acerca de")
st.sidebar.markdown("""
**Caso #13 - Query Suggestions**

Enfoque híbrido asíncrono:
- **Léxico**: <5ms, basado en diccionario
- **LLM**: ~3-5s, creativo y contextual

**Categorías:**
- 🔤 Sinónimo
- 📅 Temporal
- 🌍 Territorial
- 🎯 Técnica
- 📋 Especificación
""")

# ==================== MAIN ====================

# Header
st.title("💡 Sugerencias de Queries Relacionadas")
st.markdown("**Caso #13** - Sprint 6: Mejoras con LLM")

# Check health
health = check_api_health()
if not health.get("api_ok"):
    st.error(f"❌ API no disponible: {health.get('error', 'Error desconocido')}")
    st.info("Asegúrate de que la API esté corriendo en `http://localhost:8000`")
    st.stop()

if not health.get("suggest_ok"):
    st.warning("⚠️ Endpoint de sugerencias no disponible. Asegúrate de que `routes_query_enhanced.py` esté cargado.")

# Query input
st.subheader("🔍 Probar Sugerencias")
st.markdown("Escribe una query y obtén sugerencias relacionadas instantáneamente. **Presiona Enter** para buscar.")

# Usar form para permitir Enter
with st.form(key="search_form"):
    query = st.text_input(
        "Query del usuario",
        value=st.session_state.get("last_query", ""),
        placeholder="Ej: paro juvenil Canarias 2023",
        help="Escribe una query relacionada con datos abiertos españoles"
    )
    search_btn = st.form_submit_button("🔍 Buscar sugerencias", type="primary", use_container_width=True)

# Guardar query en session_state
if query:
    st.session_state["last_query"] = query

if not search_btn or not query:
    if not query:
        st.info("👆 Escribe una query arriba y presiona Enter para comenzar")
    st.stop()

# ==================== EXECUTE SEARCH ====================

# Contenedor para resultados
results_container = st.container()

with results_container:
    # Placeholder para actualizar progresivamente
    lexical_placeholder = st.empty()
    llm_placeholder = st.empty()
    status_placeholder = st.empty()

    # Medir tiempo
    start_time = time.time()

    # Step 1: Obtener sugerencias léxicas (inmediato)
    with st.spinner("⚡ Obteniendo sugerencias léxicas..."):
        lexical_data = get_lexical_suggestions(query, n=num_suggestions)

    lexical_time = time.time() - start_time

    # Mostrar sugerencias léxicas
    if "error" not in lexical_data:
        lexical_placeholder.markdown(f"### ⚡ Sugerencias Léxicas ({lexical_time*1000:.1f}ms)")

        suggestions = lexical_data.get("suggestions", [])
        if suggestions:
            for i, sug in enumerate(suggestions):
                render_suggestion_card(sug, i, is_llm=False)
        else:
            lexical_placeholder.info("No se encontraron sugerencias léxicas.")

        # Step 2: Si LLM está activado, hacer polling
        if use_llm:
            status_placeholder.info("🔄 Obteniendo sugerencias del LLM (puede tardar 5-15s en la primera llamada)...")

            # Obtener completas con polling
            _, complete_data = get_combined_suggestions(query, n=num_suggestions)

            llm_time = time.time() - start_time

            if "error" not in complete_data and complete_data.get("llm_count", 0) > 0:
                status_placeholder.success(f"✅ Completado en {llm_time:.1f}s")

                llm_placeholder.markdown(f"### 🤖 Sugerencias Completas (Léxico + LLM) - {llm_time:.1f}s")

                all_suggestions = complete_data.get("suggestions", [])

                # Separar léxicas vs LLM
                lexical_sugs = [s for s in all_suggestions if s.get("source") == "lexical"]
                llm_sugs = [s for s in all_suggestions if s.get("source") == "llm"]

                # Mostrar todas las sugerencias en una sola columna (más claro)
                st.markdown(f"**📊 Total: {len(all_suggestions)} sugerencias** ({len(lexical_sugs)} léxicas + {len(llm_sugs)} del LLM)")

                for sug in all_suggestions:
                    is_llm_sug = sug.get("source") == "llm"
                    render_suggestion_card(sug, 0, is_llm=is_llm_sug)
            else:
                status_placeholder.warning("⏱️ Timeout: El LLM no respondió a tiempo. Mostrando solo sugerencias léxicas.")
    else:
        lexical_placeholder.error(f"Error: {lexical_data.get('error')}")

# ==================== METRICS ====================

st.divider()
st.subheader("📊 Métricas")

if "error" not in lexical_data:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div style="text-align: center;">
            <div class="metric-value">{lexical_time*1000:.0f}ms</div>
            <div class="metric-label">Latencia Léxico</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="text-align: center;">
            <div class="metric-value">{lexical_data.get('lexical_count', 0)}</div>
            <div class="metric-label">Sugerencias Léxicas</div>
        </div>
        """, unsafe_allow_html=True)

    if use_llm and "error" not in complete_data:
        with col3:
            st.markdown(f"""
            <div style="text-align: center;">
                <div class="metric-value">{complete_data.get('llm_count', 0)}</div>
                <div class="metric-label">Sugerencias LLM</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            total = complete_data.get('total_count', 0)
            st.markdown(f"""
            <div style="text-align: center;">
                <div class="metric-value">{total}</div>
                <div class="metric-label">Total Únicas</div>
            </div>
            """, unsafe_allow_html=True)

# ==================== QUERY EXAMPLES ====================

st.divider()
st.subheader("📋 Queries de Ejemplo")

example_queries = [
    "paro juvenil Canarias",
    "vulnerabilidad económica",
    "turismo Barcelona 2023",
    "población mayor 65 años",
    "abandono escolar temprano",
]

cols = st.columns(len(example_queries))
for i, example in enumerate(example_queries):
    with cols[i]:
        if st.button(example, key=f"example_{i}", use_container_width=True):
            st.session_state["query"] = example
            st.rerun()

# ==================== FOOTER ====================

st.divider()
st.markdown("""
<div style="text-align: center; color: #6c757d; font-size: 0.85em;">
    <strong>Caso #13 - Sugerencias de Queries Relacionadas</strong><br>
    Enfoque híbrido asíncrono: léxico (<5ms) + LLM background (~3-5s)<br>
    Documentación: <code>08_Sprint6_LLM_Mejora/docs/CASO_13_QUERY_SUGGESTIONS.md</code>
</div>
""", unsafe_allow_html=True)
