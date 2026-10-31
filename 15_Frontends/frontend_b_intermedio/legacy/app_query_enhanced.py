#!/usr/bin/env python3
"""
Frontend Streamlit para Query Preprocessor (#3, #4, #12)
Fase 08: Sprint 6 - Mejoras con LLM

Permite probar interactivamente:
- Validación semántica de queries (#12)
- Interpretación estructurada (#3)
- Expansión semántica (#4)
- Comparación de búsquedas

Uso:
    source venv/bin/activate
    streamlit run app_query_enhanced.py --server.port 8503
"""

import sys
import os
from pathlib import Path
import time
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import streamlit as st

# Configurar paths
# El módulo query_preprocessor vive en 08_Sprint6_LLM_Mejora/codigo/motor/
project_root = Path(__file__).parent.parent.parent.parent / "08_Sprint6_LLM_Mejora/codigo"
sys.path.insert(0, str(project_root / "motor"))

from query_preprocessor import QueryPreprocessor, get_preprocessor

# Configuración de página
st.set_page_config(
    page_title="Query Preprocessor - Demo",
    page_icon="🔍",
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
    .valid-query {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 10px;
        border-radius: 4px;
    }
    .invalid-query {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 10px;
        border-radius: 4px;
    }
    .warning-query {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 10px;
        border-radius: 4px;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .expansion-term {
        display: inline-block;
        background-color: #e3f2fd;
        color: #1565c0;
        padding: 4px 8px;
        margin: 2px;
        border-radius: 12px;
        font-size: 0.9em;
    }
    .original-term {
        display: inline-block;
        background-color: #c8e6c9;
        color: #2e7d32;
        padding: 4px 8px;
        margin: 2px;
        border-radius: 12px;
        font-size: 0.9em;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_cached_preprocessor():
    """Obtener pre-procesador con cache."""
    return get_preprocessor(verbose=False, use_persistent_cache=True)


def check_api_health():
    """Verificar si la API está disponible."""
    try:
        response = requests.get(
            "http://localhost:8000/health",
            timeout=5,
            verify=False
        )
        return response.status_code == 200
    except:
        return False


def search_with_query(query: str, use_enhanced: bool = False, use_strict_filters: bool = False) -> dict:
    """Ejecutar búsqueda en la API."""
    try:
        if use_enhanced:
            # Usar preprocesador local + API base
            preprocessor = get_cached_preprocessor()
            preprocessed = preprocessor.process(query, apply_strict_filters=use_strict_filters)

            if not preprocessed.validation.is_valid:
                return {
                    "query_original": query,
                    "query_expandida": query,
                    "is_valid": False,
                    "alertas": preprocessed.validation.alertas,
                    "results": []
                }

            # Buscar con query expandida
            query_buscar = preprocessed.expansion.query_expandida
            response = requests.post(
                "http://localhost:8000/search",
                json={"query": query_buscar, "limit": 5},
                timeout=30,
                verify=False
            )
            response.raise_for_status()
            search_results = response.json()

            return {
                "query_original": query,
                "query_expandida": query_buscar,
                "is_valid": True,
                "intencion": preprocessed.validation.intencion,
                "temas_detectados": preprocessed.structure.temas,
                "territorio_detectado": preprocessed.structure.territorio,
                "terminos_añadidos": preprocessed.expansion.terminos_añadidos,
                "results": search_results.get("results", []),
                "total_results": search_results.get("total_results", 0),
                "metadata": {"duration_ms": preprocessed.metadata.get("duration_ms", 0)}
            }
        else:
            response = requests.post(
                "http://localhost:8000/search",
                json={"query": query, "limit": 5},
                timeout=30,
                verify=False
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": str(e), "results": []}
    """Ejecutar búsqueda en la API."""
    try:
        if use_enhanced:
            response = requests.post(
                "http://localhost:8000/enhanced/search",
                json={
                    "query": query,
                    "limit": 5,
                    "use_expansion": True,
                    "use_filters": use_strict_filters
                },
                timeout=60,
                verify=False
            )
        else:
            response = requests.post(
                "http://localhost:8000/search",
                json={"query": query, "limit": 5},
                timeout=30,
                verify=False
            )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "results": []}


def main():
    st.title("🔍 Query Preprocessor - Demo Interactivo")
    st.markdown("""
    **Propuestas #3, #4, #12:** Interpretación estructurada + Expansión semántica + Validación

    Este demo muestra cómo el LLM mejora las queries antes de buscar.
    """)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")

        st.subheader("Modo de Operación")
        modo = st.radio(
            "Selecciona modo:",
            ["Análisis de Query", "Comparación de Búsquedas", "Panel de Debug"]
        )

        st.divider()

        st.subheader("🔧 Opciones de Búsqueda")
        use_strict_filters = st.toggle(
            "Filtros estrictos (theme, territory, año)",
            value=False,
            help="Si está activado, filtra datasets que coincidan EXACTAMENTE con los metadatos detectados. Si está desactivado (recomendado), busca con la query expandida sin restricciones."
        )

        st.divider()

        st.subheader("Estado del Sistema")
        api_online = check_api_health()
        if api_online:
            st.success("🟢 API Online")
        else:
            st.error("🔴 API Offline")
            st.info("Asegúrate de que el servidor FastAPI esté corriendo en :8000")

        st.divider()

        st.subheader("Ejemplos de Query")
        ejemplos = {
            "Económica": "paro juvenil Canarias 2023",
            "Social": "vulnerabilidad económica juventud",
            "Territorial": "turismo Barcelona 2024",
            "Ambigua": "banco España",
            "Inválida": "turismo en la luna",
            "Vaga": "datos interesantes",
        }

        for nombre, query in ejemplos.items():
            if st.button(f"📋 {nombre}", key=f"btn_{nombre}"):
                st.session_state.query_input = query
                st.rerun()

    # Main content
    if modo == "Análisis de Query":
        render_analisis_mode(api_online, use_strict_filters)
    elif modo == "Comparación de Búsquedas":
        render_comparacion_mode(api_online, use_strict_filters)
    else:
        render_debug_mode()


def render_analisis_mode(api_online: bool, use_strict_filters: bool = False):
    """Renderizar modo de análisis de query."""
    st.header("🔬 Análisis de Query")

    # Input de query - vacío por defecto
    query = st.text_input(
        "Escribe tu query:",
        value=st.session_state.get("query_input", ""),
        placeholder="Ej: paro juvenil Canarias 2023",
        key="query_input"
    )

    if not query:
        st.info("👆 Escribe una query para analizar")
        return

    # Mostrar modo de búsqueda
    if use_strict_filters:
        st.warning("🔒 Modo estricto: Se aplicarán filtros de theme, territory y año exactos. Puede excluir resultados relevantes.")
    else:
        st.info("🔓 Modo flexible: Búsqueda semántica sin restricciones estructurales. Recomendado para mejor recall.")

    # Procesar query
    with st.spinner("🧠 Analizando con LLM..."):
        start_time = time.time()
        preprocessor = get_cached_preprocessor()
        result = preprocessor.process(query, apply_strict_filters=use_strict_filters)
        duration = (time.time() - start_time) * 1000

    # Mostrar validación
    st.subheader("✅ Validación (#12)")

    if result.validation.is_valid:
        if result.validation.alertas:
            st.markdown(f"""
            <div class="warning-query">
                <strong>⚠️ Query Válida pero con Alertas</strong><br>
                Intención: {result.validation.intencion} |
                Confianza: {result.validation.confianza:.0%}
            </div>
            """, unsafe_allow_html=True)
            for alerta in result.validation.alertas:
                st.warning(alerta)
        else:
            st.markdown(f"""
            <div class="valid-query">
                <strong>✅ Query Válida</strong><br>
                Intención: <strong>{result.validation.intencion}</strong> |
                Confianza: {result.validation.confianza:.0%}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="invalid-query">
            <strong>❌ Query Inválida</strong><br>
            Confianza: {result.validation.confianza:.0%}
        </div>
        """, unsafe_allow_html=True)

        for alerta in result.validation.alertas:
            st.error(alerta)

        if result.validation.sugerencia_correccion:
            st.info(f"💡 ¿Quisiste decir: **{result.validation.sugerencia_correccion}**?")

        return  # No continuar si es inválida

    # Mostrar estructura
    st.subheader("📊 Estructura Extraída (#3)")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("🎯 Temas Detectados", len(result.structure.temas))
        for tema in result.structure.temas:
            st.markdown(f"<div class='expansion-term'>{tema}</div>", unsafe_allow_html=True)

    with col2:
        st.metric("🌍 Territorio", result.structure.territorio or "No detectado")
        st.metric("📅 Años",
                 ", ".join(map(str, result.structure.años)) if result.structure.años else "No detectado")
        if result.structure.edad_rango:
            st.metric("👥 Rango Edad", result.structure.edad_rango)

    with col3:
        st.metric("💡 Conceptos Implícitos", len(result.structure.conceptos_implicitos))
        for concepto in result.structure.conceptos_implicitos[:5]:
            st.markdown(f"<div class='expansion-term'>{concepto}</div>", unsafe_allow_html=True)

    # Mostrar filtros DCAT
    if result.structure.filtros_dcat:
        st.subheader("🏷️ Filtros DCAT Detectados")
        for key, value in result.structure.filtros_dcat.items():
            st.markdown(f"**{key}:** `{value}`")

    # Mostrar expansión
    st.subheader("🔍 Expansión Semántica (#4)")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("**Query Original:**")
        terms_original = query.split()
        for term in terms_original:
            st.markdown(f"<span class='original-term'>{term}</span>", unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)

        st.markdown("**Query Expandida:**")
        terms_expanded = result.expansion.query_expandida.split()
        for term in terms_expanded[:20]:  # Limitar visualización
            if term.lower() in [t.lower() for t in terms_original]:
                st.markdown(f"<span class='original-term'>{term}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='expansion-term'>{term}</span>", unsafe_allow_html=True)

    with col2:
        st.metric("Términos Añadidos", len(result.expansion.terminos_añadidos))
        for term in result.expansion.terminos_añadidos[:8]:
            st.markdown(f"<div class='expansion-term'>{term}</div>", unsafe_allow_html=True)

    # Métricas de tiempo
    st.divider()
    cols = st.columns(4)
    cols[0].metric("⏱️ Tiempo Total", f"{duration:.0f}ms")
    cols[1].metric("🧠 Modelo LLM", result.metadata.get("model", "N/A"))
    cols[2].metric("💾 Cache", "Hit" if result.metadata.get("cached") else "Miss")

    # Botón para buscar
    if api_online:
        st.divider()
        if st.button("🔎 Buscar con Query Mejorada", type="primary", use_container_width=True):
            with st.spinner("Buscando..."):
                search_result = search_with_query(query, use_enhanced=True, use_strict_filters=use_strict_filters)

                if "results" in search_result:
                    st.success(f"✅ {search_result.get('total_results', len(search_result['results']))} resultados encontrados")

                    # Mostrar query expandida
                    if "query_expandida" in search_result:
                        st.info(f"🔍 Query usada: {search_result['query_expandida'][:100]}...")

                    # Mostrar términos añadidos
                    if "terminos_añadidos" in search_result and search_result["terminos_añadidos"]:
                        st.caption(f"Términos añadidos: {', '.join(search_result['terminos_añadidos'][:10])}")

                    for i, r in enumerate(search_result["results"][:5], 1):
                        with st.expander(f"{i}. {r.get('title', 'Sin título')[:60]}..."):
                            st.write(f"**Descripción:** {r.get('description', 'N/A')[:200]}")
                            st.write(f"**Publisher:** {r.get('publisher', 'N/A')}")
                            st.write(f"**Territorio:** {r.get('territory', 'N/A')}")
                            st.write(f"**Score:** {r.get('score', 0):.3f}")
                else:
                    st.error(f"Error en búsqueda: {search_result.get('error', 'Desconocido')}")


def render_comparacion_mode(api_online: bool, use_strict_filters: bool = False):
    """Renderizar modo de comparación."""
    st.header("⚖️ Comparación: Búsqueda Normal vs Mejorada")

    if not api_online:
        st.error("🔴 La API no está disponible. No se puede hacer comparación.")
        return

    query = st.text_input(
        "Query para comparar:",
        value=st.session_state.get("query_input", ""),
        placeholder="Ej: paro juvenil Canarias 2023",
        key="query_compare"
    )

    if not query:
        st.info("👆 Escribe una query para comparar")
        return

    # Mostrar modo
    if use_strict_filters:
        st.warning("🔒 Modo estricto activado: Filtros de theme/territory/año aplicados")
    else:
        st.info("🔓 Modo flexible: Búsqueda semántica sin restricciones estructurales")

    if st.button("🚀 Comparar Búsquedas", type="primary", use_container_width=True):
        col1, col2 = st.columns(2)

        # Búsqueda normal
        with col1:
            st.subheader("🔍 Búsqueda Normal")
            with st.spinner("Buscando..."):
                start = time.time()
                result_normal = search_with_query(query, use_enhanced=False)
                time_normal = (time.time() - start) * 1000

            st.metric("Tiempo", f"{time_normal:.0f}ms")
            st.metric("Resultados", len(result_normal.get("results", [])))

            for r in result_normal.get("results", [])[:3]:
                with st.expander(f"📄 {r.get('title', 'N/A')[:50]}..."):
                    st.write(f"Score: {r.get('score', 0):.3f}")

        # Búsqueda mejorada
        with col2:
            st.subheader("✨ Búsqueda Mejorada")
            with st.spinner("Procesando + Buscando..."):
                start = time.time()
                result_enhanced = search_with_query(query, use_enhanced=True, use_strict_filters=use_strict_filters)
                time_enhanced = (time.time() - start) * 1000

            st.metric("Tiempo", f"{time_enhanced:.0f}ms")
            st.metric("Resultados", len(result_enhanced.get("results", [])))

            if "query_expandida" in result_enhanced:
                st.info(f"Query expandida: {result_enhanced['query_expandida'][:100]}...")

            for r in result_enhanced.get("results", [])[:3]:
                with st.expander(f"📄 {r.get('title', 'N/A')[:50]}..."):
                    st.write(f"Score: {r.get('score', 0):.3f}")

        # Análisis comparativo
        st.divider()
        st.subheader("📈 Análisis Comparativo")

        normal_count = len(result_normal.get("results", []))
        enhanced_count = len(result_enhanced.get("results", []))

        cols = st.columns(3)
        cols[0].metric("Diferencia en Resultados", enhanced_count - normal_count)
        cols[1].metric("Overhead de Tiempo", f"{time_enhanced - time_normal:.0f}ms")
        ratio = f"{time_enhanced/time_normal:.1f}x" if time_normal > 0 else "N/A"
        cols[2].metric("Ratio", ratio)


def render_debug_mode():
    """Renderizar modo debug."""
    st.header("🐛 Panel de Debug")

    preprocessor = get_cached_preprocessor()

    # Info del pre-procesador
    st.subheader("ℹ️ Información del Pre-procesador")

    col1, col2 = st.columns(2)
    with col1:
        st.write("**Configuración:**")
        st.json({
            "model": preprocessor.llm.model,
            "temperature": preprocessor.llm.temperature,
            "timeout": preprocessor.llm.timeout,
            "cache_memory_size": len(preprocessor._memory_cache),
        })

    with col2:
        st.write("**Cache Persistente:**")
        if preprocessor._persistent_cache:
            st.json({
                "db_path": preprocessor._persistent_cache.db_path,
                "ttl_hours": CACHE_TTL_HOURS,
                "status": "Activo"
            })
        else:
            st.write("No activo")

    # Herramientas de mantenimiento
    st.divider()
    st.subheader("🔧 Mantenimiento")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Limpiar Cache de Memoria", use_container_width=True):
            preprocessor._memory_cache.clear()
            st.success("✅ Cache de memoria limpiado")

    with col2:
        if st.button("🗑️ Limpiar Cache Persistente", use_container_width=True):
            if preprocessor._persistent_cache:
                preprocessor._persistent_cache.clear()
                st.success("✅ Cache persistente limpiado")

    # Test manual
    st.divider()
    st.subheader("🧪 Test Manual")

    test_query = st.text_input("Query de prueba:", value="", placeholder="Ej: paro juvenil")

    if st.button("Ejecutar Test", use_container_width=True):
        with st.spinner("Procesando..."):
            import time
            t0 = time.time()
            result = preprocessor.process(test_query, use_cache=True)
            t1 = time.time()

            st.write(f"**Tiempo:** {(t1-t0)*1000:.1f}ms")
            st.write(f"**Cache:** {'Hit' if result.metadata.get('cached') else 'Miss'}")
            st.json({
                "validation": {
                    "is_valid": result.validation.is_valid,
                    "intencion": result.validation.intencion,
                    "confianza": result.validation.confianza,
                },
                "structure": {
                    "temas": result.structure.temas,
                    "territorio": result.structure.territorio,
                },
                "expansion": {
                    "terminos_añadidos": result.expansion.terminos_añadidos,
                }
            })


if __name__ == "__main__":
    main()
