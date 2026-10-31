"""
Componentes visuales para la versión pública del buscador.
Diseño limpio y amigable para usuarios finales.
"""
from pathlib import Path

import streamlit as st
from typing import Dict, List, Tuple, Optional
from common.utils import (
    get_score_color, truncate_text, API_URL,
    get_dataset_profile_info, get_complementary_datasets,
    ask_dataset_question
)


# ============================================================
# CONFIGURACIÓN DE TEMA PÚBLICO
# ============================================================

# Paleta cromática del Manual de Identidad "Infancia Digital"
# Azul oscuro = color principal (predominante)
# Rojo = color complementario (menor proporción)
# Azul claro = color de apoyo (uso más limitado)
THEME_COLORS = {
    'primary': '#080066',        # Azul oscuro corporativo (predominante)
    'primary_light': '#1F7CFF',  # Azul claro corporativo (apoyo)
    'secondary': '#64748b',      # Gris neutro para texto secundario
    'accent': '#C42A00',         # Rojo corporativo oscurecido: 5.71:1 sobre blanco (el #F53300 daba 3.92:1)
    'bg_light': '#f0ecf6',       # Fondo claro con tinte azulado (del manual)
    'bg_card': '#ffffff',
    'text_primary': '#1D1E1B',   # Negro corporativo del manual
    'text_secondary': '#585857', # Gris corporativo del manual
    'border': '#DADADA',         # Gris claro corporativo del manual
}


def get_public_css() -> str:
    """CSS personalizado para la versión pública.
    Aplica la identidad visual de Infancia Digital:
    - Tipografía Inter (secundaria del manual)
    - Colores corporativos: azul oscuro predominante, rojo complementario
    - Degradados multicolor del manual
    - Tono claro, directo y accesible
    """
    return f"""
    <style>
    /* Tipografía Inter (secundaria del manual de identidad) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Reset y estilos base */
    .stApp {{
        background-color: {THEME_COLORS['bg_light']};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* Header con degradado multicolor del manual */
    .public-header {{
        text-align: center;
        padding: 3rem 1rem 2rem 1rem;
        background: linear-gradient(135deg, {THEME_COLORS['primary']} 0%, {THEME_COLORS['primary_light']} 100%);
        border-radius: 0 0 24px 24px;
        margin-bottom: 1.5rem;
    }}

    .public-header h1 {{
        font-size: 2.25rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0;
        letter-spacing: -0.025em;
    }}

    .public-header .subtitle {{
        font-size: 1.125rem;
        color: rgba(255, 255, 255, 0.85);
        margin-top: 0.5rem;
        font-weight: 400;
    }}

    /* Barra de búsqueda estilo Google */
    .search-wrapper {{
        max-width: 680px;
        margin: 0 auto;
        padding: 0 1rem;
    }}

    /* Tarjetas de resultado limpias */
    .result-card-public {{
        background: {THEME_COLORS['bg_card']};
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        border: 1px solid {THEME_COLORS['border']};
        transition: all 0.2s ease;
        cursor: pointer;
    }}

    .result-card-public:hover {{
        box-shadow: 0 4px 16px rgba(8, 0, 102, 0.12);
        border-color: {THEME_COLORS['primary_light']};
    }}

    .result-title-public {{
        font-size: 1.125rem;
        font-weight: 600;
        color: {THEME_COLORS['primary']};
        margin: 0 0 0.5rem 0;
        line-height: 1.4;
    }}

    .result-title-public:hover {{
        text-decoration: underline;
    }}

    .result-meta-public {{
        font-size: 0.875rem;
        color: {THEME_COLORS['text_secondary']};
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex-wrap: wrap;
    }}

    .result-description-public {{
        font-size: 0.95rem;
        color: {THEME_COLORS['text_primary']};
        line-height: 1.6;
        margin-bottom: 0.75rem;
    }}

    /* Tags de formato */
    .format-tag {{
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        background-color: {THEME_COLORS['bg_light']};
        color: {THEME_COLORS['text_secondary']};
        border: 1px solid {THEME_COLORS['border']};
    }}

    /* Chips de filtros */
    .filter-chip {{
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
        background-color: {THEME_COLORS['bg_card']};
        color: {THEME_COLORS['text_secondary']};
        border: 1px solid {THEME_COLORS['border']};
        cursor: pointer;
        transition: all 0.15s ease;
        margin: 0.25rem;
    }}

    .filter-chip:hover {{
        border-color: {THEME_COLORS['primary_light']};
        color: {THEME_COLORS['primary']};
    }}

    .filter-chip.active {{
        background-color: {THEME_COLORS['primary']};
        color: white;
        border-color: {THEME_COLORS['primary']};
    }}
    .relevance-stars {{
        color: #B45309;  /* ambar accesible: 5.02:1 sobre blanco (el #fbbf24 daba 1.67:1) */
        font-size: 0.875rem;
        letter-spacing: 0.125rem;
    }}

    /* Estado vacío */
    .empty-state-public {{
        text-align: center;
        padding: 4rem 2rem;
        max-width: 480px;
        margin: 0 auto;
    }}

    .empty-state-public .icon {{
        font-size: 4rem;
        margin-bottom: 1rem;
    }}

    .empty-state-public h3 {{
        font-size: 1.25rem;
        font-weight: 600;
        color: {THEME_COLORS['text_primary']};
        margin-bottom: 0.5rem;
    }}

    .empty-state-public p {{
        font-size: 1rem;
        color: {THEME_COLORS['text_secondary']};
        line-height: 1.5;
    }}

    /* Búsquedas populares */
    .popular-searches {{
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 0.5rem;
        margin-top: 1.5rem;
    }}

    .popular-tag {{
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        background-color: {THEME_COLORS['bg_card']};
        color: {THEME_COLORS['text_secondary']};
        border: 1px solid {THEME_COLORS['border']};
        cursor: pointer;
        transition: all 0.15s ease;
    }}

    .popular-tag:hover {{
        background-color: {THEME_COLORS['primary']};
        color: white;
        border-color: {THEME_COLORS['primary']};
    }}

    /* Barra superior */
    .top-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1.5rem;
        background: {THEME_COLORS['bg_card']};
        border-bottom: 1px solid {THEME_COLORS['border']};
    }}

    .top-bar .logo {{
        font-weight: 700;
        font-size: 1.125rem;
        color: {THEME_COLORS['primary']};
    }}

    /* Footer con color corporativo */
    .public-footer {{
        text-align: center;
        padding: 2rem;
        color: {THEME_COLORS['text_secondary']};
        font-size: 0.875rem;
        border-top: 2px solid {THEME_COLORS['primary']};
        margin-top: 3rem;
        background: linear-gradient(180deg, {THEME_COLORS['bg_light']} 0%, #ffffff 100%);
    }}

    /* Responsive */
    @media (max-width: 640px) {{
        .public-header h1 {{
            font-size: 1.5rem;
        }}

        .result-card-public {{
            padding: 1rem;
        }}

        .result-title-public {{
            font-size: 1rem;
        }}
    }}
    </style>
    """


def score_to_stars(score: float) -> str:
    """Convierte score numérico a estrellas visuales."""
    if score >= 0.8:
        return "⭐⭐⭐⭐⭐"
    elif score >= 0.6:
        return "⭐⭐⭐⭐"
    elif score >= 0.4:
        return "⭐⭐⭐"
    elif score >= 0.2:
        return "⭐⭐"
    else:
        return "⭐"


def get_relevance_label(score: float) -> str:
    """Obtiene etiqueta de relevancia en español."""
    if score >= 0.8:
        return "Muy relevante"
    elif score >= 0.6:
        return "Relevante"
    elif score >= 0.4:
        return "Algo relevante"
    else:
        return "Poco relevante"


def format_relative_time(date_str: Optional[str]) -> str:
    """Formatea fecha a tiempo relativo amigable."""
    if not date_str:
        return "Fecha desconocida"

    try:
        from datetime import datetime
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        now = datetime.now(date.tzinfo) if date.tzinfo else datetime.now()
        delta = now - date

        if delta.days < 1:
            return "Hoy"
        elif delta.days < 7:
            return f"Hace {delta.days} días"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"Hace {weeks} semana{'s' if weeks > 1 else ''}"
        elif delta.days < 365:
            months = delta.days // 30
            return f"Hace {months} mes{'es' if months > 1 else ''}"
        else:
            years = delta.days // 365
            return f"Hace {years} año{'s' if years > 1 else ''}"
    except:
        return date_str[:10] if date_str else "Fecha desconocida"


# ============================================================
# COMPONENTES DE UI PÚBLICA
# ============================================================

def render_public_header():
    """Renderiza el header con la identidad visual de Infancia Digital.
    Usa el degradado azul oscuro → azul claro del manual.
    El logo se incrusta como base64 para asegurar que se renderiza dentro del div."""
    st.markdown(get_public_css(), unsafe_allow_html=True)
    logo_path = Path(__file__).parent.parent / "assets" / "logo_buscador_semantico.png"
    if logo_path.exists():
        import base64
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
        st.markdown(f"""
    <div class="public-header">
        <img src="data:image/png;base64,{logo_b64}" style="width: 70px; height: auto; margin-bottom: 0.75rem;" />
        <h1>Datatrust</h1>
        <p class="subtitle">Buscador semántico de datasets públicos</p>
    </div>
    """, unsafe_allow_html=True)
    else:
        st.markdown("""
    <div class="public-header">
        <h1>🔍 Datatrust</h1>
        <p class="subtitle">Buscador semántico de datasets públicos</p>
    </div>
    """, unsafe_allow_html=True)


def on_search_change():
    """Callback cuando cambia el texto de búsqueda (detecta Enter)."""
    if st.session_state.get("search_public", ""):
        st.session_state.enter_pressed = True


def render_search_bar_public() -> Tuple[str, int]:
    """
    Renderiza la barra de búsqueda estilo Google.

    NOTA IMPORTANTE: Streamlit no permite modificar el valor de un widget
    después de que ha sido creado. Usamos un enfoque basado en st.query_params
    para las búsquedas populares en lugar de modificar session_state directamente.

    Returns:
        Tuple[str, int]: (query, top_k)
    """
    st.markdown("""
    <style>
    .stTextInput > div > div > input {
        border-radius: 24px !important;
        border: 1px solid #DADADA !important;
        padding: 12px 20px !important;
        font-size: 16px !important;
        font-family: 'Inter', sans-serif !important;
        box-shadow: none !important;
        transition: box-shadow 0.2s ease !important;
    }
    .stTextInput > div > div > input:focus {
        box-shadow: 0 1px 6px rgba(8, 0, 102, 0.28) !important;
        border-color: #1F7CFF !important;
    }
    .stTextInput > label {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([6, 1])

    with col1:
        # Usar active_query del session_state como valor por defecto
        # Esto hace que la barra muestre la búsqueda activa aunque se cambien filtros
        default_value = st.session_state.get("active_query", "")

        query = st.text_input(
            "Buscar",
            value=default_value,
            placeholder="¿Qué datos buscas? Ej: educación Madrid, paro juvenil...",
            label_visibility="collapsed",
            on_change=on_search_change,
            key="search_public"
        )

    with col2:
        top_k = st.selectbox(
            "Mostrar",
            options=[10, 25, 50],
            index=0,
            key="top_k_public",
            label_visibility="collapsed"
        )

    return query, top_k


def render_popular_searches(on_select):
    """Renderiza búsquedas populares como chips clicables.
    Funcionan como toggle: un toque activa el filtro de categoría, otro lo quita."""
    # (emoji, etiqueta visible, VALOR real de `theme` en la BD)
    popular = [
        ("📊", "Empleo", "empleo"),
        ("🏫", "Educación", "educacion"),
        ("🌍", "Medio Ambiente", "medio-ambiente"),
        ("🏥", "Sanidad", "salud"),
        ("🚗", "Transporte", "transporte"),
        ("💰", "Economía", "economia"),
        ("🏛️", "Administración", "sector-publico"),
        ("👥", "Demografía", "demografia"),
    ]

    # CSS para resaltar botones de categorías activos vs inactivos
    # Usamos :has() para limitar solo a la sección de categorías
    st.markdown("""
    <style>
    /* Botón activo: fondo azul oscuro corporativo, texto blanco, sombra */
    div[data-testid="stButton"] > button[kind="primary"]:has(*),
    div[data-testid="stButton"] > button[kind="primary"] {
        background-color: #080066 !important;
        color: white !important;
        border: 2px solid #080066 !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(8, 0, 102, 0.3) !important;
        transform: scale(1.02);
    }
    /* Botón inactivo: fondo blanco, borde gris */
    div[data-testid="stButton"] > button[kind="secondary"] {
        background-color: #ffffff !important;
        color: #1D1E1B !important;
        border: 1px solid #DADADA !important;
        font-weight: 400 !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        border-color: #1F7CFF !important;
        color: #1F7CFF !important;
        background-color: #f0ecf6 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='category-buttons' style='text-align: center; margin-top: 1rem;'>", unsafe_allow_html=True)
    st.markdown("<p style='color: #585857; font-size: 0.875rem; margin-bottom: 0.75rem;'>📂 Categorías</p>", unsafe_allow_html=True)

    cols = st.columns(4)
    for i, (emoji, label, value) in enumerate(popular):
        with cols[i % 4]:
            # Comprobar si este filtro está activo
            current_tema = st.session_state.get('current_filters', {}).get('tema', '').lower()
            is_active = current_tema == value.lower()
            if st.button(
                f"{emoji} {label}",
                key=f"popular_{i}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                on_select(value)

    st.markdown("</div>", unsafe_allow_html=True)


def render_filter_chips(territorios: List[str], temas: List[str], current_filters: Dict, on_change):
    """Renderiza filtros como chips seleccionables."""
    filters_changed = False
    new_filters = current_filters.copy()

    # Filtro de territorio (solo los más comunes)
    common_territories = ["España", "Madrid", "Barcelona", "Canarias", "País Vasco", "Cataluña"]
    available_territories = [t for t in common_territories if t in territorios][:6]

    if available_territories:
        st.markdown("<p style='color: #585857; font-size: 0.875rem; margin: 1rem 0 0.5rem 0;'>📍 Territorio</p>", unsafe_allow_html=True)
        cols = st.columns(len(available_territories))
        for i, terr in enumerate(available_territories):
            with cols[i]:
                is_active = current_filters.get('territorio') == terr
                if st.button(
                    terr,
                    key=f"terr_{terr}",
                    type="secondary" if not is_active else "primary",
                    use_container_width=True
                ):
                    if is_active:
                        new_filters.pop('territorio', None)
                    else:
                        new_filters['territorio'] = terr
                    filters_changed = True

    # Filtro de tema (solo los más comunes)
    common_themes = ["economía", "educación", "empleo", "medio ambiente", "salud", "transporte"]
    available_themes = [t for t in common_themes if t in [tm.lower() for tm in temas]][:6]

    if available_themes:
        st.markdown("<p style='color: #585857; font-size: 0.875rem; margin: 1rem 0 0.5rem 0;'>🏷️ Categoría</p>", unsafe_allow_html=True)
        cols = st.columns(len(available_themes))
        for i, theme in enumerate(available_themes):
            with cols[i]:
                is_active = current_filters.get('tema', '').lower() == theme
                if st.button(
                    theme.capitalize(),
                    key=f"theme_{theme}",
                    type="secondary" if not is_active else "primary",
                    use_container_width=True
                ):
                    if is_active:
                        new_filters.pop('tema', None)
                    else:
                        new_filters['tema'] = theme.capitalize()
                    filters_changed = True

    return new_filters, filters_changed


def clean_facet_values(values: List[str]) -> List[str]:
    """Limpia valores de facetas eliminando duplicados y normalizando formato."""
    cleaned = []
    seen = set()

    for val in values:
        if not val:
            continue

        # Si es una lista representada como string, extraer elementos
        if isinstance(val, str) and val.startswith('[') and val.endswith(']'):
            try:
                import ast
                items = ast.literal_eval(val)
                if isinstance(items, list):
                    for item in items:
                        item_str = str(item).strip().lower()
                        if item_str and item_str not in seen:
                            seen.add(item_str)
                            cleaned.append(item_str)
                    continue
            except:
                val = val[1:-1].replace("'", "").replace('"', '')

        # Limpieza normal
        val_clean = str(val).strip()
        val_lower = val_clean.lower()

        if val_clean and val_lower not in seen:
            seen.add(val_lower)
            cleaned.append(val_clean)

    return sorted(cleaned, key=lambda x: x.lower())


def render_filters_dropdown(territorios: List[str], temas: List[str], current_filters: Dict) -> Dict:
    """Renderiza filtros como desplegables con todas las opciones.
    Sincroniza el estado del dropdown con current_filters para que los botones
    de categoría y el dropdown compartan el mismo estado."""
    new_filters = current_filters.copy()

    # Limpiar y normalizar opciones
    terr_options = clean_facet_values(territorios) if territorios else []
    tema_options = clean_facet_values(temas) if temas else []

    # "Todos" permite quitar el filtro: un selectbox de Streamlit no se puede
    # desseleccionar una vez elegido un valor.
    TODOS = "Todos"
    terr_choices = [TODOS] + [o for o in terr_options if o.lower() != TODOS.lower()]
    tema_choices = [TODOS] + [o for o in tema_options if o.lower() != TODOS.lower()]

    def _index_of(choices, value):
        """Posición del valor en las opciones; 0 es "Todos"."""
        if value:
            for i, opt in enumerate(choices):
                if opt.lower() == value.lower():
                    return i
        return 0

    terr_index = _index_of(terr_choices, current_filters.get('territorio', ''))
    tema_index = _index_of(tema_choices, current_filters.get('tema', ''))

    # Sincronizar el widget con el estado (p. ej. al pulsar un chip de categoría).
    # Se ASIGNA el valor: borrar la clave descarta la selección que el usuario
    # acaba de hacer, porque current_filters no la refleja hasta después de
    # pintar el desplegable.
    # Si la clave ya existe en session_state, se asigna el valor y NO se pasa
    # `index` (Streamlit prohíbe ambas cosas a la vez); si no existe, se pasa
    # `index` como valor inicial.
    terr_kwargs = {}
    if 'filter_terr_dropdown' in st.session_state:
        expected = terr_choices[terr_index]
        if st.session_state['filter_terr_dropdown'] != expected:
            st.session_state['filter_terr_dropdown'] = expected
    else:
        terr_kwargs['index'] = terr_index
    tema_kwargs = {}
    if 'filter_tema_dropdown' in st.session_state:
        expected = tema_choices[tema_index]
        if st.session_state['filter_tema_dropdown'] != expected:
            st.session_state['filter_tema_dropdown'] = expected
    else:
        tema_kwargs['index'] = tema_index

    def _persist_filter(widget_key, field):
        """on_change: guarda la selección ANTES de que corra el script."""
        value = st.session_state.get(widget_key)
        cf = st.session_state.get('current_filters')
        if cf is None:
            cf = {}
            st.session_state.current_filters = cf
        if value and value != TODOS:
            cf[field] = value
        else:
            cf.pop(field, None)
        if st.session_state.get('has_searched'):
            st.session_state['_refilter'] = True

    def _on_terr_change():
        _persist_filter('filter_terr_dropdown', 'territorio')

    def _on_tema_change():
        _persist_filter('filter_tema_dropdown', 'tema')

    # Layout de dos columnas
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<p style='color: #585857; font-size: 0.875rem; margin-bottom: 0.25rem;'>📍 Territorio</p>", unsafe_allow_html=True)
        st.selectbox(
            "Territorio",
            options=terr_choices,
            label_visibility="collapsed",
            key="filter_terr_dropdown",
            on_change=_on_terr_change,
            **terr_kwargs
        )

    with col2:
        st.markdown("<p style='color: #585857; font-size: 0.875rem; margin-bottom: 0.25rem;'>🏷️ Categoría</p>", unsafe_allow_html=True)
        st.selectbox(
            "Tema",
            options=tema_choices,
            label_visibility="collapsed",
            key="filter_tema_dropdown",
            on_change=_on_tema_change,
            **tema_kwargs
        )

    return st.session_state.get('current_filters', {}).copy()


def is_direct_download(url: str) -> tuple[bool, str]:
    """
    Detecta si la URL es un archivo descargable directo o una página web.

    Returns:
        tuple: (es_descargable, tipo_archivo)
    """
    if not url:
        return False, "WEB"

    url_lower = url.lower()

    # Extensiones de archivos de datos comunes
    data_extensions = {
        '.csv': 'CSV',
        '.xls': 'XLS',
        '.xlsx': 'XLSX',
        '.json': 'JSON',
        '.xml': 'XML',
        '.pdf': 'PDF',
        '.zip': 'ZIP',
        '.rar': 'RAR',
        '.tar': 'TAR',
        '.gz': 'GZ',
        '.txt': 'TXT',
        '.doc': 'DOC',
        '.docx': 'DOCX',
        '.ods': 'ODS',
        '.odt': 'ODT',
        '.shp': 'SHP',
        '.kml': 'KML',
        '.geojson': 'GEOJSON',
        '.sqlite': 'SQLITE',
        '.db': 'DB',
        '.sql': 'SQL',
        '.sdmx': 'SDMX',
        '.px': 'PX',
        '.tsv': 'TSV',
        '.rdf': 'RDF',
        '.rdfs': 'RDFS',
        '.ttl': 'TTL',
        '.nt': 'NT',
        '.svg': 'SVG',
    }

    # Patrones de descarga directa
    download_patterns = ['/download', '/descargar', '/export', '/data', '?download=']

    # Verificar extensión
    for ext, tipo in data_extensions.items():
        if url_lower.endswith(ext) or f"{ext}?" in url_lower or f"{ext}&" in url_lower:
            return True, tipo

    # Verificar patrones de descarga en URL
    for pattern in download_patterns:
        if pattern in url_lower:
            return True, "DOWNLOAD"

    return False, "WEB"


def extract_formats(result: Dict) -> List[str]:
    """Extrae todos los formatos disponibles del resultado."""
    formatos = result.get('formato', [])
    formats_clean = []

    if isinstance(formatos, list):
        for fmt in formatos:
            if isinstance(fmt, str):
                # Limpiar formatos como ["CSV", "PDF"] o CSV
                fmt_clean = fmt.strip().strip('[]').replace('"', '').replace("'", '')
                if fmt_clean and fmt_clean not in formats_clean:
                    formats_clean.append(fmt_clean.upper())
    elif isinstance(formatos, str):
        fmt_clean = formatos.strip().strip('[]').replace('"', '').replace("'", '')
        if fmt_clean:
            formats_clean.append(fmt_clean.upper())

    return formats_clean


def render_result_card_public(result: Dict, index: int, search_id: int = 0):
    """Renderiza una tarjeta de resultado limpia y amigable."""
    score = result.get("score", 0)
    stars = score_to_stars(score)
    relevance = get_relevance_label(score)

    title = result.get('title', 'Sin título')
    description = truncate_text(result.get('description', ''), 180)
    publisher = result.get('publisher', 'Desconocido')
    url = result.get('url', '#')
    dataset_id = result.get('id', '')

    # Prefijo único por búsqueda para evitar que Streamlit reutilice estado de búsquedas anteriores
    sid = f"s{search_id}"

    # Sprint 8: Obtener TL;DR y perfil del dataset (con cache)
    tldr = None
    if dataset_id:
        try:
            profile_info = get_dataset_profile_info(dataset_id)
            if profile_info:
                tldr = profile_info.get("tldr")
        except Exception:
            tldr = None

    # Escapar caracteres HTML especiales
    title = title.replace('<', '&lt;').replace('>', '&gt;') if title else 'Sin título'
    description = description.replace('<', '&lt;').replace('>', '&gt;') if description else ''
    publisher = publisher.replace('<', '&lt;').replace('>', '&gt;') if publisher else 'Desconocido'

    # Detectar tipo de enlace (archivo directo vs página web)
    es_directo, tipo_archivo = is_direct_download(url)

    # Extraer todos los formatos disponibles
    formatos_disponibles = extract_formats(result)

    # Formato principal para mostrar en el badge:
    # Priorizar el tipo real del archivo (extensión de la URL) sobre el primer
    # formato alfabético de los metadatos (que siempre es CSV por array_agg DISTINCT).
    fmt_principal = tipo_archivo if es_directo else (formatos_disponibles[0] if formatos_disponibles else 'WEB')

    # Si el tipo real del archivo no está en los formatos de metadatos, añadirlo al principio
    if es_directo and tipo_archivo and tipo_archivo not in formatos_disponibles:
        formatos_disponibles = [tipo_archivo] + formatos_disponibles

    # Construir lista de formatos para mostrar
    if formatos_disponibles and len(formatos_disponibles) > 1:
        formatos_texto = ', '.join(formatos_disponibles[:3])  # Max 3 formatos
        if len(formatos_disponibles) > 3:
            formatos_texto += f' +{len(formatos_disponibles) - 3} más'
    elif formatos_disponibles:
        formatos_texto = formatos_disponibles[0]
    else:
        formatos_texto = None

    # Nota informativa si el formato real difiere de los metadatos
    formato_nota = ""
    if es_directo and tipo_archivo and formatos_disponibles and len(formatos_disponibles) > 1:
        metadatos_fmts = [f for f in formatos_disponibles if f != tipo_archivo]
        if metadatos_fmts:
            formato_nota = f"📦 El archivo se descarga como {tipo_archivo} (puede contener {', '.join(metadatos_fmts[:2])})"

    # Territorio
    territorios = result.get('territorio', [])
    if isinstance(territorios, list) and territorios:
        location = territorios[0]
    elif isinstance(territorios, str):
        location = territorios
    else:
        location = None

    # Fecha
    issued = result.get('issued')
    time_ago = format_relative_time(issued)

    location_html = f"<span>📍 {location}</span>" if location else ""
    time_html = f"<span>🕒 {time_ago}</span>" if issued else ""

    # Construir sección de formatos/enlace
    if es_directo:
        # Es un archivo descargable directo
        link_indicator = f"📥 Descargar"
        link_color = "#C42A00"  # Rojo acento accesible sobre blanco (5.71:1)
        formato_info = f"""<div style="font-size: 0.8rem; color: #585857; margin-top: 0.5rem;">
            📄 Formato: <strong>{formatos_texto if formatos_texto else fmt_principal}</strong>
        </div>""" if formatos_texto else ""
        # Nota informativa si el formato real difiere de los metadatos
        if formato_nota:
            formato_info += f"""<div style="font-size: 0.75rem; color: #856404; margin-top: 0.25rem;">
                {formato_nota}
            </div>"""
    else:
        # Es una página web
        link_indicator = "🌐 Ver página del dataset"
        link_color = "#080066"  # Azul oscuro corporativo
        if formatos_texto:
            formato_info = f"""<div style="font-size: 0.8rem; color: #585857; margin-top: 0.5rem;">
                💡 Formatos disponibles: <strong>{formatos_texto}</strong>
            </div>"""
        else:
            formato_info = """<div style="font-size: 0.8rem; color: #ed8936; margin-top: 0.5rem;">
                ⚠️ Página web - busca el archivo descargable en el enlace
            </div>"""

    # Sprint 8: TL;DR inline (escapado para HTML)
    tldr_html = ""
    if tldr:
        tldr_safe = tldr.replace('<', '&lt;').replace('>', '&gt;')
        tldr_html = f"""
        <div style="font-size: 0.9rem; color: #1D1E1B; background: #f0ecf6; border-left: 3px solid #1F7CFF;
                    padding: 0.5rem 0.75rem; margin: 0.5rem 0; border-radius: 0 6px 6px 0; line-height: 1.5;">
            <strong>TL;DR:</strong> {tldr_safe}
        </div>
        """

    # Construir HTML como string
    html_content = f"""
    <div class="result-card-public">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
            <div>
                <a href="{url}" target="_blank" style="text-decoration: none;">
                    <div class="result-title-public">{title}</div>
                </a>
            </div>
            <div style="flex-shrink: 0; margin-left: 1rem;">
                <span class="format-tag">{fmt_principal}</span>
            </div>
        </div>

        {tldr_html}

        <div class="result-meta-public">
            <span>🏛️ {publisher}</span>
            {location_html}
            {time_html}
        </div>

        <div class="result-description-public">{description}</div>

        {formato_info}

        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.75rem;">
            <div style="font-size: 0.875rem; color: #585857;">
                <span class="relevance-stars">{stars}</span>
                <span style="margin-left: 0.5rem;">{relevance}</span>
            </div>
            <a href="{url}" target="_blank"
               style="color: {link_color}; text-decoration: none; font-weight: 500; font-size: 0.875rem;">
                {link_indicator} →
            </a>
        </div>
    </div>
    """

    # Usar st.html() si está disponible, sino st.markdown con unsafe_allow_html
    try:
        st.html(html_content)
    except:
        st.markdown(html_content, unsafe_allow_html=True)

    # Sprint 8: Datasets complementarios (bajo demanda)
    if dataset_id:
        expander_comp_key = f"expander_complementary_{sid}_{dataset_id}_{index}"
        with st.expander("🔍 ¿Datasets complementarios?", expanded=False, key=expander_comp_key):
            st.markdown(
                "<p style='color: #1D1E1B; font-size: 0.95rem;'>"
                "Buscamos datasets que podrían combinarse con este para análisis conjunto. "
                "La primera vez puede tardar unos segundos.</p>",
                unsafe_allow_html=True
            )
            try:
                with st.spinner("Buscando datasets complementarios..."):
                    complementary = get_complementary_datasets(dataset_id, limit=3)
                if complementary:
                    st.markdown(
                        "<p style='color: #1D1E1B; font-weight: 600;'>"
                        "Este dataset podría combinarse con:</p>",
                        unsafe_allow_html=True
                    )
                    for comp in complementary:
                        comp_title = comp.get("title", "Sin título")
                        comp_id = comp.get("dataset_id", "")
                        reason = comp.get("reason", "")
                        join_key = comp.get("join_key", "")
                        potential = comp.get("potential_analysis", "")
                        st.markdown(
                            f"<div style='color: #1D1E1B; background: #f0ecf6; padding: 0.75rem; "
                            f"border-radius: 8px; margin-bottom: 0.5rem; border-left: 3px solid #C42A00;'>"
                            f"<strong>{comp_title}</strong><br>"
                            f"<span style='color: #585857; font-size: 0.9rem;'>{reason}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                else:
                    st.warning("⚠️ No se encontraron datasets complementarios automáticamente.")
                    st.markdown(
                        "<p style='color: #585857; font-size: 0.875rem;'>"
                        "Prueba con otro dataset o formula una pregunta directa en el chat.</p>",
                        unsafe_allow_html=True
                    )
            except Exception as e:
                st.error(f"❌ Error cargando complementarios: {e}")

    # Sprint 8 (#10): Chat sobre el dataset (bajo demanda)
    if dataset_id:
        with st.expander("💬 Preguntar sobre este dataset", expanded=False):
            st.markdown(
                "<p style='color: #1D1E1B; font-size: 0.95rem;'>"
                "Haz una pregunta sobre este dataset. El asistente responde con los "
                "metadatos del dataset y, si el dataset tiene fichero indexado, con la "
                "estructura y el contenido real del fichero. "
                "La primera vez puede tardar unos segundos.</p>",
                unsafe_allow_html=True
            )
            chat_input_key = f"chat_input_{sid}_{dataset_id}_{index}"
            user_question = st.text_input(
                "Tu pregunta",
                placeholder="Ej: ¿Qué datos contiene? ¿Incluye datos de 2023?",
                key=chat_input_key,
                label_visibility="collapsed"
            )
            ask_button_key = f"ask_button_{sid}_{dataset_id}_{index}"
            response_key = f"chat_response_{sid}_{dataset_id}_{index}"
            if st.button("Preguntar", key=ask_button_key):
                if user_question and user_question.strip():
                    with st.spinner("🤖 Pensando..."):
                        try:
                            chat_response = ask_dataset_question(dataset_id, user_question.strip())
                            if chat_response and chat_response.get("answer"):
                                st.session_state[response_key] = chat_response
                            else:
                                st.session_state[response_key] = {
                                    "answer": "No se pudo generar una respuesta. Inténtalo con otra pregunta.",
                                    "model": "N/A",
                                    "latency_ms": 0
                                }
                        except Exception as e:
                            st.session_state[response_key] = {
                                "answer": f"Error al consultar al asistente: {e}",
                                "model": "N/A",
                                "latency_ms": 0
                            }
                else:
                    st.warning("Escribe una pregunta antes de enviar.")

            # Mostrar respuesta guardada (persiste entre re-runs)
            if response_key in st.session_state:
                resp = st.session_state[response_key]
                st.markdown(
                    f"<div style='color: #1D1E1B; background: #f0ecf6; padding: 0.75rem; "
                    f"border-radius: 8px; border-left: 3px solid #1F7CFF; margin-top: 0.5rem;'>"
                    f"<strong>Respuesta:</strong><br>"
                    f"<span style='color: #1D1E1B;'>{resp.get('answer', '')}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                st.caption(f"Modelo: {resp.get('model', 'N/A')} · {resp.get('latency_ms', 0)} ms")


def render_active_filters(filters: Dict, query: str = ""):
    """Renderiza los filtros activos como chips visuales con botón de quitar.
    También muestra la query activa si la hay."""
    chips_html = []

    if query:
        chips_html.append(
            f"<span style='display: inline-flex; align-items: center; gap: 0.4rem; "
            f"background: #080066; color: white; padding: 0.4rem 0.9rem; "
            f"border-radius: 9999px; font-size: 0.85rem; font-weight: 500; margin: 0.25rem;'>"
            f"🔍 {query}</span>"
        )

    for key, value in filters.items():
        icon = "📍" if key == "territorio" else "🏷️"
        chips_html.append(
            f"<span style='display: inline-flex; align-items: center; gap: 0.4rem; "
            f"background: #1F7CFF; color: white; padding: 0.4rem 0.9rem; "
            f"border-radius: 9999px; font-size: 0.85rem; font-weight: 500; margin: 0.25rem;'>"
            f"{icon} {value}</span>"
        )

    if chips_html:
        st.markdown(
            f"<div style='display: flex; flex-wrap: wrap; align-items: center; "
            f"margin: 0.5rem 0 1rem 0; padding: 0.75rem; "
            f"background: #f0ecf6; border-radius: 12px; "
            f"border: 1px solid #DADADA;'>"
            f"<span style='color: #585857; font-size: 0.8rem; margin-right: 0.5rem;'>Filtros activos:</span>"
            f"{''.join(chips_html)}"
            f"</div>",
            unsafe_allow_html=True
        )


def render_empty_state_public():
    """Renderiza el estado inicial amigable."""
    # Obtener count dinámico de la API (cacheado en session_state para evitar rerenders)
    datasets_count = 0
    if 'datasets_count' not in st.session_state:
        try:
            from common.utils import check_api_health
            health = check_api_health()
            datasets_count = health.get('datasets_count', 0) if health else 0
            st.session_state['datasets_count'] = datasets_count
        except Exception:
            st.session_state['datasets_count'] = 0
    else:
        datasets_count = st.session_state.get('datasets_count', 0)

    count_display = f"{datasets_count:,}".replace(",", ".") if datasets_count > 0 else "miles de"

    st.markdown(f"""
    <div class="empty-state-public">
        <div class="icon">🔍</div>
        <h3>Busca entre {count_display} datasets públicos</h3>
        <p>Escribe lo que necesitas en lenguaje natural.<br>
        Por ejemplo: "datos de tráfico en Madrid" o "estadísticas de empleo juvenil"</p>
    </div>
    """, unsafe_allow_html=True)


def render_no_results_public():
    """Renderiza mensaje cuando no hay resultados."""
    st.markdown("""
    <div class="empty-state-public">
        <div class="icon">🤔</div>
        <h3>No encontramos resultados exactos</h3>
        <p>Prueba con otros términos o elimina algunos filtros.<br>
        También puedes probar búsquedas más generales.</p>
    </div>
    """, unsafe_allow_html=True)


def render_results_header_public(query: str, total_results: int, returned: int):
    """Renderiza el header de resultados minimalista."""
    st.markdown(f"""
    <div style="padding: 1rem 0; border-bottom: 1px solid #DADADA; margin-bottom: 1rem;">
        <div style="font-size: 0.875rem; color: #585857;">
            {returned} de {total_results} resultados para "<strong>{query}</strong>"
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_public_footer():
    """Renderiza el footer con la identidad visual de Infancia Digital."""
    st.markdown("""
    <div class="public-footer">
        <p>🔍 Datatrust · Buscador Semántico</p>
        <p style="font-size: 0.75rem; margin-top: 0.5rem;">
            Datos de datos.gob.es · Búsqueda semántica con tecnología abierta
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_mode_toggle(is_advanced: bool) -> bool:
    """
    Renderiza toggle para cambiar a modo avanzado.

    Returns:
        bool: True si el usuario quiere modo avanzado
    """
    col1, col2, col3 = st.columns([1, 2, 1])

    with col3:
        if st.button("⚙️ Modo Avanzado", key="toggle_advanced", type="secondary"):
            # Redirigir a la versión técnica
            st.query_params['mode'] = 'advanced'
            st.rerun()

    return is_advanced
