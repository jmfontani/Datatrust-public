"""
Componentes visuales personalizables para el frontend V2.
Soporta búsqueda con Enter y diseño configurable.
"""
from pathlib import Path

import streamlit as st
from typing import Dict, List, Tuple
from common.utils import get_score_color, truncate_text


# ============================================================
# CONFIGURACIÓN PERSONALIZABLE
# ============================================================

# Colores del tema (personalizable)
THEME_COLORS = {
    'primary': '#667eea',
    'secondary': '#764ba2',
    'accent': '#48bb78',
    'danger': '#f56565',
    'warning': '#ed8936',
    'info': '#4299e1',
    'bg_light': '#f7fafc',
    'bg_dark': '#2d3748',
    'text_primary': '#1a202c',
    'text_secondary': '#718096',
}

# Tamaños de fuente (personalizable)
FONT_SIZES = {
    'header_title': '2.5rem',
    'header_subtitle': '1.1rem',
    'card_title': '1.2rem',
    'card_text': '0.95rem',
    'meta': '0.85rem',
    'score': '0.9rem',
}

# Bordes y espaciado (personalizable)
CARD_STYLE = {
    'border_radius': '10px',
    'padding': '1.2rem',
    'margin_bottom': '1rem',
    'shadow': '0 2px 8px rgba(0,0,0,0.1)',
}


# ============================================================
# FUNCIONES DE UTILIDAD CSS
# ============================================================

def get_custom_css() -> str:
    """Genera CSS personalizado basado en la configuración del tema."""
    return f"""
    <style>
    /* Variables CSS personalizadas */
    :root {{
        --color-primary: {THEME_COLORS['primary']};
        --color-secondary: {THEME_COLORS['secondary']};
        --color-accent: {THEME_COLORS['accent']};
        --color-bg-light: {THEME_COLORS['bg_light']};
        --color-text-primary: {THEME_COLORS['text_primary']};
        --color-text-secondary: {THEME_COLORS['text_secondary']};
    }}
    
    /* Estilos generales */
    .main {{
        background-color: var(--color-bg-light);
    }}
    
    /* Header personalizado */
    .main-header {{
        background: linear-gradient(135deg, {THEME_COLORS['primary']} 0%, {THEME_COLORS['secondary']} 100%);
        padding: 2rem;
        border-radius: {CARD_STYLE['border_radius']};
        color: white;
        margin-bottom: 2rem;
        box-shadow: {CARD_STYLE['shadow']};
    }}
    .main-header h1 {{
        margin: 0;
        font-size: {FONT_SIZES['header_title']};
        font-weight: 700;
    }}
    .main-header p {{
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: {FONT_SIZES['header_subtitle']};
    }}
    
    /* Barra de búsqueda mejorada */
    .search-container {{
        background: white;
        padding: 1.5rem;
        border-radius: {CARD_STYLE['border_radius']};
        margin-bottom: 1.5rem;
        box-shadow: {CARD_STYLE['shadow']};
        border: 2px solid #e2e8f0;
    }}
    .search-container:focus-within {{
        border-color: var(--color-primary);
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }}
    
    /* Tarjetas de resultado */
    .result-card {{
        background: white;
        padding: {CARD_STYLE['padding']};
        margin-bottom: {CARD_STYLE['margin_bottom']};
        border-radius: {CARD_STYLE['border_radius']};
        box-shadow: {CARD_STYLE['shadow']};
        border-left: 4px solid transparent;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .result-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}
    .result-score {{
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: {FONT_SIZES['score']};
        font-weight: bold;
        color: white;
    }}
    .result-title {{
        font-size: {FONT_SIZES['card_title']};
        font-weight: 600;
        color: var(--color-text-primary);
        margin: 0.5rem 0;
        line-height: 1.3;
    }}
    .result-meta {{
        color: var(--color-text-secondary);
        font-size: {FONT_SIZES['meta']};
        margin-bottom: 0.5rem;
    }}
    .result-description {{
        color: var(--color-text-secondary);
        font-size: {FONT_SIZES['card_text']};
        line-height: 1.6;
        margin-bottom: 0.5rem;
    }}
    .result-explanation {{
        background: #e6f6ff;
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        font-size: {FONT_SIZES['meta']};
        color: #0066cc;
        border-left: 3px solid #4299e1;
    }}
    
    /* Estado vacío */
    .empty-state {{
        text-align: center;
        padding: 4rem 2rem;
        color: var(--color-text-secondary);
    }}
    .empty-state-icon {{
        font-size: 4rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }}
    
    /* Badges de filtros */
    .filter-badge {{
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        margin-right: 0.5rem;
        margin-bottom: 0.25rem;
    }}
    </style>
    """


def apply_theme_colors(primary: str = None, secondary: str = None, accent: str = None):
    """Permite cambiar colores del tema dinámicamente."""
    if primary:
        THEME_COLORS['primary'] = primary
    if secondary:
        THEME_COLORS['secondary'] = secondary
    if accent:
        THEME_COLORS['accent'] = accent
    st.markdown(get_custom_css(), unsafe_allow_html=True)


# ============================================================
# COMPONENTES DE UI
# ============================================================

def render_header():
    """Renderiza el header principal con logo corporativo.
    El logo se incrusta como base64 dentro del div del header."""
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    logo_path = Path(__file__).parent.parent / "assets" / "logo_buscador_semantico.png"
    if logo_path.exists():
        import base64
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
        st.markdown(f"""
    <div class="main-header">
        <img src="data:image/png;base64,{logo_b64}" style="width: 70px; height: auto; margin-bottom: 0.75rem;" />
        <h1>Buscador Semántico de Datasets</h1>
        <p>Búsqueda híbrida: semántica + léxica + filtros facetados</p>
    </div>
    """, unsafe_allow_html=True)
    else:
        st.markdown("""
    <div class="main-header">
        <h1>🔍 Buscador Semántico de Datasets</h1>
        <p>Búsqueda híbrida: semántica + léxica + filtros facetados</p>
    </div>
    """, unsafe_allow_html=True)


def render_search_bar_v2() -> Tuple[str, int]:
    """
    Renderiza la barra de búsqueda V2 con soporte para Enter.
    
    Returns:
        Tuple[str, int]: (query, top_k)
    """
    st.markdown("""
    <style>
    /* Estilos específicos para la barra de búsqueda V2 */
    .stTextInput > div > div > input {
        font-size: 1.1rem !important;
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
    }
    /* Ocultar el label del text_input */
    .stTextInput > label {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # Usar st.session_state para detectar Enter
        if 'search_query' not in st.session_state:
            st.session_state.search_query = ""
        
        query = st.text_input(
            "Buscar datasets",
            key="search_input",
            placeholder="Ej: datos de tráfico en Madrid, educación primaria...",
            label_visibility="collapsed",
            on_change=on_search_change
        )
    
    with col2:
        top_k = st.number_input(
            "Resultados",
            min_value=1,
            max_value=50,
            value=10,
            step=5,
            key="top_k_input"
        )
    
    # Botón de búsqueda visible
    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        if st.button("🔍 Buscar", type="primary", use_container_width=True):
            st.session_state.search_triggered = True
            st.rerun()
    
    with col_btn2:
        # Mostrar hint sobre Enter
        st.markdown("<span style='color: #718096; font-size: 0.85rem;'>💡 Presiona **Enter** para buscar rápidamente</span>", unsafe_allow_html=True)
    
    return query, top_k


def on_search_change():
    """Callback cuando cambia el texto de búsqueda (detecta Enter)."""
    # Este callback se dispara cuando el usuario presiona Enter en el text_input
    st.session_state.search_triggered = True


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
    """Renderiza filtros facetados y devuelve valores seleccionados.
    Limpia los valores de facetas para eliminar entradas inválidas."""
    st.markdown("### 🎛️ Filtros")
    
    filters = {}
    
    def clean_facet_list(values):
        """Limpia una lista de facetas: elimina vacíos, duplicados, y valores que no son territorios reales."""
        cleaned = []
        seen = set()
        for val in values:
            if not val:
                continue
            # Si es una lista serializada como string, extraer elementos
            if isinstance(val, str) and val.startswith('[') and val.endswith(']'):
                try:
                    import ast
                    items = ast.literal_eval(val)
                    if isinstance(items, list):
                        for item in items:
                            item_str = str(item).strip()
                            if item_str and item_str.lower() not in seen:
                                seen.add(item_str.lower())
                                cleaned.append(item_str)
                        continue
                except:
                    val = val[1:-1].replace("'", "").replace('"', '')
            val_str = str(val).strip()
            # Filtrar valores que claramente no son territorios
            if val_str and len(val_str) > 1 and val_str.lower() not in seen:
                seen.add(val_str.lower())
                cleaned.append(val_str)
        return sorted(cleaned, key=lambda x: x.lower())
    
    # Territorio (limpiar valores)
    raw_territorios = st.session_state.get("territorios", [])
    territorios = ["Todos"] + clean_facet_list(raw_territorios)
    selected = st.selectbox("🌍 Territorio", territorios, index=0)
    if selected != "Todos":
        filters["territorio"] = selected
    
    # Tema (limpiar valores)
    raw_temas = st.session_state.get("temas", [])
    temas = ["Todos"] + clean_facet_list(raw_temas)
    selected = st.selectbox("🏷️ Tema", temas, index=0)
    if selected != "Todos":
        filters["tema"] = selected
    
    # Formato (limpiar valores)
    raw_formatos = st.session_state.get("formatos", [])
    formatos = ["Todos"] + clean_facet_list(raw_formatos)
    selected = st.selectbox("📄 Formato", formatos, index=0)
    if selected != "Todos":
        filters["formato"] = selected
    
    # Publisher (limpiar valores)
    raw_publishers = st.session_state.get("publishers", [])
    publishers = ["Todos"] + clean_facet_list(raw_publishers)
    selected = st.selectbox("🏛️ Publisher", publishers, index=0)
    if selected != "Todos":
        filters["publisher"] = selected
    
    return filters


def render_result_card(result: Dict, index: int):
    """Renderiza una tarjeta de resultado con diseño mejorado."""
    score = result.get("score", 0)
    color = get_score_color(score)
    
    # Construir HTML de la tarjeta
    explanation_html = ""
    if "explanation" in result and result["explanation"]:
        explanation_html = f'<div class="result-explanation">💡 {result["explanation"]}</div>'
    
    territorios = ", ".join(result.get("territorio", [])[:3]) if isinstance(result.get("territorio"), list) else result.get("territorio", "")
    temas = ", ".join(result.get("tema", [])[:3]) if isinstance(result.get("tema"), list) else result.get("tema", "")
    formatos = ", ".join(result.get("formato", [])[:3]) if isinstance(result.get("formato"), list) else result.get("formato", "")
    
    st.markdown(f"""
    <div class="result-card" style="border-left-color: {color};">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <span class="result-score" style="background-color: {color};">{score:.3f}</span>
            <span style="color: #a0aec0; font-size: 0.85rem; font-weight: 500;">#{index}</span>
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
        <div style="margin-top: 0.75rem;">
            <a href="{result.get('url', '#')}" target="_blank" 
               style="color: {THEME_COLORS['primary']}; text-decoration: none; font-size: 0.9rem; font-weight: 500;">
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
    <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <h3 style="color: #4a5568; margin-bottom: 0.5rem;">Empieza tu búsqueda</h3>
        <p style="max-width: 500px; margin: 0 auto; line-height: 1.6;">
            Escribe una consulta en la barra de arriba y presiona <strong>Enter</strong> o haz clic en <strong>Buscar</strong>.<br>
            Prueba con "datos de tráfico en Madrid" o "educación primaria".
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_no_results():
    """Renderiza cuando no hay resultados."""
    st.markdown("""
    <div class="empty-state">
        <div style="font-size: 3rem; margin-bottom: 1rem;">😕</div>
        <h3 style="color: #4a5568; margin-bottom: 0.5rem;">No se encontraron resultados</h3>
        <p>Prueba con otros términos o ajusta los filtros.</p>
    </div>
    """, unsafe_allow_html=True)
