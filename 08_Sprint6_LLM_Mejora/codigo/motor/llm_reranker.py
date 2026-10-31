#!/usr/bin/env python3
"""
Módulo de Re-ranking con LLM para el Buscador Semántico
Fase 08: Sprint 6 - Mejora con LLM (Propuesta #2: Re-ranking inteligente)

Este módulo toma los resultados del motor híbrido (semántico + léxica) y los reordena
usando un LLM local (Ollama) según criterios analíticos adicionales:
- Relevancia real para el objetivo del usuario
- Calidad y completitud de metadatos
- Actualidad del dataset
- Posibilidad de cruce con otros datos
- Claridad de la descripción

Uso:
    from llm_reranker import LLMReranker

    reranker = LLMReranker()
    results_reordered = reranker.rerank(
        query="consumo energético por provincias",
        results=hybrid_results,
        top_n=10
    )
"""

import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import sys
import os

# Añadir ruta al motor base
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../07_Sprint5_Integracion/codigo/motor'))

# Intentar importar SearchResult del motor base
try:
    from search_engine_pgvector import SearchResult
except ImportError:
    # Fallback: definir SearchResult localmente para tests
    @dataclass
    class SearchResult:
        """Resultado de búsqueda estructurado (fallback para tests)."""
        dataset_id: str
        title: str
        description: str
        publisher: str
        theme: str
        territory: str
        format: str
        score_semantic: float = 0.0
        score_lexical: float = 0.0
        score_final: float = 0.0
        metadata: Dict = field(default_factory=dict)

# Importar cliente LLM
from llm_client import LLMClient, create_llm_client


@dataclass
class RerankedResult:
    """Resultado de búsqueda con re-ranking LLM."""
    dataset_id: str
    title: str
    description: str
    publisher: str
    theme: str
    territory: str
    format: str
    original_rank: int
    new_rank: int
    original_score: float
    llm_relevance_score: float
    explanation: str
    metadata: Dict = None

    @classmethod
    def from_search_result(cls, result: SearchResult, original_rank: int) -> 'RerankedResult':
        """Crear RerankedResult desde SearchResult."""
        return cls(
            dataset_id=result.dataset_id,
            title=result.title,
            description=result.description,
            publisher=result.publisher,
            theme=result.theme,
            territory=result.territory,
            format=result.format,
            original_rank=original_rank,
            new_rank=original_rank,  # Se actualizará después del re-ranking
            original_score=result.score_final,
            llm_relevance_score=0.0,  # Se actualizará
            explanation="",
            metadata=result.metadata
        )


class LLMReranker:
    """
    Re-ranker basado en LLM (Ollama) para mejorar orden de resultados.

    El LLM recibe los metadatos de los Top N resultados y los reordena
    según relevancia analítica, no solo similitud vectorial.

    Por defecto usa modelo FLASH (rápido, económico). Para queries
    complejas que requieran razonamiento profundo, se puede cambiar
    a modelo PRO vía el parámetro 'model'.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: Optional[str] = None,
        timeout: int = 60,
        verbose: bool = False
    ):
        """
        Inicializar re-ranker.

        Args:
            ollama_url: URL base de Ollama
            model: Nombre del modelo (None = usar preset por defecto)
            timeout: Timeout para llamadas a LLM (segundos)
            verbose: Mostrar logs detallados
        """
        self.verbose = verbose

        # Usar cliente LLM con preset de re-ranking
        # Esto permite cambiar fácilmente a modelos más grandes
        self.llm = create_llm_client(
            use_case="reranking",
            ollama_url=ollama_url,
            verbose=verbose
        )

        # Permitir sobrescribir modelo específico
        if model:
            self.llm.model = model

    def _call_llm(self, prompt: str) -> str:
        """
        Llamar al LLM configurado.

        Args:
            prompt: Texto del prompt

        Returns:
            Respuesta del modelo
        """
        try:
            response = self.llm.generate(prompt, format="json")

            if not response.text:
                if self.verbose:
                    print(f"   ⚠️  Respuesta vacía del LLM")
                return ""

            return response.text

        except Exception as e:
            if self.verbose:
                print(f"   ⚠️  Error llamando al LLM: {e}")
            raise

    def _build_rerank_prompt(
        self,
        query: str,
        results: List[SearchResult]
    ) -> str:
        """
        Construir prompt para re-ranking.

        El prompt incluye:
        - La query del usuario
        - Metadatos de los datasets candidatos
        - Instrucciones para evaluar relevancia analítica

        Args:
            query: Consulta original del usuario
            results: Lista de resultados del motor híbrido

        Returns:
            Prompt formateado para el LLM
        """
        # Preparar resumen de datasets
        datasets_summary = []
        for i, result in enumerate(results, 1):
            # Truncar descripción para no saturar
            desc = result.description[:300] + "..." if len(result.description) > 300 else result.description

            datasets_summary.append(f"""
[{i}] Dataset ID: {result.dataset_id}
Título: {result.title}
Descripción: {desc}
Tema: {result.theme}
Territorio: {result.territory}
Publisher: {result.publisher}
Formato: {result.format}
Score original: {result.score_final:.4f}
""")

        datasets_text = "\n---\n".join(datasets_summary)

        prompt = f"""Reordena datasets según relevancia para: "{query}"

{datasets_text}

Responde SOLO con JSON. Para cada dataset:
- relevance_score: 0-10 (sé CRÍTICO, no generoso)
- explanation: justificación ESPECÍFICA en ESPAÑOL

⚠️ IMPORTANTE: Responde SIEMPRE en ESPAÑOL, independientemente del idioma de los ejemplos.

REGLAS DE PUNTUACIÓN (OBLIGATORIAS):
- 9-10: Dataset encaja PERFECTAMENTE (misma ubicación, mismo tema, indicador directo)
- 7-8: Relación válida pero INDIRECTA (por ejemplo: similar geográficamente pero no exacto)
- 5-6: Conexión DÉBIL o forzada (mismo tema general, ubicación diferente)
- 3-4: Relación casi inexistente (solo tangencial)
- 0-2: No relacionado o metadatos incoherentes

REGLAS DE EXPLICACIÓN:
1. Responde SIEMPRE en ESPAÑOL
2. Si el dataset NO está en la ubicación pedida, menciónalo explícitamente
3. Si usas palabras como "similar", "aunque", "pero" → score DEBE ser 7 o menos
4. Si dices "sin conexión" o "diferente" → score 3-4, nunca 6+

EJEMPLOS DE SCORES (en español):

Score 10: "Datos de paro juvenil en Madrid 2023, edad 16-24 exacta"
[Query: paro juvenil Madrid]

Score 6: "Datos de desempleo general en Barcelona, mismo tema pero otra ciudad"
[Query: paro juvenil Madrid] ← Diferente ubicación = score MEDIO

Score 3: "Economía juvenil en Valencia, tema relacionado pero sin datos de paro específico"
[Query: paro juvenil Madrid] ← Lejano = score BAJO

Score 9: "Turismo en Tenerife, datos de ocupación hotelera 2023"
[Query: turismo Canarias]

Score 4: "Turismo en Menorca, islas similares pero no Canarias"
[Query: turismo Canarias] ← NO es Canarias = score BAJO-MEDIO

Score 2: "Alojamientos en Murcia, tema turismo pero región diferente sin conexión"
[Query: turismo Canarias] ← Sin conexión = score MUY BAJO

Responde con este formato:
{{"ranking":[{{"original_position":1,"new_position":1,"relevance_score":9.5,"explanation":"..."}},...]}}"""

        return prompt

    def _parse_rerank_response(
        self,
        response: str,
        results: List[SearchResult]
    ) -> List[RerankedResult]:
        """
        Parsear respuesta del LLM y crear resultados reordenados.

        Args:
            response: Respuesta cruda del LLM
            results: Resultados originales

        Returns:
            Lista de RerankedResult ordenados por nueva posición
        """
        # Extraer JSON de la respuesta
        try:
            # Buscar JSON entre backticks si existe
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            data = json.loads(json_str)
            ranking = data.get("ranking", [])

            # Crear lookup de resultados originales
            original_lookup = {i+1: r for i, r in enumerate(results)}

            # Construir resultados reordenados
            reranked = []
            for item in ranking:
                orig_pos = item.get("original_position", 0)
                new_pos = item.get("new_position", orig_pos)
                score = item.get("relevance_score", 5.0)
                explanation = item.get("explanation", "")

                if orig_pos in original_lookup:
                    result = original_lookup[orig_pos]
                    reranked_result = RerankedResult.from_search_result(result, orig_pos)
                    reranked_result.new_rank = new_pos
                    reranked_result.llm_relevance_score = score
                    reranked_result.explanation = explanation
                    reranked.append((new_pos, reranked_result))

            # Ordenar por nueva posición
            reranked.sort(key=lambda x: x[0])
            return [r for _, r in reranked]

        except json.JSONDecodeError as e:
            # Si falla el parseo, devolver originales sin modificar
            print(f"Warning: Error parseando respuesta LLM: {e}")
            return [
                RerankedResult.from_search_result(r, i+1)
                for i, r in enumerate(results)
            ]

    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_n: int = 10,
        verbose: bool = False
    ) -> Tuple[List[RerankedResult], Dict]:
        """
        Re-rank resultados usando LLM.

        Args:
            query: Consulta original del usuario
            results: Resultados del motor híbrido
            top_n: Cuántos resultados enviar al LLM (los Top N)
            verbose: Si True, imprime información de debug

        Returns:
            (resultados_reordenados, metadata)
        """
        if not results:
            return [], {"status": "empty", "message": "No hay resultados para re-rank"}

        # Tomar solo top_n resultados
        top_results = results[:top_n]

        if verbose:
            print(f"Re-ranking {len(top_results)} resultados para query: '{query}'")

        try:
            # Construir prompt
            prompt = self._build_rerank_prompt(query, top_results)

            if verbose:
                print(f"Prompt length: {len(prompt)} caracteres")

            # Llamar al LLM
            response = self._call_llm(prompt)

            if verbose:
                print(f"Response length: {len(response)} caracteres")
                print(f"Response preview: {response[:500]}...")

            # Parsear respuesta
            reranked = self._parse_rerank_response(response, top_results)

            # Construir metadata
            metadata = {
                "status": "success",
                "original_count": len(results),
                "reranked_count": len(reranked),
                "model": self.llm.model,
                "timestamp": datetime.now().isoformat()
            }

            return reranked, metadata

        except Exception as e:
            # En caso de error, devolver originales
            if verbose:
                print(f"Error en re-ranking: {e}")

            reranked = [
                RerankedResult.from_search_result(r, i+1)
                for i, r in enumerate(top_results)
            ]

            metadata = {
                "status": "error",
                "error": str(e),
                "fallback": "original_order"
            }

            return reranked, metadata

    def compare_rankings(
        self,
        query: str,
        original_results: List[SearchResult],
        reranked_results: List[RerankedResult]
    ) -> Dict:
        """
        Generar análisis comparativo entre ranking original y re-rankeado.

        Args:
            query: Consulta del usuario
            original_results: Resultados originales
            reranked_results: Resultados después de re-ranking

        Returns:
            Diccionario con métricas de comparación
        """
        # Crear lookup por ID
        orig_by_id = {r.dataset_id: (i+1, r) for i, r in enumerate(original_results)}

        # Métricas
        changes = []
        improvements = 0
        degradations = 0

        for r in reranked_results:
            orig_pos = r.original_rank
            new_pos = r.new_rank
            change = orig_pos - new_pos  # Positivo = subió (mejoró)

            changes.append({
                "dataset_id": r.dataset_id,
                "title": r.title[:60],
                "original_position": orig_pos,
                "new_position": new_pos,
                "change": change,
                "explanation": r.explanation
            })

            if change > 0:
                improvements += 1
            elif change < 0:
                degradations += 1

        return {
            "query": query,
            "total_compared": len(reranked_results),
            "improvements": improvements,
            "degradations": degradations,
            "unchanged": len(reranked_results) - improvements - degradations,
            "position_changes": changes
        }


def test_reranker():
    """Test básico del re-ranker."""
    print("=" * 60)
    print("TEST DEL RE-RANKER LLM (Ollama)")
    print("=" * 60)

    # Crear re-ranker
    reranker = LLMReranker(verbose=True)

    # Verificar conexión a Ollama
    print("\n1. Verificando conexión a Ollama...")
    try:
        if reranker.llm.is_available():
            models = reranker.llm.list_models()
            print(f"   ✅ Ollama respondiendo. Modelos: {models[:3]}...")
            if reranker.llm.model not in models:
                print(f"   ⚠️ Modelo '{reranker.llm.model}' no encontrado.")
                print(f"   Usando primer modelo disponible: {models[0] if models else 'N/A'}")
                if models:
                    reranker.llm.model = models[0]
        else:
            print(f"   ❌ Ollama no disponible")
            return
    except Exception as e:
        print(f"   ❌ Error conectando a Ollama: {e}")
        return

    # Crear resultados de prueba (simulados)
    print("\n2. Creando resultados de prueba...")
    test_results = [
        SearchResult(
            dataset_id="test-001",
            title="Estadísticas de empleo juvenil por provincias",
            description="Datos del INE sobre empleo de jóvenes de 16-29 años desagregados por provincias. Periodo 2015-2023.",
            publisher="INE - Instituto Nacional de Estadística",
            theme="empleo",
            territory="España",
            format="CSV",
            score_final=0.85
        ),
        SearchResult(
            dataset_id="test-002",
            title="Paro registrado por municipios",
            description="Datos del SEPE sobre demandantes de empleo registrados a nivel municipal.",
            publisher="Ministerio de Trabajo",
            theme="empleo",
            territory="España",
            format="JSON",
            score_final=0.82
        ),
        SearchResult(
            dataset_id="test-003",
            title="Renta media por hogar",
            description="Estadísticas de renta disponible por hogares a nivel de provincias.",
            publisher="INE - Instituto Nacional de Estadística",
            theme="economia",
            territory="España",
            format="CSV",
            score_final=0.78
        ),
    ]
    print(f"   Creados {len(test_results)} resultados de prueba")

    # Test de re-ranking
    query = "vulnerabilidad económica juvenil"
    print(f"\n3. Ejecutando re-ranking...")
    print(f"   Query: '{query}'")
    print(f"   Modelo: {reranker.llm.model}")

    reranked, metadata = reranker.rerank(query, test_results, top_n=3, verbose=True)

    print(f"\n4. Resultados del re-ranking:")
    print(f"   Status: {metadata['status']}")
    print(f"   Resultados reordenados: {len(reranked)}")

    print("\n" + "-" * 60)
    print("COMPARACIÓN DE RANKINGS:")
    print("-" * 60)

    for r in reranked:
        change_symbol = "↑" if r.new_rank < r.original_rank else ("↓" if r.new_rank > r.original_rank else "→")
        print(f"\n{change_symbol} Posición: {r.original_rank} → {r.new_rank}")
        print(f"   Título: {r.title}")
        print(f"   Score LLM: {r.llm_relevance_score:.1f}/10")
        print(f"   Explicación: {r.explanation}")

    # Análisis comparativo
    print("\n" + "=" * 60)
    comparison = reranker.compare_rankings(query, test_results, reranked)
    print(f"RESUMEN:")
    print(f"  Mejoras: {comparison['improvements']}")
    print(f"  Degradaciones: {comparison['degradations']}")
    print(f"  Sin cambio: {comparison['unchanged']}")
    print("=" * 60)


if __name__ == "__main__":
    test_reranker()
