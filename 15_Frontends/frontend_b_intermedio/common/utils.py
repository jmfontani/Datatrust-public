"""
Utilidades para el frontend V2 del Buscador Semántico.
"""
import requests
import streamlit as st
from typing import Dict, List, Optional
import urllib3
import json
import os
from pathlib import Path

# Suprimir advertencias de certificado SSL autofirmado
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# URL de la API - Leer de variable de entorno o usar localhost por defecto
API_URL = os.getenv('API_URL', 'http://localhost:8000')

# Detectar entorno y ajustar ruta base
def detect_base_dir():
    """Detecta el directorio base del proyecto de forma portable."""
    # 1. Intentar detectar desde el script actual
    script_dir = Path(__file__).resolve().parent
    
    # Subir hasta encontrar la estructura del proyecto
    for parent in [script_dir, script_dir.parent, script_dir.parent.parent]:
        if (parent / "05_Sprint3_Busqueda_UI").exists() or (parent / "api").exists():
            return parent
    
    # 2. Fallback a paths conocidos
    if Path("/home/node/.openclaw/workspace").exists():
        return Path("/home/node/.openclaw/workspace/PFM/Datatrust")
    
    # 3. Último fallback: asumir estructura relativa desde home
    return Path.home() / "datos/PFM/Datatrust"

BASE_DIR = detect_base_dir()
FACETAS_FILE = BASE_DIR / "05_Sprint3_Busqueda_UI/codigo/frontend/facetas.json"


def _safe_request(url: str, method: str = "get", **kwargs) -> Optional[Dict]:
    """Realiza petición HTTP con manejo robusto de errores."""
    try:
        if method == "get":
            # GET puede disparar generación bajo demanda de TL;DR (hasta ~15-20s)
            response = requests.get(url, timeout=30, verify=False, **kwargs)
        else:
            # POST para chat LLM puede tardar hasta ~10-15s
            response = requests.post(url, timeout=60, verify=False, **kwargs)
        
        if response.status_code != 200:
            st.error(f"❌ Error HTTP {response.status_code} en {url}")
            return None
        
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            st.warning(f"⚠️ Respuesta no es JSON (Content-Type: {content_type})")
            return None
        
        try:
            return response.json()
        except json.JSONDecodeError as e:
            st.error(f"❌ Error parseando JSON: {e}")
            return None
            
    except requests.exceptions.ConnectionError:
        st.error(f"❌ No se puede conectar a la API en {API_URL}")
        return None
    except Exception as e:
        st.error(f"❌ Error en petición: {type(e).__name__}: {e}")
        return None


@st.cache_data(ttl=300)
def get_facet_values(facet: str, limit: int = 100) -> List[str]:
    """Obtiene valores de una faceta desde la API o archivo local."""
    # Primero intentar desde archivo local
    try:
        if FACETAS_FILE.exists():
            with open(FACETAS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                key_map = {
                    "territorio": "territorios",
                    "tema": "temas", 
                    "formato": "formatos",
                    "publisher": "publishers"
                }
                key = key_map.get(facet, facet)
                if key in data:
                    return [item["value"] for item in data[key][:limit]]
    except Exception as e:
        print(f"Error cargando facetas locales: {e}")
    
    # Fallback a API
    url = f"{API_URL}/facets/{facet}"
    data = _safe_request(url, params={"limit": limit})
    if data is None:
        return []
    return data.get("values", [])


def search_datasets(
    query: str,
    top_k: int = 10,
    semantic_weight: float = 0.7,
    lexical_weight: float = 0.3,
    min_score: float = 0.20,
    require_lexical: bool = True,
    territorio: Optional[str] = None,
    tema: Optional[str] = None,
    formato: Optional[str] = None,
    publisher: Optional[str] = None,
) -> Optional[Dict]:
    """Realiza una búsqueda híbrida via API.
    Si la query está vacía pero hay filtros, usa '*' para traer todos los datasets del filtro."""
    effective_query = query.strip() if query.strip() else "*"
    payload = {
        "query": effective_query,
        "top_k": top_k,
        "semantic_weight": semantic_weight,
        "lexical_weight": lexical_weight,
        "min_score": min_score if query.strip() else 0.0,
        "require_lexical_match": require_lexical if query.strip() else False,
        "territorio": territorio,
        "tema": tema,
        "formato": formato,
        "publisher": publisher,
        "explain": True,
    }
    return _safe_request(f"{API_URL}/search", method="post", json=payload)


def check_api_health() -> Optional[Dict]:
    """Verifica estado de la API."""
    return _safe_request(f"{API_URL}/health")


def format_score(score: float) -> str:
    """Formatea un score para mostrar."""
    if score >= 0.8:
        return "🟢 Excelente"
    elif score >= 0.6:
        return "🟡 Bueno"
    elif score >= 0.4:
        return "🟠 Regular"
    else:
        return "🔴 Bajo"


def get_score_color(score: float) -> str:
    """Devuelve color según score."""
    if score >= 0.8:
        return "#28a745"
    elif score >= 0.6:
        return "#ffc107"
    elif score >= 0.4:
        return "#fd7e14"
    else:
        return "#dc3545"


def truncate_text(text: str, max_length: int = 200) -> str:
    """Trunca texto con elipsis."""
    if not text:
        return ""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


@st.cache_data(ttl=300)
def get_dataset_tldr(dataset_id: str) -> Optional[str]:
    """
    Sprint 8 (#14): Obtiene el TL;DR de un dataset desde la API.
    """
    url = f"{API_URL}/complementary/tldr?dataset_id={dataset_id}"
    data = _safe_request(url)
    if data is None:
        return None
    return data.get("tldr")


def get_complementary_datasets(dataset_id: str, limit: int = 3, use_llm: bool = False) -> List[Dict]:
    """
    Sprint 8 (#5): Obtiene datasets complementarios para un dataset.
    Por defecto use_llm=False para respuesta rápida con candidatos por tema/geografía.
    """
    url = f"{API_URL}/complementary/find"
    data = _safe_request(url, method="post", json={
        "dataset_id": dataset_id,
        "limit": limit,
        "use_llm": use_llm
    })
    if data is None:
        return []
    return data.get("complementary_datasets", [])


def get_dataset_profile_info(dataset_id: str) -> Optional[Dict]:
    """
    Sprint 8: Wrapper para obtener TL;DR + complementarios.
    """
    url = f"{API_URL}/complementary/tldr?dataset_id={dataset_id}"
    data = _safe_request(url)
    return data


def ask_dataset_question(dataset_id: str, question: str, model: str = "deepseek-v4.1-flash:cloud") -> Optional[Dict]:
    """
    Sprint 8 (#10): Pregunta al asistente sobre un dataset usando metadatos.

    Args:
        dataset_id: ID del dataset
        question: Pregunta del usuario
        model: Modelo LLM a utilizar

    Returns:
        Dict con answer, source, model, latency_ms o None si falla
    """
    url = f"{API_URL}/dataset/chat"
    data = _safe_request(url, method="post", json={
        "dataset_id": dataset_id,
        "question": question,
        "model": model
    })
    return data
