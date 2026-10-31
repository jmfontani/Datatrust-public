#!/usr/bin/env python3
"""
136_materializar_ids.py — fija los ids de las consultas limpias de forma verificable.

POR QUE
El script 130 asigna ids (limp_001...) a las consultas que no los traen, pero solo
DENTRO del pool. El fichero consultas_limpias.jsonl sigue sin ids, asi que el
evaluador (132) no puede cruzarlas con el GT: el GT se indexa por "id|dataset_id".

RIESGO QUE ESTO EVITA
Si se asignaran los ids "por convencion" (mismo orden que el fichero), un solo
cambio de orden futuro desalinearia consultas y juicios EN SILENCIO: el evaluador
daria cifras plausibles y falsas. Por eso aqui los ids NO se eligen: se LEEN del
pool (que es lo que el juez uso) y se CONTRASTA la consulta contra el pool para
comprobar que coinciden. Si alguna no coincide, el script falla.

Idempotente: si el fichero ya tiene ids, los verifica y no toca nada.
"""
import json
import sys
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
LIMPIAS = ENTREG / "consultas_limpias.jsonl"
POOL = ENTREG / "pool_limpias.json"


def main():
    limpias = [json.loads(l) for l in LIMPIAS.read_text(encoding="utf-8").splitlines() if l.strip()]
    pool = json.loads(POOL.read_text(encoding="utf-8"))

    # mapa dataset_id -> consulta segun el POOL (fuente de verdad: lo que juzgo el juez)
    qid_a_query = {}
    for qid, fichas in pool.items():
        for f in fichas.values():
            q = f.get("query")
            if q:
                qid_a_query.setdefault(qid, q)
                break
        if qid not in qid_a_query:
            print(f"  AVISO: {qid} no tiene 'query' en el pool")
    print(f"  consultas en el pool : {len(qid_a_query)}")
    print(f"  consultas en el jsonl: {len(limpias)}")

    # si ya tienen id, verificar y salir
    if all(q.get("id") for q in limpias):
        ok = sum(1 for q in limpias if qid_a_query.get(q["id"]) == q["query"])
        print(f"\n  ya tienen id. coinciden con el pool: {ok}/{len(limpias)}")
        return 0 if ok == len(limpias) else 1

    # construir el mapa texto -> id
    texto_a_id = {}
    for qid, q in qid_a_query.items():
        texto_a_id.setdefault(q.strip().lower(), qid)

    asignados, fallos = 0, []
    for q in limpias:
        if q.get("id"):
            continue
        clave = q["query"].strip().lower()
        qid = texto_a_id.get(clave)
        if not qid:
            fallos.append(q["query"])
            continue
        q["id"] = qid
        asignados += 1

    print(f"\n  ids asignados desde el pool: {asignados}")
    if fallos:
        print(f"  SIN correspondencia en el pool: {len(fallos)}")
        for f in fallos[:10]:
            print(f"     {f}")
        print("\n  ABORTADO: no se escribe nada. Asignar a mano seria inventar la correspondencia.")
        return 1

    LIMPIAS.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in limpias) + "\n",
                       encoding="utf-8")
    print(f"  guardado: {LIMPIAS}")

    # verificacion: todos los ids del pool tienen su consulta en el jsonl
    ids_jsonl = {q["id"] for q in limpias}
    faltan = set(pool) - ids_jsonl
    if faltan:
        print(f"  AVISO: {len(faltan)} ids del pool sin consulta en el jsonl: {sorted(faltan)[:5]}")
    print(f"  verificacion: {len(ids_jsonl & set(pool))}/{len(pool)} ids del pool presentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
