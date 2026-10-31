"""
Utilidades para el frontend del Buscador Semántico.
"""
import requests
import streamlit as st
from typing import Dict, List, Optional
import urllib3
import json
from pathlib import Path

# Suprimir advertencias de certificado SSL autofirmado
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# URL de la API - Actualizar según el entorno
# Desarrollo local (API FastAPI):
API_URL = "http://localhost:8000"
# Servidor Fonta (si la API está en otro lugar):
# API_URL = "https://servidor1.local:8443"

# Detectar entorno y ajustar ruta base para facetas
if Path("/home/node/.openclaw/workspace").exists():
    BASE_DIR = Path("/home/node/.openclaw/workspace/PFM/Datatrust")
else:
    BASE_DIR = Path.home() / "datos/PFM/Datatrust"

FACETAS_FILE = BASE_DIR / "15_Frontends/frontend_a_basico/facetas.json"


def _safe_request(url: str, method: str = "get", **kwargs) -> Optional[Dict]:
    """Realiza petición HTTP con manejo robusto de errores."""
    try:
        if method == "get":
            response = requests.get(url, timeout=10, verify=False, **kwargs)
        else:
            response = requests.post(url, timeout=30, verify=False, **kwargs)
        
        # Verificar status code
        if response.status_code != 200:
            st.error(f"❌ Error HTTP {response.status_code} en {url}")
            st.code(f"Respuesta: {response.text[:500]}")
            return None
        
        # Verificar que sea JSON
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            st.warning(f"⚠️ Respuesta no es JSON (Content-Type: {content_type})")
            st.code(f"Primeros 500 chars: {response.text[:500]}")
            return None
        
        # Intentar parsear JSON
        try:
            return response.json()
        except json.JSONDecodeError as e:
            st.error(f"❌ Error parseando JSON: {e}")
            st.code(f"Respuesta cruda (primeros 500 chars): {response.text[:500]}")
            return None
            
    except requests.exceptions.ConnectionError:
        st.error(f"""
❌ **No se puede conectar a la API**

Verifica que:
1. La API esté corriendo: `curl {API_URL}/health`
2. La URL sea correcta en `utils.py`

URL actual: `{API_URL}`
        """)
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
    """Realiza una búsqueda híbrida via API."""
    payload = {
        "query": query,
        "top_k": top_k,
        "semantic_weight": semantic_weight,
        "lexical_weight": lexical_weight,
        "min_score": min_score,
        "require_lexical_match": require_lexical,
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
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text
