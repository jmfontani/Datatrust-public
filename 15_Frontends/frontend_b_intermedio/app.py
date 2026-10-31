#!/usr/bin/env python3
"""
Entrypoint unificado del frontend del Buscador Semántico.

Ejecutar:
    streamlit run app.py --server.port 8501

Modos:
    http://localhost:8501                -> Versión pública (rápida/visual)
    http://localhost:8501?mode=advanced  -> Versión avanzada (demostrador de capacidades)
"""
import sys
from pathlib import Path

import streamlit as st

# Añadir directorio del proyecto al path para imports absolutos
sys.path.insert(0, str(Path(__file__).parent))


def _get_host() -> str:
    """Obtiene el host de la petición actual si está disponible."""
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            return st.context.headers.get("host", "localhost:8501")
    except Exception:
        pass
    return "localhost:8501"


def _inject_favicon() -> None:
    """Declara el icono de la pestaña con una data URI.

    `page_icon` de Streamlit 1.66 genera un `<link rel="shortcut icon">` que apunta a
    /media/<hash>, y esa ruta responde 404 en este despliegue, así que el navegador se
    queda sin icono de marca. Este <link> es el que sí resuelve.
    """
    import base64

    fav = Path(__file__).parent / "assets" / "favicon_64.png"
    if not fav.exists():
        return
    b64 = base64.b64encode(fav.read_bytes()).decode()
    st.markdown(
        f'<link rel="icon" type="image/png" href="data:image/png;base64,{b64}">',
        unsafe_allow_html=True,
    )


def main():
    """Rutea entre modo público y modo avanzado según query param."""
    mode = st.query_params.get("mode", "public")
    _logo = str(Path(__file__).parent / "assets" / "logo_buscador_semantico.png")

    if mode == "advanced":
        st.set_page_config(
            page_title="Buscador Semántico - Modo Avanzado",
            page_icon=_logo,
            layout="wide",
            initial_sidebar_state="expanded",
        )
        _inject_favicon()
        from advanced.app import main as advanced_main
        advanced_main()
    else:
        st.set_page_config(
            page_title="Datos Abiertos - Buscador Semántico",
            page_icon=_logo,
            layout="wide",
            initial_sidebar_state="collapsed",
        )
        _inject_favicon()
        from public.app import main as public_main
        public_main()


if __name__ == "__main__":
    main()
