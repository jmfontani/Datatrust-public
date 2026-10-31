#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sniff_download.py
=================
Descubre el formato real de las distribuciones "sin formato" (datasets sin
ninguna distribución tabular declarada) y descarga las que resulten ser
tabulares (CSV/JSON/XLSX/XLS/TXT/ODS), incluyendo **descompresión de ZIPs**
cuando contienen un fichero tabular.

Flujo por candidato:
  GET stream -> leer Content-Type + magic bytes -> clasificar:
    - XLSX/ODS/ZIP (PK\\x03\\x04) -> descargar zip (<=zip_cap) y buscar entrada
      .csv/.json/.xlsx/.xls/.txt/.ods -> extraerla. Si no hay -> ZIP_NO_DATA.
    - XLS (OLE2 \\xD0\\xCF\\x11\\xE0) -> descargar.
    - JSON (empieza { o [) -> descargar.
    - HTML (<html/<!doctype) -> HTML.
    - PDF (%PDF) -> PDF.
    - CSV/TXT (text/* no binario) -> descargar.
    - otro -> UNKNOWN.
  Si tabular -> guardar en ~/datos/<fmt>/<id>.<ext> y done.
  Si no -> probar siguiente candidato; si ninguno -> no_tabular con reasons.

Uso:
  venv/bin/python sniff_download.py                       # todo
  venv/bin/python sniff_download.py --limit 200 --shuffle  # muestra
"""
from __future__ import annotations
import argparse, csv, io, json, os, queue, random, re, threading, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urlparse

import requests

UA = ("Mozilla/5.0 (compatible; TFM-Buscador-Semantico/1.0; academic sniff)")
CONNECT_TIMEOUT = int(os.environ.get("SNIFF_CONNECT_TIMEOUT", "15"))
READ_TIMEOUT = int(os.environ.get("SNIFF_READ_TIMEOUT", "20"))
CHUNK = 64 * 1024
ZIP_CAP = 50 * 1024 * 1024   # límite para intentar descomprimir un zip
FILE_CAP = 100 * 1024 * 1024
EXT = {"CSV": "csv", "JSON": "json", "XLSX": "xlsx", "XLS": "xls", "TXT": "txt", "ODS": "ods"}
TAB = set(EXT)

COLS = ["dataset_id", "identifier", "publisher_name", "host", "candidates",
        "status", "chosen_format", "http_status", "content_type",
        "saved_bytes", "attempts", "reason", "error", "ts"]

_host_lock = threading.Lock()
_host_sems: dict[str, threading.Semaphore] = {}
_fail_lock = threading.Lock()
_host_fails: dict[str, int] = {}     # contador de fallos por host
_dead_hosts: set[str] = set()        # hosts confirmados caídos (>= umbral fallos)
DEAD_THRESHOLD = 8                  # fallos antes de marcar un host como muerto


def get_host_sem(host, per_host):
    with _host_lock:
        if host not in _host_sems:
            _host_sems[host] = threading.Semaphore(per_host)
        return _host_sems[host]


def register_host_fail(host, threshold=DEAD_THRESHOLD):
    """Cuenta un fallo de host; si alcanza `threshold` lo marca muerto.
    Un host responsive con fallos puntuales nunca llega al umbral; uno caído
    acumula fallos rápido y se marca para saltar el resto."""
    if not host:
        return
    with _fail_lock:
        _host_fails[host] = _host_fails.get(host, 0) + 1
        if _host_fails[host] >= threshold:
            _dead_hosts.add(host)
            return True
    return False


def is_host_dead(host):
    if not host:
        return False
    with _fail_lock:
        return host in _dead_hosts


def safe_name(ident):
    if not ident:
        return "unnamed"
    import hashlib
    s = re.sub(r'[^A-Za-z0-9._-]', '_', ident).strip("._") or "unnamed"
    return s[:140] + "_" + hashlib.md5(ident.encode()).hexdigest()[:10] if len(s) > 150 else s


def out_path_for(dest, fmt, ident):
    return os.path.join(dest, fmt.lower(), f"{safe_name(ident)}.{EXT[fmt]}")


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def classify(head: bytes, ctype: str) -> str:
    """Devuelve CSV/JSON/XLSX/XLS/TXT/ODS o HTML/ZIP/PDF/XML/UNKNOWN."""
    ct = (ctype or "").lower()
    h = head or b""
    if h[:4] == b"PK\x03\x04":
        return "ZIP"
    if h[:4] == b"\xd0\xcf\x11\xe0":
        return "XLS"
    if h[:4] == b"%pdf":
        return "PDF"
    low = h[:64].lstrip().lower()
    if low.startswith(b"<!doctype html") or low.startswith(b"<html") or low.startswith(b"<head"):
        return "HTML"
    stripped = h.lstrip()
    if stripped[:1] in (b"{", b"["):
        return "JSON"
    # XML (puede ser datos estructurados, pero no tabular garantizado) -> lo
    # tratamos como no-tabular salvo que content-type diga csv
    if low.startswith(b"<?xml"):
        return "XML"
    # CSV/TXT: text/* y no binario
    if "csv" in ct:
        return "CSV"
    if "json" in ct:
        return "JSON"
    if "excel" in ct or "spreadsheet" in ct:
        # ofimático ya cubierto por magic; por si acaso
        return "UNKNOWN"
    if ct.startswith("text/plain") or ct.startswith("text/csv") or ct == "":
        # heurística: si hay comas/separadores -> CSV; si no -> TXT
        if b"," in h[:512] or b";" in h[:512] or b"\t" in h[:512]:
            return "CSV"
        # si es texto plano legible
        try:
            h[:128].decode("utf-8")
            return "TXT"
        except UnicodeDecodeError:
            return "UNKNOWN"
    return "UNKNOWN"


def try_zip_data(buf: bytes):
    """Si buf es un zip con una entrada tabular, devuelve (fmt, content_bytes).
    Sino None. También detecta XLSX/ODS como tabulares enteros."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(buf))
    except zipfile.BadZipFile:
        return None
    names = zf.namelist()
    # ¿es un xlsx/ods entero? (tiene xl/ o META-INF/manifest.xml)
    if any(n.startswith("xl/") for n in names):
        return ("XLSX", buf)
    if any(n == "META-INF/manifest.xml" for n in names) and any(n.endswith(".ods") or "content.xml" in n for n in names):
        return ("ODS", buf)
    # buscar entrada tabular
    for n in names:
        low = n.lower()
        for fmt, e in EXT.items():
            if low.endswith("." + e):
                try:
                    content = zf.read(n)
                    return (fmt, content)
                except Exception:
                    continue
    return None


def download_candidate(cand, ident, dest, args) -> dict:
    url = cand["url"]
    host = cand.get("host") or urlparse(url).netloc
    sem = get_host_sem(host, args.per_host)
    attempts = 0
    last_reason, last_status, last_ct, last_err = "OTHER", "", "", ""
    for attempt in range(1, args.max_attempts + 1):
        attempts = attempt
        with sem:
            try:
                with requests.get(url, stream=True, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                                   headers={"User-Agent": UA, "Accept": "*/*"},
                                   allow_redirects=True) as r:
                    sc = r.status_code
                    last_status = str(sc)
                    last_ct = r.headers.get("Content-Type", "")
                    if sc == 429:
                        last_reason = "HTTP_429"; last_err = "429"
                        if attempt < args.max_attempts:
                            time.sleep(min(int(r.headers.get("Retry-After", "5")), 30))
                            continue
                        return {"status": "no_tabular", "reason": last_reason,
                                "http_status": last_status, "content_type": last_ct,
                                "attempts": attempts, "error": last_err}
                    if 400 <= sc < 500:
                        return {"status": "no_tabular", "reason": "HTTP_4XX",
                                "http_status": last_status, "content_type": last_ct,
                                "attempts": attempts, "error": f"HTTP {sc}"}
                    if 500 <= sc < 600:
                        last_reason = "HTTP_5XX"; last_err = f"HTTP {sc}"
                        if attempt < args.max_attempts:
                            time.sleep(2 ** attempt); continue
                        return {"status": "no_tabular", "reason": last_reason,
                                "http_status": last_status, "content_type": last_ct,
                                "attempts": attempts, "error": last_err}
                    if sc != 200:
                        last_reason = "OTHER"; last_err = f"HTTP {sc}"
                        if attempt < args.max_attempts:
                            time.sleep(2 ** attempt); continue
                        return {"status": "no_tabular", "reason": last_reason,
                                "http_status": last_status, "content_type": last_ct,
                                "attempts": attempts, "error": last_err}
                    # leer primero hasta 16 bytes para clasificar
                    it = r.iter_content(CHUNK)
                    try:
                        first = next(it)
                    except StopIteration:
                        first = b""
                    if not first:
                        return {"status": "no_tabular", "reason": "EMPTY",
                                "http_status": last_status, "content_type": last_ct,
                                "attempts": attempts, "error": "empty body"}
                    kind = classify(first, last_ct)
                    # --- tabular directo ---
                    if kind in ("CSV", "JSON", "TXT", "XLS"):
                        out = out_path_for(dest, kind, ident)
                        os.makedirs(os.path.dirname(out), exist_ok=True)
                        total = len(first)
                        with open(out + ".part", "wb") as f:
                            f.write(first)
                            try:
                                for chunk in it:
                                    total += len(chunk)
                                    if total > FILE_CAP:
                                        f.close(); os.remove(out + ".part")
                                        return {"status": "no_tabular", "reason": "OVERSIZE",
                                                "http_status": last_status, "content_type": last_ct,
                                                "attempts": attempts, "error": f">{FILE_CAP}"}
                                    f.write(chunk)
                            except OSError as e:
                                f.close(); os.remove(out + ".part")
                                return {"status": "no_tabular", "reason": "IO",
                                        "http_status": last_status, "content_type": last_ct,
                                        "attempts": attempts, "error": str(e)[:120]}
                        os.replace(out + ".part", out)
                        return {"status": "done", "chosen_format": kind,
                                "http_status": last_status, "content_type": last_ct,
                                "saved_bytes": total, "attempts": attempts,
                                "reason": "", "error": ""}
                    # --- ZIP: descargar y buscar entrada tabular ---
                    if kind == "ZIP":
                        buf = bytearray(first)
                        over = False
                        for chunk in it:
                            buf += chunk
                            if len(buf) > ZIP_CAP:
                                over = True; break
                        if over:
                            return {"status": "no_tabular", "reason": "ZIP_OVERSIZE",
                                    "http_status": last_status, "content_type": last_ct,
                                    "attempts": attempts, "error": f"zip>{ZIP_CAP}"}
                        res = try_zip_data(bytes(buf))
                        if res:
                            fmt, content = res
                            out = out_path_for(dest, fmt, ident)
                            os.makedirs(os.path.dirname(out), exist_ok=True)
                            with open(out, "wb") as f:
                                f.write(content if isinstance(content, (bytes, bytearray)) else content)
                            return {"status": "done", "chosen_format": fmt,
                                    "http_status": last_status, "content_type": last_ct,
                                    "saved_bytes": len(content), "attempts": attempts,
                                    "reason": "", "error": ""}
                        return {"status": "no_tabular", "reason": "ZIP_NO_DATA",
                                "http_status": last_status, "content_type": last_ct,
                                "attempts": attempts, "error": "zip sin entrada tabular"}
                    # --- no tabular (HTML/PDF/XML/UNKNOWN) ---
                    return {"status": "no_tabular", "reason": kind,
                            "http_status": last_status, "content_type": last_ct,
                            "attempts": attempts, "error": ""}
            except requests.exceptions.Timeout as e:
                last_reason, last_err = "TIMEOUT", str(e)
            except requests.exceptions.ConnectionError as e:
                last_reason, last_err = "CONN_ERROR", str(e)
            except requests.exceptions.RequestException as e:
                last_reason, last_err = "OTHER", str(e)
            except Exception as e:
                # catch-all: un redirect corrupto (latin-1) no debe matar el pase
                last_reason, last_err = "OTHER", f"{type(e).__name__}: {e}"
        if attempt < args.max_attempts:
            time.sleep(2 ** attempt)
    return {"status": "no_tabular", "reason": last_reason,
            "http_status": last_status, "content_type": last_ct,
            "attempts": attempts, "error": (last_err or "")[:120]}


def download_one(row, args):
    cands = json.loads(row["candidates"]) if row.get("candidates") else []
    if not cands:
        return {**row, "status": "no_tabular", "reason": "NO_CANDIDATES", "ts": now()}
    cands = cands[:args.max_candidates]
    # fast-path: si todos los candidatos están en hosts globalmente muertos, saltar
    hosts = [c.get("host") or urlparse(c["url"]).netloc for c in cands]
    if hosts and all(is_host_dead(h) for h in hosts):
        return {**row, "status": "no_tabular", "reason": "ALL_HOSTS_DEAD",
                "chosen_format": "", "http_status": "", "content_type": "",
                "saved_bytes": "", "attempts": 0,
                "error": "todos los hosts candidatos están en cache de muertos",
                "ts": now()}
    dead = {}
    last = None
    for cand in cands:
        host = cand.get("host") or urlparse(cand["url"]).netloc
        if host in dead or is_host_dead(host):
            last = {**row, "status": "no_tabular", "reason": (dead.get(host) or "HOSTDOWN") + "_SKIP",
                    "chosen_format": "", "http_status": "", "content_type": "",
                    "saved_bytes": "", "attempts": 0,
                    "error": f"host {host} caído", "ts": now()}
            continue
        res = download_candidate(cand, row["identifier"], args.dest, args)
        if res["status"] == "done":
            return {**row, **res, "host": host, "ts": now()}
        last = {**row, **res, "host": host, "ts": now()}
        if res["reason"] in ("CONN_ERROR", "TIMEOUT", "HTTP_5XX"):
            dead[host] = res["reason"]
            register_host_fail(host, args.dead_threshold)
    return last if last else {**row, "status": "no_tabular", "reason": "NO_CANDIDATES", "ts": now()}


def save_manifest(path, rows):
    cols = list(rows[0].keys()) if rows else COLS
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)


def save_no_tabular(path, rows):
    nt = [r for r in rows if r.get("status") != "done"]
    cols = ["dataset_id", "identifier", "publisher_name", "host", "reason",
            "http_status", "content_type", "error", "attempts", "ts"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        for r in nt:
            w.writerow({k: r.get(k, "") for k in cols})


def main():
    ap = argparse.ArgumentParser(description="Sniff+descarga de datasets sin formato")
    ap.add_argument("--manifest", default="manifest_sniff.csv")
    ap.add_argument("--progress", default="sniff_progress.jsonl")
    ap.add_argument("--no-tabular", default="sniff_no_tabular.csv")
    ap.add_argument("--dest", default=os.path.expanduser("~/datos/PFM/datos"))
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--per-host", type=int, default=6)
    ap.add_argument("--max-candidates", type=int, default=3)
    ap.add_argument("--max-attempts", type=int, default=2)
    ap.add_argument("--dead-threshold", type=int, default=15,
                    help="Fallos por host antes de marcarlo muerto y saltarlo (default 15)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--shuffle", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if not os.path.exists(args.manifest):
        raise SystemExit(f"❌ No existe {args.manifest} (ejecuta build_sniff_manifest.py)")
    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))
    pending = [r for r in rows if r.get("status") == "pending"]
    if args.shuffle:
        random.Random(args.seed).shuffle(pending)
    if args.limit > 0:
        pending = pending[:args.limit]
    print(f"Pendientes a sniffear: {len(pending)} | workers={args.workers} "
          f"per-host={args.per_host} max-cands={args.max_candidates}")
    if not pending:
        save_no_tabular(args.no_tabular, rows); return

    idx = {r["dataset_id"]: i for i, r in enumerate(rows)}
    pq: queue.Queue = queue.Queue()
    cnt = [0, 0, 0]  # done, no_tabular, total
    plock = threading.Lock()

    def worker(r):
        res = download_one(r, args); pq.put(res); return res

    stop = threading.Event()

    def writer():
        with open(args.progress, "a", encoding="utf-8") as fh:
            while not (stop.is_set() and pq.empty()):
                try:
                    res = pq.get(timeout=0.5)
                except queue.Empty:
                    continue
                fh.write(json.dumps(res, ensure_ascii=False) + "\n"); fh.flush()
                cnt[2] += 1
                if res.get("status") == "done":
                    cnt[0] += 1
                else:
                    cnt[1] += 1
                if cnt[2] % 500 == 0:
                    with plock:
                        print(f"  …{cnt[2]} sniff | done={cnt[0]} no_tabular={cnt[1]}")
    wt = threading.Thread(target=writer, daemon=True); wt.start()
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(worker, r) for r in pending]
        for fut in as_completed(futs):
            res = fut.result()
            i = idx[res["dataset_id"]]
            rows[i].update({k: res.get(k, "") for k in
                            ("status", "chosen_format", "http_status", "content_type",
                             "saved_bytes", "attempts", "reason", "error", "ts")})
    stop.set(); wt.join(timeout=5)
    elapsed = time.time() - t0
    save_manifest(args.manifest, rows)
    save_no_tabular(args.no_tabular, rows)
    from collections import Counter
    by_reason = Counter(r.get("reason") for r in rows if r.get("status") == "no_tabular")
    by_fmt = Counter(r.get("chosen_format") for r in rows if r.get("status") == "done")
    total_bytes = sum(int(r.get("saved_bytes") or 0) for r in rows if r.get("status") == "done")
    print("\n" + "=" * 60)
    print(f"Sniff resumen (elapsed {elapsed:.0f}s):")
    print(f"  done (tabulares descubiertos) : {cnt[0]}")
    print(f"  no_tabular                     : {cnt[1]}")
    print(f"  bytes descubiertos             : {total_bytes/1e9:.2f} GB")
    print("  done por formato:")
    for k, v in by_fmt.most_common():
        print(f"    {k:5s}: {v}")
    print("  no_tabular por reason:")
    for k, v in by_reason.most_common():
        print(f"    {k:14s}: {v}")
    print("=" * 60)
    print(f"✅ {args.manifest} actualizado | no_tabular: {args.no_tabular}")


if __name__ == "__main__":
    main()