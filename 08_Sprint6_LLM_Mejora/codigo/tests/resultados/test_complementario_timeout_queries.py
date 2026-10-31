#!/usr/bin/env python3
"""
Test Complementario: Queries que tuvieron timeout en el test principal
Ejecuta las 6 queries que fallaron para obtener métricas completas.
"""

import requests
import json
import time
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime


# Queries que tuvieron timeout (con expectativas documentadas)
TIMEOUT_QUERIES = [
    {"id": "T1", "query": "presupuestos municipales Arganda del Rey", "categoria": "territorial",
     "expectativa": "Datos Ayuntamiento Arganda", "timeout_original": 120.13},
    {"id": "T2", "query": "turismo Canarias 2023", "categoria": "territorial",
     "expectativa": "Estadísticas turísticas Canarias", "timeout_original": 120.13},
    {"id": "T3", "query": "tráfico Madrid centro", "categoria": "territorial",
     "expectativa": "Datos movilidad Madrid capital", "timeout_original": 120.13},
    {"id": "T4", "query": "precio vivienda Barcelona", "categoria": "territorial",
     "expectativa": "Precios alquiler/compra Barcelona", "timeout_original": 120.06},
    {"id": "TM1", "query": "calidad del aire Madrid 2023", "categoria": "temporal",
     "expectativa": "Datos recientes Madrid", "timeout_original": 120.10},
    {"id": "C1", "query": "vulnerabilidad económica juventud", "categoria": "conceptual",
     "expectativa": "Riesgo pobreza juvenil", "timeout_original": 120.08},
]


@dataclass
class SearchResult:
    dataset_id: str
    title: str
    publisher: str
    rank: int
    score: float


@dataclass
class ComparisonMetrics:
    query: str
    query_id: str
    categoria: str
    v07_time: float
    v08_time: float
    v07_results: List[SearchResult]
    v08_results: List[SearchResult]
    overlap: List[str]
    v07_unique: List[str]
    v08_unique: List[str]
    rank_improvements: List[float]
    rerank_changes: int
    metadata_v08: Dict


class TestComplementario:
    def __init__(self, v07_url: str = "http://localhost:8000", v08_url: str = "http://localhost:8000"):
        self.v07_url = v07_url
        self.v08_url = v08_url

    def search_v07(self, query: str, limit: int = 10) -> tuple[List[SearchResult], float]:
        try:
            start = time.time()
            response = requests.post(
                f"{self.v07_url}/search",
                json={"query": query, "top_k": limit},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            elapsed = time.time() - start

            return [
                SearchResult(
                    dataset_id=r.get("id") or r.get("dataset_id", ""),
                    title=r.get("title", ""),
                    publisher=r.get("publisher", ""),
                    rank=i+1,
                    score=r.get("score_final", 0.0)
                )
                for i, r in enumerate(data.get("results", []))
            ], elapsed
        except Exception as e:
            print(f"   ⚠️  Error v07: {e}")
            return [], 0.0

    def search_v08(self, query: str, limit: int = 10) -> tuple[List[SearchResult], float, Dict]:
        try:
            start = time.time()
            response = requests.post(
                f"{self.v08_url}/llm/search/rerank",
                json={
                    "query": query,
                    "limit": limit,
                    "rerank_top_n": 15,
                    "use_llm": True
                },
                timeout=180
            )
            response.raise_for_status()
            data = response.json()
            elapsed = time.time() - start

            results = [
                SearchResult(
                    dataset_id=r.get("dataset_id", ""),
                    title=r.get("title", ""),
                    publisher=r.get("publisher", ""),
                    rank=i+1,
                    score=r.get("llm_relevance_score", r.get("original_score", 0.0))
                )
                for i, r in enumerate(data.get("results", []))
            ]

            return results, elapsed, data.get("metadata", {})
        except Exception as e:
            print(f"   ⚠️  Error v08: {e}")
            return [], 0.0, {}

    def compare_results(self, v07: List[SearchResult], v08: List[SearchResult],
                        v07_time: float, v08_time: float, metadata: Dict,
                        query: str, query_id: str, categoria: str) -> ComparisonMetrics:
        v07_ids = {r.dataset_id for r in v07}
        v08_ids = {r.dataset_id for r in v08}

        overlap = list(v07_ids & v08_ids)
        v07_unique = list(v07_ids - v08_ids)
        v08_unique = list(v08_ids - v07_ids)

        rank_changes = []
        rerank_changes = 0
        for item_id in overlap:
            v07_rank = next((r.rank for r in v07 if r.dataset_id == item_id), 10)
            v08_rank = next((r.rank for r in v08 if r.dataset_id == item_id), 10)
            change = v07_rank - v08_rank
            rank_changes.append(change)
            if change != 0:
                rerank_changes += 1

        return ComparisonMetrics(
            query=query,
            query_id=query_id,
            categoria=categoria,
            v07_time=v07_time,
            v08_time=v08_time,
            v07_results=v07,
            v08_results=v08,
            overlap=overlap,
            v07_unique=v07_unique,
            v08_unique=v08_unique,
            rank_improvements=rank_changes,
            rerank_changes=rerank_changes,
            metadata_v08=metadata
        )

    def run_test(self) -> Dict:
        print("=" * 80)
        print("TEST COMPLEMENTARIO: Queries que tuvieron timeout")
        print("=" * 80)
        print("\nEstas 6 queries fallaron en el test principal (timeout > 120s)")
        print("Este test complementario obtiene las métricas faltantes.\n")

        results = []
        total_time_estimate = sum(q.get('timeout_original', 120) for q in TIMEOUT_QUERIES) / 60
        print(f"Tiempo estimado: ~{total_time_estimate:.0f} minutos\n")

        for i, q in enumerate(TIMEOUT_QUERIES, 1):
            print(f"{'─' * 80}")
            print(f"[{i}/6] Query [{q['id']}]: {q['query']}")
            print(f"  Categoría: {q['categoria']} | Timeout original: {q.get('timeout_original', 'N/A')}s")

            v07_results, v07_time = self.search_v07(q['query'])
            v08_results, v08_time, v08_meta = self.search_v08(q['query'])

            print(f"\n  Resultados:")
            print(f"    v07: {len(v07_results)} items en {v07_time:.2f}s")
            print(f"    v08: {len(v08_results)} items en {v08_time:.2f}s (modelo: {v08_meta.get('model', 'N/A')})")

            comparison = self.compare_results(
                v07_results, v08_results, v07_time, v08_time, v08_meta,
                q['query'], q['id'], q['categoria']
            )

            overlap_pct = len(comparison.overlap) / len(v07_results) * 100 if v07_results else 0
            avg_change = sum(comparison.rank_improvements) / len(comparison.rank_improvements) if comparison.rank_improvements else 0

            print(f"\n  Métricas:")
            print(f"    Overlap: {len(comparison.overlap)}/{len(v07_results)} ({overlap_pct:.0f}%)")
            print(f"    Items reordenados: {comparison.rerank_changes}")
            print(f"    Mejora ranking: {avg_change:+.2f} posiciones")

            if v08_time < 120:
                print(f"    ✅ Mejoró tiempo: {q.get('timeout_original', 120):.0f}s → {v08_time:.1f}s")
            else:
                print(f"    ⚠️  Sigue lento: {v08_time:.1f}s")

            results.append(asdict(comparison))

        # Calcular métricas agregadas
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_queries": len(TIMEOUT_QUERIES),
            "avg_overlap": sum(len(r['overlap']) for r in results) / len(results),
            "avg_v08_unique": sum(len(r['v08_unique']) for r in results) / len(results),
            "avg_rank_improvement": sum(sum(r['rank_improvements']) / len(r['rank_improvements']) if r['rank_improvements'] else 0 for r in results) / len(results),
            "total_items_reordered": sum(r['rerank_changes'] for r in results),
            "avg_time_v07": sum(r['v07_time'] for r in results) / len(results),
            "avg_time_v08": sum(r['v08_time'] for r in results) / len(results),
            "by_category": {},
            "results": results
        }

        # Agrupar por categoría
        for r in results:
            cat = r['categoria']
            if cat not in summary['by_category']:
                summary['by_category'][cat] = {'overlap': [], 'improvements': [], 'changes': [], 'count': 0}
            summary['by_category'][cat]['overlap'].append(len(r['overlap']))
            summary['by_category'][cat]['improvements'].extend(r['rank_improvements'])
            summary['by_category'][cat]['changes'].append(r['rerank_changes'])
            summary['by_category'][cat]['count'] += 1

        # Calcular promedios por categoría
        for cat, data in summary['by_category'].items():
            data['avg_overlap'] = sum(data['overlap']) / len(data['overlap'])
            data['avg_improvement'] = sum(data['improvements']) / len(data['improvements']) if data['improvements'] else 0
            data['total_changes'] = sum(data['changes'])

        print(f"\n{'=' * 80}")
        print("RESUMEN DEL TEST COMPLEMENTARIO")
        print(f"{'=' * 80}")
        print(f"  Queries evaluadas: {summary['total_queries']}")
        print(f"  Overlap promedio: {summary['avg_overlap']:.1f}/10")
        print(f"  Mejora ranking: {summary['avg_rank_improvement']:+.2f} posiciones")
        print(f"  Items reordenados: {summary['total_items_reordered']}")
        print(f"  Tiempo promedio v07: {summary['avg_time_v07']:.2f}s")
        print(f"  Tiempo promedio v08: {summary['avg_time_v08']:.1f}s")
        print(f"\n  Por categoría:")
        for cat, data in summary['by_category'].items():
            print(f"    {cat:12s}: Overlap {data['avg_overlap']:.1f} | Mejora {data['avg_improvement']:+.2f} | Cambios {data['total_changes']}")

        # Comparación con test original
        print(f"\n{'=' * 80}")
        print("COMPARACIÓN CON TEST ORIGINAL")
        print(f"{'=' * 80}")
        print("Test original vs Test complementario (estas 6 queries):")
        print(f"  Territorial: Mejora 0.00 → {summary['by_category'].get('territorial', {}).get('avg_improvement', 0):+.2f}")
        print(f"  Temporal:    Mejora -0.12 → {summary['by_category'].get('temporal', {}).get('avg_improvement', 0):+.2f}")
        print(f"  Conceptual:  Mejora +0.11 → {summary['by_category'].get('conceptual', {}).get('avg_improvement', 0):+.2f}")

        return summary


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", default="/tmp/test_complementario_timeout_results.json")
    args = parser.parse_args()

    tester = TestComplementario()
    results = tester.run_test()

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Resultados guardados en: {args.output}")


if __name__ == "__main__":
    main()
