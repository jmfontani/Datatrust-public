#!/usr/bin/env python3
"""
Router de aplicaciones del Buscador Semántico.
Redirige entre versión pública (por defecto) y versión avanzada.

URLs:
    http://localhost:8501              -> Versión pública (por defecto)
    http://localhost:8501?mode=advanced  -> Versión avanzada
    http://localhost:8501?mode=demos     -> Menú de Demos Sprint 6

Variables de entorno:
    APP_MODE=advanced  -> Forzar versión avanzada
"""
import streamlit as st
import os
import sys
from pathlib import Path

# Añadir directorio al path
sys.path.insert(0, str(Path(__file__).parent))

# Detectar modo
query_mode = st.query_params.get('mode')
env_mode = os.environ.get('APP_MODE', 'public')

mode = 'public'
if query_mode == 'advanced':
    mode = 'advanced'
elif query_mode == 'demos':
    mode = 'demos'
elif env_mode == 'advanced':
    mode = 'advanced'

# Configurar página según el modo
if mode == 'advanced':
    st.set_page_config(
        page_title="Buscador Semántico - Modo Avanzado",
        page_icon="⚙️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # Importar y ejecutar versión avanzada
    import app
    app.main()

elif mode == 'demos':
    st.set_page_config(
        page_title="Demos Sprint 6 - LLM Features",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Menú de Demos
    st.title("🤖 Demos Sprint 6 - Mejoras con LLM")
    st.markdown("""
    Explora las funcionalidades avanzadas implementadas con Modelos de Lenguaje (LLM).
    """)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔍 Query Preprocessor (#3, #4, #12)")
        st.markdown("""
        **Puerto:** 8502

        Valida, interpreta y expande queries con LLM:
        - ✅ Validación semántica (#12)
        - ✅ Interpretación estructurada (#3)
        - ✅ Expansión con sinónimos (#4)
        """)
        if st.button("Ir a Query Preprocessor →", key="btn_qp", use_container_width=True):
            st.link_button("Abrir en puerto 8502", "http://servidor1.local:8502")

    with col2:
        st.markdown("### 💡 Query Suggestions (#13)")
        st.markdown("""
        **Puerto:** 8503

        Sugerencias de queries relacionadas:
        - ⚡ Léxico instantáneo (<5ms)
        - 🤖 LLM en background (~3-5s)
        - 📊 5 categorías de sugerencias
        """)
        if st.button("Ir a Query Suggestions →", key="btn_qs", use_container_width=True):
            st.link_button("Abrir en puerto 8503", "http://servidor1.local:8503")

    st.divider()

    st.markdown("### 📚 Otras Demos Disponibles")

    demos = [
        {
            "nombre": "Frontend Básico",
            "puerto": 8500,
            "descripcion": "Búsqueda semántica estándar con controles de peso y filtros.",
        },
        {
            "nombre": "LLM Re-ranking (#1, #2)",
            "puerto": 8504,
            "descripcion": "Re-ranking con LLM + explicaciones de relevancia.",
        },
    ]

    for demo in demos:
        with st.expander(f"**{demo['nombre']}** (puerto {demo['puerto']})"):
            st.markdown(demo["descripcion"])
            st.link_button(f"Abrir →", f"http://servidor1.local:{demo['puerto']}")

    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #6c757d; font-size: 0.85em;">
        <strong>Sprint 6 - Mejoras con LLM</strong><br>
        Documentación: <code>08_Sprint6_LLM_Mejora/docs/INDICE_CASOS_USO_LLM.md</code>
    </div>
    """, unsafe_allow_html=True)

else:
    st.set_page_config(
        page_title="Datos Abiertos - Buscador",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    # Importar y ejecutar versión pública
    import app_public
    app_public.main()
