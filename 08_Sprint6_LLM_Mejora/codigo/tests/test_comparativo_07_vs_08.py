#!/usr/bin/env python3
"""
Test Comparativo: Sprint 07 (Baseline) vs Sprint 08 (LLM)

Valida las mejoras de calidad introducidas con:
- Re-ranking con LLM
- Validación de metadatos
- Explicaciones de relevancia

Uso:
    python test_comparativo_07_vs_08.py --query "vulnerabilidad económica juventud" --output results.json
"""

import requests
import json
import time
import argparse
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime


# Queries de prueba representativas
TEST_QUERIES = [
    {
        "id": "Q1",
        "query": "vulnerabilidad económica juventud",
        "categoria": "socioeconómico",
        "descripcion": "Conceptos abstractos que requieren comprensión semántica"
    },
    {
        "id": "Q2",
        "query": "paro juvenil desempleo jóvenes",
        "categoria": "sinonimia",
        "descripcion": "Múltiples términos sinónimos"
    },
    {
        "id": "Q3",
        "query": "presupuestos municipales Arganda del Rey",
        "categoria": "específica",
        "descripcion": "Búsqueda específica por entidad (verifica corrección publisher)"
    },
    {
        "id": "Q4",
        "query": "calidad del aire Madrid 2023",
        "categoria": "temporal",
        "descripcion": "Con restricción temporal implícita"
    },
    {
        "id": "Q5",
        "query": "datasets medio ambiente Canarias",
        "categoria": "facetada",
        "descripcion": "Combinación tema + territorio"
    },
]


@dataclass
class SearchResult:
    """Resultado de búsqueda normalizado."""
    dataset_id: str
    title: str
    publisher: str
    rank: int
    score: float


@dataclass
class ComparisonMetrics:
    """Métricas de comparación."""
    query: str
    query_id: str
    v07_results: List[SearchResult]
    v08_results: List[SearchResult]
    overlap: List[str]
    v07_unique: List[str]
    v08_unique: List[str]
    avg_score_v07: float
    avg_score_v08: float
    rerank_improvement: float


class TestComparativo:
    """Ejecuta tests comparativos entre v07 y v08."""

    def __init__(self, v07_url: str = "http://localhost:8000", v08_url: str = "http://localhost:8000"):
        self.v07_url = v07_url
        self.v08_url = v08_url
        self.results = []

    def search_v07(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Buscar contra API v07 (baseline)."""
        try:
            response = requests.post(
                f"{self.v07_url}/search",
                json={"query": query, "top_k": limit},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()

            return [
                SearchResult(
                    dataset_id=r.get("id") or r.get("dataset_id", ""),
                    title=r.get("title", ""),
                    publisher=r.get("publisher", ""),
                    rank=i+1,
                    score=r.get("score_final", 0.0)
                )
                for i, r in enumerate(data.get("results", []))
            ]
        except Exception as e:
            print(f"   ⚠️  Error v07: {e}")
            return []

    def search_v08(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Buscar contra API v08 (con LLM re-ranking)."""
        try:
            response = requests.post(
                f"{self.v08_url}/llm/search/rerank",
                json={
                    "query": query,
                    "limit": limit,
                    "rerank_top_n": 10,
                    "use_llm": True
                },
                timeout=180
            )
            response.raise_for_status()
            data = response.json()

            return [
                SearchResult(
                    dataset_id=r.get("dataset_id", ""),
                    title=r.get("title", ""),
                    publisher=r.get("publisher", ""),
                    rank=i+1,
                    score=r.get("llm_relevance_score", r.get("original_score", 0.0))
                )
                for i, r in enumerate(data.get("results", []))
            ]
        except Exception as e:
            print(f"   ⚠️  Error v08: {e}")
            return []

    def compare_results(self, v07: List[SearchResult], v08: List[SearchResult],
                        query: str, query_id: str) -> ComparisonMetrics:
        """Comparar resultados y calcular métricas."""
        v07_ids = {r.dataset_id for r in v07}
        v08_ids = {r.dataset_id for r in v08}

        overlap = list(v07_ids & v08_ids)
        v07_unique = list(v07_ids - v08_ids)
        v08_unique = list(v08_ids - v07_ids)

        rank_changes = []
        for item_id in overlap:
            v07_rank = next((r.rank for r in v07 if r.dataset_id == item_id), 10)
            v08_rank = next((r.rank for r in v08 if r.dataset_id == item_id), 10)
            rank_changes.append(v07_rank - v08_rank)

        avg_change = sum(rank_changes) / len(rank_changes) if rank_changes else 0

        return ComparisonMetrics(
            query=query,
            query_id=query_id,
            v07_results=v07,
            v08_results=v08,
            overlap=overlap,
            v07_unique=v07_unique,
            v08_unique=v08_unique,
            avg_score_v07=sum(r.score for r in v07) / len(v07) if v07 else 0,
            avg_score_v08=sum(r.score for r in v08) / len(v08) if v08 else 0,
            rerank_improvement=avg_change
        )

    def run_test(self, queries: List[Dict] = None, verbose: bool = True) -> Dict:
        """Ejecutar test completo."""
        queries = queries or TEST_QUERIES
        results = []

        if verbose:
            print("=" * 70)
            print("TEST COMPARATIVO: Sprint 07 vs Sprint 08")
            print("=" * 70)
            print(f"\nConfiguración:")
            print(f"  v07 (Baseline): {self.v07_url}")
            print(f"  v08 (LLM):      {self.v08_url}")
            print(f"  Queries:        {len(queries)}")

        for q in queries:
            if verbose:
                print(f"\n{'─' * 70}")
                print(f"Query [{q['id']}]: {q['query']}")
                print(f"  Categoría: {q.get('categoria', 'N/A')}")

            start = time.time()
            v07_results = self.search_v07(q['query'])
            v07_time = time.time() - start

            start = time.time()
            v08_results = self.search_v08(q['query'])
            v08_time = time.time() - start

            if verbose:
                print(f"  v07: {len(v07_results)} resultados en {v07_time:.2f}s")
                print(f"  v08: {len(v08_results)} resultados en {v08_time:.2f}s")

            comparison = self.compare_results(v07_results, v08_results, q['query'], q['id'])

            if verbose:
                print(f"\n  Métricas:")
                print(f"    Overlap: {len(comparison.overlap)}/{len(v07_results)} items")
                print(f"    v08 únicos: {len(comparison.v08_unique)}")
                print(f"    Mejora ranking promedio: {comparison.rerank_improvement:+.1f} posiciones")

                if comparison.v08_unique[:3]:
                    print(f"\n    Nuevos en v08:")
                    for did in comparison.v08_unique[:3]:
                        r = next((r for r in v08_results if r.dataset_id == did), None)
                        if r:
                            print(f"      #{r.rank}: {r.title[:50]}...")

            results.append(asdict(comparison))

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_queries": len(queries),
            "v07_url": self.v07_url,
            "v08_url": self.v08_url,
            "avg_overlap": sum(len(r['overlap']) for r in results) / len(results) if results else 0,
            "avg_v08_unique": sum(len(r['v08_unique']) for r in results) / len(results) if results else 0,
            "avg_rank_improvement": sum(r['rerank_improvement'] for r in results) / len(results) if results else 0,
            "results": results
        }

        if verbose:
            print(f"\n{'=' * 70}")
            print("RESUMEN")
            print(f"{'=' * 70}")
            print(f"  Overlap promedio:     {summary['avg_overlap']:.1f} items/query")
            print(f"  Nuevos en v08:        {summary['avg_v08_unique']:.1f} items/query")
            print(f"  Mejora de ranking:    {summary['avg_rank_improvement']:+.2f} posiciones")
            print(f"\nConclusión: {'✅ v08 mejora' if summary['avg_rank_improvement'] > 0.5 else '⚠️ Sin mejora significativa'}")

        return summary


def main():
    parser = argparse.ArgumentParser(description="Test comparativo v07 vs v08")
    parser.add_argument("--v07-url", default="http://localhost:8000", help="URL API v07")
    parser.add_argument("--v08-url", default="http://localhost:8000", help="URL API v08 (con /llm)")
    parser.add_argument("--output", "-o", help="Guardar resultados en JSON")
    parser.add_argument("--query", "-q", help="Test individual con query personalizada")
    args = parser.parse_args()

    tester = TestComparativo(v07_url=args.v07_url, v08_url=args.v08_url)

    if args.query:
        queries = [{"id": "CUSTOM", "query": args.query, "categoria": "custom"}]
        results = tester.run_test(queries)
    else:
        results = tester.run_test()

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Resultados guardados en: {args.output}")


if __name__ == "__main__":
    main()
