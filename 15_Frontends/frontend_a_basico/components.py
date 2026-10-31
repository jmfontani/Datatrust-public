"""
Componentes visuales reutilizables para el frontend.
"""
from pathlib import Path

import streamlit as st
from typing import Dict, List
from utils import get_score_color, truncate_text


def render_header():
    """Renderiza el header principal con logo corporativo."""
    logo_path = Path(__file__).parent / "assets" / "logo_buscador_semantico.png"
    if logo_path.exists():
        col1, col2 = st.columns([1, 5])
        with col1:
            st.image(str(logo_path), width=80)
        with col2:
            st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
    }
    </style>
    <div class="main-header">
        <h1>Buscador Semántico de Datasets</h1>
        <p>Búsqueda híbrida: semántica + léxica + filtros facetados</p>
    </div>
    """, unsafe_allow_html=True)
    else:
        st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
    }
    </style>
    <div class="main-header">
        <h1>🔍 Buscador Semántico de Datasets</h1>
        <p>Búsqueda híbrida: semántica + léxica + filtros facetados</p>
    </div>
    """, unsafe_allow_html=True)


def render_search_bar() -> str:
    """Renderiza la barra de búsqueda."""
    st.markdown("""
    <style>
    .search-container {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input(
            "Buscar datasets",
            placeholder="Ej: datos de tráfico en Madrid, educación primaria...",
            label_visibility="collapsed"
        )
    with col2:
        top_k = st.number_input("Resultados", min_value=1, max_value=50, value=10, step=5)
    
    return query, top_k


def render_weight_controls() -> tuple:
    """Renderiza controles de pesos semántico/léxico."""
    st.markdown("### ⚖️ Configuración de Búsqueda")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        semantic_weight = st.slider(
            "Peso Semántico",
            0.0, 1.0, 0.7, 0.05,
            help="Mayor valor = más importancia a la similitud de significado"
        )
    
    with col2:
        lexical_weight = st.slider(
            "Peso Léxico",
            0.0, 1.0, 0.3, 0.05,
            help="Mayor valor = más importancia a coincidencia de palabras exactas"
        )
    
    with col3:
        st.metric("Total", f"{semantic_weight + lexical_weight:.1f}")
    
    # Normalizar pesos
    total = semantic_weight + lexical_weight
    if total > 0:
        sem_norm = semantic_weight / total
        lex_norm = lexical_weight / total
    else:
        sem_norm, lex_norm = 0.5, 0.5
    
    # Mostrar proporción visual
    st.progress(sem_norm, text=f"Semántico: {sem_norm:.0%} | Léxico: {lex_norm:.0%}")
    
    return sem_norm, lex_norm


def render_filters() -> Dict:
    """Renderiza filtros facetados y devuelve valores seleccionados."""
    st.markdown("### 🎛️ Filtros")
    
    filters = {}
    
    # Territorio
    territorios = ["Todos"] + st.session_state.get("territorios", [])
    selected = st.selectbox("🌍 Territorio", territorios, index=0)
    if selected != "Todos":
        filters["territorio"] = selected
    
    # Tema
    temas = ["Todos"] + st.session_state.get("temas", [])
    selected = st.selectbox("🏷️ Tema", temas, index=0)
    if selected != "Todos":
        filters["tema"] = selected
    
    # Formato
    formatos = ["Todos"] + st.session_state.get("formatos", [])
    selected = st.selectbox("📄 Formato", formatos, index=0)
    if selected != "Todos":
        filters["formato"] = selected
    
    # Publisher
    publishers = ["Todos"] + st.session_state.get("publishers", [])
    selected = st.selectbox("🏛️ Publisher", publishers, index=0)
    if selected != "Todos":
        filters["publisher"] = selected
    
    return filters


def render_result_card(result: Dict, index: int):
    """Renderiza una tarjeta de resultado."""
    score = result.get("score", 0)
    color = get_score_color(score)
    
    st.markdown(f"""
    <style>
    .result-card {{
        border-left: 4px solid {color};
        background: white;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .result-score {{
        background: {color};
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: bold;
    }}
    .result-title {{
        font-size: 1.2rem;
        font-weight: 600;
        color: #333;
        margin: 0.5rem 0;
    }}
    .result-meta {{
        color: #666;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }}
    .result-description {{
        color: #555;
        line-height: 1.5;
        margin-bottom: 0.5rem;
    }}
    .result-explanation {{
        background: #e7f3ff;
        padding: 0.5rem;
        border-radius: 5px;
        font-size: 0.9rem;
        color: #0066cc;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Construir HTML de la tarjeta
    explanation_html = ""
    if "explanation" in result and result["explanation"]:
        explanation_html = f'<div class="result-explanation">💡 {result["explanation"]}</div>'
    
    territorios = ", ".join(result.get("territorio", [])[:3])
    temas = ", ".join(result.get("tema", [])[:3])
    formatos = ", ".join(result.get("formato", [])[:3])
    
    st.markdown(f"""
    <div class="result-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span class="result-score">{score:.3f}</span>
            <span style="color: #999; font-size: 0.85rem;">#{index}</span>
        </div>
        <div class="result-title">{result.get('title', 'Sin título')}</div>
        <div class="result-meta">
            🏛️ {result.get('publisher', 'Desconocido')} | 
            🌍 {territorios} | 
            🏷️ {temas} | 
            📄 {formatos}
        </div>
        <div class="result-description">{truncate_text(result.get('description', ''), 250)}</div>
        {explanation_html}
        <div style="margin-top: 0.5rem;">
            <a href="{result.get('url', '#')}" target="_blank" style="color: #667eea; text-decoration: none; font-size: 0.9rem;">
                🔗 Ver dataset →
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_stats(result_data: Dict):
    """Renderiza estadísticas de la búsqueda."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Resultados",
            f"{result_data.get('returned_results', 0)}/{result_data.get('total_results', 0)}"
        )
    with col2:
        st.metric(
            "Tiempo",
            f"{result_data.get('search_time_ms', 0):.0f} ms"
        )
    with col3:
        st.metric(
            "Peso Semántico",
            f"{result_data.get('semantic_weight', 0.7):.0%}"
        )
    with col4:
        st.metric(
            "Peso Léxico",
            f"{result_data.get('lexical_weight', 0.3):.0%}"
        )


def render_empty_state():
    """Renderiza estado vacío antes de la primera búsqueda."""
    st.markdown("""
    <style>
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: #666;
    }
    .empty-state-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }
    .empty-state h3 {
        color: #333;
        margin-bottom: 0.5rem;
    }
    .empty-state p {
        max-width: 500px;
        margin: 0 auto;
        line-height: 1.6;
    }
    </style>
    <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <h3>Empieza tu búsqueda</h3>
        <p>Escribe una consulta en el panel de la izquierda y haz clic en Buscar.<br>
        Prueba con "datos de tráfico en Madrid" o "educación primaria".</p>
    </div>
    """, unsafe_allow_html=True)


def render_no_results():
    """Renderiza cuando no hay resultados."""
    st.markdown("""
    <style>
    .no-results {
        text-align: center;
        padding: 3rem 2rem;
        color: #666;
    }
    </style>
    <div class="no-results">
        <div style="font-size: 3rem; margin-bottom: 1rem;">😕</div>
        <h3>No se encontraron resultados</h3>
        <p>Prueba con otros términos o ajusta los filtros.</p>
    </div>
    """, unsafe_allow_html=True)
