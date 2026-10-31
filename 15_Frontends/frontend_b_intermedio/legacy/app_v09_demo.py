#!/usr/bin/env python3
"""
Frontend Demo V09 - Prueba de Endpoints LLM
===========================================

Versión del frontend que permite probar los nuevos endpoints:
- /llm/enhance (búsqueda con re-ranking LLM)
- /llm/explain (explicaciones de relevancia)

Ejecutar:
    cd ~/datos/PFM/Datatrust/15_Frontends/frontend_c_avanzado
    streamlit run app_v09_demo.py --server.port 8502

Requiere:
    - API corriendo (main_v2_final_v07.py con router_v09 cargado)
    - Ollama disponible
"""

import os
import sys
from pathlib import Path
import requests
import urllib3

# Suprimir advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Importar componentes del frontend básico (ruta absoluta)
FRONTEND_A_DIR = Path(__file__).parent.parent / "frontend_a_basico"
sys.path.insert(0, str(FRONTEND_A_DIR))

try:
    import streamlit as st
    from components import render_header, render_result_card
except ImportError:
    print("Error: streamlit no está instalado. Ejecuta: pip install streamlit")
    sys.exit(1)

# Configuración
API_URL = "http://localhost:8000"

# Configuración de página
st.set_page_config(
    page_title="Demo V09 - LLM Features",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def check_api_health():
    """Verifica estado de la API y del módulo LLM."""
    try:
        # Check API base
        resp = requests.get(f"{API_URL}/health", timeout=5, verify=False)
        if resp.status_code != 200:
            return {"api_ok": False, "error": "API no responde"}

        # Check LLM module
        resp_llm = requests.get(f"{API_URL}/llm/health", timeout=5, verify=False)
        if resp_llm.status_code == 200:
            llm_data = resp_llm.json()
            return {
                "api_ok": True,
                "llm_ok": llm_data.get("ollama_available", False),
                "model": llm_data.get("reranker_model", "N/A")
            }
        else:
            return {"api_ok": True, "llm_ok": False, "error": "Router LLM no cargado"}

    except Exception as e:
        return {"api_ok": False, "error": str(e)}


def search_llm_enhance(query, limit=10, rerank_top_n=15):
    """Llama al endpoint /llm/search/rerank."""
    try:
        with st.spinner("🤖 Re-ranking con LLM (puede tardar unos segundos)..."):
            # Primero obtener resultados estándar para tener las URLs
            resp_std = requests.post(
                f"{API_URL}/search",
                json={"query": query, "top_k": rerank_top_n * 2},  # Más resultados para cubrir el rerank
                timeout=10,
                verify=False
            )
            resp_std.raise_for_status()
            std_data = resp_std.json()
            # Crear mapa de dataset_id -> url
            url_map = {r.get("id"): r.get("url", "#") for r in std_data.get("results", [])}

            # Ahora llamar al endpoint LLM
            resp = requests.post(
                f"{API_URL}/llm/search/rerank",
                json={
                    "query": query,
                    "limit": limit,
                    "rerank_top_n": rerank_top_n,
                    "include_explanations": True
                },
                timeout=120,
                verify=False
            )
            resp.raise_for_status()
            data = resp.json()
            # Normalizar resultados para que coincidan con el formato de render_result_card
            results = []
            for r in data.get("results", []):
                dataset_id = r.get("dataset_id")
                results.append({
                    "dataset_id": dataset_id,
                    "title": r.get("title"),
                    "description": r.get("description"),
                    "publisher": r.get("publisher"),
                    "territorio": r.get("territory", []),
                    "tema": r.get("theme", []),
                    "formato": r.get("format", []),
                    "url": url_map.get(dataset_id, dataset_id),  # Usar URL del estándar o dataset_id como fallback
                    "score": r.get("llm_relevance_score", 0) / 10.0,  # Normalizar a 0-1
                    "score_final": r.get("llm_relevance_score", 0),
                    "original_rank": r.get("original_rank", 0),
                    "new_rank": r.get("new_rank", 0),
                    "explanation": r.get("explanation", "")
                })
            return {"query": query, "results": results, "metadata": data.get("metadata", {})}
    except requests.exceptions.Timeout:
        st.error("⏱️ Timeout: El LLM está tardando demasiado. Inténtalo de nuevo.")
        return None
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None


def search_standard(query, limit=10):
    """Llama al endpoint /search estándar."""
    try:
        resp = requests.post(
            f"{API_URL}/search",
            json={"query": query, "top_k": limit},
            timeout=10,
            verify=False
        )
        resp.raise_for_status()
        data = resp.json()
        # Normalizar formato para que coincida con render_result_card
        results = []
        for i, r in enumerate(data.get("results", [])):
            results.append({
                "dataset_id": r.get("id"),
                "title": r.get("title"),
                "description": r.get("description"),
                "publisher": r.get("publisher"),
                "territorio": r.get("territorio", []),
                "tema": r.get("tema", []),
                "formato": r.get("formato", []),
                "url": r.get("url", "#"),
                "score": r.get("score", 0),
                "score_final": r.get("score_final", 0),
                "new_rank": i + 1,
                "explanation": r.get("explanation", "")
            })
        return {"query": query, "results": results, "metadata": {"mode": "standard"}}
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None


def explain_dataset(query, dataset_id):
    """Llama al endpoint /llm/explain."""
    try:
        with st.spinner("🤖 Generando explicación..."):
            resp = requests.post(
                f"{API_URL}/llm/explain",
                json={"query": query, "dataset_id": dataset_id},
                timeout=30,
                verify=False
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None


def render_comparison(v07_results, v08_results):
    """Renderiza comparación lado a lado de v07 vs v08."""
    st.markdown("### 📊 Comparación V07 vs V08 (LLM)")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**V07 - Búsqueda Híbrida**")
        for r in v07_results[:5]:
            score = r.get("llm_relevance_score", 0)
            st.markdown(f"{r['new_rank']}. {r['title'][:50]}... (score: {score:.2f})")

    with col2:
        st.markdown("**V08 - Con Re-ranking LLM**")
        for r in v08_results[:5]:
            score = r.get("llm_relevance_score", 0)
            orig = r.get("original_rank", 0)
            delta = orig - r["new_rank"]
            delta_str = f"(↑{delta})" if delta > 0 else f"(↓{abs(delta)})" if delta < 0 else "(=)"
            st.markdown(f"{r['new_rank']}. {r['title'][:50]}... (score: {score:.1f}) {delta_str}")


def main():
    st.title("🤖 Demo V09 - LLM Features")
    st.markdown("Prueba de los nuevos endpoints `/llm/enhance` y `/llm/explain`")

    # Sidebar - Estado y Configuración
    with st.sidebar:
        st.header("⚙️ Configuración")

        # Check estado
        health = check_api_health()

        if not health["api_ok"]:
            st.error(f"❌ API no disponible: {health.get('error', 'Unknown')}")
            st.info("Asegúrate de que la API esté corriendo en puerto 8000")
            return

        st.success("✅ API Conectada")

        if health.get("llm_ok"):
            st.success(f"✅ LLM Listo ({health.get('model', 'N/A')})")
        else:
            st.warning("⚠️ LLM no disponible")
            st.info("Verifica que Ollama esté corriendo")

        st.markdown("---")

        # Selección de modo
        modo = st.radio(
            "Modo de búsqueda:",
            ["V07 Estándar (rápido)", "V08 LLM Enhance (lento)", "Comparar ambos"],
            help="V08 usa re-ranking LLM y tarda 60-90s"
        )

        if "V08" in modo or "Comparar" in modo:
            rerank_n = st.slider("Items a re-rankear", 5, 20, 15)
        else:
            rerank_n = 15

        st.markdown("---")

        # Info de ayuda
        st.markdown("""
        **Diferencias:**

        **V07 (Estándar):**
        - Búsqueda híbrida semántica + léxica
        - ~0.1 segundos
        - Ranking por score híbrido

        **V08 (LLM):**
        - Toma resultados V07
        - Re-ranking con LLM
        - Incluye explicaciones
        - ~60-90 segundos
        """)

    # Área principal
    st.markdown("---")

    query = st.text_input("🔍 Buscar datasets:", placeholder="ej: paro juvenil desempleo jóvenes")

    col1, col2 = st.columns([1, 4])
    with col1:
        buscar = st.button("🔍 Buscar", type="primary", use_container_width=True)

    if not buscar or not query.strip():
        st.info("👆 Escribe una búsqueda y pulsa 'Buscar'")
        st.markdown("""
        **Ejemplos para probar:**
        - `paro juvenil desempleo jóvenes` (sinonimia)
        - `sostenibilidad urbana` (conceptual)
        - `turismo Canarias 2023` (territorial)
        - `emisiones CO2 2022 2023` (temporal)
        """)
        return

    # Ejecutar búsqueda según modo
    if modo == "V07 Estándar (rápido)":
        results = search_standard(query)
        if results:
            st.markdown(f"### Resultados para: *{query}*")
            for r in results["results"]:
                render_result_card(r, r["new_rank"])

    elif modo == "V08 LLM Enhance (lento)":
        if not health.get("llm_ok"):
            st.error("❌ LLM no disponible. No se puede usar modo V08.")
            return

        results = search_llm_enhance(query, rerank_top_n=rerank_n)
        if results:
            st.markdown(f"### Resultados V08 para: *{query}*")
            st.info(f"⏱️ Tiempo: {results.get('metadata', {}).get('total_time_ms', 0)/1000:.1f}s | "
                    f"Modelo: {results.get('metadata', {}).get('model', 'N/A')}")

            for r in results["results"]:
                with st.container():
                    render_result_card(r, r["new_rank"])
                    if r.get("explanation"):
                        with st.expander("🤖 Explicación del LLM"):
                            st.write(r["explanation"])

                            # Botón para explicación detallada
                            if st.button(f"🔍 Análisis detallado de '{r['title'][:30]}...'", key=f"exp_{r['dataset_id']}"):
                                explanation = explain_dataset(query, r["dataset_id"])
                                if explanation:
                                    st.markdown("**Análisis completo:**")
                                    st.write(explanation.get("explanation", ""))
                                    st.markdown("**Factores de relevancia:**")
                                    for f in explanation.get("factors", []):
                                        st.markdown(f"- **{f['factor']}**: {f['score']:.2f} - {f['description']}")

    elif modo == "Comparar ambos":
        col_std, col_llm = st.columns(2)

        with col_std:
            st.markdown("### V07 (Estándar)")
            v07_results = search_standard(query)
            if v07_results:
                for r in v07_results["results"][:5]:
                    render_result_card(r, r["new_rank"])

        with col_llm:
            st.markdown("### V08 (LLM)")
            if health.get("llm_ok"):
                v08_results = search_llm_enhance(query, rerank_top_n=rerank_n)
                if v08_results:
                    st.info(f"⏱️ {v08_results.get('metadata', {}).get('total_time_ms', 0)/1000:.1f}s")
                    for r in v08_results["results"][:5]:
                        delta = r.get("original_rank", 0) - r["new_rank"]
                        delta_icon = "🟢" if delta > 0 else "🔴" if delta < 0 else "⚪"
                        render_result_card(r, r["new_rank"])
                        st.caption(f"{delta_icon} Posición original: {r.get('original_rank', 'N/A')}")
            else:
                st.error("LLM no disponible")


if __name__ == "__main__":
    main()
