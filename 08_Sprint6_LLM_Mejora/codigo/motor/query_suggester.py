#!/usr/bin/env python3
"""
Query Suggester - Generador de sugerencias de queries relacionadas
Fase 08: Sprint 6 - Caso #13: Sugerencias de Queries Relacionadas

Enfoque híbrido asíncrono:
1. Léxico (<5ms) - Basado en diccionario + estructura
2. LLM (~3-5s) - Creativo, en background

Uso:
    from query_suggester import QuerySuggester

    suggester = QuerySuggester()

    # Sugerencias léxicas (instantáneas)
    lexical = suggester.suggest_lexical("paro juvenil Canarias")

    # Sugerencias LLM (background, más creativas)
    llm = await suggester.suggest_llm("paro juvenil Canarias")
"""

import json
import re
import asyncio
from typing import Dict, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import sys
import os

# Añadir ruta al motor
sys.path.insert(0, os.path.dirname(__file__))

from lexical_expander import get_lexical_expander, LexicalExpander
from query_preprocessor import get_preprocessor, QueryPreprocessor

# Ruta al diccionario de sinónimos
SINONIMOS_JSON_PATH = Path(__file__).parent / "sinonimos.json"

# Términos técnicos del dominio (para sugerencias "expert")
TERMINOS_TECNICOS = {
    "paro": ["EPA", "tasa de desempleo", "paro registrado", "demandantes de empleo"],
    "empleo": ["afiliación SS", "contratos registrados", "puestos de trabajo", "ocupación"],
    "población": ["censo", "padrón municipal", "población residente", "habitantes"],
    "vivienda": ["parque residencial", "viviendas principales", "viviendas vacías", "hogares"],
    "economía": ["PIB", "renta per cápita", "VAB", "valor añadido bruto"],
    "turismo": ["pernoctaciones", "llegadas", "tasa de ocupación hotelera", "plazas hoteleras"],
    "sanidad": ["tarjeta sanitaria", "atención primaria", "hospitalizaciones", "consulta externa"],
    "educación": ["tasa de graduación", "abandono educativo temprano", "alumnos matriculados", "centros educativos"],
    "medioambiente": ["emisiones CO2", "calidad del aire", "residuos urbanos", "consumo energético"],
    "transporte": ["flota de vehículos", "accidentalidad", "movilidad", "tráfico rodado"],
}

# Plantillas de sugerencias por categoría
SUGGESTION_TEMPLATES = {
    "sinonimo": [
        "{sinonimo} {contexto}",
        "{sinonimo} {territorio}",
        "{sinonimo} {año}",
    ],
    "especificacion": [
        "{tema} {detalle} {territorio}",
        "{tema} por {desglose}",
    ],
    "generalizacion": [
        "{tema_padre} {territorio}",
        "{categoria} {territorio}",
    ],
    "temporal": [
        "{tema} {año_anterior}",
        "{tema} últimos {n} años",
        "{tema} evolución {año_inicio}-{año_fin}",
    ],
    "territorial": [
        "{tema} {ambito_superior}",
        "{tema} por municipio",
        "{tema} {ambito_inferior}",
    ],
    "tecnica": [
        "{termino_tecnico} {territorio}",
        "{indicador} {territorio}",
    ],
}


@dataclass
class Suggestion:
    """Una sugerencia de query relacionada."""
    text: str
    category: str  # sinonimo, especificacion, generalizacion, temporal, territorial, tecnica
    reason: str
    confidence: float = 0.0
    source: str = "lexical"  # lexical, llm


@dataclass
class SuggestionResult:
    """Resultado completo de sugerencias."""
    query_original: str
    suggestions: List[Suggestion] = field(default_factory=list)
    lexical_count: int = 0
    llm_count: int = 0
    duration_ms: float = 0.0
    llm_pending: bool = False


class QuerySuggester:
    """
    Generador de sugerencias de queries relacionadas (#13).

    Enfoque híbrido:
    - Léxico: instantáneo (<5ms), basado en diccionario
    - LLM: background (~3-5s), creativo y contextual
    """

    def __init__(self,
                 preprocessor: Optional[QueryPreprocessor] = None,
                 lexical_expander: Optional[LexicalExpander] = None,
                 ollama_url: str = "http://localhost:11434",
                 verbose: bool = False):
        """
        Inicializar sugeridor.

        Args:
            preprocessor: Para obtener estructura de query
            lexical_expander: Para expansión léxica
            ollama_url: URL de Ollama para LLM
            verbose: Mostrar logs
        """
        self.preprocessor = preprocessor or get_preprocessor(ollama_url=ollama_url, verbose=verbose)
        self.lexical_expander = lexical_expander or get_lexical_expander()
        self.ollama_url = ollama_url
        self.verbose = verbose

        # Cargar sinónimos
        self.sinonimos = self._cargar_sinonimos()

        # Cache de resultados LLM (en memoria)
        self._llm_cache: Dict[str, List[Suggestion]] = {}

    def _cargar_sinonimos(self) -> Dict:
        """Cargar diccionario de sinónimos desde JSON."""
        if not SINONIMOS_JSON_PATH.exists():
            return {}

        with open(SINONIMOS_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('sinonimos', {})

    def suggest_lexical(self, query: str, n: int = 5,
                        categories: Optional[List[str]] = None) -> SuggestionResult:
        """
        Generar sugerencias usando solo léxico (instantáneo).

        Args:
            query: Query original
            n: Número máximo de sugerencias
            categories: Filtrar por categoría (None = todas)

        Returns:
            SuggestionResult con sugerencias léxicas
        """
        start = datetime.now()

        # Obtener estructura de la query
        structure = self._get_structure(query)

        suggestions: List[Suggestion] = []
        seen: Set[str] = set()

        # Límite por categoría para asegurar diversidad
        max_per_category = max(2, n // 2)  # Al menos 2 por categoría

        # Definir categorías y sus generadores
        category_generators = [
            ("sinonimo", lambda: self._suggest_by_synonyms(query, structure)),
            ("temporal", lambda: self._suggest_temporal(query, structure)),
            ("territorial", lambda: self._suggest_territorial(query, structure)),
            ("tecnica", lambda: self._suggest_technical(query, structure)),
            ("especificacion", lambda: self._suggest_specification(query, structure)),
        ]

        # Recoger sugerencias de cada categoría con límite
        for cat_name, generator in category_generators:
            if categories and cat_name not in categories:
                continue

            cat_suggestions = []
            for sug in generator():
                if sug.text.lower() not in seen and sug.text.lower() != query.lower():
                    seen.add(sug.text.lower())
                    cat_suggestions.append(sug)
                    if len(cat_suggestions) >= max_per_category:
                        break

            suggestions.extend(cat_suggestions)

        duration = (datetime.now() - start).total_seconds() * 1000

        # Limitar a n sugerencias, priorizando por confianza
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        suggestions = suggestions[:n]

        return SuggestionResult(
            query_original=query,
            suggestions=suggestions,
            lexical_count=len(suggestions),
            duration_ms=duration
        )

    async def suggest_llm(self, query: str, n: int = 5,
                          structure: Optional[Dict] = None) -> SuggestionResult:
        """
        Generar sugerencias usando LLM (background, más creativas).

        Args:
            query: Query original
            n: Número máximo de sugerencias
            structure: Estructura pre-computada (opcional)

        Returns:
            SuggestionResult con sugerencias del LLM
        """
        start = datetime.now()

        # Check cache
        cache_key = f"llm:{query.lower().strip()}"
        if cache_key in self._llm_cache:
            return SuggestionResult(
                query_original=query,
                suggestions=self._llm_cache[cache_key],
                llm_count=len(self._llm_cache[cache_key]),
                duration_ms=0.1,
                llm_pending=False
            )

        # Obtener estructura si no se proporciona
        if not structure:
            struct = self._get_structure(query)
            structure = {
                "temas": struct.temas,
                "territorio": struct.territorio,
                "años": struct.años,
                "conceptos_implicitos": struct.conceptos_implicitos,
            }

        # Construir prompt
        prompt = self._build_llm_prompt(query, structure)

        try:
            # Importar cliente LLM
            from llm_client import create_llm_client
            llm = create_llm_client(use_case="query_expansion", ollama_url=self.ollama_url, verbose=self.verbose)

            response = llm.generate(prompt, format="json")
            parsed = json.loads(response.text)

            suggestions = []
            for item in parsed.get("suggestions", []):
                sug = Suggestion(
                    text=item.get("query", ""),
                    category=item.get("category", "llm"),
                    reason=item.get("reason", ""),
                    confidence=item.get("confidence", 0.7),
                    source="llm"
                )
                if sug.text and sug.text.lower() != query.lower():
                    suggestions.append(sug)

            # Cache
            self._llm_cache[cache_key] = suggestions

            duration = (datetime.now() - start).total_seconds() * 1000

            return SuggestionResult(
                query_original=query,
                suggestions=suggestions[:n],
                llm_count=len(suggestions[:n]),
                duration_ms=duration,
                llm_pending=False
            )

        except Exception as e:
            if self.verbose:
                print(f"[QuerySuggester] Error LLM: {e}")

            # Fallback: retornar empty
            return SuggestionResult(
                query_original=query,
                suggestions=[],
                llm_count=0,
                duration_ms=0,
                llm_pending=False
            )

    def suggest_combined(self, query: str, n_lexical: int = 3,
                         n_llm: int = 3) -> tuple:
        """
        Generar sugerencias combinadas (léxico + LLM en background).

        Returns:
            tuple: (lexical_result, llm_task)
            El caller puede await llm_task para obtener resultados LLM
        """
        # Léxico inmediato
        lexical_result = self.suggest_lexical(query, n=n_lexical)

        # LLM en background
        llm_task = asyncio.create_task(
            self.suggest_llm(query, n=n_llm)
        )

        return lexical_result, llm_task

    def _get_structure(self, query: str):
        """Obtener estructura de la query."""
        try:
            result = self.preprocessor.process(query, use_cache=True)
            return result.structure
        except Exception:
            # Fallback: estructura vacía
            from query_preprocessor import QueryStructure
            return QueryStructure()

    def _suggest_by_synonyms(self, query: str, structure) -> List[Suggestion]:
        """Generar sugerencias reemplazando con sinónimos."""
        suggestions = []
        query_lower = query.lower()

        # Extraer palabras clave
        words = [w for w in query_lower.split() if len(w) > 2]

        for word in words:
            if word in self.sinonimos:
                for sinonimo in self.sinonimos[word]:
                    # Reemplazar palabra con sinónimo
                    new_query = query_lower.replace(word, sinonimo)
                    suggestions.append(Suggestion(
                        text=new_query.strip(),
                        category="sinonimo",
                        reason=f"Sinónimo de '{word}'",
                        confidence=0.9
                    ))

        # También usar expansión léxica
        expanded = self.lexical_expander.expand(query)
        if expanded["query_expandida"] != query:
            suggestions.append(Suggestion(
                text=expanded["query_expandida"],
                category="sinonimo",
                reason="Expansión con sinónimos",
                confidence=0.85
            ))

        return suggestions

    def _suggest_temporal(self, query: str, structure) -> List[Suggestion]:
        """Generar sugerencias con variaciones temporales."""
        suggestions = []
        current_year = datetime.now().year

        # Si hay año en la query, sugerir año anterior/siguiente
        if structure.años:
            for year in structure.años:
                # Año anterior
                prev_query = re.sub(r'\b' + str(year) + r'\b', str(year - 1), query)
                if prev_query != query:
                    suggestions.append(Suggestion(
                        text=prev_query,
                        category="temporal",
                        reason=f"Año anterior ({year - 1})",
                        confidence=0.8
                    ))

                # Año siguiente
                next_query = re.sub(r'\b' + str(year) + r'\b', str(year + 1), query)
                if next_query != query:
                    suggestions.append(Suggestion(
                        text=next_query,
                        category="temporal",
                        reason=f"Año siguiente ({year + 1})",
                        confidence=0.75
                    ))
        else:
            # Si no hay año, sugerir "últimos años"
            for tema in structure.temas[:2]:
                suggestions.append(Suggestion(
                    text=f"{tema} últimos 5 años",
                    category="temporal",
                    reason="Serie temporal",
                    confidence=0.7
                ))

        return suggestions

    def _suggest_territorial(self, query: str, structure) -> List[Suggestion]:
        """Generar sugerencias con variaciones territoriales."""
        suggestions = []

        if structure.territorio:
            territorio = structure.territorio

            # Mapeo de ámbitos
            ambitios = {
                "Canarias": ["España", "por isla", "por municipio"],
                "Cataluña": ["España", "por provincia", "por municipio"],
                "Andalucía": ["España", "por provincia", "por municipio"],
                "Madrid": ["España", "por municipio", "Comunidad de Madrid"],
                "Barcelona": ["Cataluña", "España", "área metropolitana"],
                "Valencia": ["Comunidad Valenciana", "España", "por municipio"],
                "Sevilla": ["Andalucía", "España", "provincia de Sevilla"],
            }

            if territorio in ambitios:
                for ambito in ambitios[territorio]:
                    new_query = query.replace(territorio, ambito)
                    suggestions.append(Suggestion(
                        text=new_query,
                        category="territorial",
                        reason=f"Ámbito: {ambito}",
                        confidence=0.75
                    ))
        else:
            # Si no hay territorio, sugerir "España" o "por municipio"
            for tema in structure.temas[:2]:
                suggestions.append(Suggestion(
                    text=f"{tema} España",
                    category="territorial",
                    reason="Ámbito nacional",
                    confidence=0.7
                ))
                suggestions.append(Suggestion(
                    text=f"{tema} por municipio",
                    category="territorial",
                    reason="Desglose municipal",
                    confidence=0.65
                ))

        return suggestions

    def _suggest_technical(self, query: str, structure) -> List[Suggestion]:
        """Generar sugerencias con terminología técnica."""
        suggestions = []

        for tema in structure.temas:
            # Buscar término técnico para cada tema
            for keyword, tecnicos in TERMINOS_TECNICOS.items():
                if keyword in query.lower():
                    for termino in tecnicos[:2]:  # Máximo 2 sugerencias
                        suggestions.append(Suggestion(
                            text=f"{termino} {structure.territorio or ''}".strip(),
                            category="tecnica",
                            reason=f"Término técnico: {termino}",
                            confidence=0.7
                        ))

        return suggestions

    def _suggest_specification(self, query: str, structure) -> List[Suggestion]:
        """Generar sugerencias más específicas o generalizadas."""
        suggestions = []

        # Desgloses comunes
        desgloses = ["por edad", "por sexo", "por municipio", "anual", "trimestral"]

        for tema in structure.temas[:2]:
            for desglose in desgloses:
                suggestions.append(Suggestion(
                    text=f"{tema} {desglose} {structure.territorio or ''}".strip(),
                    category="especificacion",
                    reason=f"Desglose: {desglose}",
                    confidence=0.65
                ))

        return suggestions

    def _build_llm_prompt(self, query: str, structure: Dict) -> str:
        """Construir prompt para LLM."""
        temas_str = ", ".join(structure.get("temas", []))
        territorio = structure.get("territorio", "no especificado")
        anos = structure.get("años", [])
        conceptos = structure.get("conceptos_implicitos", [])

        return f"""Eres un asistente experto en datos abiertos españoles (datos.gob.es).

Query del usuario: "{query}"

Estructura detectada:
- Temas: {temas_str}
- Territorio: {territorio}
- Años: {anos if anos else "no especificado"}
- Conceptos implícitos: {conceptos if conceptos else "ninguno"}

Genera 5-7 queries alternativas que un ciudadano podría usar para buscar
datos SIMILARES o RELACIONADOS. Las sugerencias deben ser:

1. Variaciones con sinónimos (ej: "paro" → "desempleo")
2. Queries más específicas (con desglose territorial o temporal)
3. Queries más generales (categoría superior)
4. Términos técnicos relacionados (ej: "EPA", "AROPE")
5. Queries relacionadas conceptualmente

Responde EXACTAMENTE en formato JSON:
{{
    "suggestions": [
        {{
            "query": "desempleo jóvenes Canarias",
            "category": "sinonimo",
            "reason": "Sinónimo directo de 'paro juvenil'",
            "confidence": 0.9
        }},
        ...
    ]
}}

Categorías válidas: sinonimo, especificacion, generalizacion, temporal, territorial, tecnica, relacionada

IMPORTANTE: Las queries deben ser REALISTAS y útiles para buscar en datos.gob.es."""


# Singleton para uso en API
_suggester_instance: Optional[QuerySuggester] = None

def get_query_suggester(ollama_url: str = "http://localhost:11434",
                        verbose: bool = False) -> QuerySuggester:
    """Obtener instancia singleton del sugeridor."""
    global _suggester_instance
    if _suggester_instance is None:
        _suggester_instance = QuerySuggester(
            ollama_url=ollama_url,
            verbose=verbose
        )
    return _suggester_instance


if __name__ == "__main__":
    import time

    print("=" * 70)
    print("TEST DEL QUERY SUGGESTER (#13 - Sugerencias de Queries)")
    print("=" * 70)

    suggester = get_query_suggester(verbose=True)

    test_queries = [
        "paro juvenil Canarias",
        "vulnerabilidad económica",
        "turismo Barcelona 2023",
        "población mayor 65 años",
    ]

    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"📝 Query: '{query}'")
        print("="*70)

        # Test léxico
        t0 = time.time()
        lexical_result = suggester.suggest_lexical(query, n=5)
        t1 = time.time()

        print(f"\n⚡ LÉXICO ({(t1-t0)*1000:.1f}ms):")
        for i, sug in enumerate(lexical_result.suggestions, 1):
            print(f"  {i}. [{sug.category}] {sug.text}")
            print(f"     → {sug.reason} (conf: {sug.confidence:.2f})")

        print(f"\n📊 Total léxicas: {lexical_result.lexical_count}")

    print("\n" + "=" * 70)
    print("TESTS COMPLETADOS")
    print("=" * 70)
