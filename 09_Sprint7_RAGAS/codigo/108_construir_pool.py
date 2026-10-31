#!/usr/bin/env python3
"""
108_construir_pool.py — FASE B, paso 1.

Construye el POOL que se va a juzgar: la UNION del top-20 de varios sistemas.

Motivo (medido en 100_sesgo_pool.py): el pool de junio cubre solo el 28 % del
top-30 actual, y el motor actual cubre el 71 % de la union de sistemas. Juzgar
solo un motor sesga el GT a su favor: un motor distinto (p.ej. BGE-M3) que
encuentre un documento relevante no encontrado por el actual seria PENALIZADO
por encontrarlo, porque ese documento no estaria juzgado.

El pool incluye una via LEXICA PURA, que no usa embeddings: es la garantia de que
el GT no queda atado a un encoder concreto.

Salida: pool_a_juzgar.json con, por consulta, la lista de fichas a juzgar con su
titulo y descripcion (lo que el juez necesita), marcando cuales YA estan juzgadas.
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import psycopg2
from psycopg2.extras import DictCursor

API = "http://localhost:8000/search"
GT = Path(__file__).resolve().parent.parent / "entregables" / "ground_truth.jsonl"
ETIQ = Path(__file__).resolve().parent.parent / "entregables" / "gt_etiquetas.json"
SALIDA = Path(__file__).resolve().parent.parent / "entregables" / "pool_a_juzgar.json"

TOP = 20
SISTEMAS = {
    "actual": {"semantic_weight": 0.7, "lexical_weight": 0.3},
    "semantico": {"semantic_weight": 1.0, "lexical_weight": 0.0},
    "lexico": {"semantic_weight": 0.0, "lexical_weight": 1.0},
}
# recorte de la descripcion que se le pasa al juez (mantiene el coste bajo)
MAX_DESC = 800


def norm(t):
    return " ".join((t or "").lower().split())


def busca(query, **kw):
    body = {"query": query, "top_k": TOP}
    body.update(kw)
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=90).read())
    except Exception as e:
        print(f"     aviso: {e}")
        return []
    return d.get("results") or d.get("datasets") or []


def main():
    consultas = []
    for ln in GT.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            consultas.append(json.loads(ln))
    etiq = json.loads(ETIQ.read_text(encoding="utf-8"))["etiquetas"]
    ya_juzgado = set(etiq.keys())          # "query_id|dataset_id"

    conn = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "postgres"),
                            dbname=os.getenv("POSTGRES_DB", "buscador"),
                            user=os.getenv("POSTGRES_USER", "postgres"),
                            password=os.getenv("POSTGRES_PASSWORD", "postgres"))

    print("=" * 74)
    print("CONSTRUCCION DEL POOL A JUZGAR (Fase B)")
    print("=" * 74)
    print(f"\n  consultas        : {len(consultas)}")
    print(f"  sistemas en pool : {', '.join(SISTEMAS)}")
    print(f"  top por sistema  : {TOP}")
    print(f"  etiquetas previas: {len(ya_juzgado)}")

    pool = []
    t0 = time.time()
    tot_juzg = tot_sin = 0

    for q in consultas:
        qid = q.get("id")
        vistos = {}     # dataset_id -> datos de la ficha
        aporta = {}     # dataset_id -> set de sistemas que lo traen
        for nom, kw in SISTEMAS.items():
            for r in busca(q["query"], **kw):
                did = r.get("dataset_id") or r.get("id")
                if not did:
                    continue
                aporta.setdefault(did, set()).add(nom)
                if did not in vistos:
                    vistos[did] = {
                        "dataset_id": did,
                        "title": r.get("title") or "",
                        "publisher": r.get("publisher") or "",
                        "format": r.get("format") or "",
                    }

        # traer descripciones (el juez las necesita para decidir)
        ids = list(vistos)
        desc = {}
        if ids:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""SELECT dataset_id, description, theme_label,
                                      territory_label
                               FROM datasets WHERE dataset_id = ANY(%s)""", (ids,))
                for r in cur.fetchall():
                    desc[r["dataset_id"]] = dict(r)

        fichas = []
        for did in ids:
            d = desc.get(did, {})
            juzgada = f"{qid}|{did}" in ya_juzgado
            if juzgada:
                tot_juzg += 1
            else:
                tot_sin += 1
            fichas.append({
                "dataset_id": did,
                "title": vistos[did]["title"],
                "description": (d.get("description") or "")[:MAX_DESC],
                "theme_label": d.get("theme_label") or "",
                "territory_label": d.get("territory_label") or "",
                "sistemas": sorted(aporta.get(did, [])),
                "ya_juzgada": juzgada,
            })
        fichas.sort(key=lambda f: -len(f["sistemas"]))
        pool.append({
            "query_id": qid,
            "query": q["query"],
            "categoria": q.get("categoria"),
            "dificultad": q.get("dificultad"),
            "descripcion_intencion": q.get("descripcion"),
            "n_fichas": len(fichas),
            "n_sin_juzgar": sum(1 for f in fichas if not f["ya_juzgada"]),
            "fichas": fichas,
        })
        print(f"  {qid:14} pool {len(fichas):>3}  sin juzgar {sum(1 for f in fichas if not f['ya_juzgada']):>3}")

    dt = time.time() - t0
    print(f"\n### resumen ({dt:.0f} s) ###\n")
    print(f"  fichas en el pool (con repeticion por consulta): {tot_juzg + tot_sin}")
    print(f"  YA juzgadas   : {tot_juzg} ({100*tot_juzg/max(tot_juzg+tot_sin,1):.0f} %)")
    print(f"  SIN juzgar    : {tot_sin} ({100*tot_sin/max(tot_juzg+tot_sin,1):.0f} %)")

    # analisis del solapamiento entre sistemas
    solo_uno = {}
    for p in pool:
        for f in p["fichas"]:
            if len(f["sistemas"]) == 1:
                solo_uno[f["sistemas"][0]] = solo_uno.get(f["sistemas"][0], 0) + 1
    print(f"\n  fichas que SOLO trae un sistema (justifica el pool union):")
    for k, v in sorted(solo_uno.items(), key=lambda kv: -kv[1]):
        n_sin = sum(1 for p in pool for f in p["fichas"]
                    if f["sistemas"] == [k] and not f["ya_juzgada"])
        print(f"     {k:12} {v:>5} fichas  (de ellas {n_sin} sin juzgar)")

    json.dump({"meta": {
        "fase": "B",
        "sistemas": list(SISTEMAS),
        "top_por_sistema": TOP,
        "generado": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n_consultas": len(consultas),
        "total_fichas": tot_juzg + tot_sin,
        "ya_juzgadas": tot_juzg,
        "sin_juzgar": tot_sin,
        "nota": ("Pool = union del top-20 de 3 sistemas, uno de ellos lexico puro "
                 "(no usa embeddings). Evita el sesgo de pooling medido: sin el, "
                 "un motor distinto seria penalizado por encontrar documentos "
                 "relevantes que el actual no encuentra."),
    }, "pool": pool}, SALIDA.open("w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n  guardado: {SALIDA}")
    print(f"  ({SALIDA.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
