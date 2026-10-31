"""
POC: Buscador Semántico de Datasets (datos.gob.es)
Aplicación Streamlit con búsqueda TF-IDF, filtros y explicaciones de relevancia.
"""
import streamlit as st
import json
import time

from utils.search_mock import get_engine, _simplify_format
from utils.relevance import explain_relevance, format_score_badge, get_match_highlights

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Buscador Semántico de Datasets",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for cards
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .dataset-card {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border-left: 4px solid #1f77b4;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .dataset-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.3rem;
        text-decoration: none;
    }
    .dataset-title:hover {
        text-decoration: underline;
    }
    .dataset-meta {
        font-size: 0.85rem;
        color: #666;
        margin-bottom: 0.5rem;
    }
    .dataset-desc {
        font-size: 0.95rem;
        color: #333;
        line-height: 1.5;
        margin-bottom: 0.6rem;
    }
    .score-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .score-high { background-color: #d4edda; color: #155724; }
    .score-mid  { background-color: #fff3cd; color: #856404; }
    .score-low  { background-color: #f8d7da; color: #721c24; }
    .explanation-box {
        background-color: #e7f3ff;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        font-size: 0.85rem;
        color: #004085;
        margin-top: 0.4rem;
    }
    .highlight {
        background-color: #fff3cd;
        padding: 0 2px;
        border-radius: 3px;
        font-weight: 600;
    }
    .filter-section {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .stats-bar {
        display: flex;
        gap: 1.5rem;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid #eee;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🔍 Buscador Semántico de Datasets")
st.caption("Explora datasets abiertos de datos.gob.es con búsqueda inteligente basada en TF-IDF")

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Filtros")

    engine = get_engine()

    # Theme filter
    themes = engine.get_themes()
    theme_options = ["Todos"] + [t["value"] for t in themes]
    theme_labels = ["Todos"] + [t["label"] for t in themes]
    theme_filter = st.selectbox("🎯 Tema", theme_options, format_func=lambda x: theme_labels[theme_options.index(x)])

    # Spatial filter
    spatials = engine.get_spatials()
    spatial_options = ["Todos"] + spatials
    spatial_filter = st.selectbox("🌍 Territorio", spatial_options)

    # Format filter
    formats = engine.get_formats()
    format_options = ["Todos"] + formats
    format_filter = st.selectbox("📁 Formato", format_options)

    st.divider()
    st.markdown("**ℹ️ Información**")
    st.markdown(f"- Datasets cargados: **{len(engine.datasets)}**")
    st.markdown("- Motor: TF-IDF (scikit-learn)")
    st.markdown("- Tiempo objetivo: <2s")

# ---------------------------------------------------------------------------
# Search bar
# ---------------------------------------------------------------------------
col1, col2 = st.columns([6, 1])
with col1:
    query = st.text_input("🔎 Buscar datasets...", placeholder="Ej: ruido ambiental, contaminación Madrid, empleo...", label_visibility="collapsed")
with col2:
    top_k = st.selectbox("Resultados", [5, 10, 20, 50], index=1, label_visibility="collapsed")

# ---------------------------------------------------------------------------
# Search execution
# ---------------------------------------------------------------------------
if query or any(f != "Todos" for f in [theme_filter, spatial_filter, format_filter]):
    start_time = time.perf_counter()
    results = engine.search(
        query=query,
        theme_filter=theme_filter,
        spatial_filter=spatial_filter,
        format_filter=format_filter,
        top_k=top_k,
    )
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Stats bar
    st.markdown(
        f"""
        <div class="stats-bar">
            <span>📊 <b>{len(results)}</b> resultados</span>
            <span>⏱️ <b>{elapsed_ms}ms</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not results:
        st.info("No se encontraron datasets con los filtros aplicados. Prueba a ampliar la búsqueda.")
    else:
        for ds in results:
            score = ds.get("score", 0.0)
            badge_class = "score-high" if score >= 0.5 else ("score-mid" if score >= 0.2 else "score-low")
            badge_text = format_score_badge(score)

            # Explicación de relevancia
            expl = explain_relevance(ds, query)

            # Título con link
            title_html = f'<a class="dataset-title" href="{ds.get("source_url", "#")}" target="_blank">{ds.get("title_es", "Sin título")}</a>'

            # Metadatos
            meta_parts = []
            pub = ds.get("publisher_name", "")
            if pub:
                meta_parts.append(f"🏛️ {pub}")
            spatial = ds.get("spatial_name", "")
            if spatial and spatial != "desconocido":
                meta_parts.append(f"🌍 {spatial}")
            ds_formats = ds.get("formats", [])
            if ds_formats:
                fmt_labels = [_simplify_format(f) for f in ds_formats[:4]]
                meta_parts.append(f"📁 {', '.join(fmt_labels)}")
            modified = ds.get("modified", "")
            if modified:
                meta_parts.append(f"🗓️ {modified[:10]}")

            meta_html = " · ".join(meta_parts)

            # Descripción resaltada
            desc = ds.get("description_es", "") or "Sin descripción."
            if len(desc) > 350:
                desc = desc[:350] + "..."

            # Resaltar términos coincidentes
            highlights = get_match_highlights(desc, query)
            desc_html = "".join(
                f'<span class="highlight">{frag}</span>' if is_match else frag
                for frag, is_match in highlights
            )

            # Tarjeta completa
            st.markdown(
                f"""
                <div class="dataset-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        {title_html}
                        <span class="score-badge {badge_class}">{badge_text or 'Relevancia'} {score:.3f}</span>
                    </div>
                    <div class="dataset-meta">{meta_html}</div>
                    <div class="dataset-desc">{desc_html}</div>
                    <div class="explanation-box">💡 <b>Por qué:</b> {expl["explanation"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Footer con info
        st.caption("Los resultados se ordenan por relevancia (similitud coseno TF-IDF).")

else:
    # Estado inicial: mostrar algunos datasets aleatorios o destacados
    st.info("👆 Escribe una búsqueda o selecciona filtros para comenzar.")
    st.subheader("🎲 Descubre datasets")
    import random
    random.seed(42)
    featured = random.sample(engine.datasets, min(6, len(engine.datasets)))
    cols = st.columns(3)
    for idx, ds in enumerate(featured):
        with cols[idx % 3]:
            with st.container():
                st.markdown(f"**{ds.get('title_es', 'Sin título')[:60]}...**")
                st.caption(f"🏛️ {ds.get('publisher_name', 'Desconocido')}")
                st.caption(f"🌍 {ds.get('spatial_name', 'N/A')}")
                if st.button("Ver detalle", key=f"feat_{idx}"):
                    st.session_state["query"] = ds.get("title_es", "")
                    st.rerun()
