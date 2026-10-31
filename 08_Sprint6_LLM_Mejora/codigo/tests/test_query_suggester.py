#!/usr/bin/env python3
"""
Tests unitarios para Query Suggester (#13)

20 tests cubriendo:
- Generación léxica de sugerencias
- Categorías de sugerencias (sinónimo, temporal, territorial, técnica)
- Edge cases (queries vacías, ambiguas, sin match)
- Integración con LLM (opcional)
"""

import sys
import os
import pytest
from pathlib import Path

# Añadir ruta al motor
sys.path.insert(0, str(Path(__file__).parent.parent / "motor"))

from query_suggester import (
    QuerySuggester,
    Suggestion,
    SuggestionResult,
    get_query_suggester,
    TERMINOS_TECNICOS,
)


class TestQuerySuggesterLexical:
    """Tests para generación léxica de sugerencias."""

    @pytest.fixture
    def suggester(self):
        """Crear sugeridor para tests."""
        return get_query_suggester(verbose=False)

    def test_suggest_basic(self, suggester):
        """Test 1: Generación básica de sugerencias."""
        result = suggester.suggest_lexical("paro juvenil", n=5)

        assert isinstance(result, SuggestionResult)
        assert result.query_original == "paro juvenil"
        assert len(result.suggestions) > 0
        assert result.lexical_count > 0
        assert result.duration_ms < 100  # Debe ser <100ms

    def test_suggest_with_synonyms(self, suggester):
        """Test 2: Sugerencias con sinónimos directos."""
        result = suggester.suggest_lexical("paro", n=5)

        # Debe contener al menos un sinónimo de "paro"
        suggestion_texts = [s.text.lower() for s in result.suggestions]
        has_synonym = any(
            "desempleo" in t or "atur" in t or "parados" in t
            for t in suggestion_texts
        )
        assert has_synonym, "Debe contener sinónimos de 'paro'"

    def test_suggest_preserves_original_meaning(self, suggester):
        """Test 3: Sugerencias mantienen significado original."""
        result = suggester.suggest_lexical("empleo juvenil", n=5)

        # Las sugerencias deben estar relacionadas con empleo
        for sug in result.suggestions:
            text_lower = sug.text.lower()
            # Debe contener términos relacionados con empleo o jóvenes
            assert any(
                term in text_lower
                for term in ["empleo", "trabajo", "ocupación", "jóvenes", "juvenil", "paro"]
            ), f"Sugerencia '{sug.text}' no parece relacionada con empleo juvenil"

    def test_suggest_categories(self, suggester):
        """Test 4: Filtrado por categorías."""
        # Solo sinónimos
        result_sin = suggester.suggest_lexical("paro", n=10, categories=["sinonimo"])
        for sug in result_sin.suggestions:
            assert sug.category == "sinonimo"

        # Solo temporal
        result_temp = suggester.suggest_lexical("paro 2023", n=10, categories=["temporal"])
        for sug in result_temp.suggestions:
            assert sug.category == "temporal"

    def test_suggest_temporal_variations(self, suggester):
        """Test 5: Variaciones temporales."""
        result = suggester.suggest_lexical("paro 2023", n=5)

        # Debe sugerir 2022 o 2024
        suggestion_texts = [s.text.lower() for s in result.suggestions]
        has_temporal = any("2022" in t or "2024" in t for t in suggestion_texts)
        assert has_temporal, "Debe contener variaciones temporales"

    def test_suggest_territorial_variations(self, suggester):
        """Test 6: Variaciones territoriales."""
        result = suggester.suggest_lexical("paro Canarias", n=5)

        # Debe sugerir España o por municipio
        suggestion_texts = [s.text.lower() for s in result.suggestions]
        has_territorial = any(
            "españa" in t or "municipio" in t or "isla" in t
            for t in suggestion_texts
        )
        assert has_territorial, "Debe contener variaciones territoriales"

    def test_suggest_technical_terms(self, suggester):
        """Test 7: Términos técnicos del dominio."""
        result = suggester.suggest_lexical("paro registrado", n=5)

        # Debe sugerir términos técnicos como EPA, tasa de desempleo
        suggestion_texts = [s.text.lower() for s in result.suggestions]
        has_technical = any(
            "epa" in t or "tasa" in t or "desempleo" in t
            for t in suggestion_texts
        )
        assert has_technical, "Debe contener términos técnicos"

    def test_suggest_confidence_ordering(self, suggester):
        """Test 8: Sugerencias ordenadas por confianza."""
        result = suggester.suggest_lexical("vivienda", n=5)

        if len(result.suggestions) > 1:
            for i in range(len(result.suggestions) - 1):
                assert result.suggestions[i].confidence >= result.suggestions[i + 1].confidence

    def test_suggest_no_duplicates(self, suggester):
        """Test 9: Sin sugerencias duplicadas."""
        result = suggester.suggest_lexical("turismo Barcelona", n=10)

        texts = [s.text.lower().strip() for s in result.suggestions]
        assert len(texts) == len(set(texts)), "No debe haber sugerencias duplicadas"

    def test_suggest_limit(self, suggester):
        """Test 10: Respeta límite n."""
        result = suggester.suggest_lexical("economía", n=3)

        assert len(result.suggestions) <= 3


class TestQuerySuggesterEdgeCases:
    """Tests para casos edge y errores."""

    @pytest.fixture
    def suggester(self):
        """Crear sugeridor para tests."""
        return get_query_suggester(verbose=False)

    def test_empty_query(self, suggester):
        """Test 11: Query vacía."""
        result = suggester.suggest_lexical("", n=5)

        assert result.query_original == ""
        # Debe manejar gracefully, quizás sin sugerencias
        assert isinstance(result, SuggestionResult)

    def test_single_word_query(self, suggester):
        """Test 12: Query de una palabra."""
        result = suggester.suggest_lexical("salud", n=5)

        assert result.query_original == "salud"
        assert len(result.suggestions) >= 0  # Puede no tener sugerencias

    def test_very_long_query(self, suggester):
        """Test 13: Query muy larga."""
        long_query = "paro juvenil desempleo jóvenes menores de 30 años Canarias España"
        result = suggester.suggest_lexical(long_query, n=5)

        assert result.query_original == long_query
        assert isinstance(result, SuggestionResult)

    def test_query_with_special_chars(self, suggester):
        """Test 14: Query con caracteres especiales."""
        result = suggester.suggest_lexical("paro juvenil (Canarias) 2023", n=5)

        assert result.query_original == "paro juvenil (Canarias) 2023"
        assert isinstance(result, SuggestionResult)

    def test_query_unknown_terms(self, suggester):
        """Test 15: Query con términos desconocidos."""
        result = suggester.suggest_lexical("xyz123 abc456", n=5)

        assert result.query_original == "xyz123 abc456"
        # No debe fallar, puede no tener sugerencias
        assert isinstance(result, SuggestionResult)

    def test_query_accents(self, suggester):
        """Test 16: Query con acentos."""
        result = suggester.suggest_lexical("población española", n=5)

        assert result.query_original == "población española"
        assert isinstance(result, SuggestionResult)


class TestQuerySuggesterIntegration:
    """Tests de integración."""

    @pytest.fixture
    def suggester(self):
        """Crear sugeridor con preprocessor real."""
        return get_query_suggester(verbose=False)

    def test_integration_with_preprocessor(self, suggester):
        """Test 17: Integración con QueryPreprocessor."""
        # Esta query debe tener estructura detectada
        result = suggester.suggest_lexical("paro juvenil Canarias 2023", n=5)

        assert result.query_original == "paro juvenil Canarias 2023"
        assert len(result.suggestions) > 0

        # Verificar que las sugerencias son coherentes
        for sug in result.suggestions:
            assert sug.text  # Texto no vacío
            assert sug.category  # Categoría definida
            assert sug.reason  # Razón explicada

    def test_suggestion_categories_present(self, suggester):
        """Test 18: Todas las categorías están presentes."""
        # Query que debería activar múltiples categorías
        result = suggester.suggest_lexical("paro Canarias 2023", n=10)

        categories_found = set(sug.category for sug in result.suggestions)

        # Debe tener al menos 2 categorías diferentes
        assert len(categories_found) >= 2, f"Categorías encontradas: {categories_found}"

    def test_real_world_queries(self, suggester):
        """Test 19: Queries del mundo real."""
        real_queries = [
            "vulnerabilidad económica",
            "abandono escolar temprano",
            "renta per cápita municipio",
            "turismo hoteles 2023",
            "población mayor 65 años",
        ]

        for query in real_queries:
            result = suggester.suggest_lexical(query, n=3)
            assert isinstance(result, SuggestionResult)
            assert result.query_original == query

    def test_suggestion_reasons_are_helpful(self, suggester):
        """Test 20: Las razones son útiles para el usuario."""
        result = suggester.suggest_lexical("paro", n=5)

        for sug in result.suggestions:
            assert len(sug.reason) > 10, f"Razón muy corta: {sug.reason}"
            # La razón debe explicar por qué se sugiere
            assert any(
                word in sug.reason.lower()
                for word in ["sinónimo", "relacionado", "término", "ámbito", "año", "desglose"]
            ), f"Razón no explicativa: {sug.reason}"


class TestTerminosTecnicos:
    """Tests para términos técnicos del dominio."""

    def test_tecnicos_dict_not_empty(self):
        """Test: Diccionario de técnicos no vacío."""
        assert len(TERMINOS_TECNICOS) > 0

    def test_tecnicos_has_expected_domains(self):
        """Test: Domains esperados presentes."""
        expected_domains = ["paro", "empleo", "población", "economia", "turismo"]

        for domain in expected_domains:
            # Verificar que al menos algún dominio relacionado existe
            has_related = any(
                domain.lower() in k.lower() for k in TERMINOS_TECNICOS.keys()
            )
            assert has_related, f"Dominio '{domain}' no encontrado en TERMINOS_TECNICOS"


if __name__ == "__main__":
    # Ejecutar tests sin pytest (para debug)
    print("=" * 70)
    print("TESTS MANUALES DE QUERY SUGGESTER")
    print("=" * 70)

    suggester = get_query_suggester(verbose=True)

    test_queries = [
        ("paro juvenil", 5),
        ("vulnerabilidad económica", 5),
        ("turismo Barcelona 2023", 5),
        ("población mayor 65", 5),
        ("", 5),  # Edge case: vacía
        ("xyz123", 5),  # Edge case: desconocida
    ]

    passed = 0
    failed = 0

    for query, n in test_queries:
        print(f"\n{'='*70}")
        print(f"📝 Query: '{query}'")
        print("="*70)

        try:
            result = suggester.suggest_lexical(query, n=n)
            print(f"✅ OK - {result.lexical_count} sugerencias en {result.duration_ms:.1f}ms")

            for i, sug in enumerate(result.suggestions, 1):
                print(f"  {i}. [{sug.category}] {sug.text}")
                print(f"     → {sug.reason} (conf: {sug.confidence:.2f})")

            passed += 1
        except Exception as e:
            print(f"❌ FAIL: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESUMEN: {passed} passed, {failed} failed")
    print("=" * 70)
