#!/usr/bin/env python3
"""
Test Comparativo Extendido: Sprint 07 vs Sprint 08
20 queries para validación estadística de mejora de calidad

Métricas clave:
- Overlap: % de resultados en común
- Ranking improvement: cambio promedio de posición para items comunes
- Nuevos relevantes: items que aparecen solo en v08 y son relevantes
"""

import requests
import json
import time
import argparse
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime


# 20 Queries de prueba representativas
TEST_QUERIES = [
    # SINONIMIA (4 queries)
    {"id": "S1", "query": "paro juvenil desempleo jóvenes", "categoria": "sinonimia", "expectativa": "Tasa de desempleo juvenil"},
    {"id": "S2", "query": "renta ingresos salarios", "categoria": "sinonimia", "expectativa": "Datos económicos renta"},
    {"id": "S3", "query": "contaminación calidad aire", "categoria": "sinonimia", "expectativa": "Datos medioambientales"},
    {"id": "S4", "query": "población habitantes demografía", "categoria": "sinonimia", "expectativa": "Censos demográficos"},

    # CONCEPTUALES (4 queries)
    {"id": "C1", "query": "vulnerabilidad económica juventud", "categoria": "conceptual", "expectativa": "Riesgo pobreza juvenil"},
    {"id": "C2", "query": "sostenibilidad urbana", "categoria": "conceptual", "expectativa": "Movilidad/energía sostenible"},
    {"id": "C3", "query": "brecha digital educación", "categoria": "conceptual", "expectativa": "Datos tecnología educativa"},
    {"id": "C4", "query": "equidad territorial servicios", "categoria": "conceptual", "expectativa": "Acceso servicios básicos"},

    # ESPECÍFICAS TERRITORIALES (4 queries)
    {"id": "T1", "query": "presupuestos municipales Arganda del Rey", "categoria": "territorial", "expectativa": "Datos Ayuntamiento Arganda"},
    {"id": "T2", "query": "turismo Canarias 2023", "categoria": "territorial", "expectativa": "Estadísticas turísticas Canarias"},
    {"id": "T3", "query": "tráfico Madrid centro", "categoria": "territorial", "expectativa": "Datos movilidad Madrid capital"},
    {"id": "T4", "query": "precio vivienda Barcelona", "categoria": "territorial", "expectativa": "Precios alquiler/compra Barcelona"},

    # TEMPORALES (4 queries)
    {"id": "TM1", "query": "calidad del aire Madrid 2023", "categoria": "temporal", "expectativa": "Datos recientes Madrid"},
    {"id": "TM2", "query": "emisiones CO2 2022 2023", "categoria": "temporal", "expectativa": "Datos recientes emisiones"},
    {"id": "TM3", "query": "empleo último trimestre", "categoria": "temporal", "expectativa": "EPA reciente"},
    {"id": "TM4", "query": "energía renovable 2023 2024", "categoria": "temporal", "expectativa": "Datos recientes renovables"},

    # FACETADAS / MULTITÉRMINO (2 queries)
    {"id": "F1", "query": "datasets medio ambiente Canarias", "categoria": "facetada", "expectativa": "Filtrado tema + territorio"},
    {"id": "F2", "query": "transporte público Barcelona metro autobús", "categoria": "facetada", "expectativa": "Múltiples formatos transporte"},

    # CALIDAD METADATOS (2 queries)
    {"id": "M1", "query": "padrón municipal completo", "categoria": "metadatos", "expectativa": "Datasets con buenos metadatos"},
    {"id": "M2", "query": "catastro edificios", "categoria": "metadatos", "expectativa": "Datos catastrales completos"},
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
    categoria: str
    v07_results: List[SearchResult]
    v08_results: List[SearchResult]
    overlap: List[str]
    v07_unique: List[str]
    v08_unique: List[str]
    avg_score_v07: float
    avg_score_v08: float
    rank_improvements: List[float]  # Cambios específicos por item
    rerank_changes: int  # Cuántos items cambiaron de posición


class TestComparativo:
    """Ejecuta tests comparativos entre v07 y v08."""

    def __init__(self, v07_url: str = "http://localhost:8000", v08_url: str = "http://localhost:8000"):
        self.v07_url = v07_url
        self.v08_url = v08_url
        self.results = []

    def search_v07(self, query: str, limit: int = 10) -> tuple[List[SearchResult], float]:
        """Buscar contra API v07 (baseline)."""
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
        """Buscar contra API v08 (con LLM re-ranking)."""
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

            metadata = data.get("metadata", {})
            return results, elapsed, metadata
        except Exception as e:
            print(f"   ⚠️  Error v08: {e}")
            return [], 0.0, {}

    def compare_results(self, v07: List[SearchResult], v08: List[SearchResult],
                        query: str, query_id: str, categoria: str) -> ComparisonMetrics:
        """Comparar resultados y calcular métricas."""
        v07_ids = {r.dataset_id for r in v07}
        v08_ids = {r.dataset_id for r in v08}

        overlap = list(v07_ids & v08_ids)
        v07_unique = list(v07_ids - v08_ids)
        v08_unique = list(v08_ids - v07_ids)

        # Calcular cambios de ranking para items en overlap
        rank_changes = []
        rerank_changes = 0
        for item_id in overlap:
            v07_rank = next((r.rank for r in v07 if r.dataset_id == item_id), 10)
            v08_rank = next((r.rank for r in v08 if r.dataset_id == item_id), 10)
            change = v07_rank - v08_rank  # Positivo = mejoró (subió)
            rank_changes.append(change)
            if change != 0:
                rerank_changes += 1

        return ComparisonMetrics(
            query=query,
            query_id=query_id,
            categoria=categoria,
            v07_results=v07,
            v08_results=v08,
            overlap=overlap,
            v07_unique=v07_unique,
            v08_unique=v08_unique,
            avg_score_v07=sum(r.score for r in v07) / len(v07) if v07 else 0,
            avg_score_v08=sum(r.score for r in v08) / len(v08) if v08 else 0,
            rank_improvements=rank_changes,
            rerank_changes=rerank_changes
        )

    def run_test(self, queries: List[Dict] = None, verbose: bool = True) -> Dict:
        """Ejecutar test completo."""
        queries = queries or TEST_QUERIES
        results = []

        if verbose:
            print("=" * 80)
            print("TEST COMPARATIVO EXTENDIDO: Sprint 07 vs Sprint 08")
            print("=" * 80)
            print(f"\nConfiguración:")
            print(f"  v07 (Baseline): {self.v07_url}")
            print(f"  v08 (LLM):      {self.v08_url}")
            print(f"  Queries:        {len(queries)}")
            print(f"  Est. tiempo:    ~{len(queries) * 1.5:.0f} minutos")

        for i, q in enumerate(queries, 1):
            if verbose:
                print(f"\n{'─' * 80}")
                print(f"[{i}/{len(queries)}] Query [{q['id']}]: {q['query']}")
                print(f"  Categoría: {q.get('categoria', 'N/A')} | Expectativa: {q.get('expectativa', 'N/A')}")

            v07_results, v07_time = self.search_v07(q['query'])
            v08_results, v08_time, v08_meta = self.search_v08(q['query'])

            if verbose:
                print(f"  v07: {len(v07_results)} resultados en {v07_time:.2f}s")
                print(f"  v08: {len(v08_results)} resultados en {v08_time:.2f}s (LLM: {v08_meta.get('model', 'N/A')})")

            comparison = self.compare_results(v07_results, v08_results, q['query'], q['id'], q['categoria'])

            if verbose:
                overlap_pct = len(comparison.overlap) / len(v07_results) * 100 if v07_results else 0
                avg_change = sum(comparison.rank_improvements) / len(comparison.rank_improvements) if comparison.rank_improvements else 0
                print(f"\n  Métricas:")
                print(f"    Overlap: {len(comparison.overlap)}/{len(v07_results)} ({overlap_pct:.0f}%)")
                print(f"    Items reordenados: {comparison.rerank_changes}")
                print(f"    Mejora ranking promedio: {avg_change:+.1f} posiciones")

                if comparison.v08_unique[:2]:
                    print(f"    Nuevos en v08: {len(comparison.v08_unique)} items")

            results.append(asdict(comparison))

        # Calcular métricas agregadas por categoría
        categorias = {}
        for r in results:
            cat = r['categoria']
            if cat not in categorias:
                categorias[cat] = {'overlap': [], 'improvements': [], 'changes': []}
            categorias[cat]['overlap'].append(len(r['overlap']))
            categorias[cat]['improvements'].extend(r['rank_improvements'])
            categorias[cat]['changes'].append(r['rerank_changes'])

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_queries": len(queries),
            "v07_url": self.v07_url,
            "v08_url": self.v08_url,
            "avg_overlap": sum(len(r['overlap']) for r in results) / len(results) if results else 0,
            "avg_v08_unique": sum(len(r['v08_unique']) for r in results) / len(results) if results else 0,
            "avg_rank_improvement": sum(sum(r['rank_improvements']) / len(r['rank_improvements']) if r['rank_improvements'] else 0 for r in results) / len(results) if results else 0,
            "total_items_reordered": sum(r['rerank_changes'] for r in results),
            "by_category": {
                cat: {
                    "avg_overlap": sum(data['overlap']) / len(data['overlap']),
                    "avg_improvement": sum(data['improvements']) / len(data['improvements']) if data['improvements'] else 0,
                    "total_changes": sum(data['changes'])
                }
                for cat, data in categorias.items()
            },
            "results": results
        }

        if verbose:
            print(f"\n{'=' * 80}")
            print("RESUMEN GLOBAL")
            print(f"{'=' * 80}")
            print(f"  Overlap promedio:        {summary['avg_overlap']:.1f}/10 ({summary['avg_overlap']/10*100:.0f}%)")
            print(f"  Nuevos en v08:           {summary['avg_v08_unique']:.1f}/query")
            print(f"  Mejora ranking promedio: {summary['avg_rank_improvement']:+.2f} posiciones")
            print(f"  Total items reordenados: {summary['total_items_reordered']}")

            print(f"\n{'=' * 80}")
            print("POR CATEGORÍA")
            print(f"{'=' * 80}")
            for cat, data in summary['by_category'].items():
                print(f"  {cat:15s}: Overlap {data['avg_overlap']:4.1f} | Mejora {data['avg_improvement']:+5.2f} | Cambios {data['total_changes']:3d}")

            # Interpretación
            print(f"\n{'=' * 80}")
            print("CONCLUSIÓN")
            print(f"{'=' * 80}")
            if summary['avg_rank_improvement'] > 0.3:
                print("✅ v08 MEJORA SIGNIFICATIVAMENTE el ranking")
            elif summary['avg_rank_improvement'] > 0.1:
                print("🟡 v08 muestra MEJORAS MODERADAS en ranking")
            elif summary['avg_rank_improvement'] < -0.1:
                print("🔴 v08 EMPEORA el ranking - revisar configuración")
            else:
                print("⚪ v08 mantiene el ranking sin cambios significativos")

        return summary


def main():
    parser = argparse.ArgumentParser(description="Test comparativo extendido v07 vs v08")
    parser.add_argument("--v07-url", default="http://localhost:8000", help="URL API v07")
    parser.add_argument("--v08-url", default="http://localhost:8000", help="URL API v08")
    parser.add_argument("--output", "-o", default="/tmp/test_comparativo_20_results.json", help="Guardar resultados")
    parser.add_argument("--subset", type=int, help="Usar solo N primeras queries para test rápido")
    args = parser.parse_args()

    tester = TestComparativo(v07_url=args.v07_url, v08_url=args.v08_url)

    queries = TEST_QUERIES[:args.subset] if args.subset else TEST_QUERIES
    results = tester.run_test(queries)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Resultados guardados en: {args.output}")


if __name__ == "__main__":
    main()
