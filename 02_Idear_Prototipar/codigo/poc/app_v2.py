import streamlit as st
import sys
import os

# ---------------------------------------------------------------------------
# 1. Choose engine version
# ---------------------------------------------------------------------------
# Default to semantic (v2).  Set search_mode="tfidf" to force legacy engine.
search_mode = os.environ.get("SEARCH_MODE", "semantic").lower()

if search_mode == "tfidf":
    from utils.search_mock import get_engine
    ENGINE_LABEL = "TF-IDF"
    ENGINE_BADGE = "🔤 TF-IDF (palabras clave)"
else:
    from utils.search_semantic import get_engine
    ENGINE_LABEL = "Semántica"
    ENGINE_BADGE = "🧠 Búsqueda Semántica (Embeddings)"

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=f"DatasetSeeker – POC v2 ({ENGINE_LABEL})",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; }
    .stTextInput>div>div>input { font-size: 18px; padding: 12px; }
    .result-card {
        border: 1px solid #e6e6e6;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        background: #fafafa;
    }
    .result-title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
    .result-meta  { font-size: 13px; color: #555; }
    .score-pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 500;
    }
    .score-high   { background: #d4edda; color: #155724; }
    .score-medium { background: #fff3cd; color: #856404; }
    .score-low    { background: #f8d7da; color: #721c24; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
col_left, col_right = st.columns([3, 1])
with col_left:
    st.title("🔍 DatasetSeeker")
    st.caption("Descubre datasets públicos con búsqueda semántica inteligente")
with col_right:
    st.markdown(f"\n\n**{ENGINE_BADGE}**")

st.divider()

# ---------------------------------------------------------------------------
# Engine init (cached)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _init_engine():
    return get_engine()

engine = _init_engine()

# ---------------------------------------------------------------------------
# Search bar
# ---------------------------------------------------------------------------
query = st.text_input(
    "¿Qué datos buscas?",
    placeholder="Ej: 'población envejecida en pueblos pequeños', 'accidentes laborales por sector'",
    key="search_query",
)

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
with st.expander("⚙️ Filtros avanzados", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        themes = [{"value": "Todos", "label": "Todos los temas"}] + engine.get_themes()
        theme_filter = st.selectbox(
            "Tema",
            options=[t["value"] for t in themes],
            format_func=lambda x: next((t["label"] for t in themes if t["value"] == x), x),
        )
    with col2:
        spatials = ["Todos"] + engine.get_spatials()
        spatial_filter = st.selectbox("Territorio", options=spatials)
    with col3:
        formats = ["Todos"] + engine.get_formats()
        format_filter = st.selectbox("Formato", options=formats)

    top_k = st.slider("Resultados", min_value=5, max_value=50, value=10, step=5)

# ---------------------------------------------------------------------------
# Search execution
# ---------------------------------------------------------------------------
if query.strip():
    with st.spinner("Buscando datasets relevantes..."):
        results = engine.search(
            query=query,
            theme_filter=theme_filter,
            spatial_filter=spatial_filter,
            format_filter=format_filter,
            top_k=top_k,
        )

    # Stats
    st.markdown(f"**{len(results)} resultados** para \"{query}\"")
    if results and "_response_time_ms" in results[0]:
        st.caption(f"⏱️ Tiempo de respuesta: {results[0]['_response_time_ms']} ms")

    # Results
    for rank, ds in enumerate(results, start=1):
        score = ds.get("score", 0)
        if score >= 70:
            score_class = "score-high"
            score_label = "Alta relevancia"
        elif score >= 40:
            score_class = "score-medium"
            score_label = "Relevancia media"
        else:
            score_class = "score-low"
            score_label = "Relevancia baja"

        # Format pills
        fmt_pills = ""
        for fmt in ds.get("formats", [])[:3]:
            simple = fmt.split("/")[-1].upper() if "/" in fmt else fmt
            fmt_pills += f"<span style='display:inline-block; margin-right:6px; padding:2px 8px; background:#e9ecef; border-radius:4px; font-size:12px;'>{simple}</span>"

        # Themes
        theme_labels = []
        for t in ds.get("themes", []):
            label = t.split("/")[-1].replace("-", " ").title() if "/" in t else t
            theme_labels.append(label)

        st.markdown(f"""
        <div class='result-card'>
            <div class='result-title'>
                {rank}. {ds.get('title_es', 'Sin título')}
                <span class='score-pill {score_class}'>{score}% – {score_label}</span>
            </div>
            <div class='result-meta'>
                📁 {ds.get('publisher_name', 'Sin publisher')} &nbsp;|&nbsp;
                🗺️ {ds.get('_spatial_inferred', ds.get('spatial_name', 'Sin ubicación'))}
            </div>
            <div style='margin-top:8px; font-size:14px; color:#333;'>
                {ds.get('description_es', '')[:250]}...
            </div>
            <div style='margin-top:8px;'>
                {fmt_pills}
            </div>
            <div style='margin-top:4px; font-size:12px; color:#666;'>
                Temas: {', '.join(theme_labels[:2])}
            </div>
            <div style='margin-top:8px;'>
                <a href="{ds.get('source_url', '#')}" target="_blank" style="font-size:13px;">
                    🔗 Ver en datos.gob.es →
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Semantic explanation
    if search_mode == "semantic" and results:
        st.divider()
        st.subheader("🧠 ¿Por qué estos resultados?")
        st.info(
            "Esta búsqueda usa **embeddings semánticos** (modelo multilingual MiniLM). "
            "Entiende el significado de tu consulta, no solo las palabras exactas. "
            "Ejemplo: buscar 'pueblos que se vacían' también encuentra datasets sobre "
            "'población envejecida' o 'exodo rural' aunque no contengan esas palabras exactas."
        )

else:
    # Empty state
    st.info("👆 Escribe una consulta en lenguaje natural para descubrir datasets.")
    st.markdown("""
    **Ejemplos de búsquedas que funcionan bien:**
    - "población envejecida en pueblos pequeños"
    - "accidentes de trabajo por sector industrial"
    - "calidad del aire en ciudades grandes"
    - "gasto sanitario por comunidad autónoma"
    """)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    "POC DatasetSeeker v2.0 | Motor: " + ENGINE_BADGE + " | "
    "Datos: datos.gob.es (muestra de 100 datasets)"
)
