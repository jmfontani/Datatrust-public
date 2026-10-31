#!/usr/bin/env python3
"""
137_medir_discrepancia_embeddings.py — mide cuanto cambia el recalculo (Fase D).

POR QUE
El plan dice que hay fichas cuyo vector no se reproduce desde la BD. Antes de
gastar tiempo recalculando 94.461 vectores, hay que CUANTIFICAR el cambio:

  1. similitud coseno entre el vector guardado y el recalculado
  2. si el recalculo cambia el RANKING de la propia ficha (se busca su titulo
     y se ve en que puesto queda antes y despues)

Si 1 es ~1.0 y 2 no cambia, la Fase D es higiene, no mejora. Si no, es un bug
que afecta a la linea base.

USO
  python3 137_medir_discrepancia_embeddings.py --muestra 400
"""
import argparse
import json
import os
import sys

import numpy as np
import psycopg2
from psycopg2.extras import DictCursor

DB = dict(host=os.environ.get("DB_HOST", "buscador_postgres"),
          port=int(os.environ.get("DB_PORT", 5432)),
          dbname=os.environ.get("DB_NAME", "buscador"),
          user=os.environ.get("DB_USER", "postgres"),
          password=os.environ.get("DB_PASSWORD", "postgres"))

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"

# el MISMO texto que usa generate_embeddings_pg.py
SQL_TEXTO = """
    SELECT dataset_id, title, description, keywords, theme_label, territory_label,
           COALESCE(title,'') || ' ' || COALESCE(description,'') || ' ' ||
           COALESCE(array_to_string(keywords,' '),'') || ' ' ||
           COALESCE(theme_label,'') || ' ' || COALESCE(territory_label,'') AS texto,
           embedding::text AS emb_guardado
    FROM datasets
    WHERE embedding IS NOT NULL
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=400)
    ap.add_argument("--salida", default="../entregables/discrepancia_embeddings.json")
    args = ap.parse_args()

    from sentence_transformers import SentenceTransformer
    print(f"  cargando {MODEL_NAME}@{MODEL_REVISION[:8]}...", flush=True)
    modelo = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)
    print(f"  max_seq_length efectivo: {modelo.max_seq_length}", flush=True)

    conn = psycopg2.connect(**DB)
    with conn.cursor(cursor_factory=DictCursor) as cur:
        # muestra estratificada por longitud del texto
        cur.execute(SQL_TEXTO + " AND length(COALESCE(description,'')) < 80 "
                                " ORDER BY random() LIMIT %s", (args.muestra // 4,))
        cortas = cur.fetchall()
        cur.execute(SQL_TEXTO + " AND length(COALESCE(description,'')) BETWEEN 80 AND 300 "
                                " ORDER BY random() LIMIT %s", (args.muestra // 4,))
        medias = cur.fetchall()
        cur.execute(SQL_TEXTO + " AND length(COALESCE(description,'')) > 300 "
                                " ORDER BY random() LIMIT %s", (args.muestra // 4,))
        largas = cur.fetchall()
        cur.execute(SQL_TEXTO + " AND length(COALESCE(title,'')||' '||COALESCE(description,'')||' '||"
                                " COALESCE(array_to_string(keywords,' '),'')) > 900 "
                                " ORDER BY random() LIMIT %s", (args.muestra // 4,))
        muy_largas = cur.fetchall()

    filas = cortas + medias + largas + muy_largas
    print(f"  muestra: {len(filas)} fichas "
          f"({len(cortas)} cortas, {len(medias)} medias, {len(largas)} largas, "
          f"{len(muy_largas)} muy largas)", flush=True)

    textos = [f["texto"] for f in filas]
    print("  recalculando...", flush=True)
    nuevos = modelo.encode(textos, batch_size=64, normalize_embeddings=True,
                           show_progress_bar=False, convert_to_numpy=True)

    def parse(v):
        return np.array(json.loads(v), dtype=np.float32)

    grupos = {"cortas (<80)": cortas, "medias (80-300)": medias,
              "largas (>300)": largas, "muy largas (texto>900)": muy_largas}
    res = {}
    print()
    print(f"  {'grupo':22} {'coseno medio':>13} {'min':>7} {'<0.999':>8} {'<0.99':>7}")
    print(f"  {'-'*22} {'-'*13} {'-'*7} {'-'*8} {'-'*7}")
    detalle = []
    for i, (nom, g) in enumerate(grupos.items()):
        sims = []
        for j, f in enumerate(g):
            idx = sum(len(x) for x in list(grupos.values())[:i]) + j
            ant = parse(f["emb_guardado"])
            nue = nuevos[idx]
            na, nn = np.linalg.norm(ant), np.linalg.norm(nue)
            if na > 0 and nn > 0:
                sims.append(float(np.dot(ant, nue) / (na * nn)))
            detalle.append({"dataset_id": f["dataset_id"], "grupo": nom,
                            "len_texto": len(f["texto"]),
                            "sim_guardado_vs_recalculado": round(sims[-1], 6)})
        if sims:
            a = np.array(sims)
            res[nom] = {"n": len(a), "coseno_medio": round(float(a.mean()), 6),
                        "coseno_min": round(float(a.min()), 6),
                        "frac_bajo_0999": round(float((a < 0.999).mean()), 4),
                        "frac_bajo_099": round(float((a < 0.99).mean()), 4)}
            print(f"  {nom:22} {a.mean():13.6f} {a.min():7.4f} "
                  f"{(a<0.999).mean():8.1%} {(a<0.99).mean():7.1%}")

    todos = [d["sim_guardado_vs_recalculado"] for d in detalle]
    a = np.array(todos)
    print()
    print(f"  GLOBAL: coseno medio {a.mean():.6f} · min {a.min():.6f} · "
          f"{(a<0.999).mean():.1%} por debajo de 0.999")

    salida = {"modelo": MODEL_NAME, "revision": MODEL_REVISION,
              "muestra": len(filas), "por_grupo": res,
              "global": {"coseno_medio": round(float(a.mean()), 6),
                         "coseno_min": round(float(a.min()), 6),
                         "n_no_reproducen_0999": int((a < 0.999).sum()),
                         "n_no_reproducen_099": int((a < 0.99).sum())},
              "detalle": detalle}
    with open(args.salida, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=1)
    print(f"\n  guardado: {args.salida}")


if __name__ == "__main__":
    main()
