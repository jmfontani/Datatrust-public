#!/usr/bin/env python3
"""
Genera embeddings para todos los datasets limpios usando Sentence Transformers.

Input:  datos/processed/datasets_clean.jsonl
Output: datos/processed/embeddings.npy

Usa el modelo configurado: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
"""
import json
import logging
import os
import time
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Revision fijada: sin ella se descarga la rama "main", que es un puntero movil
# y puede devolver pesos distintos bajo el mismo nombre (ver docs/PINNING-DEPENDENCIAS.md).
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
EMBEDDING_DIM = 384

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "datos" / "processed"
INPUT_PATH = PROCESSED_DIR / "datasets_clean.jsonl"
OUTPUT_PATH = PROCESSED_DIR / "embeddings.npy"


def main():
    start = time.perf_counter()

    # 1. Cargar datasets limpios
    logger.info(f"Cargando {INPUT_PATH}...")
    texts = []
    ids = []
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            ds = json.loads(line)
            ids.append(ds["identifier"])
            texts.append(ds.get("embedding_text", ""))

    logger.info(f"Cargados {len(texts)} datasets")
    logger.info(f"Texto medio: {sum(len(t) for t in texts) / len(texts):.0f} chars")

    # 2. Cargar modelo
    logger.info(f"Cargando modelo {MODEL_NAME}...")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)
    logger.info(f"Modelo cargado. Dimensión: {model.get_sentence_embedding_dimension()}")

    # 3. Generar embeddings en batches
    logger.info("Generando embeddings...")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
        batch_size=32,
    )

    elapsed = time.perf_counter() - start
    logger.info(f"Embeddings generados: {embeddings.shape} en {elapsed:.1f}s ({len(texts)/elapsed:.0f} docs/s)")

    # 4. Guardar
    np.save(OUTPUT_PATH, embeddings)
    size_mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
    logger.info(f"✓ Guardado en {OUTPUT_PATH} ({size_mb:.1f} MB)")

    # 5. Guardar metadatos
    meta = {
        "model": MODEL_NAME,
        "dimension": EMBEDDING_DIM,
        "num_datasets": len(ids),
        "output_shape": list(embeddings.shape),
        "elapsed_seconds": round(elapsed, 1),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_file": str(INPUT_PATH),
    }
    meta_path = PROCESSED_DIR / "embeddings_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info(f"✓ Metadatos: {meta_path}")


if __name__ == "__main__":
    main()
