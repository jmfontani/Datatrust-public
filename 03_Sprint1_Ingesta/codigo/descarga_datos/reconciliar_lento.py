#!/usr/bin/env python3
"""Reconcilia manifest_lento.csv con sniff_progress_lento.jsonl (crash SIGTERM)."""
import csv
import json

csv.field_size_limit(10 * 1024 * 1024)

prog = [json.loads(l) for l in open("sniff_progress_lento.jsonl", encoding="utf-8")]
hoy = {r["dataset_id"]: r for r in prog if str(r.get("ts", "")).startswith("2026-08-27")}
print(f"registros del pase lento: {len(hoy)}")

rows = list(csv.DictReader(open("manifest_lento.csv", encoding="utf-8")))
fieldnames = list(rows[0].keys())
KEYS = ("status", "chosen_format", "http_status", "content_type",
        "saved_bytes", "attempts", "reason", "error", "ts")
n_upd = 0
for r in rows:
    p = hoy.pop(r["dataset_id"], None)
    if p:
        for k in KEYS:
            r[k] = p.get(k, "")
        n_upd += 1
print(f"actualizados en manifest: {n_upd}; sin correspondencia: {len(hoy)}")

with open("manifest_lento.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(r)

from collections import Counter
c = Counter(r["status"] for r in rows)
print("estado manifest_lento:", dict(c))