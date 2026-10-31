#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_manifest.py
=================
Construye el manifiesto de descarga a partir de los raw .jsonl de la ingesta
de datos.gob.es.

Para cada dataset (dedup por `identifier`) elige UNA sola distribución tabular
priorizando el formato más sencillo de procesar: CSV > JSON > XLSX > XLS > TXT.
Descarta los datasets sin ninguna distribución tabular y los ficheros cuyo
`byte_size` declarado supere el cap (cola patológica).

Salida: manifest.csv con una fila por dataset a descargar (status=pending).
"""
from __future__ import annotations
import argparse
import csv
import glob
import hashlib
import json
import os
import re
import sys
from collections import Counter
from urllib.parse import urlparse

# Prioridad de formato tabular: mayor = más sencillo de procesar.
PRIORIDAD = {"CSV": 5, "JSON": 4, "XLSX": 3, "XLS": 2, "TXT": 1}
EXT = {"CSV": "csv", "JSON": "json", "XLSX": "xlsx", "XLS": "xls", "TXT": "txt"}

CAP_DEFAULT_MB = 100


def safe_name(ident: str) -> str:
    """Sanea un identifier a nombre de fichero válido en exFAT/Windows:
    descarta ': / \\ * ? " < > |' y similares; recorta y añade hash si es muy largo."""
    if not ident:
        return "unnamed"
    s = re.sub(r'[^A-Za-z0-9._-]', '_', ident).strip("._")
    if not s:
        s = "unnamed"
    if len(s) > 150:
        s = s[:140] + "_" + hashlib.md5(ident.encode("utf-8")).hexdigest()[:10]
    return s


def normalizar_formato(dist: dict) -> str:
    """Devuelve el formato normalizado (CSV/JSON/...) o '' si no es tabular."""
    f = (dist.get("format") or "").strip()
    # el campo format suele venir como URI de authority: .../file-type/CSV
    if "/" in f:
        f = f.rsplit("/", 1)[-1]
    f = f.upper()
    if f in PRIORIDAD:
        return f
    # heurística por extensión en access_url si format vacío o raro
    if f == "" or f not in PRIORIDAD:
        u = (dist.get("access_url") or "").lower().split("?", 1)[0]
        # mirar extensión final
        for ext in ("csv", "json", "xlsx", "xls", "txt"):
            if u.endswith("." + ext) or ("/" + ext + "/") in u or ("." + ext + ".") in u:
                return ext.upper()
    return ""


def elegir_distribucion(distributions: list, cap_bytes: int):
    """Elige la distribución tabular de mayor prioridad con size <= cap.
    Devuelve (formato, dist) o (None, None)."""
    cands = []
    for dist in distributions or []:
        f = normalizar_formato(dist)
        if f == "":
            continue
        bs = dist.get("byte_size")
        try:
            bs = int(bs) if bs not in (None, "") else None
        except (ValueError, TypeError):
            bs = None
        # saltar los que declaran tamaño superior al cap (cola patológica)
        if bs is not None and bs > cap_bytes:
            continue
        cands.append((PRIORIDAD[f], f, dist))
    if not cands:
        return None, None
    cands.sort(key=lambda x: -x[0])  # más fácil primero
    return cands[0][1], cands[0][2]


def main():
    ap = argparse.ArgumentParser(description="Construir manifest.csv de descarga")
    ap.add_argument("--raw-dir", default="../datos/raw",
                    help="Directorio con los .jsonl de la ingesta (default ../datos/raw)")
    ap.add_argument("--out", default="manifest.csv")
    ap.add_argument("--dest", default=os.path.expanduser("~/datos/PFM/datos"),
                    help="Raíz de destino de los ficheros descargados")
    ap.add_argument("--cap-mb", type=float, default=CAP_DEFAULT_MB,
                    help="Cap por fichero en MB (default 100)")
    args = ap.parse_args()

    raw_dir = os.path.abspath(args.raw_dir)
    cap_bytes = int(args.cap_mb * 1024 * 1024)
    files = sorted(glob.glob(os.path.join(raw_dir, "*.jsonl")))
    if not files:
        sys.exit(f"❌ No hay .jsonl en {raw_dir}")

    seen = set()
    n_total = 0
    n_descartados_no_tabular = 0
    n_descartados_cap = 0
    filas = []
    por_formato = Counter()
    hosts = Counter()

    for fn in files:
        with open(fn, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ident = d.get("identifier")
                if not ident or ident in seen:
                    continue
                seen.add(ident)
                n_total += 1

                dists = d.get("distributions") or []
                # contabiliza descartes por cap antes de elegir
                formato_elegido, dist = elegir_distribucion(dists, cap_bytes)
                if formato_elegido is None:
                    # ¿había tabulares pero todos >cap? -> descarte por cap
                    tiene_tabular = any(normalizar_formato(dd) for dd in dists)
                    if tiene_tabular:
                        n_descartados_cap += 1
                    else:
                        n_descartados_no_tabular += 1
                    continue

                url = dist.get("access_url") or ""
                host = urlparse(url).netloc if url else ""
                publisher = (d.get("publisher_name") or "").strip()
                try:
                    ds = int(dist.get("byte_size")) if dist.get("byte_size") not in (None, "") else ""
                except (ValueError, TypeError):
                    ds = ""

                out_path = os.path.join(
                    args.dest, formato_elegido.lower(),
                    f"{safe_name(ident)}.{EXT[formato_elegido]}"
                )

                filas.append({
                    "dataset_id": ident,
                    "identifier": ident,
                    "publisher_name": publisher,
                    "host": host,
                    "access_url": url,
                    "chosen_format": formato_elegido,
                    "declared_size": ds,
                    "out_path": out_path,
                    "status": "pending",
                    "http_status": "",
                    "content_type": "",
                    "saved_bytes": "",
                    "attempts": "",
                    "reason": "",
                    "error": "",
                    "ts": "",
                })
                por_formato[formato_elegido] += 1
                hosts[host] += 1

    cols = ["dataset_id", "identifier", "publisher_name", "host", "access_url",
            "chosen_format", "declared_size", "out_path", "status", "http_status",
            "content_type", "saved_bytes", "attempts", "reason", "error", "ts"]
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(filas)

    total_decl = sum(f["declared_size"] for f in filas if isinstance(f["declared_size"], int))
    print(f"Datasets únicos (identifier): {n_total}")
    print(f"  a descargar (≥1 tabular ≤cap): {len(filas)}")
    print(f"  descartados sin tabular     : {n_descartados_no_tabular}")
    print(f"  descartados por cap {args.cap_mb}MB   : {n_descartados_cap}")
    print("Composición por formato elegido:")
    for f, k in por_formato.most_common():
        print(f"  {f:5s}: {k}")
    print(f"Tamaño declarado acumulado (con byte_size): {total_decl/1e9:.2f} GB")
    print(f"Hosts distintos: {len(hosts)}")
    print(f"Top 8 hosts:")
    for h, k in hosts.most_common(8):
        print(f"  {k:6d}  {h}")
    print(f"\n✅ Manifiesto escrito: {args.out} ({len(filas)} filas pending)")


if __name__ == "__main__":
    main()