#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_datasets.py
====================
Descargador resumable y respetuoso de los datasets tabulares listados en
manifest.csv (producido por build_manifest.py).

Características:
  - Reanudable: procesa solo filas status=pending; las done/inaccesible se conservan.
  - Concurrencia ThreadPoolExecutor(workers) con semáforo por host (per-host),
    para no tumbar hosts pequeños con anti-bot.
  - Sniff de Content-Type: descarta HTML landing (reason=HTML_LANDING).
  - Cap en disco por fichero (aborta si supera --cap-mb) -> reason=OVERSIZE.
  - Sniff de magic bytes: valida que el fichero corresponda al formato elegido
    (XLSX=PK.., XLS=OLE2, JSON={/[, CSV/TXT tolerante) -> reason=BADFORMAT si no.
  - Reintentos con backoff exponencial; clasifica la causa (HTTP_4XX/5XX/429,
    TIMEOUT, CONN_ERROR, REDIRECT_LOOP, OTHER).
  - Registro explícito de inaccesibles en inaccesibles.csv.
  - Idempotente: si el fichero ya existe y pasa sniff, marca done sin redescargar.
  - Progreso: una línea JSON por item en download_progress.jsonl (thread-safe).

Uso:
  venv/bin/python download_datasets.py                 # todo pendiente
  venv/bin/python download_datasets.py --limit 300     # muestra
  venv/bin/python download_datasets.py --only-host datos.canarias.es
  venv/bin/python download_datasets.py --retry-inaccessible
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import queue
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urlparse

import requests

UA = ("Mozilla/5.0 (compatible; TFM-Buscador-Semantico/1.0; "
      "+https://github.com/ academic research dataset downloader)")

EXT = {"CSV": "csv", "JSON": "json", "XLSX": "xlsx", "XLS": "xls", "TXT": "txt"}


def safe_name(ident: str) -> str:
    if not ident:
        return "unnamed"
    s = re.sub(r'[^A-Za-z0-9._-]', '_', ident).strip("._")
    if not s:
        s = "unnamed"
    if len(s) > 150:
        s = s[:140] + "_" + hashlib.md5(ident.encode("utf-8")).hexdigest()[:10]
    return s


def compute_out_path(dest: str, chosen: str, ident: str) -> str:
    return os.path.join(dest, chosen.lower(), f"{safe_name(ident)}.{EXT.get(chosen, 'bin')}")


CONNECT_TIMEOUT = 15
READ_TIMEOUT = 300
CHUNK = 64 * 1024
MAX_ATTEMPTS = 3

COLS = ["dataset_id", "identifier", "publisher_name", "host", "access_url",
        "chosen_format", "declared_size", "out_path", "status", "http_status",
        "content_type", "saved_bytes", "attempts", "reason", "error", "ts"]

# ---- Sniff de magic bytes ---------------------------------------------------
def sniff_format(path: str, chosen: str, content_type: str) -> bool:
    """True si el fichero descargado parece coherente con chosen_format."""
    try:
        with open(path, "rb") as f:
            head = f.read(8)
    except OSError:
        return False
    if not head:
        return False
    ct = (content_type or "").lower()
    if chosen in ("XLSX",):
        return head[:4] == b"PK\x03\x04"
    if chosen == "XLS":
        return head[:4] == b"\xd0\xcf\x11\xe0"
    if chosen == "JSON":
        s = head.lstrip()
        return s[:1] in (b"{", b"[")
    if chosen in ("CSV", "TXT"):
        # tolerante: no es HTML ni binario ofimático; aceptamos texto imprimible
        if head[:4] == b"PK\x03\x04" or head[:4] == b"\xd0\xcf\x11\xe0":
            return False
        # rechazar HTML explícito aunque el Content-Type no lo dijera
        low = head[:64].lower()
        if low.startswith(b"<!doctype html") or low.startswith(b"<html"):
            return False
        return True
    return True


# ---- Semáforo por host ------------------------------------------------------
_host_lock = threading.Lock()
_host_sems: dict[str, threading.Semaphore] = {}
_fail_lock = threading.Lock()
_host_fails: dict[str, int] = {}
_dead_hosts: set[str] = set()
DEAD_THRESHOLD = 15


def get_host_sem(host: str, per_host: int) -> threading.Semaphore:
    with _host_lock:
        if host not in _host_sems:
            _host_sems[host] = threading.Semaphore(per_host)
        return _host_sems[host]


def register_host_fail(host, threshold):
    if not host:
        return
    with _fail_lock:
        _host_fails[host] = _host_fails.get(host, 0) + 1
        if _host_fails[host] >= threshold:
            _dead_hosts.add(host)


def is_host_dead(host):
    if not host:
        return False
    with _fail_lock:
        return host in _dead_hosts


# ---- Intento de un único candidato (fmt, url) ------------------------------
def _try_candidate(cand: dict, row: dict, args) -> dict:
    chosen = cand["fmt"]
    out_path = compute_out_path(args.dest, chosen, row["identifier"])
    url = cand["url"]
    host = cand.get("host") or urlparse(url).netloc
    cap_bytes = int(args.cap_mb * 1024 * 1024)

    # Idempotencia: si ya existe y pasa sniff -> done sin redescargar
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        if sniff_format(out_path, chosen, ""):
            return {**row, "chosen_format": chosen, "access_url": url, "host": host,
                    "status": "done", "saved_bytes": os.path.getsize(out_path),
                    "reason": "", "error": "", "http_status": "", "content_type": "",
                    "attempts": 0, "ts": now()}
        try:
            os.remove(out_path)
        except OSError:
            pass

    sem = get_host_sem(host, args.per_host)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    part = out_path + ".part"

    last_err = ""
    last_reason = "OTHER"
    last_status = ""
    last_ct = ""
    attempts = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        attempts = attempt
        with sem:
            try:
                with requests.get(url, stream=True, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                                  headers={"User-Agent": UA, "Accept": "*/*"},
                                  allow_redirects=True) as r:
                    last_status = str(r.status_code)
                    last_ct = r.headers.get("Content-Type", "")
                    ctype = last_ct.lower()
                    # HTML landing
                    if ctype.startswith("text/html"):
                        last_reason = "HTML_LANDING"
                        last_err = f"Content-Type={last_ct}"
                        return _inaccesible(row, last_reason, last_status, last_ct,
                                            attempts, last_err, chosen=chosen, url=url, host=host)
                    # Content-Length > cap
                    cl = r.headers.get("Content-Length")
                    if cl and cl.isdigit() and int(cl) > cap_bytes:
                        last_reason = "OVERSIZE"
                        last_err = f"Content-Length={cl} > cap {cap_bytes}"
                        return _inaccesible(row, last_reason, last_status, last_ct,
                                            attempts, last_err, chosen=chosen, url=url, host=host)
                    if r.status_code == 429:
                        ra = r.headers.get("Retry-After", "5")
                        try:
                            wait = min(int(ra), 30)
                        except ValueError:
                            wait = 5
                        last_reason = "HTTP_429"
                        last_err = "429 Too Many Requests"
                        if attempt < MAX_ATTEMPTS:
                            time.sleep(wait)
                            continue
                        return _inaccesible(row, last_reason, last_status, last_ct,
                                            attempts, last_err, chosen=chosen, url=url, host=host)
                    if 500 <= r.status_code < 600:
                        last_reason = "HTTP_5XX"
                        last_err = f"HTTP {r.status_code}"
                        if attempt < MAX_ATTEMPTS:
                            time.sleep(2 ** attempt)
                            continue
                        return _inaccesible(row, last_reason, last_status, last_ct,
                                            attempts, last_err, chosen=chosen, url=url, host=host)
                    if 400 <= r.status_code < 500:
                        last_reason = "HTTP_4XX"
                        last_err = f"HTTP {r.status_code}"
                        return _inaccesible(row, last_reason, last_status, last_ct,
                                            attempts, last_err, chosen=chosen, url=url, host=host)
                    if r.status_code != 200:
                        last_reason = "OTHER"
                        last_err = f"HTTP {r.status_code}"
                        if attempt < MAX_ATTEMPTS:
                            time.sleep(2 ** attempt)
                            continue
                        return _inaccesible(row, last_reason, last_status, last_ct,
                                            attempts, last_err, chosen=chosen, url=url, host=host)

                    # 200 OK: stream a .part con cap
                    total = 0
                    try:
                        with open(part, "wb") as f:
                            for chunk in r.iter_content(CHUNK):
                                if not chunk:
                                    continue
                                total += len(chunk)
                                if total > cap_bytes:
                                    f.close()
                                    try:
                                        os.remove(part)
                                    except OSError:
                                        pass
                                    return _inaccesible(row, "OVERSIZE", last_status,
                                                        last_ct, attempts,
                                                        f"streamed > cap {cap_bytes}",
                                                        chosen=chosen, url=url, host=host)
                                f.write(chunk)
                    except OSError as e:
                        last_reason = "OTHER"
                        last_err = f"io:{e}"
                        if attempt < MAX_ATTEMPTS:
                            time.sleep(2 ** attempt)
                            continue
                        return _inaccesible(row, last_reason, last_status, last_ct,
                                            attempts, last_err, chosen=chosen, url=url, host=host)
                    if total == 0:
                        try:
                            os.remove(part)
                        except OSError:
                            pass
                        last_reason = "OTHER"
                        last_err = "empty body"
                        if attempt < MAX_ATTEMPTS:
                            continue
                        return _inaccesible(row, last_reason, last_status, last_ct,
                                            attempts, last_err, chosen=chosen, url=url, host=host)
                    # sniff
                    if not sniff_format(part, chosen, last_ct):
                        try:
                            os.replace(part, out_path)
                        except OSError:
                            pass
                        return _inaccesible(row, "BADFORMAT", last_status, last_ct,
                                            attempts, "magic-byte mismatch",
                                            saved_bytes=total, chosen=chosen, url=url, host=host)
                    os.replace(part, out_path)
                    return {**row, "chosen_format": chosen, "access_url": url, "host": host,
                            "status": "done", "http_status": last_status,
                            "content_type": last_ct, "saved_bytes": total,
                            "attempts": attempts, "reason": "", "error": "",
                            "ts": now()}

            except requests.exceptions.Timeout as e:
                last_reason = "TIMEOUT"
                last_err = str(e)
            except requests.exceptions.ConnectionError as e:
                last_reason = "CONN_ERROR"
                last_err = str(e)
            except requests.exceptions.TooManyRedirects as e:
                last_reason = "REDIRECT_LOOP"
                last_err = str(e)
            except requests.exceptions.RequestException as e:
                last_reason = "OTHER"
                last_err = str(e)
            except Exception as e:
                # catch-all: un ítem corrupto (p.ej. redirect latin-1) no debe matar el pase
                last_reason = "OTHER"
                last_err = f"{type(e).__name__}: {e}"
        if attempt < MAX_ATTEMPTS:
            time.sleep(2 ** attempt)

    return _inaccesible(row, last_reason, last_status, last_ct, attempts, last_err,
                        chosen=chosen, url=url, host=host)


# ---- Descarga de un item con FALLBACK entre candidatos ---------------------
def download_one(row: dict, args) -> dict:
    # candidates: JSON list de {fmt,url,host,size} ordenado por prioridad
    if row.get("candidates"):
        try:
            candidates = json.loads(row["candidates"])
        except json.JSONDecodeError:
            candidates = []
    else:
        candidates = [{"fmt": row["chosen_format"], "url": row["access_url"],
                        "host": row.get("host", "")}]
    if not candidates:
        return _inaccesible(row, "NO_CANDIDATES", "", "", 0, "sin candidatos tabulares")

    # acota el nº de candidatos a probar (ya ordenados por prioridad CSV>...>TXT)
    candidates = candidates[:args.max_candidates]
    # fast-path: si todos los candidatos están en hosts globalmente muertos, saltar
    cand_hosts = [c.get("host") or urlparse(c["url"]).netloc for c in candidates]
    if cand_hosts and all(is_host_dead(h) for h in cand_hosts):
        return _inaccesible(row, "ALL_HOSTS_DEAD", "", "", 0,
                            "todos los hosts candidatos en cache de muertos",
                            chosen=candidates[0]["fmt"], url=candidates[0]["url"],
                            host=cand_hosts[0])
    dead_hosts = {}  # host -> reason marcado como caído (a nivel de dataset)
    last = None
    for cand in candidates:
        host = cand.get("host") or urlparse(cand["url"]).netloc
        # short-circuit: si este host ya falló como caído (dataset o global), saltar
        if host in dead_hosts or is_host_dead(host):
            last = _inaccesible(row, (dead_hosts.get(host) or "HOSTDOWN") + "_SKIP", "", "", 0,
                                f"host {host} caído, candidato saltado",
                                chosen=cand["fmt"], url=cand["url"], host=host)
            continue
        res = _try_candidate(cand, row, args)
        if res["status"] == "done":
            return res
        last = res
        # si el fallo es de host (caído), marcarlo para no volver a probarlo
        if res.get("reason") in ("CONN_ERROR", "TIMEOUT", "HTTP_5XX"):
            dead_hosts[host] = res["reason"]
            register_host_fail(host, args.dead_threshold)  # cache global con umbral
        # fallos a nivel de recurso (HTML, BADFORMAT, OVERSIZE, 4XX, 429):
        # probar el siguiente candidato (fallback)
    return last if last else _inaccesible(row, "NO_CANDIDATES", "", "", 0, "sin candidatos")


def _inaccesible(row, reason, status, ct, attempts, err, saved_bytes="",
                 chosen=None, url=None, host=None):
    return {**row, "chosen_format": chosen or row.get("chosen_format", ""),
            "access_url": url or row.get("access_url", ""),
            "host": host or row.get("host", ""),
            "status": "inaccesible", "http_status": status,
            "content_type": ct, "saved_bytes": saved_bytes,
            "attempts": attempts, "reason": reason, "error": (err or "")[:200],
            "ts": now()}


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---- IO manifest ------------------------------------------------------------
def load_manifest(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def save_manifest(path: str, rows: list[dict]):
    # fieldnames dinámicos para conservar columnas extra (p.ej. candidates)
    cols = list(rows[0].keys()) if rows else COLS
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def save_inaccesibles(path: str, rows: list[dict]):
    inacc = [r for r in rows if r.get("status") != "done"]
    cols = ["dataset_id", "identifier", "publisher_name", "host", "access_url",
            "chosen_format", "reason", "http_status", "error", "attempts", "ts"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in inacc:
            w.writerow({k: r.get(k, "") for k in cols})


def main():
    ap = argparse.ArgumentParser(description="Descargador de datasets tabulares")
    ap.add_argument("--manifest", default="manifest.csv")
    ap.add_argument("--progress", default="download_progress.jsonl")
    ap.add_argument("--inaccesibles", default="inaccesibles.csv")
    ap.add_argument("--dest", default=os.path.expanduser("~/datos/PFM/datos"))
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--per-host", type=int, default=3)
    ap.add_argument("--cap-mb", type=float, default=100)
    ap.add_argument("--max-candidates", type=int, default=6,
                    help="Máx. candidatos a probar por dataset en el fallback (default 6)")
    ap.add_argument("--dead-threshold", type=int, default=15,
                    help="Fallos por host antes de marcarlo muerto globalmente (default 15)")
    ap.add_argument("--limit", type=int, default=0, help="Máximo nº de items (0=todos)")
    ap.add_argument("--only-host", default=None, help="Procesar solo este host")
    ap.add_argument("--shuffle", action="store_true",
                    help="Aleatoriza el orden de los pending (semilla fija) para muestreo representativo por host")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--retry-inaccessible", action="store_true",
                    help="Reabrir los inaccesibles (lee inaccesibles.csv)")
    ap.add_argument("--reasons", default="",
                    help="Con --retry-inaccessible: solo reabrir inaccesibles cuyo reason "
                         "esté en esta lista (coma-sep.). Útil para aplicar fallback solo a "
                         "fallos de recurso (HTML_LANDING,BADFORMAT,OVERSIZE,HTTP_4XX) y "
                         "saltar hosts caídos (CONN_ERROR,TIMEOUT,HTTP_5XX).")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.manifest):
        sys.exit(f"❌ No existe {args.manifest} (ejecuta build_manifest.py)")

    rows = load_manifest(args.manifest)

    # retry-inaccessible: reabre los de inaccesibles.csv (opcionalmente filtrando reasons)
    if args.retry_inaccessible and os.path.exists(args.inaccesibles):
        reason_filter = None
        if args.reasons:
            reason_filter = set(s.strip().upper() for s in args.reasons.split(",") if s.strip())
        with open(args.inaccesibles, newline="", encoding="utf-8") as fh:
            inacc_map = {r["dataset_id"]: r.get("reason", "") for r in csv.DictReader(fh)}
        inacc_ids = set(inacc_map)
        n_reopen = 0; n_skip_reason = 0
        for r in rows:
            if r["dataset_id"] in inacc_ids and r.get("status") != "done":
                if reason_filter is not None and inacc_map[r["dataset_id"]] not in reason_filter:
                    n_skip_reason += 1
                    continue
                r["status"] = "pending"
                r["reason"] = ""
                r["http_status"] = ""
                r["error"] = ""
                n_reopen += 1
        msg = f"🔁 Reabiertos {n_reopen} inaccesibles para reintento."
        if reason_filter is not None:
            msg += f" (saltados {n_skip_reason} por reason fuera de {sorted(reason_filter)})"
        print(msg)

    pending = [r for r in rows if r.get("status") == "pending"]
    if args.only_host:
        pending = [r for r in pending if r["host"] == args.only_host]
    if args.shuffle:
        random.Random(args.seed).shuffle(pending)
    if args.limit and args.limit > 0:
        pending = pending[:args.limit]

    print(f"Pendientes a procesar: {len(pending)} | workers={args.workers} "
          f"per-host={args.per_host} cap={args.cap_mb}MB")
    if not pending:
        print("Nada que hacer.")
        save_inaccesibles(args.inaccesibles, rows)
        return
    if args.dry_run:
        for r in pending[:10]:
            print(" ", r["dataset_id"], r["chosen_format"], r["host"], r["access_url"][:70])
        return

    # mapeo dataset_id -> índice para actualizar resultados
    idx = {r["dataset_id"]: i for i, r in enumerate(rows)}
    pq: queue.Queue = queue.Queue()
    done_counter = [0]
    inacc_counter = [0]
    print_lock = threading.Lock()

    def worker(r):
        res = download_one(r, args)
        pq.put(res)
        return res

    # hilo escritor de progreso
    stop = threading.Event()

    def progress_writer():
        n = 0
        with open(args.progress, "a", encoding="utf-8") as fh:
            while not (stop.is_set() and pq.empty()):
                try:
                    res = pq.get(timeout=0.5)
                except queue.Empty:
                    continue
                fh.write(json.dumps(res, ensure_ascii=False) + "\n")
                fh.flush()
                n += 1
                if res.get("status") == "done":
                    done_counter[0] += 1
                else:
                    inacc_counter[0] += 1
                if n % 500 == 0:
                    with print_lock:
                        print(f"  …{n} procesados | done={done_counter[0]} "
                              f"inaccesible={inacc_counter[0]}")

    pw = threading.Thread(target=progress_writer, daemon=True)
    pw.start()

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(worker, r) for r in pending]
        for fut in as_completed(futures):
            try:
                res = fut.result()
            except Exception as e:
                print(f"⚠️ worker exception (ignorada): {type(e).__name__}: {e}")
                continue
            i = idx[res["dataset_id"]]
            rows[i].update({k: res.get(k, "") for k in
                            ("status", "http_status", "content_type", "saved_bytes",
                             "attempts", "reason", "error", "ts")})
    stop.set()
    pw.join(timeout=5)

    elapsed = time.time() - t0
    save_manifest(args.manifest, rows)
    save_inaccesibles(args.inaccesibles, rows)

    # resumen
    from collections import Counter
    by_status = Counter(r.get("status") for r in rows)
    by_reason = Counter(r.get("reason") for r in rows if r.get("status") == "inaccesible")
    by_fmt_done = Counter(r.get("chosen_format") for r in rows if r.get("status") == "done")
    by_host_done = Counter(r.get("host") for r in rows if r.get("status") == "done")
    by_host_inacc = Counter(r.get("host") for r in rows if r.get("status") == "inaccesible")
    total_bytes = sum(int(r.get("saved_bytes") or 0) for r in rows if r.get("status") == "done")

    print("\n" + "=" * 60)
    print(f"Resumen (elapsed {elapsed:.0f}s):")
    print(f"  done        : {by_status.get('done',0)}")
    print(f"  inaccesible : {by_status.get('inaccesible',0)}")
    print(f"  pending     : {by_status.get('pending',0)} (no procesados)")
    print(f"  bytes OK    : {total_bytes/1e9:.2f} GB")
    print("  Inaccesibles por reason:")
    for k, v in by_reason.most_common():
        print(f"    {k:14s}: {v}")
    print("  Done por formato:")
    for k, v in by_fmt_done.most_common():
        print(f"    {k:5s}: {v}")
    print("  Top 10 hosts DONE:")
    for k, v in by_host_done.most_common(10):
        print(f"    {v:6d}  {k}")
    print("  Top 10 hosts INACCESIBLE:")
    for k, v in by_host_inacc.most_common(10):
        print(f"    {v:6d}  {k}")
    print("=" * 60)
    print(f"✅ manifest actualizado: {args.manifest}")
    print(f"✅ inaccesibles: {args.inaccesibles}")


if __name__ == "__main__":
    main()