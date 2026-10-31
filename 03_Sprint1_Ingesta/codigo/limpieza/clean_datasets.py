#!/usr/bin/env python3
"""
Limpieza y normalización de datasets de datos.gob.es para Sprint 1.

Pipeline:
  1. Carga todos los batches JSONL raw
  2. Normaliza spatial_name (typos, códigos)
  3. Infiere territorio desde publisher/título/descripción cuando spatial está vacío
  4. Traduce códigos de publisher a nombres legibles
  5. Normaliza formatos MIME → etiquetas cortas
  6. Limpia y enriquece embedding_text
  7. Deduplica
  8. Genera dataset procesado → datos/processed/datasets_clean.jsonl
  9. Genera sample enriched → datos/processed/sample_enriched.json (500 datasets para POC)

Usage:
  python clean_datasets.py [--dry-run] [--sample N]
"""

import argparse
import json
import logging
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Config ──────────────────────────────────────────────────────────────────
RAW_DIR = Path(__file__).resolve().parent.parent.parent / "datos" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "datos" / "processed"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Publisher code → Human-readable name ────────────────────────────────────
PUBLISHER_MAP: Dict[str, str] = {
    # CCAA principales
    "A01002820": "Junta de Andalucía",
    "A02002834": "IAEST - Gobierno de Aragón",
    "A03002858": "Principado de Asturias",
    "A04003003": "Govern de les Illes Balears",
    "A04027063": "INE - Instituto Nacional de Estadística",
    "A05003423": "ISTAC - Gobierno de Canarias",
    "A05003638": "Gobierno de Canarias (Turismo)",
    "A06003562": "Gobierno de Cantabria",
    "A07002862": "Junta de Castilla y León",
    "A08002880": "Junta de Castilla-La Mancha",
    "A09002970": "Generalitat de Catalunya",
    "A10002983": "Generalitat Valenciana",
    "A11002839": "Junta de Extremadura",
    "A12002994": "Xunta de Galicia",
    "A13002908": "Comunidad de Madrid",
    "A14002961": "Comunidad Autónoma de la Región de Murcia",
    "A14003041": "Diputación Foral de Bizkaia",
    "A15002917": "Gobierno de Navarra",
    "A16003011": "Gobierno Vasco (Open Data Euskadi)",
    "A17002943": "Xunta de Galicia",
    "A19002898": "Gobierno de La Rioja",
    # Ministerios y organismos estatales
    "E00003801": "Ministerio del Interior",
    "E00116401": "INTA - Instituto Nacional de Técnica Aeroespacial",
    "E00125901": "Ministerio de Defensa",
    "E00130502": "DGT - Dirección General de Tráfico",
    "E05024301": "Ministerio para la Transición Ecológica",
    "E05024401": "Ministerio de Agricultura, Pesca y Alimentación",
    "E05068001": "MITECO - Ministerio para la Transición Ecológica",
    "E05070101": "Ministerio de Sanidad",
    "E05071301": "Ministerio de Ciencia e Innovación",
    "E05072501": "Ministerio de Inclusión, Seguridad Social y Migraciones",
    "E05073401": "Ministerio de Universidades",
    "E05230301": "Ministerio de Educación y Formación Profesional",
    "E05228601": "Ministerio de Educación",
    "E05233601": "Ministerio de Transportes",
    "E05251701": "Ministerio de Asuntos Económicos y Transformación Digital",
    "E0DAT0002": "CNIG - Centro Nacional de Información Geográfica",
    "E04926001": "Ministerio de Hacienda",
    "EA0010987": "Ministerio de Agricultura, Pesca y Alimentación",
    "EA0019768": "Biblioteca Nacional de España",
    "EA0001302": "Ministerio de Justicia",
    "EA0001304": "Ministerio de Asuntos Exteriores",
    "EA0003337": "Ministerio de Cultura",
    "EA0022362": "Ministerio de Agricultura",
    "EA0028512": "Ministerio de Industria y Turismo",
    "EA0040772": "Ministerio de Transportes y Movilidad Sostenible",
    "EA0041513": "Ministerio de Trabajo (SEPE)",
    "EA0042469": "Ministerio de Vivienda y Agenda Urbana",
    "EA0042823": "Ministerio de Sanidad",
    "EA0042931": "Ministerio de Derechos Sociales y Agenda 2030",
    "EA0043088": "Ministerio de Igualdad",
    "EA0043369": "Ministerio para la Transición Ecológica",
    "EA0044367": "Ministerio de Asuntos Económicos y Transformación Digital",
    # Institutos y organismos autónomos
    "I00000687": "Congreso de los Diputados",
    "GE0012152": "GRAFCAN - Cartografía de Canarias",
    "A03002951": "Principado de Asturias",
    "A06004074": "Gobierno de Cantabria",
    # Universidades
    "U00200001": "Universidad de Barcelona",
    "U00800001": "Universidad de Granada",
    "U01000001": "Universidad de Santiago de Compostela",
    "U01200001": "Universidad de Sevilla",
    "U01600001": "Universidad de Valladolid",
    "U01900001": "Universidad de Cádiz",
    "U02100001": "Universidad de Zaragoza",
    "U02300001": "Universidad de Almería",
    "U03600001": "Universidad de La Rioja",
    "U04800001": "Universidad de Huelva",
    "U04900001": "Universidad de Jaén",
    "U05600001": "Universidad de Burgos",
    # Ayuntamientos
    "L01010590": "Ayto. de Vitoria-Gasteiz",
    "L01030092": "Ayto. de Alicante",
    "L01061535": "Ayto. de Almería",
    "L01080193": "Ayto. de Barcelona",
    "L01081017": "Ayto. de Bilbao",
    "L01081691": "Ayto. de Burgos",
    "L01082009": "Ayto. de Cáceres",
    "L01082114": "Ayto. de Sant Feliu de Llobregat",
    "L01082798": "Ayto. de Castellón",
    "L01100377": "Ayto. de Cádiz",
    "L01110146": "Ayto. de Córdoba",
    "L01140425": "Ayto. de Huelva",
    "L01140673": "Ayto. de Jaén",
    "L01280066": "Ayto. de León",
    "L01280148": "Ayto. de Arganda del Rey",
    "L01280796": "Ayto. de Madrid",
    "L01281132": "Ayto. de Málaga",
    "L01281150": "Ayto. de Murcia",
    "L01281317": "Ayto. de San Lorenzo de El Escorial",
    "L01290672": "Ayto. de Torrelodones",
    "L01300161": "Ayto. de Valencia",
    "L01300243": "Ayto. de Salamanca",
    "L01330241": "Ayto. de Gijón",
    "L01330045": "Ayto. de Sevilla",
    "L01350167": "Ayto. de Las Palmas de Gran Canaria",
    "L01360577": "Ayto. de Vigo",
    "L01380380": "Ayto. de Santa Cruz de Tenerife",
    "L01390759": "Ayto. de Pamplona",
    "L01401945": "Ayto. de Segovia",
    "L01462444": "Ayto. de Valladolid",
    "L01462508": "Junta de Gobierno del Ayuntamiento de Valencia",
    "L01480209": "Ayto. de Vitoria-Gasteiz",
    "L01502973": "Ayto. de Logroño",
    "L02000014": "Ayto. de Toledo",
    "L03380005": "Cabildo de Tenerife",
    "L03380010": "Cabildo de Gran Canaria",
    "L03380011": "Cabildo de La Palma",
    # Diputaciones
    "L01200697": "Diputación de Gipuzkoa",
    "L02000001": "Diputación Foral de Álava",
    "L02000003": "Diputación de Alicante",
    "L02000008": "Diputación de Barcelona",
    "L02000012": "Diputación de Castellón",
    "L02000020": "Ayto. de Lasarte-Oria",
    "L02000047": "Diputación de Palencia",
    "L02000048": "Diputación Foral de Bizkaia",
}

# Fallback: organizaciones con prefijo conocido
ORG_PREFIX_MAP = {
    "A01": "Junta de Andalucía",
    "A02": "Gobierno de Aragón",
    "A03": "Principado de Asturias",
    "A04": "Govern de les Illes Balears",
    "A05": "Gobierno de Canarias",
    "A06": "Gobierno de Cantabria",
    "A07": "Junta de Castilla y León",
    "A08": "Junta de Castilla-La Mancha",
    "A09": "Generalitat de Catalunya",
    "A10": "Generalitat Valenciana",
    "A11": "Junta de Extremadura",
    "A12": "Xunta de Galicia",
    "A13": "Comunidad de Madrid",
    "A14": "Gobierno Vasco",
    "A15": "Gobierno de Navarra",
    "A16": "Gobierno Vasco",
    "A17": "Xunta de Galicia",
    "A19": "Gobierno de La Rioja",
    "E0": "Organismo Estatal",
    "E05": "Ministerio",
    "EA0": "Ministerio",
    "I0": "Organismo Público",
    "L01": "Ayuntamiento",
    "L02": "Diputación",
    "L03": "Cabildo",
    "U0": "Universidad Pública",
    "U02": "Universidad de Barcelona",
    "U01": "Universidad Pública",
    "LA0": "Organismo Autónomo",
}


def resolve_publisher_name(pub_code: str) -> str:
    """Resuelve nombre legible de publisher, con fallback por prefijo."""
    if pub_code in PUBLISHER_MAP:
        return PUBLISHER_MAP[pub_code]
    
    # Fallback por prefijo
    for prefix, name in ORG_PREFIX_MAP.items():
        if pub_code.startswith(prefix):
            return f"{name} ({pub_code})"
    
    return pub_code


# ── Spatial normalization ───────────────────────────────────────────────────
SPATIAL_NORMALIZE: Dict[str, str] = {
    "": "",
    "Pais Vasco": "País Vasco",
    "Cataluna": "Cataluña",
    "Castilla La Mancha": "Castilla-La Mancha",
    "Castilla Leon": "Castilla y León",
    "Castellon": "Comunitat Valenciana",
    "Castellón": "Comunitat Valenciana",
    "Alicante": "Comunitat Valenciana",
    "Alicante/Alacant": "Comunitat Valenciana",
    "Region Murcia": "Región de Murcia",
    "Comunidad Foral Navarra": "Navarra",
    "Madrid": "Comunidad de Madrid",
    "Zaragoza": "Aragón",
    "Zaragoza (Provincia)": "Aragón",
    "Malaga": "Andalucía",
    "Barcelona": "Cataluña",
    "3117735": "Comunidad de Madrid",
    "Madrid": "Comunidad de Madrid",
    "Aragon": "Aragón",
    # Códigos ESP_ y variantes
    "ESP_BCN": "Cataluña",
    "ESP_CIA_CEU": "Ceuta",
    "ESP_CMA_ANDAL": "Andalucía",
    "ESP_CMA_BALEAR": "Illes Balears",
    # Provincias sueltas → CCAA
    "Teruel": "Aragón",
    "Huesca": "Aragón",
    "Leon": "Castilla y León",
    "Jaen": "Andalucía",
    "Granada": "Andalucía",
    "Burgos": "Castilla y León",
    "Vizcaya": "País Vasco",
    "Alava": "País Vasco",
    "La Rioja": "La Rioja",
    "Cantabria": "Cantabria",
    # Otros
    "N2f22873f271d4f1a9c6add5e51819dbf": "España",
    "Comunidad Madrid": "Comunidad de Madrid",
    "Principado Asturias": "Asturias",
    "Andalucia": "Andalucía",
    "A Coruna": "Galicia",
}


def normalize_spatial(name: str) -> str:
    """Normaliza nombres de territorio."""
    name = name.strip()
    if name in SPATIAL_NORMALIZE:
        return SPATIAL_NORMALIZE[name]
    return name


# ── Spatial inference ───────────────────────────────────────────────────────

def infer_spatial(
    spatial_name: str,
    publisher_name: str,
    title: str,
    description: str,
) -> str:
    """Infiere el territorio cuando spatial_name viene vacío."""
    if spatial_name.strip():
        return spatial_name.strip()

    text = f"{publisher_name} | {title} | {description}".lower()

    patterns = [
        # Canarias
        (["tenerife", "gran canaria", "lanzarote", "la palma", "fuerteventura",
          "la gomera", "el hierro", "istac", "grafcan", "gobierno de canarias"], "Canarias"),
        (["canarias", "canario", "canaria"], "Canarias"),
        # Aragón
        (["zaragoza", "huesca", "teruel", "gobierno de aragón"], "Aragón"),
        (["aragón", "aragon"], "Aragón"),
        # Cataluña
        (["barcelona", "girona", "lleida", "tarragona", "generalitat"], "Cataluña"),
        (["cataluña", "catalunya", "catalonia"], "Cataluña"),
        # Madrid
        (["comunidad de madrid", "ayuntamiento de madrid", "canal isabel ii"], "Comunidad de Madrid"),
        (["madrid"], "Comunidad de Madrid"),
        # País Vasco
        (["bilbao", "donostia", "vitoria", "euskadi", "euskal", "gobierno vasco",
          "bizkaia", "gipuzkoa", "álava", "alava", "lasarte-oria", "nareak"], "País Vasco"),
        # Andalucía
        (["sevilla", "málaga", "malaga", "granada", "córdoba", "cordoba",
          "almería", "jaén", "huelva", "cádiz", "cadiz", "junta de andalucía"], "Andalucía"),
        # C. Valenciana
        (["valenciana", "valencia", "alicante", "castellón", "castellon",
          "generalitat valenciana"], "Comunitat Valenciana"),
        # Galicia
        (["coruña", "pontevedra", "ourense", "lugo", "xunta", "galego"], "Galicia"),
        (["galicia"], "Galicia"),
        # Navarra
        (["navarra", "nafarroa", "pamplona", "iruña"], "Navarra"),
        # Castilla y León
        (["castilla y león", "castilla y leon", "junta de castilla",
          "valladolid", "salamanca", "segovia", "león", "palencia",
          "burgos", "zamora", "ávila", "soria"], "Castilla y León"),
        # Castilla-La Mancha
        (["castilla-la mancha", "castilla la mancha", "albacete",
          "ciudad real", "cuenca", "guadalajara", "toledo"], "Castilla-La Mancha"),
        # Baleares
        (["mallorca", "menorca", "ibiza", "eivissa", "formentera", "govern balear"], "Illes Balears"),
        (["baleares", "illes balears"], "Illes Balears"),
        # Asturias
        (["asturias", "principado de asturias", "oviedo", "gijón"], "Asturias"),
        # Cantabria
        (["cantabria", "santander"], "Cantabria"),
        # Extremadura
        (["extremadura", "badajoz", "cáceres", "caceres"], "Extremadura"),
        # Murcia
        (["región de murcia", "region de murcia", "murcia"], "Región de Murcia"),
        # La Rioja
        (["la rioja", "logroño"], "La Rioja"),
        # Ceuta / Melilla
        (["ceuta"], "Ceuta"),
        (["melilla"], "Melilla"),
        # Nacional
        (["españa", "espana", "gobierno de españa", "dgt", "ministerio",
          "biblioteca nacional", "sepe", "miteco", "ine ", "cnig"], "España"),
    ]

    for keywords, label in patterns:
        if any(kw in text for kw in keywords):
            return label

    return "España"


# ── Format normalization ────────────────────────────────────────────────────

FORMAT_MAP: Dict[str, str] = {
    "http://publications.europa.eu/resource/authority/file-type/CSV": "CSV",
    "http://publications.europa.eu/resource/authority/file-type/TXT": "TXT",
    "http://publications.europa.eu/resource/authority/file-type/XLSX": "XLSX",
    "http://publications.europa.eu/resource/authority/file-type/PDF": "PDF",
    "http://publications.europa.eu/resource/authority/file-type/XLS": "XLS",
    "http://publications.europa.eu/resource/authority/file-type/XML": "XML",
    "http://publications.europa.eu/resource/authority/file-type/ZIP": "ZIP",
    "http://publications.europa.eu/resource/authority/file-type/JSON": "JSON",
    "http://publications.europa.eu/resource/authority/file-type/ODS": "ODS",
    "http://publications.europa.eu/resource/authority/file-type/HTML": "HTML",
    "http://publications.europa.eu/resource/authority/file-type/GEOJSON": "GeoJSON",
    "http://publications.europa.eu/resource/authority/file-type/RDF": "RDF",
    "http://publications.europa.eu/resource/authority/file-type/TURTLE": "Turtle",
    "http://publications.europa.eu/resource/authority/file-type/SPARQLQ": "SPARQL",
    "http://publications.europa.eu/resource/authority/file-type/GML": "GML",
    "http://publications.europa.eu/resource/authority/file-type/KML": "KML",
    "http://publications.europa.eu/resource/authority/file-type/WMS": "WMS",
    "http://publications.europa.eu/resource/authority/file-type/WFS": "WFS",
}


def normalize_format(fmt_value) -> str:
    """MIME → etiqueta legible. Soporta string y dict."""
    if isinstance(fmt_value, dict):
        mime = fmt_value.get("value", "")
        if not mime:
            mime = fmt_value.get("_about", "")
    else:
        mime = fmt_value
    mime = str(mime).strip()
    if not mime:
        return ""
    if mime in FORMAT_MAP:
        return FORMAT_MAP[mime]
    if "/" in mime:
        return mime.split("/")[-1].upper()
    return mime


# ── Theme normalization ─────────────────────────────────────────────────────

THEME_CODE_MAP: Dict[str, str] = {
    "ENVI": "medio ambiente",
    "GOVE": "sector publico",
    "TRAN": "transporte",
    "SOCI": "sociedad bienestar",
    "EDUC": "educacion",
    "ECON": "economia",
    "REGI": "demografia",
    "ENER": "energia",
    "ac": "medio ambiente",
    "ps": "salud",
    "hb": "vivienda",
    "sd": "desarrollo sostenible",
    "sr": "sector rural",
    "hy": "hidrologia",
    "ad": "administracion",
    "af": "agricultura",
    "er": "energias renovables",
    "am": "medio ambiente",
    "br": "biodiversidad",
    "ef": "economia",
}


def normalize_theme(uri: str) -> str:
    """Extrae label legible de URI de tema."""
    label = uri.split("/")[-1].replace("-", " ")
    # Si es un código corto, mapearlo
    if label in THEME_CODE_MAP:
        return THEME_CODE_MAP[label]
    return label


# ── Core cleaning ───────────────────────────────────────────────────────────

def clean_dataset(ds: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza un dataset individual."""
    # 1. Publisher → legible
    pub_code = ds.get("publisher_name", "").strip()
    ds["publisher_name_original"] = pub_code
    ds["publisher_name"] = resolve_publisher_name(pub_code)

    # 2. Spatial → normalizado + inferido
    raw_spatial = normalize_spatial(ds.get("spatial_name", ""))
    ds["spatial_name_original"] = raw_spatial
    inferred = infer_spatial(
        raw_spatial,
        ds["publisher_name"],  # usar nombre resuelto, no el código original
        ds.get("title_es", ""),
        ds.get("description_es", ""),
    )
    ds["spatial_name"] = inferred
    ds["spatial_inferred"] = (raw_spatial == "")

    # 3. Formats → legibles
    raw_formats = []
    clean_formats = []
    for dist in ds.get("distributions", []):
        fmt = dist.get("format", "")
        if fmt:
            raw_formats.append(fmt)
            clean = normalize_format(fmt)
            if clean and clean not in clean_formats:
                clean_formats.append(clean)
    ds["formats_raw"] = raw_formats
    ds["formats"] = clean_formats

    # 4. Themes → labels legibles
    theme_labels = [normalize_theme(t) for t in ds.get("themes", [])]
    ds["theme_labels"] = list(dict.fromkeys(theme_labels))  # deduplicar

    # 5. Keywords → limpiar vacíos/duplicados
    keywords = [k.strip() for k in ds.get("keywords", []) if k.strip()]
    ds["keywords"] = list(dict.fromkeys(keywords))

    # 6. Descripción → trim
    desc = ds.get("description_es", "").strip()
    if len(desc) < 20 and ds.get("description_en", ""):
        desc = ds.get("description_en", "").strip()
    ds["description_es_clean"] = desc[:1000]

    # 7. Reconstruir embedding_text
    parts = [ds.get("title_es", ""), ds.get("title_en", "")]
    if ds.get("description_es_clean"):
        parts.append(ds["description_es_clean"])
    if theme_labels:
        parts.append("Temas: " + ", ".join(theme_labels))
    if ds["keywords"]:
        parts.append("Palabras clave: " + ", ".join(ds["keywords"]))
    parts.append("Territorio: " + inferred)
    ds["embedding_text"] = " \n ".join(p for p in parts if p)

    # 8. Normalizar fecha
    modified = ds.get("modified", "")
    if modified:
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(modified)
            ds["modified_iso"] = dt.strftime("%Y-%m-%d")
        except Exception:
            ds["modified_iso"] = modified[:10] if len(modified) >= 10 else modified
    else:
        ds["modified_iso"] = ""

    # 9. Extraer URL principal
    primary_url = ""
    for dist in ds.get("distributions", []):
        url = dist.get("download_url", "") or dist.get("access_url", "")
        if url:
            primary_url = url
            break
    ds["primary_url"] = primary_url

    return ds


# ── Main pipeline ───────────────────────────────────────────────────────────

def load_raw_datasets(raw_dir: Path) -> List[Dict[str, Any]]:
    """Carga todos los datasets desde archivos JSONL."""
    datasets = []
    batch_files = sorted(f for f in os.listdir(raw_dir) if f.endswith(".jsonl"))
    logger.info(f"Cargando {len(batch_files)} batches...")
    for bf in batch_files:
        path = os.path.join(raw_dir, bf)
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    datasets.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    logger.info(f"Cargados {len(datasets)} datasets.")
    return datasets


def run_cleaning(dry_run: bool = False, sample_size: int = 500):
    """Pipeline principal de limpieza."""
    start = time.perf_counter()

    datasets = load_raw_datasets(RAW_DIR)

    logger.info("Limpiando datasets...")
    cleaned = []
    identifiers = set()
    duplicates = 0

    for ds in datasets:
        id_ = ds.get("identifier", "")
        if id_ in identifiers:
            duplicates += 1
            continue
        identifiers.add(id_)
        cleaned.append(clean_dataset(ds))

    elapsed = time.perf_counter() - start
    logger.info(f"Limpieza completada en {elapsed:.1f}s")
    logger.info(f"  Total: {len(datasets)} → {len(cleaned)} (dup descartados: {duplicates})")

    # Stats
    spatial_dist = Counter(ds["spatial_name"] for ds in cleaned)
    pub_dist = Counter(ds["publisher_name"] for ds in cleaned)
    theme_dist = Counter()
    for ds in cleaned:
        for t in ds["theme_labels"]:
            theme_dist[t] += 1
    fmt_dist = Counter()
    for ds in cleaned:
        for f in ds["formats"]:
            fmt_dist[f] += 1
    spatial_inferred = sum(1 for ds in cleaned if ds["spatial_inferred"])

    logger.info(f"\n=== ESTADÍSTICAS POST-LIMPIEZA ===")
    logger.info(f"Datasets únicos: {len(cleaned)}")
    logger.info(f"Territorios inferidos: {spatial_inferred} ({100*spatial_inferred/len(cleaned):.1f}%)")
    logger.info(f"Territorios únicos: {len(spatial_dist)}")
    logger.info(f"Publishers únicos: {len(pub_dist)}")
    logger.info(f"Temas únicos: {len(theme_dist)}")
    logger.info(f"Formatos únicos: {len(fmt_dist)}")
    logger.info(f"\nTop territorios:")
    for k, v in spatial_dist.most_common(15):
        logger.info(f"  {k}: {v}")
    logger.info(f"\nTop publishers:")
    for k, v in pub_dist.most_common(10):
        logger.info(f"  {k}: {v}")
    logger.info(f"\nTop temas:")
    for k, v in theme_dist.most_common(10):
        logger.info(f"  {k}: {v}")

    # Save
    if not dry_run:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

        out_path = PROCESSED_DIR / "datasets_clean.jsonl"
        logger.info(f"\nGuardando {len(cleaned)} datasets en {out_path}...")
        with open(out_path, "w", encoding="utf-8") as f:
            for ds in cleaned:
                json.dump(ds, f, ensure_ascii=False)
                f.write("\n")
        logger.info(f"✓ {out_path} ({out_path.stat().st_size / 1024 / 1024:.1f} MB)")

        sample = cleaned[:sample_size]
        sample_path = PROCESSED_DIR / "sample_enriched.json"
        logger.info(f"Guardando muestra de {len(sample)} en {sample_path}...")
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ {sample_path} ({sample_path.stat().st_size / 1024 / 1024:.1f} MB)")

        stats = {
            "total_datasets": len(cleaned),
            "spatial_inferred": spatial_inferred,
            "unique_spatial": len(spatial_dist),
            "unique_publishers": len(pub_dist),
            "unique_themes": len(theme_dist),
            "unique_formats": len(fmt_dist),
            "spatial_distribution": dict(spatial_dist.most_common()),
            "publisher_distribution": dict(pub_dist.most_common()),
            "theme_distribution": dict(theme_dist.most_common()),
            "format_distribution": dict(fmt_dist.most_common()),
            "cleaned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "elapsed_seconds": round(elapsed, 1),
        }
        stats_path = PROCESSED_DIR / "cleaning_stats.json"
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ {stats_path}")
    else:
        logger.info("\n[DRY RUN] No se escribieron archivos.")

    return cleaned


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Limpieza de datasets datos.gob.es")
    parser.add_argument("--dry-run", action="store_true", help="Solo analizar, no escribir")
    parser.add_argument("--sample", type=int, default=500, help="Tamaño del sample enriquecido")
    args = parser.parse_args()

    run_cleaning(dry_run=args.dry_run, sample_size=args.sample)
