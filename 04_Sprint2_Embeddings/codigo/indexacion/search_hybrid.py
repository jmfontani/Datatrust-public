#!/usr/bin/env python3
"""
Motor de búsqueda híbrida (semántica + léxica + filtros facetados).

Uso:
  python search_hybrid.py "datos de tráfico en Madrid" --territorio "Comunidad de Madrid" --top-k 10
  python search_hybrid.py "educación primaria" --tema "educacion" --formato "CSV" --top-k 20
"""
import argparse
import json
import logging
import pickle
import time
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Rutas
BASE_DIR = Path(__file__).resolve().parent.parent.parent
INDICES_DIR = BASE_DIR / "04_Sprint2_Embeddings" / "datos" / "indices"
DATASETS_PATH = BASE_DIR / "03_Sprint1_Ingesta" / "datos" / "processed" / "datasets_clean.jsonl"
EMBEDDINGS_PATH = BASE_DIR / "04_Sprint2_Embeddings" / "datos" / "processed" / "embeddings.npy"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Revision fijada: sin ella se descarga la rama "main", que es un puntero movil
# y puede devolver pesos distintos bajo el mismo nombre (ver docs/PINNING-DEPENDENCIAS.md).
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"


class HybridSearcher:
    def __init__(self):
        logger.info("Inicializando buscador híbrido...")
        start = time.perf_counter()

        # Cargar modelo
        self.model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)

        # Cargar embeddings
        self.embeddings = np.load(EMBEDDINGS_PATH)
        logger.info(f"Embeddings cargados: {self.embeddings.shape}")

        # Cargar índices
        with open(INDICES_DIR / "id_position_map.json", "r") as f:
            self.id_to_pos = json.load(f)
        self.pos_to_id = {v: k for k, v in self.id_to_pos.items()}

        with open(INDICES_DIR / "index_tema.json", "r") as f:
            self.index_tema = json.load(f)

        with open(INDICES_DIR / "index_territorio.json", "r") as f:
            self.index_territorio = json.load(f)

        with open(INDICES_DIR / "index_formato.json", "r") as f:
            self.index_formato = json.load(f)

        with open(INDICES_DIR / "index_publisher.json", "r") as f:
            self.index_publisher = json.load(f)

        # Cargar BM25
        with open(INDICES_DIR / "bm25_index.pkl", "rb") as f:
            bm25_data = pickle.load(f)
            self.bm25 = bm25_data["bm25"]
            self.bm25_id_map = bm25_data["id_map"]

        # Cargar datasets en memoria (para mostrar resultados)
        self.datasets = {}
        with open(DATASETS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                ds = json.loads(line)
                self.datasets[ds["identifier"]] = ds

        logger.info(f"Buscador listo en {time.perf_counter() - start:.2f}s")

    def search_semantic(self, query: str, top_k: int = 100) -> list:
        """Búsqueda semántica por similitud de coseno."""
        # Generar embedding de la query
        query_embedding = self.model.encode([query], normalize_embeddings=True)[0]

        # Calcular similitud coseno (producto punto porque están normalizados)
        similarities = np.dot(self.embeddings, query_embedding)

        # Obtener top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [
            {
                "id": self.pos_to_id[int(idx)],
                "score_semantic": float(similarities[idx]),
                "position": int(idx),
            }
            for idx in top_indices
        ]

    def search_lexical(self, query: str, top_k: int = 100) -> list:
        """Búsqueda léxica con BM25."""
        import re

        tokenized_query = re.findall(r"\b\w+\b", query.lower())
        scores = self.bm25.get_scores(tokenized_query)

        top_indices = np.argsort(scores)[::-1][:top_k]

        return [
            {
                "id": self.bm25_id_map[idx],
                "score_lexical": float(scores[idx]),
                "position": idx,
            }
            for idx in top_indices
            if scores[idx] > 0
        ]

    def filter_by_facet(self, candidates: list, **filters) -> list:
        """Filtrar candidatos por facetas."""
        filtered = candidates

        if filters.get("territorio"):
            terr_ids = set(self.index_territorio.get(filters["territorio"], []))
            filtered = [c for c in filtered if c["id"] in terr_ids]

        if filters.get("tema"):
            tema_ids = set(self.index_tema.get(filters["tema"], []))
            filtered = [c for c in filtered if c["id"] in tema_ids]

        if filters.get("formato"):
            fmt_ids = set(self.index_formato.get(filters["formato"], []))
            filtered = [c for c in filtered if c["id"] in fmt_ids]

        if filters.get("publisher"):
            pub_ids = set(self.index_publisher.get(filters["publisher"], []))
            filtered = [c for c in filtered if c["id"] in pub_ids]

        return filtered

    def search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.7,
        lexical_weight: float = 0.3,
        **filters,
    ) -> list:
        """
        Búsqueda híbrida combinando semántica y léxica con filtros facetados.
        """
        start = time.perf_counter()

        # Búsqueda semántica
        semantic_results = self.search_semantic(query, top_k=top_k * 3)
        semantic_scores = {r["id"]: r["score_semantic"] for r in semantic_results}

        # Búsqueda léxica
        lexical_results = self.search_lexical(query, top_k=top_k * 3)
        lexical_scores = {r["id"]: r["score_lexical"] for r in lexical_results}

        # Combinar resultados
        all_ids = set(semantic_scores.keys()) | set(lexical_scores.keys())

        combined = []
        for ds_id in all_ids:
            s_score = semantic_scores.get(ds_id, 0)
            l_score = lexical_scores.get(ds_id, 0)

            # Normalizar scores (min-max por separado)
            max_sem = max(semantic_scores.values()) if semantic_scores else 1
            max_lex = max(lexical_scores.values()) if lexical_scores else 1

            s_norm = s_score / max_sem if max_sem > 0 else 0
            l_norm = l_score / max_lex if max_lex > 0 else 0

            combined_score = semantic_weight * s_norm + lexical_weight * l_norm

            combined.append({
                "id": ds_id,
                "score": combined_score,
                "score_semantic": s_score,
                "score_lexical": l_score,
            })

        # Ordenar por score combinado
        combined.sort(key=lambda x: x["score"], reverse=True)

        # Aplicar filtros facetados
        filtered = self.filter_by_facet(combined, **filters)

        # Retornar top-k con datos completos
        results = []
        for item in filtered[:top_k]:
            ds = self.datasets.get(item["id"], {})
            results.append({
                "id": item["id"],
                "score": round(item["score"], 4),
                "score_semantic": round(item["score_semantic"], 4),
                "score_lexical": round(item["score_lexical"], 4),
                "title": ds.get("title_es", ds.get("title", "Sin título")),
                "description": ds.get("description_es", "")[:200] + "..." if len(ds.get("description_es", "")) > 200 else ds.get("description_es", ""),
                "territorio": ds.get("spatial_name", []),
                "tema": ds.get("theme_labels", []),
                "formato": ds.get("format_labels", []),
                "publisher": ds.get("publisher_name", "Desconocido"),
                "url": ds.get("source_url", ""),
            })

        elapsed = time.perf_counter() - start
        logger.info(f"Búsqueda completada en {elapsed:.3f}s")

        return results


def main():
    parser = argparse.ArgumentParser(description="Buscador híbrido de datasets")
    parser.add_argument("query", help="Consulta de búsqueda")
    parser.add_argument("--top-k", type=int, default=10, help="Número de resultados")
    parser.add_argument("--territorio", help="Filtrar por territorio")
    parser.add_argument("--tema", help="Filtrar por tema")
    parser.add_argument("--formato", help="Filtrar por formato")
    parser.add_argument("--publisher", help="Filtrar por publisher")
    parser.add_argument(
        "--semantic-weight", type=float, default=0.7, help="Peso de búsqueda semántica"
    )
    parser.add_argument(
        "--lexical-weight", type=float, default=0.3, help="Peso de búsqueda léxica"
    )

    args = parser.parse_args()

    # Inicializar buscador
    searcher = HybridSearcher()

    # Ejecutar búsqueda
    results = searcher.search(
        query=args.query,
        top_k=args.top_k,
        semantic_weight=args.semantic_weight,
        lexical_weight=args.lexical_weight,
        territorio=args.territorio,
        tema=args.tema,
        formato=args.formato,
        publisher=args.publisher,
    )

    # Mostrar resultados
    print(f"\n{'='*80}")
    print(f"🔍 Query: '{args.query}'")
    if args.territorio:
        print(f"   Territorio: {args.territorio}")
    if args.tema:
        print(f"   Tema: {args.tema}")
    print(f"{'='*80}\n")

    for i, r in enumerate(results, 1):
        print(f"{i}. [{r['score']:.3f}] {r['title']}")
        print(f"   🏛️  {r['publisher']} | 🌍 {', '.join(r['territorio'][:3])}")
        print(f"   🏷️  {', '.join(r['tema'][:3])} | 📄 {', '.join(r['formato'][:3])}")
        print(f"   {r['description'][:150]}...")
        print(f"   🔗 {r['url']}")
        print()

    print(f"{'='*80}")
    print(f"Total resultados: {len(results)}")


if __name__ == "__main__":
    main()
