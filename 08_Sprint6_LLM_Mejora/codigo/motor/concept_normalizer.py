#!/usr/bin/env python3
"""
Normalización Conceptual para Búsqueda Semántica - EXPERIMENTAL

Módulo para detectar conceptos en queries y clasificar resultados
como equivalente/relacionado/complementario/no_equivalente.

Uso: Experimental - Activar solo con conceptual_normalization=True

Autor: Fonta
Fecha: 2026-06-05
"""

import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache

# Intentar cargar YAML, si no está disponible usar fallback
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# ============================================
# CONFIGURACIÓN
# ============================================

DEFAULT_CONCEPTS_PATH = Path(__file__).parent.parent / "config" / "conceptos_semanticos.yml"

# Multiplicadores de score por clasificación conceptual
SCORE_MULTIPLIERS = {
    "equivalente": 1.15,
    "relacionado": 1.00,
    "complementario": 0.90,
    "no_equivalente": 0.60,
    "desconocido": 1.00,
}

# Umbrales
MIN_SCORE_FOR_ADJUSTMENT = 0.1  # No ajustar scores muy bajos


# ============================================
# FUNCIONES DE NORMALIZACIÓN DE TEXTO
# ============================================

def normalize_text(text: str) -> str:
    """
    Normaliza texto para matching conceptual:
    - Minúsculas
    - Elimina tildes
    - Limpia puntuación básica
    - Colapsa espacios múltiples

    Args:
        text: Texto a normalizar

    Returns:
        Texto normalizado
    """
    if not text:
        return ""

    # Minúsculas
    text = text.lower()

    # Eliminar tildes (normalización NFD → eliminar combinantes → NFC)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = unicodedata.normalize('NFC', text)

    # Eliminar puntuación (mantener letras, números, espacios)
    text = re.sub(r'[^\w\s]', '', text)

    # Colapsar espacios múltiples
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def normalize_query_for_detection(query: str) -> str:
    """
    Normaliza query específicamente para detección de conceptos.
    Mantiene la estructura de palabras para matching de frases.
    """
    return normalize_text(query)


# ============================================
# CARGA DE CONCEPTOS
# ============================================

@lru_cache(maxsize=1)
def load_concepts(path: Optional[str] = None) -> dict:
    """
    Carga diccionario de conceptos desde YAML.
    Usa caché para evitar recargar en cada petición.

    Args:
        path: Ruta al archivo YAML (opcional, usa default si None)

    Returns:
        Diccionario de conceptos anidados
    """
    if path is None:
        path = str(DEFAULT_CONCEPTS_PATH)

    concepts_path = Path(path)

    if not concepts_path.exists():
        return {}

    if not YAML_AVAILABLE:
        # Fallback básico sin YAML - cargar como texto plano
        # (no implementado, retornar vacío)
        return {}

    try:
        with open(concepts_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Extraer solo los conceptos (excluir metadata)
        concepts = {k: v for k, v in data.items() if k != 'metadata'}
        return concepts

    except Exception as e:
        print(f"Error cargando conceptos: {e}")
        return {}


def get_all_subconcepts(concepts: dict) -> Dict[str, dict]:
    """
    Aplana la estructura jerárquica de conceptos.

    Args:
        concepts: Diccionario jerárquico {dominio: {subconcepto: {...}}}

    Returns:
        Diccionario plano {subconcepto: {...}}
    """
    flat = {}
    for domain, subconcepts in concepts.items():
        if isinstance(subconcepts, dict):
            for sub_id, sub_data in subconcepts.items():
                if isinstance(sub_data, dict) and 'label' in sub_data:
                    # Añadir referencia al dominio padre
                    flat[sub_id] = {**sub_data, 'domain': domain}
    return flat


# ============================================
# DETECCIÓN DE CONCEPTOS EN QUERY
# ============================================

def detect_concept(query: str, concepts: Optional[dict] = None) -> Optional[dict]:
    """
    Detecta si la query contiene triggers de algún concepto conocido.

    Estrategia:
    1. Normalizar query
    2. Buscar triggers de cada subconcepto
    3. Retornar el primer concepto detectado (o el más específico)

    Args:
        query: Query del usuario
        concepts: Diccionario de conceptos (opcional, carga default si None)

    Returns:
        Dict con concept_id, concept_label, domain, matched_triggers
        o None si no se detecta concepto
    """
    if concepts is None:
        concepts = load_concepts()

    if not concepts:
        return None

    query_normalized = normalize_query_for_detection(query)
    query_words = set(query_normalized.split())

    # Obtener todos los subconceptos planos
    subconcepts = get_all_subconcepts(concepts)

    best_match = None
    best_score = 0

    for subconcept_id, subconcept_data in subconcepts.items():
        triggers = subconcept_data.get('triggers', [])

        for trigger in triggers:
            trigger_normalized = normalize_text(trigger)

            # Matching exacto de frase
            if trigger_normalized in query_normalized:
                # Score basado en longitud del trigger (más específico = mayor score)
                score = len(trigger_normalized.split())
                if score > best_score:
                    best_score = score
                    best_match = {
                        'concept_id': subconcept_id,
                        'concept_label': subconcept_data.get('label', subconcept_id),
                        'domain': subconcept_data.get('domain', 'unknown'),
                        'matched_trigger': trigger,
                        'confidence': min(1.0, score / 4.0),  # Normalizar a 0-1
                    }

            # Matching por palabras clave (si el trigger es multi-palabra)
            elif len(trigger_normalized.split()) >= 2:
                trigger_words = set(trigger_normalized.split())
                overlap = len(trigger_words & query_words)
                if overlap >= len(trigger_words) * 0.7:  # 70% overlap
                    score = overlap
                    if score > best_score:
                        best_score = score
                        best_match = {
                            'concept_id': subconcept_id,
                            'concept_label': subconcept_data.get('label', subconcept_id),
                            'domain': subconcept_data.get('domain', 'unknown'),
                            'matched_trigger': trigger,
                            'confidence': min(1.0, score / 4.0),
                            'partial_match': True,
                        }

    return best_match


# ============================================
# EXPANSIÓN DE QUERY CONCEPTUAL
# ============================================

def build_conceptual_expansion(
    query: str,
    detected_concept: Optional[dict],
    concepts: Optional[dict] = None
) -> str:
    """
    Construye expansión de query añadiendo equivalentes del concepto detectado.

    Args:
        query: Query original
        detected_concept: Concepto detectado por detect_concept() o None
        concepts: Diccionario de conceptos

    Returns:
        Query expandida con equivalentes (o query original si no hay concepto)
    """
    if concepts is None:
        concepts = load_concepts()

    # Si no hay concepto detectado, devolver query original
    if detected_concept is None:
        return query

    concept_id = detected_concept.get('concept_id')
    if not concept_id:
        return query

    # Buscar el concepto en la estructura jerárquica
    equivalentes = []
    for domain, subconcepts in concepts.items():
        if isinstance(subconcepts, dict) and concept_id in subconcepts:
            equivalentes = subconcepts[concept_id].get('equivalentes', [])
            break

    if not equivalentes:
        return query

    # Añadir equivalentes que no estén ya en la query
    query_normalized = normalize_query_for_detection(query)
    query_words = set(query_normalized.split())

    nuevos_terminos = []
    for equivalente in equivalentes:
        eq_normalized = normalize_text(equivalente)
        # Añadir solo si no está ya implícito en la query
        if eq_normalized not in query_normalized:
            eq_words = set(eq_normalized.split())
            if not eq_words.issubset(query_words):
                nuevos_terminos.append(equivalente)

    if not nuevos_terminos:
        return query

    # Construir query expandida (originales primero, luego equivalentes)
    expanded = query + " " + " ".join(nuevos_terminos[:5])  # Limitar a 5 equivalentes

    return expanded


# ============================================
# CLASIFICACIÓN CONCEPTUAL DE RESULTADOS
# ============================================

def classify_result_conceptually(
    result: dict,
    detected_concept: Optional[dict],
    concepts: Optional[dict] = None
) -> dict:
    """
    Clasifica un resultado como equivalente/relacionado/complementario/no_equivalente.

    Usa title, description, theme y publisher para la clasificación.

    Args:
        result: Resultado de búsqueda con title, description, theme, etc.
        detected_concept: Concepto detectado o None
        concepts: Diccionario de conceptos

    Returns:
        Dict con classification, matched_terms, penalized_terms, explanation
    """
    if concepts is None:
        concepts = load_concepts()

    # Si no hay concepto detectado, devolver desconocido
    if detected_concept is None:
        return {
            'conceptual_relation': 'desconocido',
            'conceptual_score': 1.0,
            'matched_terms': [],
            'penalized_terms': [],
            'conceptual_explanation': 'No se detectó concepto en la query.',
        }

    concept_id = detected_concept.get('concept_id')
    if not concept_id:
        return {
            'conceptual_relation': 'desconocido',
            'conceptual_score': 1.0,
            'matched_terms': [],
            'penalized_terms': [],
            'conceptual_explanation': 'Concepto sin ID válido.',
        }

    # Extraer términos del concepto
    terminos = {}
    for domain, subconcepts in concepts.items():
        if isinstance(subconcepts, dict) and concept_id in subconcepts:
            data = subconcepts[concept_id]
            terminos = {
                'equivalentes': set(normalize_text(t) for t in data.get('equivalentes', [])),
                'relacionados': set(normalize_text(t) for t in data.get('relacionados', [])),
                'complementarios': set(normalize_text(t) for t in data.get('complementarios', [])),
                'no_equivalentes': set(normalize_text(t) for t in data.get('no_equivalentes', [])),
            }
            break

    if not terminos:
        return {
            'conceptual_relation': 'desconocido',
            'conceptual_score': 1.0,
            'matched_terms': [],
            'penalized_terms': [],
            'conceptual_explanation': 'Concepto no encontrado en diccionario.',
        }

    # Normalizar contenido del resultado
    result_text = normalize_text(
        f"{result.get('title', '')} {result.get('description', '')} {result.get('theme', '')}"
    )
    result_words = set(result_text.split())

    # Buscar coincidencias
    matched = {'equivalentes': [], 'relacionados': [], 'complementarios': [], 'no_equivalentes': []}

    for categoria, terminos_set in terminos.items():
        for termino in terminos_set:
            # Matching exacto de frase
            if termino in result_text:
                matched[categoria].append(termino)
            # Matching por palabras (para términos cortos)
            elif len(termino.split()) <= 2:
                termino_words = set(termino.split())
                if termino_words.issubset(result_words):
                    matched[categoria].append(termino)

    # Determinar clasificación (prioridad: no_equivalentes > equivalentes > relacionados > complementarios)
    classification = 'desconocido'
    explanation = ''

    if matched['no_equivalentes']:
        classification = 'no_equivalente'
        explanation = f"El resultado contiene términos NO equivalentes al concepto: {', '.join(matched['no_equivalentes'][:3])}"
    elif matched['equivalentes']:
        classification = 'equivalente'
        explanation = f"El resultado contiene términos equivalentes al concepto: {', '.join(matched['equivalentes'][:3])}"
    elif matched['relacionados']:
        classification = 'relacionado'
        explanation = f"El resultado está relacionado semánticamente: {', '.join(matched['relacionados'][:3])}"
    elif matched['complementarios']:
        classification = 'complementario'
        explanation = f"El resultado es complementario al concepto: {', '.join(matched['complementarios'][:3])}"
    else:
        explanation = "No se encontraron términos conceptuales en el resultado."

    # Calcular score conceptual
    multiplier = SCORE_MULTIPLIERS.get(classification, 1.0)

    return {
        'concept_id': concept_id,
        'concept_label': detected_concept.get('concept_label', concept_id),
        'conceptual_relation': classification,
        'conceptual_score': multiplier,
        'matched_terms': matched['equivalentes'] + matched['relacionados'],
        'penalized_terms': matched['no_equivalentes'],
        'conceptual_explanation': explanation,
    }


# ============================================
# AJUSTE DE SCORE
# ============================================

def apply_conceptual_score_adjustment(
    result: dict,
    classification: dict
) -> dict:
    """
    Aplica ajuste de score basado en clasificación conceptual.

    Args:
        result: Resultado con campo 'score' o 'llm_score'
        classification: Clasificación conceptual de classify_result_conceptually()

    Returns:
        Resultado con score_original y score_conceptual_adjusted
    """
    # Obtener score original
    original_score = result.get('score', result.get('llm_score', 0.0))

    # Obtener multiplicador
    multiplier = classification.get('conceptual_score', 1.0)

    # Aplicar ajuste solo si el score original supera el umbral
    if original_score >= MIN_SCORE_FOR_ADJUSTMENT:
        adjusted_score = original_score * multiplier
    else:
        adjusted_score = original_score

    # Devolver resultado con metadatos conceptuales
    return {
        **result,
        'score_original': original_score,
        'score_conceptual_adjusted': round(adjusted_score, 6),
        'conceptual_relation': classification.get('conceptual_relation', 'desconocido'),
        'conceptual_explanation': classification.get('conceptual_explanation', ''),
    }


# ============================================
# FUNCIONES DE UTILIDAD
# ============================================

def get_concept_info(concept_id: str, concepts: Optional[dict] = None) -> Optional[dict]:
    """
    Obtiene información completa de un concepto por su ID.

    Args:
        concept_id: ID del subconcepto (ej: 'desempleo_juvenil')
        concepts: Diccionario de conceptos

    Returns:
        Dict con toda la información del concepto o None
    """
    if concepts is None:
        concepts = load_concepts()

    for domain, subconcepts in concepts.items():
        if isinstance(subconcepts, dict) and concept_id in subconcepts:
            data = subconcepts[concept_id]
            return {
                **data,
                'concept_id': concept_id,
                'domain': domain,
            }

    return None


def list_available_concepts(concepts: Optional[dict] = None) -> List[dict]:
    """
    Lista todos los conceptos disponibles.

    Args:
        concepts: Diccionario de conceptos

    Returns:
        Lista de dicts con concept_id, label, domain, triggers_count
    """
    if concepts is None:
        concepts = load_concepts()

    result = []
    for domain, subconcepts in concepts.items():
        if isinstance(subconcepts, dict):
            for sub_id, sub_data in subconcepts.items():
                if isinstance(sub_data, dict) and 'label' in sub_data:
                    result.append({
                        'concept_id': sub_id,
                        'label': sub_data.get('label', sub_id),
                        'domain': domain,
                        'triggers_count': len(sub_data.get('triggers', [])),
                    })

    return sorted(result, key=lambda x: x['label'])


# ============================================
# API PÚBLICA DEL MÓDULO
# ============================================

__all__ = [
    # Carga
    'load_concepts',
    'get_all_subconcepts',
    'get_concept_info',
    'list_available_concepts',

    # Normalización
    'normalize_text',
    'normalize_query_for_detection',

    # Detección
    'detect_concept',

    # Expansión
    'build_conceptual_expansion',

    # Clasificación
    'classify_result_conceptually',

    # Ajuste de score
    'apply_conceptual_score_adjustment',

    # Constantes
    'SCORE_MULTIPLIERS',
    'DEFAULT_CONCEPTS_PATH',
]


# ============================================
# TEST RÁPIDO (para desarrollo)
# ============================================

if __name__ == '__main__':
    # Test básico
    print("=== Test Concept Normalizer ===\n")

    concepts = load_concepts()
    print(f"Conceptos cargados: {len(concepts)} dominios")

    test_queries = [
        "paro juvenil por municipio",
        "alquiler vivienda madrid",
        "gasto sanitario comunidades",
        "abandono escolar temprano",
        "calidad del aire ciudad",
        "query sin concepto claro",
    ]

    print("\n=== Detección de Conceptos ===")
    for query in test_queries:
        detected = detect_concept(query, concepts)
        if detected:
            print(f"✓ '{query}' → {detected['concept_label']} ({detected['confidence']:.2f})")
        else:
            print(f"✗ '{query}' → sin concepto")

    print("\n=== Expansión de Query ===")
    query = "paro juvenil"
    detected = detect_concept(query, concepts)
    if detected:
        expanded = build_conceptual_expansion(query, detected, concepts)
        print(f"Original:  {query}")
        print(f"Expandida: {expanded}")

    print("\n=== Clasificación de Resultados ===")
    test_results = [
        {'title': 'Tasa de paro juvenil por comunidades', 'description': 'Datos de desempleo juvenil', 'theme': 'Empleo'},
        {'title': 'Contratos laborales de jóvenes', 'description': 'Estadísticas de contratación', 'theme': 'Empleo'},
        {'title': 'Abandono escolar temprano', 'description': 'Tasas de abandono educativo', 'theme': 'Educación'},
    ]

    for res in test_results:
        classification = classify_result_conceptually(res, detected, concepts)
        print(f"\n{res['title']}")
        print(f"  Clasificación: {classification['conceptual_relation']}")
        print(f"  Explicación: {classification['conceptual_explanation']}")
