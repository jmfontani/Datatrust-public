#!/usr/bin/env python3
"""
114_reproducibilidad_api.py — ¿es determinista el motor?

Si la misma consulta da rankings distintos en dos ejecuciones, TODAS las
metricas anteriores son ruido y ningun experimento es concluyente. Es la
comprobacion que hay que hacer ANTES de creerse cualquier comparacion.

Se prueba:
  1. la misma consulta, N veces seguidas, con cada configuracion
  2. las 47 consultas del GT, dos pasadas completas
  3. el papel del campo `expanded_query` (la normalizacion conceptual puede
     introducir aleatoriedad si expande distinto cada vez)
"""
import json
import sys
import urllib.request
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
GT = ENTREG / "ground_truth.jsonl"
API = "http://localhost:8000/search"
SALIDA = ENTREG / "reproducibilidad_api.json"

CONFIGS = {
    "actual": {"semantic_weight": 0.7, "lexical_weight": 0.3},
    "lexico": {"semantic_weight": 0.0, "lexical_weight": 1.0},
    "semantico": {"semantic_weight": 1.0, "lexical_weight": 0.0},
}


def busca(query, **kw):
    body = {"query": query, "top_k": 10}
    body.update(kw)
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=90).read())
    except Exception as e:
        return None, None, str(e)
    res = d.get("results") or d.get("datasets") or []
    return ([r.get("dataset_id") for r in res],
            {"expanded": d.get("expanded_query"),
             "concepto": d.get("detected_concept"),
             "norm_activa": d.get("conceptual_normalization_active")},
            None)


def main():
    consultas = [json.loads(l) for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()]
    print("=" * 74)
    print("REPRODUCIBILIDAD DEL MOTOR")
    print("=" * 74)

    informe = {}

    # ---- 1. misma consulta repetida ----
    print("\n### 1. LA MISMA CONSULTA, 5 VECES SEGUIDAS ###\n")
    for nom, kw in CONFIGS.items():
        q = consultas[0]["query"]
        vistos = []
        meta = None
        for _ in range(5):
            ids, m, err = busca(q, **kw)
            vistos.append(tuple(ids or []))
            meta = meta or m
        unicos = len(set(vistos))
        print(f"  {nom:10} rankings distintos en 5 pasadas: {unicos}  "
              f"(n={len(vistos[0])})  {'ESTABLE' if unicos == 1 else '!! INESTABLE'}")
        if nom == "actual" and meta:
            print(f"     expanded_query: {str(meta.get('expanded'))[:100]}")
            print(f"     concepto detectado: {meta.get('concepto')}")
        informe[f"repetida_{nom}"] = {"rankings_distintos": unicos, "n": len(vistos[0])}

    # ---- 2. las 47 consultas, dos pasadas ----
    print("\n### 2. LAS 47 CONSULTAS, DOS PASADAS COMPLETAS ###\n")
    for nom, kw in CONFIGS.items():
        p1, p2 = {}, {}
        vacias = 0
        for q in consultas:
            ids1, _, _ = busca(q["query"], **kw)
            ids2, _, _ = busca(q["query"], **kw)
            p1[q["id"]] = tuple(ids1 or [])
            p2[q["id"]] = tuple(ids2 or [])
            if not ids1:
                vacias += 1
        dif = [qid for qid in p1 if p1[qid] != p2[qid]]
        iguales = sum(1 for a, b in zip(p1.values(), p2.values()) if a == b)
        print(f"  {nom:10} consultas con ranking distinto: {len(dif):>2}/47  "
              f"consultas SIN resultados: {vacias:>2}  "
              f"{'DETERMINISTA' if not dif else '!! NO DETERMINISTA'}")
        if dif:
            for qid in dif[:5]:
                print(f"     {qid}: difieren")
        informe[f"pasadas_{nom}"] = {"distintas": len(dif), "vacias": vacias,
                                     "identicas": iguales}

    # ---- 3. ¿el lexico devuelve vacio a menudo? ----
    print("\n### 3. RESULTADOS VACIOS Y COBERTURA ###\n")
    for nom, kw in CONFIGS.items():
        vacias = 0
        ns = []
        for q in consultas:
            ids, _, _ = busca(q["query"], **kw)
            n = len(ids or [])
            ns.append(n)
            if n == 0:
                vacias += 1
        print(f"  {nom:10} consultas sin ningun resultado: {vacias:>2}/47   "
              f"media de resultados: {sum(ns)/len(ns):.1f}   min {min(ns)} max {max(ns)}")
        informe[f"vacios_{nom}"] = {"vacias": vacias, "media": sum(ns)/len(ns),
                                    "min": min(ns), "max": max(ns)}

    print("\n### CONCLUSION ###\n")
    det = all(informe[f"pasadas_{n}"]["distintas"] == 0 for n in CONFIGS)
    if det:
        print("  El motor ES determinista. Las metricas son comparables y los")
        print("  resultados anteriores son validos.")
    else:
        print("  !! El motor NO es determinista. Las metricas contienen ruido y")
        print("  ninguna comparacion es concluyente hasta resolverlo.")

    SALIDA.write_text(json.dumps({"meta": {"fecha": "auto"}, "informe": informe},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
