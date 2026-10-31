#!/usr/bin/env python3
"""
139_verificar_embedding_text_original.py — el vector guardado sale del
`embedding_text` de la limpieza?

CONTEXTO (Fase D)
El 137 midio que el vector guardado NO se reproduce con la concatenacion que usa
`generate_embeddings_pg.py` (coseno medio 0,935; 0,86 en fichas cortas). El 138
descarto 15 combinaciones de campos sin dar con ninguna.

Inspeccionando el repo se encontro que los vectores originales se generaron con
`generate_embeddings.py` (Sprint1), que vectoriza el campo `embedding_text`
construido por `clean_datasets.py`:

    title_es \\n title_en \\n description_es_clean
              \\n Temas: <temas> \\n Palabras clave: <kw> \\n Territorio: <terr>

Es decir: NO es la concatenacion que usa el script pg actual. Este script lo
verifica sobre los vectores realmente guardados en la BD.

Si reproduce (coseno ~1.0), la conclusion para la Fase D es importante:
recalcular con el texto "actual" CAMBIA el ranking aunque el modelo sea el mismo.
Es un cambio de TEXTO, no de modelo.

USO
  python3 139_verificar_embedding_text_original.py --muestra 40
"""
import argparse
import json
import os

import numpy as np
import psycopg2
from psycopg2.extras import DictCursor

DB = dict(host=os.environ.get("DB_HOST", "buscador_postgres"),
          port=int(os.environ.get("DB_PORT", 5432)),
          dbname=os.environ.get("DB_NAME", "buscador"),
          user=os.environ.get("DB_USER", "postgres"),
          password=os.environ.get("DB_PASSWORD", "postgres"))

MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
REV = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=40)
    ap.add_argument("--entrada",
                    default="/codigo/datos/processed/datasets_clean.jsonl")
    ap.add_argument("--salida", default="../entregables/verificacion_embedding_text.json")
    args = ap.parse_args()

    # 1. cargar el embedding_text original
    orig = {}
    with open(args.entrada, encoding="utf-8") as fh:
        for line in fh:
            ds = json.loads(line)
            orig[ds["identifier"]] = ds.get("embedding_text", "")
    print(f"  embedding_text originales: {len(orig)}", flush=True)

    conn = psycopg2.connect(**DB)
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT dataset_id, embedding::text AS emb FROM datasets "
                    " WHERE embedding IS NOT NULL ORDER BY random() LIMIT %s",
                    (args.muestra * 3,))
        filas = cur.fetchall()

    # solo los que tienen embedding_text original
    filas = [f for f in filas if f["dataset_id"] in orig][:args.muestra]
    print(f"  muestra con texto original: {len(filas)}", flush=True)
    if not filas:
        print("  ERROR: ningun dataset_id coincide con el fichero de la limpieza")
        return

    from sentence_transformers import SentenceTransformer
    print(f"  cargando {MODELO}@{REV[:8]}...", flush=True)
    modelo = SentenceTransformer(MODELO, revision=REV)

    textos = [orig[f["dataset_id"]] for f in filas]
    print(f"  longitud media del texto original: "
          f"{np.mean([len(t) for t in textos]):.0f} chars", flush=True)
    embs = modelo.encode(textos, batch_size=32, normalize_embeddings=True,
                         convert_to_numpy=True, show_progress_bar=False)

    sims = []
    for f, e in zip(filas, embs):
        g = np.array(json.loads(f["emb"]), dtype=np.float32)
        g = g / (np.linalg.norm(g) or 1)
        sims.append(float(np.dot(g, e)))
    a = np.array(sims)

    print()
    print(f"  coseno guardado vs recalculado desde embedding_text ORIGINAL:")
    print(f"     media {a.mean():.6f} · min {a.min():.6f} · max {a.max():.6f}")
    print(f"     exactos (>0.9999): {int((a>0.9999).sum())}/{len(a)}")
    print(f"     >0.999:            {int((a>0.999).sum())}/{len(a)}")
    print()
    if a.mean() > 0.999:
        print("  => CONFIRMADO: los vectores se generaron con el embedding_text")
        print("     de la limpieza (Sprint1), NO con la concatenacion del script pg.")
        print("     Recalcular con el texto actual CAMBIA el ranking: es un cambio")
        print("     de TEXTO, no de modelo.")
    else:
        print("  => NO reproduce. El desajuste no es solo de texto.")
    print()
    # comparativa: cuanto se parece el texto nuevo al viejo
    print(f"  (control) los dos textos son distintos:")
    print(f"     ejemplo ORIGINAL   : {repr(textos[0][:110])}")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("""SELECT COALESCE(title,'')||' '||COALESCE(description,'')||' '||
                       COALESCE(array_to_string(keywords,' '),'')||' '||
                       COALESCE(theme_label,'')||' '||COALESCE(territory_label,'')
                       AS nuevo FROM datasets WHERE dataset_id=%s""",
                    (filas[0]["dataset_id"],))
        nuevo = cur.fetchone()["nuevo"]
    print(f"     ejemplo SCRIPT PG  : {repr(nuevo[:110])}")

    with open(args.salida, "w", encoding="utf-8") as fh:
        json.dump({"modelo": MODELO, "revision": REV, "muestra": len(filas),
                   "coseno_medio": round(float(a.mean()), 6),
                   "coseno_min": round(float(a.min()), 6),
                   "n_exactos": int((a > 0.9999).sum()),
                   "confirmado": bool(a.mean() > 0.999)}, fh,
                  ensure_ascii=False, indent=1)
    print(f"\n  guardado: {args.salida}")


if __name__ == "__main__":
    main()
