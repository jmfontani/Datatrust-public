#!/usr/bin/env python3
"""Construye el manifiesto del pase lento: reabre los ALL_HOSTS_DEAD del sniff.

Los 17.945 datasets saltados por 'endpoints lentos' (host no respondía en 20s)
se marcan pending en un manifiesto aparte para re-sniffearlos con timeout largo
(SNIFF_READ_TIMEOUT=150) sin tocar el manifiesto original.
"""
import csv

SRC = "manifest_sniff.csv"
DST = "manifest_lento.csv"

csv.field_size_limit(10 * 1024 * 1024)
rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
fieldnames = list(rows[0].keys()) if rows else []
n = 0
for r in rows:
    if r.get("status") == "no_tabular" and r.get("reason") == "ALL_HOSTS_DEAD":
        r["status"] = "pending"
        r["reason"] = ""
        n += 1
with open(DST, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(r)
print(f"Reabiertos {n} de {len(rows)} datasets -> {DST}")