#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_sniff_manifest.py
=======================
Construye manifest_sniff.csv para los datasets que NO tienen ninguna
distribución tabular declarada (los ~50.680 excluidos del plan principal).
Para cada uno selecciona hasta 3 distribuciones candidatas a sniffear,
ordenadas por probabilidad de ser un fichero descargable:
  1) las que declaran un format (aunque no sea tabular) -> suelen ser ficheros reales
  2) las que tienen extensión de fichero en la URL
  3) el resto
El descargador de sniff hará un GET, mirará Content-Type + magic bytes y, si
resulta ser CSV/JSON/XLSX/XLS/TXT/ODS, lo descargará.
"""
from __future__ import annotations
import csv, glob, hashlib, json, os, re
from urllib.parse import urlparse

TAB_SNIFF = {"CSV", "JSON", "XLSX", "XLS", "TXT", "ODS"}
TAB_DECL = {"CSV", "JSON", "XLSX", "XLS", "TXT"}  # lo que ya cubre el plan principal


def norm_full(dist):
    """Misma heurística que build_manifest.normalizar_formato: declared format
    o extensión en la URL. Devuelve CSV/JSON/... o ''."""
    f = (dist.get("format") or "").strip()
    if "/" in f:
        f = f.rsplit("/", 1)[-1]
    f = f.upper()
    if f in TAB_DECL:
        return f
    if f == "" or f not in TAB_DECL:
        u = (dist.get("access_url") or "").lower().split("?", 1)[0]
        for ext in ("csv", "json", "xlsx", "xls", "txt"):
            if u.endswith("." + ext) or ("/" + ext + "/") in u or ("." + ext + ".") in u:
                return ext.upper()
    return ""


def norm(dist):
    f = (dist.get("format") or "").strip()
    if "/" in f:
        f = f.rsplit("/", 1)[-1]
    return f.upper()


def has_file_ext(url):
    u = (url or "").lower().split("?", 1)[0].rsplit("/", 1)[-1]
    m = re.search(r"\.([a-z0-9]{2,5})$", u)
    return m.group(1) if m else None


def main():
    raw_dir = os.path.abspath("../datos/raw")
    out = "manifest_sniff.csv"
    # excluir datasets ya procesados por el plan principal
    main_ids = set()
    if os.path.exists("manifest.csv"):
        main_ids = {r["dataset_id"] for r in csv.DictReader(open("manifest.csv", encoding="utf-8"))}
    seen = set()
    rows = []
    n_no_tab = 0
    n_skip_main = 0
    for fn in sorted(glob.glob(os.path.join(raw_dir, "*.jsonl"))):
        with open(fn, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ident = d.get("identifier")
                if not ident or ident in seen:
                    continue
                seen.add(ident)
                if ident in main_ids:
                    n_skip_main += 1
                    continue
                dists = d.get("distributions") or []
                # ¿tiene alguna tabular (declarada o por extensión)? -> ya cubierta
                if any(norm_full(x) in TAB_DECL for x in dists):
                    continue
                # selecciona hasta 3 candidatas a sniffear
                cands = []
                for dist in dists:
                    url = dist.get("access_url") or ""
                    if not url:
                        continue
                    f = norm(dist)
                    ext = has_file_ext(url)
                    host = urlparse(url).netloc
                    # puntuación de "parece fichero descargable"
                    score = 0
                    if f and f != "HTML":
                        score += 2  # declara format (fichero real probable)
                    if ext and ext not in ("htm", "html", "asp", "aspx", "jsp", "php"):
                        score += 1
                    cands.append({"score": score, "fmt": f, "url": url,
                                  "host": host, "ext": ext or ""})
                cands.sort(key=lambda c: -c["score"])
                cands = cands[:3]
                if not cands:
                    continue  # sin distribuciones con URL -> no se puede sniffear
                n_no_tab += 1
                rows.append({
                    "dataset_id": ident,
                    "identifier": ident,
                    "publisher_name": (d.get("publisher_name") or "").strip(),
                    "host": cands[0]["host"],
                    "candidates": json.dumps(cands, ensure_ascii=False),
                    "status": "pending",
                    "chosen_format": "",
                    "http_status": "",
                    "content_type": "",
                    "saved_bytes": "",
                    "attempts": "",
                    "reason": "",
                    "error": "",
                    "ts": "",
                })
    cols = ["dataset_id", "identifier", "publisher_name", "host", "candidates",
            "status", "chosen_format", "http_status", "content_type",
            "saved_bytes", "attempts", "reason", "error", "ts"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Datasets sin tabular: {n_no_tab} | con candidatos a sniffear: {len(rows)} | "
          f"excluidos por estar en manifest.csv: {n_skip_main}")
    from collections import Counter
    print("Candidatas por dataset:", dict(Counter(len(json.loads(r['candidates'])) for r in rows).most_common()))
    print(f"✅ {out} escrito")


if __name__ == "__main__":
    main()