"""
Generación de explicaciones de relevancia para resultados de búsqueda.
Simula explicaciones semánticas basadas en palabras clave coincidentes.
"""
from typing import List, Dict, Any
import re


def explain_relevance(dataset: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Genera una explicación de por qué un dataset es relevante para la query.

    Args:
        dataset: Dict con los datos del dataset.
        query: Texto de búsqueda original.

    Returns:
        Dict con:
            - matched_keywords: lista de términos coincidentes
            - explanation: texto legible de explicación
            - field_scores: puntuación por campo (título, descripción, keywords, temas)
    """
    if not query or not query.strip():
        return {
            "matched_keywords": [],
            "explanation": "Dataset destacado por popularidad y completitud de metadatos.",
            "field_scores": {},
        }

    query_terms = _tokenize(query)

    # Campos a evaluar
    fields = {
        "título": dataset.get("title_es", ""),
        "descripción": dataset.get("description_es", ""),
        "keywords": " ".join(dataset.get("keywords", [])),
        "temas": " ".join(dataset.get("themes", [])),
    }

    matched = set()
    field_scores = {}

    for field_name, text in fields.items():
        text_lower = text.lower()
        field_matches = []
        for term in query_terms:
            if term in text_lower:
                field_matches.append(term)
                matched.add(term)
        if field_matches:
            field_scores[field_name] = len(field_matches)

    matched_list = sorted(matched)

    # Generar explicación legible
    explanation = _build_explanation(matched_list, field_scores, dataset)

    return {
        "matched_keywords": matched_list,
        "explanation": explanation,
        "field_scores": field_scores,
    }


def _tokenize(text: str) -> List[str]:
    """Tokeniza y normaliza la query."""
    text = text.lower().strip()
    # Quitar acentos básicos (simplificado)
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "à": "a", "è": "e", "ì": "i", "ò": "o", "ù": "u",
        "ñ": "n",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Extraer palabras alfabéticas de 2+ caracteres
    tokens = [t for t in re.findall(r"[a-z0-9]+", text) if len(t) >= 2]
    return tokens


def _build_explanation(
    matched: List[str], field_scores: Dict[str, int], dataset: Dict[str, Any]
) -> str:
    """Construye texto explicativo basado en coincidencias."""
    if not matched:
        return (
            "Este dataset podría ser relevante por sus metadatos relacionados, "
            "aunque no hay coincidencias directas con los términos buscados."
        )

    parts = []
    # Identificar campo principal
    best_field = max(field_scores, key=field_scores.get) if field_scores else "descripción"

    # Palabras clave encontradas
    kw_phrase = ", ".join(f'"{m}"' for m in matched[:5])
    parts.append(f"Coincide con {kw_phrase} en el {best_field}.")

    # Si hay keywords específicas del dataset que también matchean
    ds_keywords = dataset.get("keywords", [])
    ds_kw_matched = [k for k in ds_keywords if any(m in k.lower() for m in matched)]
    if ds_kw_matched:
        parts.append(f"Etiquetado como: {', '.join(ds_kw_matched[:3])}.")

    # Territorio
    spatial = dataset.get("spatial_name", "").strip()
    if spatial and spatial != "desconocido":
        parts.append(f"Ámbito territorial: {spatial}.")

    return " ".join(parts)


def format_score_badge(score: float) -> str:
    """
    Devuelve una etiqueta visual para el score (usado en Streamlit).
    """
    if score >= 0.5:
        return "🔥 Alta"
    elif score >= 0.3:
        return "⭐ Media"
    elif score > 0:
        return "📌 Baja"
    return ""


def get_match_highlights(text: str, query: str) -> List[tuple]:
    """
    Devuelve lista de (fragmento, es_match) para resaltar términos en UI.

    Args:
        text: Texto base.
        query: Query con términos a resaltar.

    Returns:
        Lista de tuplas (fragmento_texto, bool_is_match).
    """
    if not text or not query:
        return [(text, False)]

    terms = _tokenize(query)
    if not terms:
        return [(text, False)]

    # Construir patrón regex OR-insensitive
    pattern = re.compile(
        "(" + "|".join(re.escape(t) for t in terms) + ")",
        re.IGNORECASE,
    )

    result = []
    last_end = 0
    for match in pattern.finditer(text):
        start, end = match.span()
        if start > last_end:
            result.append((text[last_end:start], False))
        result.append((text[start:end], True))
        last_end = end
    if last_end < len(text):
        result.append((text[last_end:], False))

    return result
