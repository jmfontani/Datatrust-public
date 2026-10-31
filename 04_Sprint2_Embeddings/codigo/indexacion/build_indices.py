#!/usr/bin/env python3
"""
Construye índices de búsqueda para los datasets.

Input:  03_Sprint1_Ingesta/datos/processed/datasets_clean.jsonl
        04_Sprint2_Embeddings/datos/processed/embeddings.npy
Output: 04_Sprint2_Embeddings/datos/indices/

Índices creados:
  - id_position_map.json:    dataset_id → índice en embeddings
  - index_tema.json:         tema → [dataset_ids]
  - index_territorio.json:   territorio → [dataset_ids]
  - index_formato.json:      formato → [dataset_ids]
  - index_publisher.json:    publisher → [dataset_ids]
  - bm25_index.pkl:          Índice BM25 para búsqueda léxica
"""
import json
import logging
import pickle
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Rutas
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATASETS_PATH = BASE_DIR / "03_Sprint1_Ingesta" / "datos" / "processed" / "datasets_clean.jsonl"
EMBEDDINGS_PATH = BASE_DIR / "04_Sprint2_Embeddings" / "datos" / "processed" / "embeddings.npy"
OUTPUT_DIR = BASE_DIR / "04_Sprint2_Embeddings" / "datos" / "indices"


def build_indices():
    start = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Cargar datasets
    logger.info(f"Cargando datasets desde {DATASETS_PATH}...")
    datasets = []
    with open(DATASETS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            datasets.append(json.loads(line))
    logger.info(f"Cargados {len(datasets)} datasets")

    # 2. Verificar embeddings
    logger.info(f"Cargando embeddings desde {EMBEDDINGS_PATH}...")
    embeddings = np.load(EMBEDDINGS_PATH)
    logger.info(f"Embeddings shape: {embeddings.shape}")

    if len(datasets) != embeddings.shape[0]:
        logger.error(
            f"MISMATCH: {len(datasets)} datasets vs {embeddings.shape[0]} embeddings"
        )
        raise ValueError("Número de datasets no coincide con embeddings")

    # 3. Crear mapa ID → posición
    logger.info("Creando mapa ID → posición...")
    id_position_map = {}
    for idx, ds in enumerate(datasets):
        id_position_map[ds["identifier"]] = idx

    map_path = OUTPUT_DIR / "id_position_map.json"
    with open(map_path, "w") as f:
        json.dump(id_position_map, f)
    logger.info(f"✓ ID map guardado: {map_path} ({len(id_position_map)} entradas)")

    # 4. Crear índices inversos
    logger.info("Creando índices inversos...")

    indices = {
        "tema": defaultdict(list),
        "territorio": defaultdict(list),
        "formato": defaultdict(list),
        "publisher": defaultdict(list),
    }

    for ds in datasets:
        ds_id = ds["identifier"]

        # Temas (lista)
        for tema in ds.get("theme_labels", []):
            indices["tema"][tema].append(ds_id)

        # Territorios (lista o string)
        spatial = ds.get("spatial_name", [])
        if isinstance(spatial, str):
            spatial = [spatial]
        for terr in spatial:
            indices["territorio"][terr].append(ds_id)

        # Formatos (lista)
        for fmt in ds.get("format_labels", []):
            indices["formato"][fmt].append(ds_id)

        # Publisher (string)
        pub = ds.get("publisher_name", ds.get("publisher", "desconocido"))
        indices["publisher"][pub].append(ds_id)

    # Guardar índices inversos
    for name, idx in indices.items():
        # Convertir defaultdict a dict normal para JSON
        idx_dict = dict(idx)
        out_path = OUTPUT_DIR / f"index_{name}.json"
        with open(out_path, "w") as f:
            json.dump(idx_dict, f)
        logger.info(
            f"✓ Índice {name}: {len(idx_dict)} claves, "
            f"{sum(len(v) for v in idx_dict.values())} referencias"
        )

    # 5. Crear índice BM25 para búsqueda léxica
    logger.info("Creando índice BM25...")
    tokenized_corpus = []
    for ds in datasets:
        # Tokenizar texto de búsqueda (título + descripción + keywords)
        text = ds.get("embedding_text", "")
        # Tokenización simple: minúsculas y split por espacios/puntuación
        import re

        tokens = re.findall(r"\b\w+\b", text.lower())
        tokenized_corpus.append(tokens)

    bm25 = BM25Okapi(tokenized_corpus)

    bm25_path = OUTPUT_DIR / "bm25_index.pkl"
    with open(bm25_path, "wb") as f:
        pickle.dump(
            {
                "bm25": bm25,
                "id_map": [ds["identifier"] for ds in datasets],
                "corpus_size": len(tokenized_corpus),
            },
            f,
        )
    logger.info(f"✓ BM25 index guardado: {bm25_path}")

    # 6. Guardar metadatos
    meta = {
        "num_datasets": len(datasets),
        "embedding_shape": list(embeddings.shape),
        "indices": {
            name: {
                "num_keys": len(idx),
                "total_refs": sum(len(v) for v in idx.values()),
            }
            for name, idx in indices.items()
        },
        "bm25": {
            "corpus_size": len(tokenized_corpus),
            "avg_doc_len": bm25.avgdl,
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(time.perf_counter() - start, 2),
    }

    meta_path = OUTPUT_DIR / "index_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info(f"✓ Metadatos: {meta_path}")

    elapsed = time.perf_counter() - start
    logger.info(
        f"\n✅ Índices creados en {elapsed:.1f}s"
        f"\n   Datasets indexados: {len(datasets)}"
        f"\n   Embeddings: {embeddings.shape}"
        f"\n   Output: {OUTPUT_DIR}"
    )

    return meta


if __name__ == "__main__":
    build_indices()
