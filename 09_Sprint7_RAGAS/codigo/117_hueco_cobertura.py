#!/usr/bin/env python3
"""
117_hueco_cobertura.py — el ranking ya es estable, ¿queda algo sin juzgar?

Al arreglar el bug de top_k el orden cambió, así que hay fichas del top-10 que
pueden no estar juzgadas (y al revés). Mide el hueco para las tres
configuraciones y lo deja listo para juzgar.

Sin esto, la cobertura declarada (98 %) no corresponde al ranking que se mide.
"""
import json
import sys
import urllib.request
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
GT = ENTREG / "ground_truth.jsonl"
ETIQ = ENTREG / "gt_etiquetas_v2.json"
API = "http://localhost:8000/search"
SALIDA = ENTREG / "hueco_tras_bugfix.json"

CONFIGS = {
    "actual": {"semantic_weight": 0.7, "lexical_weight": 0.3},
    "semantico": {"semantic_weight": 1.0, "lexical_weight": 0.0},
    "lexico": {"semantic_weight": 0.0, "lexical_weight": 1.0},
}


def busca(q, **kw):
    b = {"query": q, "top_k": 10}
    b.update(kw)
    r = urllib.request.Request(API, data=json.dumps(b).encode(),
                               headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(r, timeout=90).read())
    return d.get("results") or []


def main():
    consultas = [json.loads(l) for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()]
    etiq = set(json.loads(ETIQ.read_text(encoding="utf-8"))["etiquetas"])

    print("=" * 76)
    print("HUECO DE COBERTURA TRAS EL ARREGLO DEL BUG")
    print("=" * 76)

    informe = {}
    pendientes = {}
    for nom, kw in CONFIGS.items():
        total = sin = 0
        por_q = {}
        for q in consultas:
            for r in busca(q["query"], **kw):
                did = r.get("dataset_id") or r.get("id")
                total += 1
                if f"{q['id']}|{did}" not in etiq:
                    sin += 1
                    por_q.setdefault(q["id"], []).append(did)
        cob = 100 * (total - sin) / total if total else 0
        print(f"\n  {nom:10} top-10 fichas {total:>4}  sin juicio {sin:>3}  cobertura {cob:.1f} %")
        for qid, ids in por_q.items():
            print(f"     [{qid}] {len(ids)}")
        informe[nom] = {"total": total, "sin_juicio": sin, "cobertura": round(cob, 2)}
        pendientes[nom] = por_q

    # union de pendientes (una ficha puede faltar en varias configuraciones)
    union = {}
    for nom, por_q in pendientes.items():
        for qid, ids in por_q.items():
            union.setdefault(qid, set()).update(ids)
    n_union = sum(len(v) for v in union.values())
    print(f"\n### UNION A JUZGAR ###\n")
    print(f"  consultas afectadas: {len(union)}")
    print(f"  pares (consulta, ficha) distintos: {n_union}")
    for qid, ids in sorted(union.items()):
        print(f"     [{qid}] {len(ids)}")

    (ENTREG / "_pendientes_tras_bugfix.json").write_text(
        json.dumps([{"query_id": q, "dataset_id": d} for q, ids in union.items() for d in ids],
                   ensure_ascii=False, indent=1), encoding="utf-8")
    SALIDA.write_text(json.dumps({"informe": informe,
                                  "a_juzgar": {k: sorted(v) for k, v in union.items()}},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
