#!/usr/bin/env python3
"""Reconcilia manifest.csv con download_progress.jsonl (resultados del reintento).

Descarga del reintento de hoy (2026-08-27 19:5x/20:xx): los resultados quedaron
en el JSONL pero el manifiesto no llegó a guardarse por el crash latin-1.
Para cada registro de hoy: actualiza status/reason/error/formato en manifest.csv.
"""
import csv
import json

csv.field_size_limit(10 * 1024 * 1024)

prog = [json.loads(l) for l in open("download_progress.jsonl", encoding="utf-8")]
hoy = {r["dataset_id"]: r for r in prog
       if str(r.get("ts", "")).startswith("2026-08-27 19:5")
       or str(r.get("ts", "")).startswith("2026-08-27 20:")}
print(f"registros del reintento: {len(hoy)}")

rows = list(csv.DictReader(open("manifest.csv", encoding="utf-8")))
fieldnames = list(rows[0].keys())
KEYS = ("status", "chosen_format", "http_status", "content_type",
        "saved_bytes", "attempts", "reason", "error", "ts", "out_path")
n_upd = 0
for r in rows:
    p = hoy.pop(r["dataset_id"], None)
    if p:
        for k in KEYS:
            r[k] = p.get(k, "")
        if p.get("out_path"):
            r["out_path"] = p["out_path"]
        n_upd += 1
print(f"actualizados en manifest: {n_upd}; sin correspondencia: {len(hoy)}")

with open("manifest.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(r)

from collections import Counter
c = Counter(r["status"] for r in rows)
print("estado manifest:", dict(c))