#!/usr/bin/env python3
"""
138_diagnosticar_texto_embeddings.py — con que texto se generaron los vectores guardados?

POR QUE
El 137 muestra que el vector guardado NO se reproduce con el texto del script
actual (coseno medio 0,935; 0,86 en fichas cortas). Eso significa una de dos:

  a) los vectores se generaron con OTRO texto (otra combinacion de campos)
  b) se generaron con OTRO modelo

Antes de recalcular 94.461 vectores hay que saberlo: si es (a), recalcular con el
texto actual CAMBIA el ranking aunque el modelo sea el mismo. Si es (b), la
linea base esta construida con otro modelo del que se cree.

METODO
Se toman fichas discrepantes y se prueba una lista de combinaciones de texto
conocidas. La que devuelva coseno ~1.0 con el guardado es la que se uso.
Si NINGUNA se acerca, se prueba otro modelo.

USO
  python3 138_diagnosticar_texto_embeddings.py --muestra 30
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


def variantes(f):
    """Combinaciones de texto plausibles, la actual la primera."""
    t = (f["title"] or "").strip()
    d = (f["description"] or "").strip()
    k = " ".join(f["keywords"] or []) if f["keywords"] else ""
    th = (f["theme_label"] or "").strip()
    te = (f["territory_label"] or "").strip()
    pub = (f["publisher"] or "").strip()
    sub = (f["subtheme_label"] or "").strip()
    muni = (f["municipality"] or "").strip()
    url = (f["url"] or "").strip()
    return {
        "t+d+k+theme+territory (script actual)": f"{t} {d} {k} {th} {te}",
        "t+d+k+theme+territory+publisher": f"{t} {d} {k} {th} {te} {pub}",
        "t+d": f"{t} {d}",
        "d": d,
        "t": t,
        "t+d+k": f"{t} {d} {k}",
        "d+k": f"{d} {k}",
        "d+t": f"{d} {t}",
        "t: d": f"{t}: {d}",
        "t. d": f"{t}. {d}",
        "t - d": f"{t} - {d}",
        "t+d+theme+subtheme+territory+muni": f"{t} {d} {th} {sub} {te} {muni}",
        "t+d+k+theme+subtheme+territory+muni+publisher": f"{t} {d} {k} {th} {sub} {te} {muni} {pub}",
        "d+url": f"{d} {url}",
        "d + ' ' + t + ' ' + k": f"{d} {t} {k}",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=30)
    ap.add_argument("--salida", default="../entregables/diagnostico_texto_embeddings.json")
    args = ap.parse_args()

    from sentence_transformers import SentenceTransformer
    print(f"  cargando {MODELO}@{REV[:8]}...", flush=True)
    modelo = SentenceTransformer(MODELO, revision=REV)

    conn = psycopg2.connect(**DB)
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("""
            SELECT dataset_id, title, description, keywords, theme_label, territory_label,
                   publisher, subtheme_label, municipality, url, embedding::text AS emb
            FROM datasets
            WHERE embedding IS NOT NULL AND length(COALESCE(description,'')) < 100
            ORDER BY random() LIMIT %s
        """, (args.muestra,))
        filas = cur.fetchall()
    print(f"  muestra: {len(filas)} fichas CORTAS (las mas discrepantes)", flush=True)

    guardados = [np.array(json.loads(f["emb"]), dtype=np.float32) for f in filas]
    guardados = [g / (np.linalg.norm(g) or 1) for g in guardados]

    nombres = list(variantes(filas[0]).keys())
    print()
    print(f"  {'variante de texto':46} {'coseno medio':>12} {'min':>7} {'#exactos':>9}")
    print(f"  {'-'*46} {'-'*12} {'-'*7} {'-'*9}")
    res = {}
    for nom in nombres:
        textos = [variantes(f)[nom] for f in filas]
        embs = modelo.encode(textos, batch_size=64, normalize_embeddings=True,
                             convert_to_numpy=True, show_progress_bar=False)
        sims = [float(np.dot(g, e)) for g, e in zip(guardados, embs)]
        a = np.array(sims)
        n_exactos = int((a > 0.9999).sum())
        res[nom] = {"coseno_medio": round(float(a.mean()), 6),
                    "coseno_min": round(float(a.min()), 6),
                    "n_casi_exactos": n_exactos}
        print(f"  {nom:46} {a.mean():12.6f} {a.min():7.4f} {n_exactos:4d}/{len(a)}")

    mejor = max(res, key=lambda k: res[k]["coseno_medio"])
    print()
    print(f"  MEJOR VARIANTE: {mejor}  ->  {res[mejor]['coseno_medio']:.6f}")
    if res[mejor]["coseno_medio"] > 0.999:
        print("  => los vectores se generaron con ESE texto. El script actual NO lo usa.")
    else:
        print("  => NINGUNA combinacion reproduce el vector guardado:")
        print("     el desajuste NO es de texto (probablemente otro modelo o")
        print("     otra version/codificacion de la ingesta original).")

    with open(args.salida, "w", encoding="utf-8") as fh:
        json.dump({"modelo": MODELO, "revision": REV, "muestra": len(filas),
                   "variantes": res, "mejor": mejor}, fh,
                  ensure_ascii=False, indent=1)
    print(f"\n  guardado: {args.salida}")


if __name__ == "__main__":
    main()
