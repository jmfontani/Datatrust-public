#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
index_files_to_db.py
====================
Indexa el contenido de los ficheros descargados en la tabla `dataset_files`
(migración 005). Para cada dataset `done` de manifest.csv / manifest_sniff.csv:
  - carga el fichero con pandas (chardet/xlrd/openpyxl/json),
  - extrae esquema (columns + tipos + valores muestra), n_rows, n_columns,
  - extrae content_text (header + muestra, cap 32KB) para el índice léxico,
  - inserta en dataset_files (resumable: solo procesa status=pending),
  - recalcula content_tsvector al final.

Caps: ficheros > --max-full-read-mb (5) → solo esquema (status=schema_only, sin content_text).
Errores por fichero (encoding, JSON corrupto, XLSX dañado) → status=failed + error; no aborta.

Uso:
  venv/bin/python index_files_to_db.py --populate      # pre-poblar filas pending desde manifiestos
  venv/bin/python index_files_to_db.py                 # indexar los pending
  venv/bin/python index_files_to_db.py --limit 50      # muestra
  venv/bin/python index_files_to_db.py --update-tsvector   # solo recalcular tsvector
"""
from __future__ import annotations
import argparse, csv, io, json, os, sys, time, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import psycopg2, psycopg2.extras
import pandas as pd

# ampliar límite de tamaño de campo del csv module (campos >128KB)
csv.field_size_limit(10 * 1024 * 1024)

try:
    import chardet
except ImportError:
    chardet = None

import hashlib, re

DEST = os.path.expanduser("~/datos/PFM/datos")
EXT = {"CSV": "csv", "JSON": "json", "XLSX": "xlsx", "XLS": "xls", "TXT": "txt", "ODS": "ods"}


def safe_name(ident):
    if not ident:
        return "unnamed"
    s = re.sub(r'[^A-Za-z0-9._-]', '_', ident).strip("._") or "unnamed"
    return s[:140] + "_" + hashlib.md5(ident.encode("utf-8")).hexdigest()[:10] if len(s) > 150 else s


def compute_out_path(fmt, ident):
    return os.path.join(DEST, fmt.lower(), f"{safe_name(ident)}.{EXT.get(fmt, 'bin')}")

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "dbname": os.getenv("POSTGRES_DB", "buscador"),
}

CONTENT_CAP = 32 * 1024          # cap de content_text para tsvector
SCHEMA_SAMPLE_ROWS = 100         # nrows para esquema de ficheros grandes
SMALL_FULL_ROWS = 500            # nrows para content_text de ficheros medianos
SAMPLE_VALUES = 5                # valores muestra por columna
INSERT_CHUNK = 500
PER_FILE_TIMEOUT = 90            # s, por fichero (carga lenta/hanging)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def detect_encoding(path):
    if chardet is None:
        return "latin1"
    try:
        with open(path, "rb") as f:
            raw = f.read(8192)
        enc = chardet.detect(raw)["encoding"]
        return enc or "latin1"
    except Exception:
        return "latin1"


def _json_top_keys(head):
    """Extrae claves top de un head JSON (posiblemente truncado) vía regex."""
    return list(dict.fromkeys(re.findall(r'"([A-Za-z0-9_\-\.]+)"\s*:', head)))[:50]


def _clean_val(v):
    """Valor muestra limpio (string corto, sin NaN/None)."""
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        s = str(v)
        return s[:80]
    except Exception:
        return None


def extract_columns(df):
    """Devuelve [{name, dtype, sample_values:[...]}] y n_columns."""
    cols = []
    for c in df.columns:
        try:
            s = df[c].dropna().astype(str).head(SAMPLE_VALUES).tolist()
        except Exception:
            s = []
        cols.append({"name": str(c), "dtype": str(df[c].dtype),
                     "sample_values": [_clean_val(x) for x in s]})
    return cols, len(cols)


def df_to_content_text(df, cap=CONTENT_CAP):
    """Header + muestra de filas como texto, capado."""
    try:
        n = min(len(df), SMALL_FULL_ROWS)
        out = df.head(n).to_csv(index=False, sep="\t")
        if len(out) > cap:
            out = out[:cap]
        return out
    except Exception:
        return None


def _guess_sep(path):
    """Peek primera línea y cuenta delimitadores para elegir sep (evita leer
    el fichero entero que hace sep=None/engine=python)."""
    try:
        with open(path, "rb") as f:
            head = f.read(16384)
        # primera línea no vacía
        for line in head.split(b"\n")[:3]:
            if line.strip():
                first = line
                break
        else:
            return ","
        counts = {b";": first.count(b";"), b",": first.count(b","),
                  b"\t": first.count(b"\t")}
        sep = max(counts, key=counts.get)
        return sep.decode("latin1") if counts[sep] > 0 else ","
    except Exception:
        return ","


def read_csv_robust(path, nrows):
    """Lee CSV/TXT con C engine + sep guess (bounded por nrows, sin leer todo).
    Fallback a python engine con separadores explícitos solo si C falla."""
    enc = detect_encoding(path)
    sep = _guess_sep(path)
    encs = [enc, "latin1", "utf-8"]
    seps = [sep, ";", ",", "\t"]
    last_err = None
    last_empty = None
    for enc_try in encs:
        for s in seps:
            engine = "python" if s in (r"\s+",) else "c"
            try:
                df = pd.read_csv(path, encoding=enc_try, sep=s, engine=engine,
                                 nrows=nrows, on_bad_lines="skip", dtype=str)
                if df is not None and not df.empty:
                    return df
                if df is not None:
                    last_empty = df
            except Exception as e:
                last_err = e
                continue
    if last_empty is not None:
        return last_empty
    return None


def read_excel_bounded(path, fmt, nrows, big_mb):
    """XLSX/XLS/ODS: si >big_mb usa openpyxl read_only (streaming, bounded);
    si no, pandas.read_excel normal."""
    size = os.path.getsize(path)
    engine = {"XLSX": "openpyxl", "XLS": "xlrd", "ODS": "odf"}.get(fmt)
    if size > big_mb * 1024 * 1024 and fmt in ("XLSX",):
        try:
            from openpyxl import load_workbook
            from itertools import islice
            wb = load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
            rows = list(islice(ws.iter_rows(values_only=True), nrows + 1))
            wb.close()
            if not rows:
                return pd.DataFrame()
            header = [str(c) if c is not None else "" for c in rows[0]]
            data = [[str(c) if c is not None else "" for c in r] for r in rows[1:]]
            return pd.DataFrame(data, columns=header)
        except Exception:
            pass  # cae al fallback de pandas
    try:
        return pd.read_excel(path, engine=engine, nrows=nrows, dtype=str)
    except Exception:
        return None


def extract_one(row, max_full_read_mb):
    """Carga el fichero y devuelve dict con campos a insertar (o status=failed)."""
    path = row["file_path"]
    fmt = row["format"]
    size = 0
    try:
        size = os.path.getsize(path)
    except OSError:
        return {"status": "failed", "error": "file not found", "size_bytes": None,
                "n_rows": None, "n_columns": None, "columns": None, "content_text": None}
    big = size > max_full_read_mb * 1024 * 1024

    try:
        if fmt in ("CSV", "TXT"):
            df = read_csv_robust(path, SMALL_FULL_ROWS)
            if df is None:
                return {"status": "failed", "error": "no se pudo parsear (encoding/sep)",
                        "size_bytes": size, "n_rows": None, "n_columns": None,
                        "columns": None, "content_text": None}
            cols, ncol = extract_columns(df)
            n_rows = len(df)
            content = df_to_content_text(df)
        elif fmt == "JSON":
            # JSON grande: NO json.load entero (cuelga); usar head para keys + contenido
            if size > max_full_read_mb * 1024 * 1024:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    head = f.read(CONTENT_CAP)
                cols = [{"name": k, "dtype": "json", "sample_values": []}
                        for k in _json_top_keys(head)]
                ncol = len(cols); n_rows = None
                content = head
            else:
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        data = json.load(f)
                except Exception:
                    # JSON truncado/malformado: head como contenido, keys vía regex
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        head = f.read(CONTENT_CAP)
                    cols = [{"name": k, "dtype": "json", "sample_values": []}
                            for k in _json_top_keys(head)]
                    return {"status": "done", "size_bytes": size, "n_rows": None,
                            "n_columns": len(cols),
                            "columns": json.dumps(cols, ensure_ascii=False) if cols else None,
                            "content_text": head, "error": None}
                if isinstance(data, list):
                    df = pd.json_normalize(data[:SMALL_FULL_ROWS])
                    cols, ncol = extract_columns(df) if not df.empty else ([], 0)
                    n_rows = len(data)
                    content = df_to_content_text(df) if not df.empty else json.dumps(data[:5], ensure_ascii=False, default=str)[:CONTENT_CAP]
                elif isinstance(data, dict):
                    cols = [{"name": k, "dtype": type(v).__name__,
                             "sample_values": [_clean_val(v)]} for k, v in list(data.items())[:50]]
                    ncol = len(cols); n_rows = None
                    content = json.dumps(data, ensure_ascii=False, default=str)[:CONTENT_CAP]
                else:
                    cols, ncol, n_rows, content = [], 0, None, None
        elif fmt in ("XLSX", "XLS", "ODS"):
            df = read_excel_bounded(path, fmt, SMALL_FULL_ROWS, max_full_read_mb)
            if df is None:
                return {"status": "failed", "error": "no se pudo leer excel",
                        "size_bytes": size, "n_rows": None, "n_columns": None,
                        "columns": None, "content_text": None}
            cols, ncol = extract_columns(df)
            n_rows = len(df)
            content = df_to_content_text(df)
        else:
            return {"status": "failed", "error": f"formato no soportado: {fmt}",
                    "size_bytes": size, "n_rows": None, "n_columns": None,
                    "columns": None, "content_text": None}
        return {
            "status": "done",
            "size_bytes": size, "n_rows": n_rows, "n_columns": ncol,
            "columns": json.dumps(cols, ensure_ascii=False) if cols else None,
            "content_text": content, "error": None,
        }
    except Exception as e:
        return {"status": "failed", "error": f"{type(e).__name__}: {str(e)[:200]}",
                "size_bytes": size, "n_rows": None, "n_columns": None,
                "columns": None, "content_text": None}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def populate_pending(manifests):
    """Pre-pobla dataset_files con dataset_id/file_path/format/source status=pending."""
    rows = []
    for path, source in manifests:
        if not os.path.exists(path):
            print(f"⚠️ manifiesto no encontrado: {path}")
            continue
        for r in csv.DictReader(open(path, encoding="utf-8")):
            if r.get("status") != "done":
                continue
            fp = r.get("out_path")
            if not fp:
                # sniff manifest no tiene out_path: computarlo (misma lógica que sniff_download)
                fmt = r.get("chosen_format", "")
                if fmt and fmt.upper() in EXT:
                    fp = compute_out_path(fmt.upper(), r["dataset_id"])
            if not fp:
                continue
            rows.append((r["dataset_id"], fp, r.get("chosen_format", "").upper(), source))
    print(f"Filas done en manifiestos: {len(rows)}")
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO dataset_files (dataset_id, file_path, format, source) "
                "VALUES %s ON CONFLICT (dataset_id) DO NOTHING",
                [(did, fp, fmt, src) for (did, fp, fmt, src) in rows],
                page_size=INSERT_CHUNK,
            )
        n = conn.cursor()
        n.execute("SELECT count(*) FROM dataset_files")
        total = n.fetchone()[0]
    print(f"✅ dataset_files pre-poblada: {total} filas (pending)")
    return total


def fetch_pending(limit, only_format, rebuild_failed):
    conn = get_conn()
    sql = "SELECT dataset_id, file_path, format, source FROM dataset_files WHERE status='pending'"
    if rebuild_failed:
        sql = sql.replace("status='pending'", "status IN ('pending','failed')")
    if only_format:
        sql += f" AND format='{only_format}'"
    if limit:
        sql += f" LIMIT {limit}"
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    conn.close()
    return rows


def update_results(rows_results):
    """Inserta/actualiza resultados en chunks."""
    conn = get_conn()
    n = 0
    with conn:
        with conn.cursor() as cur:
            # actualizar por dataset_id (UPDATE) ya que la fila ya existe (pre-poblada)
            sql = (
                "UPDATE dataset_files SET size_bytes=%s, n_rows=%s, n_columns=%s, "
                "columns=%s::jsonb, content_text=%s, status=%s, error=%s, indexed_at=NOW() "
                "WHERE dataset_id=%s"
            )
            batch = []
            for r in rows_results:
                ct = r["content_text"]
                if ct and "\x00" in ct:
                    ct = ct.replace("\x00", "")
                batch.append((r["size_bytes"], r["n_rows"], r["n_columns"],
                              r["columns"], ct, r["status"],
                              r["error"], r["dataset_id"]))
                if len(batch) >= INSERT_CHUNK:
                    psycopg2.extras.execute_batch(cur, sql, batch, page_size=INSERT_CHUNK)
                    n += len(batch); batch = []
            if batch:
                psycopg2.extras.execute_batch(cur, sql, batch, page_size=INSERT_CHUNK)
                n += len(batch)
    conn.close()
    return n


def update_tsvector():
    conn = get_conn()
    print("Recalculando content_tsvector ...")
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE dataset_files SET content_tsvector = "
                "to_tsvector('spanish', COALESCE(content_text,'')) "
                "WHERE content_text IS NOT NULL AND content_tsvector IS NULL"
            )
            print(f"  tsvector actualizados: {cur.rowcount} filas")
    conn.close()


def main():
    ap = argparse.ArgumentParser(description="Indexar ficheros descargados en dataset_files")
    ap.add_argument("--manifest", default="manifest.csv")
    ap.add_argument("--manifest-sniff", default="manifest_sniff.csv")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max-full-read-mb", type=float, default=5)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only-format", default=None)
    ap.add_argument("--populate", action="store_true", help="Solo pre-poblar pending desde manifiestos")
    ap.add_argument("--rebuild-failed", action="store_true", help="Reprocesar también los failed")
    ap.add_argument("--update-tsvector", action="store_true", help="Solo recalcular content_tsvector")
    ap.add_argument("--no-tsvector", action="store_true", help="No recalcular tsvector al final")
    args = ap.parse_args()

    if args.update_tsvector:
        update_tsvector()
        return

    manifests = [(args.manifest, "base"), (args.manifest_sniff, "sniff")]

    if args.populate:
        populate_pending(manifests)
        return

    # pre-poblar si la tabla está vacía
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM dataset_files")
            total = cur.fetchone()[0]
    conn.close()
    if total == 0:
        print("Tabla vacía: pre-poblando desde manifiestos...")
        populate_pending(manifests)

    pending = fetch_pending(args.limit, args.only_format, args.rebuild_failed)
    print(f"Pendientes a indexar: {len(pending)} | workers={args.workers} max-full-read={args.max_full_read_mb}MB")

    if not pending:
        if not args.no_tsvector:
            update_tsvector()
        print("Nada que indexar.")
        return

    from collections import Counter
    cnt = Counter()
    t0 = time.time()
    results_buf = []

    def flush():
        nonlocal results_buf
        if results_buf:
            update_results(results_buf)
            results_buf = []

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut_map = {ex.submit(extract_one, r, args.max_full_read_mb): r for r in pending}
        for i, fut in enumerate(as_completed(fut_map), 1):
            r = fut_map[fut]
            try:
                res = fut.result(timeout=PER_FILE_TIMEOUT)
            except Exception as e:
                res = {"status": "failed", "error": f"timeout/exc: {type(e).__name__}: {str(e)[:120]}",
                       "size_bytes": None, "n_rows": None, "n_columns": None,
                       "columns": None, "content_text": None}
            res["dataset_id"] = r["dataset_id"]
            cnt[res["status"]] += 1
            results_buf.append(res)
            if len(results_buf) >= INSERT_CHUNK:
                flush()
            if i % 500 == 0:
                elapsed = time.time() - t0
                print(f"  …{i}/{len(pending)} | done={cnt['done']} schema_only={cnt['schema_only']} "
                      f"failed={cnt['failed']} | {i/elapsed:.1f}/s")
    flush()
    elapsed = time.time() - t0
    print(f"\nIndexados {sum(cnt.values())} en {elapsed:.0f}s → {dict(cnt)}")

    if not args.no_tsvector:
        update_tsvector()

    # resumen desde la vista
    conn = get_conn()
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM v_dataset_files_summary")
            print("Resumen:", dict(cur.fetchone()))
    conn.close()


if __name__ == "__main__":
    main()