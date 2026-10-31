#!/usr/bin/env python3
"""
Script de ingesta V2 - CON lógica anti-duplicados
Re-ingesta desde cero, descarta datasets ya vistos por identifier.

API: https://datos.gob.es/apidata/catalog/dataset
"""

import argparse
import json
import logging
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlencode

# ── Configuración ───────────────────────────────────────────────────────────

API_BASE_URL = "https://datos.gob.es/apidata/catalog/dataset.json"
API_TIMEOUT = 30
RETRIES = 3
BACKOFF = 1.0
RATE_LIMIT_DELAY = 0.5

STATE_FILE = ".ingest_state_v2.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def http_get_json(url: str, retries: int = RETRIES) -> Optional[Dict]:
    """GET HTTP con retry."""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "PFM-Ingesta/2.0"},
            )
            with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = BACKOFF * (2 ** attempt)
                logger.warning(f"HTTP {e.code}, reintentando en {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"HTTP Error {e.code}: {e.reason}")
                return None
        except Exception as e:
            if attempt < retries:
                wait = BACKOFF * (2 ** attempt)
                logger.warning(f"Error {e}, reintentando en {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"Error en request: {e}")
                return None
    return None


def fetch_page(page: int = 0, page_size: int = 100) -> Dict[str, Any]:
    """Obtiene una página de datasets."""
    params = {"_page": page, "_pageSize": page_size}
    url = f"{API_BASE_URL}?{urlencode(params)}"
    data = http_get_json(url)
    if data is None:
        return {"items": [], "has_next": False}
    result = data.get("result", {})
    items = result.get("items", [])
    has_next = "next" in result
    return {"items": items, "has_next": has_next}


# ── Funciones de extracción (copiadas de v1) ────────────────────────────────

def extract_multilingual_text(field_data: Any, lang: str = "es") -> str:
    if isinstance(field_data, list):
        texts = []
        for item in field_data:
            if isinstance(item, dict):
                item_lang = item.get("_lang", "es")
                if item_lang == lang or lang is None:
                    texts.append(item.get("_value", ""))
        return " ".join(filter(None, texts))
    elif isinstance(field_data, dict):
        return field_data.get("_value", "") if field_data.get("_lang") == lang else ""
    elif isinstance(field_data, str):
        return field_data
    return ""


def extract_all_text(field_data: Any) -> str:
    if isinstance(field_data, list):
        texts = [item.get("_value", "") for item in field_data if isinstance(item, dict)]
        return " ".join(filter(None, texts))
    elif isinstance(field_data, str):
        return field_data
    return ""


def extract_uri_last_segment(uri: Any) -> str:
    if not uri:
        return ""
    if isinstance(uri, dict):
        uri = uri.get("_about", uri.get("value", ""))
    uri = str(uri)
    return uri.rstrip("/").split("/")[-1].replace("-", " ")


def extract_spatial_info(spatial_data: Any) -> Dict[str, str]:
    if isinstance(spatial_data, list):
        spatial_data = spatial_data[0] if spatial_data else ""
    if isinstance(spatial_data, dict):
        uri = spatial_data.get("_about", "")
    else:
        uri = str(spatial_data) if spatial_data else ""
    name = extract_uri_last_segment(uri)
    level = "desconocido"
    if "/Pais/" in uri or "/pais/" in uri.lower():
        level = "pais"
    elif "/Autonomia/" in uri or "/autonomia/" in uri.lower():
        level = "autonomia"
    elif "/Provincia/" in uri or "/provincia/" in uri.lower():
        level = "provincia"
    elif "/Municipio/" in uri or "/municipio/" in uri.lower():
        level = "municipio"
    return {"uri": uri, "name": name, "level": level}


def extract_themes(theme_data: Any) -> List[str]:
    themes = []
    if isinstance(theme_data, list):
        for t in theme_data:
            if isinstance(t, dict):
                val = t.get("_value", "")
                if val:
                    themes.append(val)
            elif isinstance(t, str) and t:
                themes.append(t)
    elif isinstance(theme_data, str) and theme_data:
        themes.append(theme_data)
    return themes


def extract_keywords(keyword_data: Any) -> List[str]:
    keywords = []
    if isinstance(keyword_data, list):
        for k in keyword_data:
            if isinstance(k, dict):
                val = k.get("_value", "")
                if val:
                    keywords.append(val)
            elif isinstance(k, str) and k:
                keywords.append(k)
    elif isinstance(keyword_data, str) and keyword_data:
        keywords.append(keyword_data)
    return keywords


def extract_distributions(dist_data: Any) -> List[Dict]:
    distributions = []
    if isinstance(dist_data, list):
        for d in dist_data:
            if isinstance(d, dict):
                distributions.append({
                    "title": d.get("title", ""),
                    "format": d.get("format", ""),
                    "access_url": d.get("accessURL", "") if isinstance(d.get("accessURL"), str) else "",
                    "download_url": d.get("downloadURL", "") if isinstance(d.get("downloadURL"), str) else "",
                })
    elif isinstance(dist_data, dict):
        distributions.append({
            "title": dist_data.get("title", ""),
            "format": dist_data.get("format", ""),
            "access_url": dist_data.get("accessURL", "") if isinstance(dist_data.get("accessURL"), str) else "",
            "download_url": dist_data.get("downloadURL", "") if isinstance(dist_data.get("downloadURL"), str) else "",
        })
    return distributions


def transform_dataset(raw: Dict) -> Dict:
    title_es = extract_multilingual_text(raw.get("title"), "es")
    title_en = extract_multilingual_text(raw.get("title"), "en")
    desc_es = extract_multilingual_text(raw.get("description"), "es")
    desc_en = extract_multilingual_text(raw.get("description"), "en")
    all_titles = extract_all_text(raw.get("title"))
    all_descriptions = extract_all_text(raw.get("description"))
    themes = extract_themes(raw.get("theme"))
    keywords = extract_keywords(raw.get("keyword"))
    spatial_info = extract_spatial_info(raw.get("spatial"))
    publisher_data = raw.get("publisher", {})
    if isinstance(publisher_data, list):
        publisher_data = publisher_data[0] if publisher_data else {}
    publisher_uri = publisher_data.get("_about", "") if isinstance(publisher_data, dict) else str(publisher_data)
    license_data = raw.get("license", "")
    license_uri = license_data.get("_about", "") if isinstance(license_data, dict) else str(license_data)
    temporal_data = raw.get("temporal", "")
    if isinstance(temporal_data, list):
        temporal_data = temporal_data[0] if temporal_data else ""
    if isinstance(temporal_data, dict):
        temporal_str = temporal_data.get("_about", "")
    else:
        temporal_str = str(temporal_data) if temporal_data else ""
    issued = raw.get("issued", "")
    modified = raw.get("modified", "")
    distributions = extract_distributions(raw.get("distribution"))
    theme_text = " ".join(themes)
    keyword_text = " ".join(keywords)
    embedding_text = f"""{all_titles}
{all_titles}
{all_descriptions}
Temas: {theme_text}
Palabras clave: {keyword_text}
Territorio: {spatial_info['name']}""".strip()
    search_text = f"{all_titles} {all_descriptions} {theme_text} {keyword_text} {spatial_info['name']}"
    return {
        "identifier": raw.get("identifier", ""),
        "source_url": raw.get("_about", ""),
        "title_es": title_es,
        "title_en": title_en,
        "description_es": desc_es,
        "description_en": desc_en,
        "embedding_text": embedding_text,
        "metadata_vector": None,
        "themes": themes,
        "keywords": keywords,
        "spatial_uri": spatial_info["uri"],
        "spatial_level": spatial_info["level"],
        "spatial_name": spatial_info["name"],
        "publisher_uri": publisher_uri,
        "publisher_name": extract_uri_last_segment(publisher_uri),
        "license_uri": license_uri,
        "license_name": extract_uri_last_segment(license_uri),
        "temporal_coverage": temporal_str,
        "accrual_periodicity": extract_uri_last_segment(raw.get("accrualPeriodicity", "")),
        "issued": issued,
        "modified": modified,
        "distributions": distributions,
        "search_text": search_text,
        "ingested_at": datetime.utcnow().isoformat(),
    }


# ── Persistencia ───────────────────────────────────────────────────────────

def save_state(state_path: Path, state: Dict):
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def load_state(state_path: Path) -> Dict:
    if state_path.exists():
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_batch(output_dir: Path, batch_num: int, datasets: List[Dict], fmt: str = "jsonl") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    if fmt == "jsonl":
        filepath = output_dir / f"batch_{batch_num:04d}.jsonl"
        with open(filepath, "w", encoding="utf-8") as f:
            for ds in datasets:
                f.write(json.dumps(ds, ensure_ascii=False) + "\n")
    else:
        filepath = output_dir / f"batch_{batch_num:04d}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(datasets, f, ensure_ascii=False, indent=2)
    return filepath


# ── Pipeline V2 con deduplicación ───────────────────────────────────────────

def run_ingestion_v2(
    output_dir: Path,
    limit: Optional[int] = None,
    resume: bool = False,
    batch_size: int = 1000,
    fmt: str = "jsonl",
    page_size: int = 100,
):
    """Pipeline con anti-duplicados por identifier."""

    state_path = output_dir / STATE_FILE
    state = load_state(state_path) if resume else {}

    start_page = state.get("page", 0)
    batch_num = state.get("batch_num", 0)
    total_ingested = state.get("total_ingested", 0)
    total_unique = state.get("total_unique", 0)
    errors = state.get("errors", 0)
    seen_identifiers: Set[str] = set(state.get("seen_identifiers", []))

    logger.info("=" * 60)
    logger.info("INICIO INGESTA V2 - datos.gob.es (ANTI-DUPLICADOS)")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Formato: {fmt}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"IDs únicos previos: {len(seen_identifiers)}")
    if resume and start_page > 0:
        logger.info(f"Reanudando desde página: {start_page}")
    logger.info("=" * 60)

    try:
        current_page = start_page
        current_batch = []
        skipped_duplicates = 0
        skipped_empty = 0

        while True:
            logger.info(f"Fetching página {current_page}...")

            result = fetch_page(page=current_page, page_size=page_size)
            datasets = result.get("items", [])
            has_next = result.get("has_next", False)

            if not datasets:
                logger.warning("No se obtuvieron datasets en esta página. Fin.")
                break

            for raw in datasets:
                if limit and total_unique >= limit:
                    logger.info(f"Límite de {limit} datasets únicos alcanzado.")
                    break

                identifier = raw.get("identifier", "")
                if not identifier:
                    skipped_empty += 1
                    continue

                # ANTI-DUPLICADO: saltar si ya vimos este ID
                if identifier in seen_identifiers:
                    skipped_duplicates += 1
                    continue

                try:
                    normalized = transform_dataset(raw)
                    current_batch.append(normalized)
                    seen_identifiers.add(identifier)
                    total_ingested += 1
                    total_unique += 1
                except Exception as e:
                    logger.error(f"Error transformando dataset {identifier}: {e}")
                    errors += 1

            if limit and total_unique >= limit:
                break

            if len(current_batch) >= batch_size:
                filepath = save_batch(output_dir, batch_num, current_batch, fmt)
                logger.info(
                    f"  → Guardado batch {batch_num}: {len(current_batch)} datasets → {filepath.name} "
                    f"(total únicos: {total_unique:,}, saltados: {skipped_duplicates:,})"
                )
                current_batch = []
                batch_num += 1

                save_state(state_path, {
                    "page": current_page + 1,
                    "batch_num": batch_num,
                    "total_ingested": total_ingested,
                    "total_unique": total_unique,
                    "errors": errors,
                    "skipped_duplicates": skipped_duplicates,
                    "skipped_empty": skipped_empty,
                    "seen_identifiers": list(seen_identifiers),
                    "last_update": datetime.utcnow().isoformat(),
                })

            if not has_next:
                logger.info("No hay más páginas. Fin de la ingesta.")
                break

            current_page += 1
            time.sleep(RATE_LIMIT_DELAY)

        # Guardar batch residual
        if current_batch:
            filepath = save_batch(output_dir, batch_num, current_batch, fmt)
            logger.info(
                f"  → Guardado batch final {batch_num}: {len(current_batch)} datasets → {filepath.name}"
            )
            batch_num += 1

        # Estado final
        save_state(state_path, {
            "page": current_page,
            "batch_num": batch_num,
            "total_ingested": total_ingested,
            "total_unique": total_unique,
            "errors": errors,
            "skipped_duplicates": skipped_duplicates,
            "skipped_empty": skipped_empty,
            "seen_identifiers": list(seen_identifiers),
            "completed": True,
            "last_update": datetime.utcnow().isoformat(),
        })

        logger.info("=" * 60)
        logger.info("INGESTA V2 COMPLETADA")
        logger.info(f"Total procesados (API): {total_ingested:,}")
        logger.info(f"Total únicos guardados: {total_unique:,}")
        logger.info(f"Duplicados saltados: {skipped_duplicates:,}")
        logger.info(f"IDs vacíos saltados: {skipped_empty:,}")
        logger.info(f"Errores: {errors}")
        logger.info(f"Total batches: {batch_num}")
        logger.info(f"Archivos guardados en: {output_dir}")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Ingesta interrumpida por usuario.")
        save_state(state_path, {
            "page": current_page,
            "batch_num": batch_num,
            "total_ingested": total_ingested,
            "total_unique": total_unique,
            "errors": errors,
            "skipped_duplicates": skipped_duplicates,
            "skipped_empty": skipped_empty,
            "seen_identifiers": list(seen_identifiers),
            "completed": False,
            "last_update": datetime.utcnow().isoformat(),
        })
        logger.info(f"Estado guardado en {state_path}. Usa --resume para continuar.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Ingesta V2 con anti-duplicados - datos.gob.es",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python3 ingest_datos_gob_v2.py --output data/raw_v2/
  python3 ingest_datos_gob_v2.py --resume --output data/raw_v2/
        """,
    )
    parser.add_argument("--output", "-o", type=Path, default=Path("data/raw_v2"), help="Directorio de salida")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Máximo datasets únicos")
    parser.add_argument("--resume", "-r", action="store_true", help="Reanudar desde estado anterior")
    parser.add_argument("--batch-size", "-b", type=int, default=1000, help="Datasets por archivo batch")
    parser.add_argument("--page-size", "-p", type=int, default=100, help="Datasets por página de API")
    parser.add_argument("--format", "-f", choices=["jsonl", "json"], default="jsonl")
    args = parser.parse_args()

    run_ingestion_v2(
        output_dir=args.output,
        limit=args.limit,
        resume=args.resume,
        batch_size=args.batch_size,
        fmt=args.format,
        page_size=args.page_size,
    )


if __name__ == "__main__":
    main()
