#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_candidates.py
=================
Añade al manifest.csv una columna `candidates` con la lista ORDENADA de todas
las distribuciones tabulares del dataset (prioridad CSV>JSON>XLSX>XLS>TXT),
para que el descargador pueda hacer FALLBACK: si el formato elegido falla,
probar el siguiente. No resetea el estado (status) ni ninguna columna existente.
"""
from __future__ import annotations
import csv, glob, hashlib, json, os, re, sys
from urllib.parse import urlparse

TAB = {"CSV", "JSON", "XLSX", "XLS", "TXT"}
PRIORIDAD = {"CSV": 5, "JSON": 4, "XLSX": 3, "XLS": 2, "TXT": 1}
EXT = {"CSV": "csv", "JSON": "json", "XLSX": "xlsx", "XLS": "xls", "TXT": "txt"}


def safe_name(ident):
    if not ident:
        return "unnamed"
    s = re.sub(r'[^A-Za-z0-9._-]', '_', ident).strip("._") or "unnamed"
    return s[:140] + "_" + hashlib.md5(ident.encode()).hexdigest()[:10] if len(s) > 150 else s


def norm(dist):
    f = (dist.get("format") or "").strip()
    if "/" in f:
        f = f.rsplit("/", 1)[-1]
    f = f.upper()
    if f in TAB:
        return f
    if f == "" or f not in TAB:
        u = (dist.get("access_url") or "").lower().split("?", 1)[0]
        for ext in ("csv", "json", "xlsx", "xls", "txt"):
            if u.endswith("." + ext):
                return ext.upper()
    return ""


def main():
    raw_dir = os.path.abspath("../datos/raw")
    manifest_path = sys.argv[1] if len(sys.argv) > 1 else "manifest.csv"
    cap_bytes = int(float(os.environ.get("CAP_MB", "100")) * 1024 * 1024)

    # 1) construir candidates por identifier (dedup)
    candidates_by_id = {}
    for fn in sorted(glob.glob(os.path.join(raw_dir, "*.jsonl"))):
        with open(fn, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ident = d.get("identifier")
                if not ident or ident in candidates_by_id:
                    continue
                cs = []
                seen_url = set()
                for dist in (d.get("distributions") or []):
                    f = norm(dist)
                    if f == "":
                        continue
                    url = dist.get("access_url") or ""
                    if not url or url in seen_url:
                        continue
                    try:
                        bs = int(dist.get("byte_size")) if dist.get("byte_size") not in (None, "") else None
                    except (ValueError, TypeError):
                        bs = None
                    if bs is not None and bs > cap_bytes:
                        continue  # respeta el cap
                    cs.append({"fmt": f, "url": url, "size": bs,
                               "host": urlparse(url).netloc})
                    seen_url.add(url)
                cs.sort(key=lambda c: -PRIORIDAD[c["fmt"]])
                candidates_by_id[ident] = cs

    # 2) actualizar manifest añadiendo columna candidates, conservando estado
    rows = list(csv.DictReader(open(manifest_path, encoding="utf-8")))
    if not rows:
        sys.exit("manifest vacío")
    cols = list(rows[0].keys())
    if "candidates" not in cols:
        cols = cols + ["candidates"]
    added = 0
    for r in rows:
        cs = candidates_by_id.get(r["dataset_id"], [])
        # si no hay candidates en raw (p.ej. dataset sin tabular, no debería), dejar []
        r["candidates"] = json.dumps(cs, ensure_ascii=False)
        if cs:
            added += 1
    with open(manifest_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Datasets en manifest: {len(rows)} | con candidates (≥1 tabular): {added}")
    from collections import Counter
    distrib = Counter(len(json.loads(r['candidates'])) for r in rows if r['candidates'])
    print("Distribución de nº de candidatos:", dict(distrib.most_common()))
    print("✅ manifest.csv actualizado con columna candidates (estado conservado)")


if __name__ == "__main__":
    main()