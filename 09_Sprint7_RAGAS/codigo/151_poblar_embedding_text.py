#!/usr/bin/env python3
"""151_poblar_embedding_text.py — añade y puebla la columna `embedding_text`.

POR QUE
La Fase D cerró con una deuda estructural: los vectores del catálogo NO son
reproducibles desde la BD, porque el texto con el que se generaron (el
`embedding_text` de la limpieza) no se guarda en ninguna columna. Reconstruirlo
desde los campos actuales da coseno 0,923 (5/80 exactos).

La salida del JSONL de limpieza es la única fuente con el texto EXACTO: reproduce
el vector guardado a 0,999979 (39/40 exactos).

QUE HACE
1. Crea la columna `embedding_text TEXT` si no existe (idempotente).
2. Vuelca a un TSV los pares (dataset_id, embedding_text) del JSONL de limpieza
   que existen en la BD.
3. Carga el TSV con `\\copy` de psql (COPY del lado cliente).
4. Verifica: cuántas filas quedan pobladas y cuántas sin texto.

USO
  python3 151_poblar_embedding_text.py            # simula (no escribe)
  python3 151_poblar_embedding_text.py --aplicar  # escribe de verdad
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

B = Path.home() / ("datos/PFM/Datatrust")
JSONL = B / "03_Sprint1_Ingesta/codigo/datos/processed/datasets_clean.jsonl"
TSV = Path.home() / (".el asistente/cache/scratch/embedding_text.tsv")

PSQL = ["psql", "-h", "127.0.0.1", "-p", "5432", "-U", "postgres", "-d", "buscador"]
ENV = {"PGPASSWORD": "postgres"}


def sql(q, t=600):
    import os
    e = dict(os.environ); e.update(ENV)
    r = subprocess.run(PSQL + ["-t", "-A", "-c", q], capture_output=True,
                       text=True, timeout=t, env=e)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:400])
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()

    print("=== 1. estado de partida ===")
    total = int(sql("SELECT count(*) FROM datasets;"))
    print(f"  fichas en BD: {total}")
    existe = int(sql("SELECT count(*) FROM information_schema.columns "
                     "WHERE table_name='datasets' AND column_name='embedding_text';"))
    print(f"  columna embedding_text existe: {'SI' if existe else 'NO'}")

    if not args.aplicar:
        print("\n  (simulación: vuelca el TSV y para)")

    print("\n=== 2. leer el JSONL de limpieza ===")
    dbids = set(x for x in sql("SELECT dataset_id FROM datasets;").splitlines() if x.strip())
    print(f"  dataset_id en BD: {len(dbids)}")

    n_leidos = n_usados = 0
    with JSONL.open(encoding="utf-8") as fh, TSV.open("w", encoding="utf-8") as out:
        for linea in fh:
            if not linea.strip():
                continue
            n_leidos += 1
            d = json.loads(linea)
            did = d.get("identifier")
            txt = d.get("embedding_text") or ""
            if did and did in dbids and txt:
                # TSV: hay que escapar tabuladores y saltos de linea reales
                out.write(did + "\t" + txt.replace("\\", "\\\\")
                          .replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r") + "\n")
                n_usados += 1
    print(f"  leidas del JSONL : {n_leidos}")
    print(f"  escritas al TSV   : {n_usados}")
    print(f"  TSV: {TSV} ({TSV.stat().st_size/1e6:.1f} MB)")

    if not args.aplicar:
        print("\n  Nada escrito en la BD. Repite con --aplicar.")
        return 0

    print("\n=== 3. crear la columna ===")
    if not existe:
        sql("ALTER TABLE datasets ADD COLUMN embedding_text TEXT;")
        print("  columna creada")
    else:
        print("  ya existia")

    print("\n=== 4. cargar el TSV ===")
    # tabla temporal para no tocar la definitiva hasta el UPDATE
    sql("DROP TABLE IF EXISTS _emb_tmp;"
        "CREATE TABLE _emb_tmp (dataset_id TEXT PRIMARY KEY, embedding_text TEXT);")
    import os
    e = dict(os.environ); e.update(ENV)
    r = subprocess.run(PSQL + ["-c", f"\\copy _emb_tmp (dataset_id, embedding_text) "
                                    f"FROM '{TSV}' WITH (FORMAT text)"],
                       capture_output=True, text=True, timeout=1800, env=e)
    if r.returncode != 0:
        print("  ERROR en \\copy:", r.stderr.strip()[:400]); return 1
    print("  cargadas en _emb_tmp:", sql("SELECT count(*) FROM _emb_tmp;"))

    print("\n=== 5. actualizar datasets ===")
    sql("UPDATE datasets d SET embedding_text = t.embedding_text "
        "FROM _emb_tmp t WHERE d.dataset_id = t.dataset_id;", t=1800)
    print("  UPDATE hecho")

    print("\n=== 6. verificar ===")
    pob = int(sql("SELECT count(*) FROM datasets WHERE embedding_text IS NOT NULL;"))
    vac = int(sql("SELECT count(*) FROM datasets WHERE embedding_text IS NULL;"))
    print(f"  con embedding_text: {pob}")
    print(f"  sin embedding_text: {vac}")
    print(f"  cobertura: {pob/total:.1%}")
    sql("DROP TABLE IF EXISTS _emb_tmp;")
    print("  tabla temporal eliminada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
