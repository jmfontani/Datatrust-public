#!/usr/bin/env python3
"""
Tests Unitarios para Concept Normalizer - EXPERIMENTAL

Casos de prueba para el módulo de normalización conceptual.
No requiere PostgreSQL ni API corriendo.

Uso:
    python -m pytest tests/test_concept_normalizer.py -v
    python tests/test_concept_normalizer.py  # Test rápido directo

Autor: Fonta
Fecha: 2026-06-05
"""

import sys
from pathlib import Path

# Añadir path al motor
sys.path.insert(0, str(Path(__file__).parent.parent / "motor"))

from concept_normalizer import (
    normalize_text,
    detect_concept,
    build_conceptual_expansion,
    classify_result_conceptually,
    apply_conceptual_score_adjustment,
    load_concepts,
    get_concept_info,
    list_available_concepts,
    SCORE_MULTIPLIERS,
)


# ============================================
# TESTS DE NORMALIZACIÓN DE TEXTO
# ============================================

def test_normalize_text_basic():
    """Test básico de normalización."""
    assert normalize_text("HOLA") == "hola"
    assert normalize_text("Hola") == "hola"
    print("✓ test_normalize_text_basic")


def test_normalize_text_accents():
    """Test de eliminación de tildes."""
    assert normalize_text("población") == "poblacion"
    assert normalize_text("educación") == "educacion"
    assert normalize_text("público") == "publico"
    assert normalize_text("jóvenes") == "jovenes"
    print("✓ test_normalize_text_accents")


def test_normalize_text_punctuation():
    """Test de limpieza de puntuación."""
    assert normalize_text("hola, mundo!") == "hola mundo"
    assert normalize_text("test...") == "test"
    assert normalize_text("¿qué tal?") == "que tal"
    print("✓ test_normalize_text_punctuation")


def test_normalize_text_spaces():
    """Test de colapso de espacios."""
    assert normalize_text("hola    mundo") == "hola mundo"
    assert normalize_text("  test  ") == "test"
    print("✓ test_normalize_text_spaces")


# ============================================
# TESTS DE DETECCIÓN DE CONCEPTOS
# ============================================

def test_detect_concept_paro_juvenil():
    """Detecta 'paro juvenil por municipio' como desempleo_juvenil."""
    concepts = load_concepts()
    result = detect_concept("paro juvenil por municipio", concepts)

    assert result is not None, "Debería detectar concepto"
    assert result['concept_id'] == 'desempleo_juvenil'
    assert 'juvenil' in result.get('matched_trigger', '').lower() or result['concept_label'] == 'Desempleo juvenil'
    print("✓ test_detect_concept_paro_juvenil")


def test_detect_concept_alquiler():
    """Detecta 'alquiler vivienda madrid' como alquiler_vivienda."""
    concepts = load_concepts()
    result = detect_concept("alquiler vivienda madrid", concepts)

    assert result is not None, "Debería detectar concepto"
    assert result['concept_id'] == 'alquiler_vivienda'
    print("✓ test_detect_concept_alquiler")


def test_detect_concept_gasto_sanitario():
    """Detecta 'gasto sanitario comunidades' como gasto_sanitario."""
    concepts = load_concepts()
    result = detect_concept("gasto sanitario comunidades", concepts)

    assert result is not None, "Debería detectar concepto"
    assert result['concept_id'] == 'gasto_sanitario'
    print("✓ test_detect_concept_gasto_sanitario")


def test_detect_concept_abandono_escolar():
    """Detecta 'abandono escolar temprano' como abandono_escolar."""
    concepts = load_concepts()
    result = detect_concept("abandono escolar temprano", concepts)

    assert result is not None, "Debería detectar concepto"
    assert result['concept_id'] == 'abandono_escolar'
    print("✓ test_detect_concept_abandono_escolar")


def test_detect_concept_sin_concepto():
    """Query sin concepto claro devuelve None o desconocido."""
    concepts = load_concepts()
    result = detect_concept("query sin concepto claro xyz", concepts)

    # Puede ser None o un match débil - ambos son aceptables
    if result is not None:
        assert result['confidence'] < 0.5, "Match debería ser débil"
    print("✓ test_detect_concept_sin_concepto")


# ============================================
# TESTS DE EXPANSIÓN DE QUERY
# ============================================

def test_expandir_con_equivalentes():
    """Expande query con equivalentes seguros."""
    concepts = load_concepts()
    detected = detect_concept("paro juvenil", concepts)

    assert detected is not None, "Debería detectar concepto"

    expanded = build_conceptual_expansion("paro juvenil", detected, concepts)

    # La query expandida debería ser más larga
    assert len(expanded) > len("paro juvenil")
    # Debería contener la query original
    assert "paro juvenil" in expanded
    print("✓ test_expandir_con_equivalentes")


def test_expandir_sin_concepto():
    """Sin concepto detectado, devuelve query original."""
    concepts = load_concepts()

    # Pasar None explícitamente
    expanded = build_conceptual_expansion("xyz abc query rara", None, concepts)
    assert expanded == "xyz abc query rara"
    print("✓ test_expandir_sin_concepto")


# ============================================
# TESTS DE CLASIFICACIÓN DE RESULTADOS
# ============================================

def test_clasificar_equivalente():
    """Clasifica resultado con 'tasa de paro juvenil' como equivalente."""
    concepts = load_concepts()
    detected = detect_concept("paro juvenil", concepts)

    result = {
        'title': 'Tasa de paro juvenil por comunidades autónomas',
        'description': 'Datos de desempleo juvenil trimestral',
        'theme': 'Empleo',
    }

    classification = classify_result_conceptually(result, detected, concepts)

    assert classification['conceptual_relation'] == 'equivalente'
    assert classification['conceptual_score'] == SCORE_MULTIPLIERS['equivalente']
    print("✓ test_clasificar_equivalente")


def test_clasificar_no_equivalente():
    """Clasifica 'contratos laborales jóvenes' como no_equivalente."""
    concepts = load_concepts()
    detected = detect_concept("paro juvenil", concepts)

    result = {
        'title': 'Contratos laborales de jóvenes menores de 30 años',
        'description': 'Estadísticas de contratación y alta en seguridad social',
        'theme': 'Empleo',
    }

    classification = classify_result_conceptually(result, detected, concepts)

    assert classification['conceptual_relation'] == 'no_equivalente'
    assert classification['conceptual_score'] == SCORE_MULTIPLIERS['no_equivalente']
    print("✓ test_clasificar_no_equivalente")


def test_clasificar_complementario():
    """Clasifica 'abandono escolar' como complementario para paro juvenil."""
    concepts = load_concepts()
    detected = detect_concept("paro juvenil", concepts)

    result = {
        'title': 'Abandono escolar temprano por comunidades',
        'description': 'Tasas de abandono educativo en población juvenil',
        'theme': 'Educación',
    }

    classification = classify_result_conceptually(result, detected, concepts)

    assert classification['conceptual_relation'] == 'complementario'
    assert classification['conceptual_score'] == SCORE_MULTIPLIERS['complementario']
    print("✓ test_clasificar_complementario")


def test_clasificar_desconocido():
    """Sin concepto detectado, devuelve desconocido sin cambiar score."""
    concepts = load_concepts()

    # Pasar None explícitamente como detected_concept
    classification = classify_result_conceptually(
        {'title': 'Resultado', 'description': 'Genérico', 'theme': 'General'},
        None,  # Sin concepto
        concepts
    )

    assert classification['conceptual_relation'] == 'desconocido'
    assert classification['conceptual_score'] == 1.0
    print("✓ test_clasificar_desconocido")


# ============================================
# TESTS DE AJUSTE DE SCORE
# ============================================

def test_ajustar_score_equivalente():
    """Ajusta score con multiplicador 1.15 para equivalente."""
    result = {'score': 0.5}
    classification = {'conceptual_score': 1.15, 'conceptual_relation': 'equivalente'}

    adjusted = apply_conceptual_score_adjustment(result, classification)

    assert adjusted['score_original'] == 0.5
    assert abs(adjusted['score_conceptual_adjusted'] - 0.575) < 0.001
    assert adjusted['conceptual_relation'] == 'equivalente'
    print("✓ test_ajustar_score_equivalente")


def test_ajustar_score_no_equivalente():
    """Ajusta score con multiplicador 0.60 para no_equivalente."""
    result = {'score': 0.5}
    classification = {'conceptual_score': 0.60, 'conceptual_relation': 'no_equivalente'}

    adjusted = apply_conceptual_score_adjustment(result, classification)

    assert adjusted['score_original'] == 0.5
    assert abs(adjusted['score_conceptual_adjusted'] - 0.30) < 0.001
    assert adjusted['conceptual_relation'] == 'no_equivalente'
    print("✓ test_ajustar_score_no_equivalente")


def test_ajustar_score_bajo_umbral():
    """No ajusta scores muy bajos (< 0.1)."""
    result = {'score': 0.05}
    classification = {'conceptual_score': 1.15, 'conceptual_relation': 'equivalente'}

    adjusted = apply_conceptual_score_adjustment(result, classification)

    # Score por debajo del umbral no se ajusta
    assert adjusted['score_original'] == 0.05
    assert adjusted['score_conceptual_adjusted'] == 0.05
    print("✓ test_ajustar_score_bajo_umbral")


# ============================================
# TESTS DE UTILIDAD
# ============================================

def test_list_available_concepts():
    """Lista todos los conceptos disponibles."""
    concepts = load_concepts()
    available = list_available_concepts(concepts)

    assert len(available) > 0, "Debería haber conceptos disponibles"

    # Verificar estructura
    for concept in available:
        assert 'concept_id' in concept
        assert 'label' in concept
        assert 'domain' in concept
        assert 'triggers_count' in concept

    print(f"✓ test_list_available_concepts ({len(available)} conceptos)")


def test_get_concept_info():
    """Obtiene información completa de un concepto."""
    concepts = load_concepts()
    info = get_concept_info('desempleo_juvenil', concepts)

    assert info is not None, "Debería encontrar el concepto"
    assert info['concept_id'] == 'desempleo_juvenil'
    assert info['domain'] == 'empleo'
    assert 'label' in info
    assert 'triggers' in info
    assert 'equivalentes' in info
    print("✓ test_get_concept_info")


# ============================================
# TEST PRINCIPAL
# ============================================

def run_all_tests():
    """Ejecuta todos los tests."""
    print("=" * 60)
    print("TESTS UNITARIOS - CONCEPT NORMALIZER")
    print("=" * 60)
    print()

    tests = [
        # Normalización
        test_normalize_text_basic,
        test_normalize_text_accents,
        test_normalize_text_punctuation,
        test_normalize_text_spaces,

        # Detección
        test_detect_concept_paro_juvenil,
        test_detect_concept_alquiler,
        test_detect_concept_gasto_sanitario,
        test_detect_concept_abandono_escolar,
        test_detect_concept_sin_concepto,

        # Expansión
        test_expandir_con_equivalentes,
        test_expandir_sin_concepto,

        # Clasificación
        test_clasificar_equivalente,
        test_clasificar_no_equivalente,
        test_clasificar_complementario,
        test_clasificar_desconocido,

        # Ajuste de score
        test_ajustar_score_equivalente,
        test_ajustar_score_no_equivalente,
        test_ajustar_score_bajo_umbral,

        # Utilidad
        test_list_available_concepts,
        test_get_concept_info,
    ]

    passed = 0
    failed = 0
    skipped = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"RESULTADOS: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
