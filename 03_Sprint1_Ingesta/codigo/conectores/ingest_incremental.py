#!/usr/bin/env python3
"""
Ingesta incremental de datos.gob.es — Upsert directo a PostgreSQL.

Descarga datasets de la API de datos.gob.es y hace INSERT ... ON CONFLICT
para actualizar los existentes y insertar los nuevos. Solo genera embeddings
para datasets nuevos o modificados.

Uso:
  python3 ingest_incremental.py
  python3 ingest_incremental.py --dry-run    # solo reporta, no escribe
  python3 ingest_incremental.py --limit 100  # solo procesa 100 datasets

Requiere variables de entorno:
  POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""

import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlencode

import psycopg2
from psycopg2.extras import execute_batch

# ── Configuración ───────────────────────────────────────────────────────────

API_BASE_URL = "https://datos.gob.es/apidata/catalog/dataset.json"
API_TIMEOUT = 30
RETRIES = 3
BACKOFF = 1.0
RATE_LIMIT_DELAY = 0.5
PAGE_SIZE = 100
BATCH_SIZE = 500

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── HTTP ────────────────────────────────────────────────────────────────────


def http_get_json(url: str, retries: int = RETRIES) -> Optional[Dict]:
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "PFM-Ingesta/3.0"},
            )
            with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = BACKOFF * (2**attempt)
                logger.warning(f"HTTP {e.code}, reintentando en {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"HTTP Error {e.code}: {e.reason}")
                return None
        except Exception as e:
            if attempt < retries:
                wait = BACKOFF * (2**attempt)
                logger.warning(f"Error {e}, reintentando en {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"Error en request: {e}")
                return None
    return None


def fetch_page(page: int = 0) -> Dict[str, Any]:
    params = {"_page": page, "_pageSize": PAGE_SIZE}
    url = f"{API_BASE_URL}?{urlencode(params)}"
    data = http_get_json(url)
    if data is None:
        return {"items": [], "has_next": False}
    result = data.get("result", {})
    items = result.get("items", [])
    has_next = "next" in result
    return {"items": items, "has_next": has_next}


# ── Normalización ──────────────────────────────────────────────────────────


def normalize_dataset(item: Dict) -> Dict:
    """Normaliza un dataset de la API al esquema de PostgreSQL."""
    # Identifier (required, unique) — usar _about (URL de datos.gob.es) como clave
    # La BD guarda en dataset_id la URL del portal original, pero raw_metadata->>'source_url'
    # contiene la URL de datos.gob.es (_about). Usamos _about para matching.
    about_url = item.get("_about", "")
    identifier = item.get("identifier", "")
    if not about_url and not identifier:
        return None

    # dataset_id final: preferir identifier si es URL del portal original,
    # sino usar _about (que es la URL de datos.gob.es)
    dataset_id = identifier if (identifier and identifier.startswith("http")) else about_url

    # Title (puede ser list de dicts multi-idioma o string)
    title_raw = item.get("title", "")
    if isinstance(title_raw, list) and title_raw:
        # [{"_value": "...", "_lang": "es"}, ...]
        for t in title_raw:
            if isinstance(t, dict) and t.get("_lang") == "es":
                title = t.get("_value", "")
                break
        else:
            title = title_raw[0].get("_value", "") if isinstance(title_raw[0], dict) else str(title_raw[0])
    elif isinstance(title_raw, dict):
        title = title_raw.get("_value", str(title_raw))
    else:
        title = str(title_raw) if title_raw else ""

    # Description (puede ser list de dicts multi-idioma o string)
    desc_raw = item.get("description", "")
    if isinstance(desc_raw, list) and desc_raw:
        for d in desc_raw:
            if isinstance(d, dict) and d.get("_lang") == "es":
                desc_raw = d.get("_value", "")
                break
        else:
            desc_raw = desc_raw[0].get("_value", "") if isinstance(desc_raw[0], dict) else str(desc_raw[0])
    elif isinstance(desc_raw, dict):
        desc_raw = desc_raw.get("_value", str(desc_raw))
    else:
        desc_raw = str(desc_raw) if desc_raw else ""
    description = desc_raw

    # Publisher
    publisher = item.get("publisher", "")
    if isinstance(publisher, dict):
        publisher = publisher.get("name", publisher.get("_about", str(publisher)))
    elif isinstance(publisher, list) and publisher:
        p = publisher[0]
        publisher = p.get("name", p.get("_about", str(p))) if isinstance(p, dict) else str(p)
    publisher = str(publisher) if publisher else ""

    # Theme
    theme_raw = item.get("theme", "")
    if isinstance(theme_raw, list) and theme_raw:
        theme_raw = theme_raw[0]
    if isinstance(theme_raw, dict):
        theme = theme_raw.get("_about", "").split("/")[-1] if theme_raw.get("_about") else ""
        theme_label = theme_raw.get("label", "")
        if isinstance(theme_label, list) and theme_label:
            theme_label = theme_label[0].get("_value", str(theme_label[0])) if isinstance(theme_label[0], dict) else str(theme_label[0])
        elif isinstance(theme_label, dict):
            theme_label = theme_label.get("_value", str(theme_label))
    else:
        theme = str(theme_raw).split("/")[-1] if theme_raw else ""
        theme_label = str(theme_raw) if theme_raw else ""
    theme = str(theme) if theme else ""
    theme_label = str(theme_label) if theme_label else ""

    # Territory (spatial)
    spatial = item.get("spatial", "")
    if isinstance(spatial, list) and spatial:
        spatial = spatial[0]
    if isinstance(spatial, dict):
        territory = spatial.get("_about", "").split("/")[-1] if spatial.get("_about") else ""
        territory_label = spatial.get("label", "")
        if isinstance(territory_label, list) and territory_label:
            territory_label = territory_label[0].get("_value", str(territory_label[0])) if isinstance(territory_label[0], dict) else str(territory_label[0])
        elif isinstance(territory_label, dict):
            territory_label = territory_label.get("_value", str(territory_label))
    else:
        territory = str(spatial) if spatial else ""
        territory_label = territory if territory else ""
    territory = str(territory) if territory else ""
    territory_label = str(territory_label) if territory_label else ""

    # Format
    fmt_raw = item.get("distribution", [])
    formats = set()
    if isinstance(fmt_raw, list):
        for dist in fmt_raw:
            if isinstance(dist, dict):
                fmt = dist.get("format", "")
                if fmt:
                    formats.add(str(fmt).split("/")[-1])
    format_str = ",".join(sorted(formats)) if formats else ""

    # Language
    language = item.get("language", "es")
    if isinstance(language, list):
        language = language[0] if language else "es"
    if isinstance(language, dict):
        language = language.get("_value", "es")
    language = str(language).split("/")[-1] if language else "es"

    # License
    license_url = item.get("license", "")
    if isinstance(license_url, dict):
        license_url = license_url.get("_about", str(license_url))
    elif isinstance(license_url, list) and license_url:
        license_url = license_url[0].get("_about", str(license_url[0])) if isinstance(license_url[0], dict) else str(license_url[0])
    license_url = str(license_url) if license_url else ""

    # Frequency
    frequency = item.get("accrualPeriodicity", "")
    if isinstance(frequency, dict):
        frequency = frequency.get("_about", str(frequency))
    elif isinstance(frequency, list) and frequency:
        frequency = frequency[0].get("_about", str(frequency[0])) if isinstance(frequency[0], dict) else str(frequency[0])
    frequency = str(frequency).split("/")[-1] if frequency else ""

    # Temporal coverage
    temporal = item.get("temporal", "")
    if isinstance(temporal, dict):
        temporal = f"{temporal.get('start', '')}/{temporal.get('end', '')}"

    # URL
    url = item.get("landingPage", item.get("_about", ""))

    # Keywords
    keywords = item.get("keyword", [])
    if isinstance(keywords, list):
        parts = []
        for k in keywords:
            if isinstance(k, dict):
                parts.append(k.get("_value", str(k)))
            else:
                parts.append(str(k))
        keywords = ", ".join(parts)
    elif isinstance(keywords, dict):
        keywords = keywords.get("_value", str(keywords))

    # Tags
    tags = item.get("tag", "")
    if isinstance(tags, list):
        tags = ", ".join(str(t) for t in tags)
    if isinstance(tags, dict):
        tags = tags.get("_value", str(tags))

    # Embedding text (para generar embeddings)
    embedding_text = f"{title}. {description}. {keywords} {theme_label} {territory_label}"

    # Search vector (para full-text search)
    search_text = f"{title} {description} {keywords} {theme_label} {territory_label} {publisher}"

    return {
        "dataset_id": dataset_id[:255] if dataset_id else None,
        "_about": about_url[:255] if about_url else "",
        "title": title[:500] if title else None,
        "description": description,
        "publisher": publisher[:500] if publisher else None,
        "publisher_id": (publisher[:255] if publisher else "")[:255],
        "theme": theme[:255] if theme else None,
        "theme_label": theme_label[:500] if theme_label else None,
        "territory": territory[:255] if territory else None,
        "territory_label": territory_label[:500] if territory_label else None,
        "format": format_str[:50] if format_str else None,
        "language": str(language)[:10] if language else "es",
        "license": str(license_url)[:255] if license_url else None,
        "frequency": str(frequency)[:50] if frequency else None,
        "temporal_coverage": str(temporal)[:255] if temporal else None,
        "url": str(url)[:1000] if url else None,
        "keywords": str(keywords) if keywords else None,
        "tags": str(tags) if tags else None,
        "embedding_text": embedding_text.strip(),
        "search_text": search_text.strip(),
        "raw_metadata": json.dumps(item, ensure_ascii=False),
    }


# ── PostgreSQL ─────────────────────────────────────────────────────────────


def pg_connect():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "buscador"),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD", "postgres"),
    )


def get_existing_ids(conn) -> Set[str]:
    """Devuelve el set de dataset_id + source_url ya en la BD."""
    with conn.cursor() as cur:
        # dataset_id + raw_metadata->>'source_url' (URL de datos.gob.es)
        cur.execute("SELECT dataset_id FROM datasets")
        ids = {row[0] for row in cur.fetchall() if row[0]}
        cur.execute("SELECT raw_metadata->>'source_url' FROM datasets WHERE raw_metadata->>'source_url' IS NOT NULL")
        ids.update(row[0] for row in cur.fetchall() if row[0])
        return ids


def upsert_batch(conn, records: List[Dict], dry_run: bool = False) -> tuple:
    """Hace upsert de un lote de datasets. Devuelve (inserted, updated)."""
    if dry_run or not records:
        return (0, 0)

    # Usar execute_values para mayor eficiencia y evitar problemas con execute_batch
    from psycopg2.extras import execute_values

    sql = """
        INSERT INTO datasets (
            dataset_id, title, description, publisher, publisher_id,
            theme, theme_label, territory, territory_label, format,
            language, license, frequency, temporal_coverage, url,
            keywords, tags, search_vector, raw_metadata, updated_at
        ) VALUES %s
        ON CONFLICT (dataset_id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            publisher = EXCLUDED.publisher,
            theme = EXCLUDED.theme,
            theme_label = EXCLUDED.theme_label,
            territory = EXCLUDED.territory,
            territory_label = EXCLUDED.territory_label,
            format = EXCLUDED.format,
            keywords = EXCLUDED.keywords,
            tags = EXCLUDED.tags,
            search_vector = EXCLUDED.search_vector,
            raw_metadata = EXCLUDED.raw_metadata,
            updated_at = CURRENT_TIMESTAMP
        WHERE datasets.title IS DISTINCT FROM EXCLUDED.title
           OR datasets.description IS DISTINCT FROM EXCLUDED.description
           OR datasets.raw_metadata IS DISTINCT FROM EXCLUDED.raw_metadata
    """

    # Preparar tuplas para execute_values — deduplicar por dataset_id
    seen_ids = set()
    values = []
    for r in records:
        ds_id = r.get("dataset_id")
        if not ds_id or ds_id in seen_ids:
            continue
        seen_ids.add(ds_id)

        rm = r.get("raw_metadata")
        if isinstance(rm, str):
            rm_str = rm
        else:
            rm_str = json.dumps(rm or {}, ensure_ascii=False)

        # keywords y tags son text[] en PostgreSQL — convertir string a lista
        kw = r.get("keywords")
        if kw and isinstance(kw, str):
            kw_list = [k.strip() for k in kw.split(",") if k.strip()]
        elif kw and isinstance(kw, list):
            kw_list = kw
        else:
            kw_list = []

        tg = r.get("tags")
        if tg and isinstance(tg, str):
            tg_list = [t.strip() for t in tg.split(",") if t.strip()]
        elif tg and isinstance(tg, list):
            tg_list = tg
        else:
            tg_list = []

        values.append((
            ds_id,
            r.get("title"),
            r.get("description"),
            r.get("publisher"),
            r.get("publisher_id", ""),
            r.get("theme"),
            r.get("theme_label"),
            r.get("territory"),
            r.get("territory_label"),
            r.get("format"),
            r.get("language", "es"),
            r.get("license"),
            r.get("frequency"),
            r.get("temporal_coverage"),
            r.get("url"),
            kw_list,
            tg_list,
            r.get("search_text", ""),
            rm_str,
        ))

    # Usar execute_values con template que convierte search_text a tsvector
    template = """(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, to_tsvector('spanish', %s), %s::jsonb, CURRENT_TIMESTAMP)"""

    with conn.cursor() as cur:
        execute_values(cur, sql, values, template=template, page_size=100)
        conn.commit()
        return (cur.rowcount, len(values))


def get_datasets_needing_embeddings(conn) -> List[str]:
    """Devuelve dataset_ids sin embedding."""
    with conn.cursor() as cur:
        cur.execute("SELECT dataset_id FROM datasets WHERE embedding IS NULL LIMIT 1000")
        return [row[0] for row in cur.fetchall()]


# ── Pipeline ───────────────────────────────────────────────────────────────


def run_incremental(dry_run: bool = False, limit: int = None):
    logger.info("=" * 60)
    logger.info("INGESTA INCREMENTAL datos.gob.es → PostgreSQL")
    logger.info(f"Modo: {'DRY RUN' if dry_run else 'WRITE'}")
    logger.info("=" * 60)

    # Conectar a PG
    conn = pg_connect()
    logger.info("Conectado a PostgreSQL")

    # IDs existentes
    existing_ids = get_existing_ids(conn)
    logger.info(f"Datasets en BD: {len(existing_ids):,}")

    # Descargar de la API
    total_fetched = 0
    total_new = 0
    total_updated = 0
    total_unchanged = 0
    page = 0
    batch = []

    while True:
        data = fetch_page(page)
        items = data["items"]
        if not items:
            break

        for item in items:
            normalized = normalize_dataset(item)
            if not normalized:
                continue

            total_fetched += 1
            # Un dataset es "nuevo" si ni su dataset_id ni su _about están en la BD
            is_new = (normalized["dataset_id"] not in existing_ids
                      and normalized.get("_about", "") not in existing_ids)

            if is_new:
                total_new += 1
            else:
                total_updated += 1

            batch.append(normalized)

            if len(batch) >= BATCH_SIZE:
                ins, upd = upsert_batch(conn, batch, dry_run)
                logger.info(
                    f"Página {page}: {total_fetched:,} procesados | "
                    f"Nuevos: {total_new:,} | Actualizados: {total_updated:,}"
                )
                batch = []

            if limit and total_fetched >= limit:
                logger.info(f"Límite de {limit} alcanzado")
                break

        if limit and total_fetched >= limit:
            break

        if not data["has_next"]:
            break

        page += 1
        time.sleep(RATE_LIMIT_DELAY)

    # Procesar lote final
    if batch:
        ins, upd = upsert_batch(conn, batch, dry_run)

    # Verificar embeddings faltantes
    needing_emb = get_datasets_needing_embeddings(conn)
    if needing_emb:
        logger.info(f"⚠️ {len(needing_emb):,} datasets sin embedding — ejecutar generate_embeddings.py")

    conn.close()

    logger.info("=" * 60)
    logger.info("INGESTA INCREMENTAL COMPLETADA")
    logger.info(f"Total descargados (API): {total_fetched:,}")
    logger.info(f"Nuevos insertados: {total_new:,}")
    logger.info(f"Actualizados: {total_updated:,}")
    logger.info(f"Sin embedding: {len(needing_emb):,}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Ingesta incremental datos.gob.es → PostgreSQL (upsert)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Solo reportar, no escribir")
    parser.add_argument("--limit", type=int, default=None, help="Máximo datasets a procesar")
    args = parser.parse_args()

    run_incremental(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()