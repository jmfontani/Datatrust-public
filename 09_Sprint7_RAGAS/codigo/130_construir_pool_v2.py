#!/usr/bin/env python3
"""
130_construir_pool_v2.py — pool TREC para las 169 consultas nuevas (Fase C, paso 3).

Reutiliza la logica del 108 (union de los tres sistemas, TOP=20) pero para el
conjunto ampliado a 216 consultas.

POR QUE UNION DE SISTEMAS
Es el diseno tipo TREC: el pool se construye con la union de lo que devuelven
TODOS los motores, no solo el que se quiere evaluar. Si el pool se construyera
solo con el motor A, el motor B estaria penalizado por traer documentos que nadie
juzgo. Ya se midio el efecto (script 100): pool sesgado -> cobertura 71 %, y la
conclusion sobre que motor es mejor SALIA INVERTIDA.

El motor lexico es el que mas aporta aqui: en la Fase B traia 338 fichas que los
otros no traian.

SALIDA
entregables/pool_nuevas.json — pares (consulta, ficha) a juzgar, con metadatos
listos para el prompt del juez.
"""
import argparse
import json
import os
import sys
import urllib.request
from collections import Counter
from pathlib import Path

import psycopg2
from psycopg2.extras import DictCursor

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
NUEVAS = ENTREG / "consultas_validadas.jsonl"
ETIQ = ENTREG / "gt_etiquetas_v2.json"
SALIDA = ENTREG / "pool_nuevas.json"

API = "http://localhost:8000/search"
TOP = 20
MAX_DESC = 800
SISTEMAS = {
    "actual": {"semantic_weight": 0.7, "lexical_weight": 0.3},
    "semantico": {"semantic_weight": 1.0, "lexical_weight": 0.0},
    "lexico": {"semantic_weight": 0.0, "lexical_weight": 1.0},
}


def busca(query, **kw):
    body = {"query": query, "top_k": TOP}
    body.update(kw)
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=120).read())
    except Exception as e:
        print(f"     aviso: {e}")
        return []
    return d.get("results") or d.get("datasets") or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", default=str(NUEVAS))
    ap.add_argument("--salida", default=str(SALIDA))
    ap.add_argument("--etiquetas", default=str(ETIQ))
    ap.add_argument("--prefijo-id", default="limp_",
                    help="prefijo para asignar id a las consultas que no lo tengan")
    args = ap.parse_args()

    consultas = [json.loads(l) for l in Path(args.entrada).read_text(encoding="utf-8").splitlines() if l.strip()]
    # asignar id estable a las consultas que no lo traigan
    for i, q in enumerate(consultas, 1):
        if not q.get("id"):
            q["id"] = f"{args.prefijo_id}{i:03d}"
    con_id = sum(1 for q in consultas if q.get("id"))
    etiq = json.loads(Path(args.etiquetas).read_text(encoding="utf-8"))["etiquetas"]
    ya = set(etiq.keys())
    print(f"  entrada: {args.entrada}")
    print(f"  ids asignados: {con_id}/{len(consultas)}")
    print(f"  etiquetas previas: {len(ya)}")

    print("=" * 78)
    print("POOL TREC PARA LAS CONSULTAS NUEVAS")
    print("=" * 78)
    print(f"\n  consultas nuevas : {len(consultas)}")
    print(f"  TOP por sistema  : {TOP}   sistemas: {', '.join(SISTEMAS)}")
    print(f"  ya juzgado       : {len(ya)} pares\n")

    conn = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "postgres"),
                            dbname=os.getenv("POSTGRES_DB", "buscador"),
                            user=os.getenv("POSTGRES_USER", "postgres"),
                            password=os.getenv("POSTGRES_PASSWORD", "postgres"))

    pool = {}
    aporta = Counter()
    solo_lexico = []
    for i, q in enumerate(consultas, 1):
        vistos = {}
        for nom, kw in SISTEMAS.items():
            for rank, r in enumerate(busca(q["query"], **kw), 1):
                did = r.get("dataset_id") or r.get("id")
                if not did:
                    continue
                if did not in vistos:
                    vistos[did] = {"dataset_id": did, "sistemas": [], "ranks": {}}
                vistos[did]["sistemas"].append(nom)
                vistos[did]["ranks"][nom] = rank
                aporta[nom] += 1
        for did, v in vistos.items():
            if v["sistemas"] == ["lexico"]:
                solo_lexico.append((q["id"], did))
        nuevos = {did: v for did, v in vistos.items() if f"{q['id']}|{did}" not in ya}
        for did, v in nuevos.items():
            v.update({"query_id": q["id"], "query": q["query"],
                      "categoria": q["categoria"], "dificultad": q.get("dificultad"),
                      "intencion": q.get("descripcion"),
                      "criterios": q.get("criterios_relevancia")})
        pool[q["id"]] = nuevos
        if i % 25 == 0 or i == len(consultas):
            tot = sum(len(v) for v in pool.values())
            print(f"  [{i:3}/{len(consultas)}] acumulado: {tot} pares sin juicio")

    # metadatos de las fichas
    ids = {d for v in pool.values() for d in v}
    print(f"\n  fichas distintas en el pool: {len(ids)}  -> trayendo metadatos...")
    meta = {}
    lista = list(ids)
    for ini in range(0, len(lista), 5000):
        lote = lista[ini:ini + 5000]
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""SELECT dataset_id, title, description, theme_label,
                                  territory_label FROM datasets
                           WHERE dataset_id = ANY(%s)""", (lote,))
            for r in cur.fetchall():
                meta[r["dataset_id"]] = dict(r)
    conn.close()

    faltan_meta = [d for d in ids if d not in meta]
    for qid, v in pool.items():
        for did in list(v):
            m = meta.get(did)
            if not m:
                del v[did]
                continue
            v[did]["title"] = (m.get("title") or "")[:220]
            v[did]["description"] = (m.get("description") or "")[:MAX_DESC]
            v[did]["theme_label"] = m.get("theme_label") or ""
            v[did]["territory_label"] = m.get("territory_label") or ""

    total = sum(len(v) for v in pool.values())
    print(f"\n### RESUMEN ###\n")
    print(f"  pares a juzgar     : {total}")
    print(f"  consultas con pool : {len([1 for v in pool.values() if v])}")
    print(f"  consultas vacias   : {len([1 for v in pool.values() if not v])}")
    print(f"  fichas sin metadatos (descartadas): {len(faltan_meta)}")
    print(f"  pares ya juzgados (excluidos)     : {sum(1 for v in pool.values() for _ in v) - total + 0}")
    print(f"\n  aportacion por sistema (con repeticiones): {dict(aporta)}")
    print(f"  pares que SOLO trae el lexico: {len(solo_lexico)}")
    if solo_lexico:
        c = Counter(q for q, _ in solo_lexico)
        top = c.most_common(5)
        print(f"     consultas donde mas aporta: {top}")
    print(f"\n  lotes de 10 previstos: {total//10 + len(pool)}")

    Path(args.salida).write_text(json.dumps(pool, ensure_ascii=False), encoding="utf-8")
    print(f"\n  guardado: {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
