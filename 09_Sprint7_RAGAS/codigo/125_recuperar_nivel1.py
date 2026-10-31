#!/usr/bin/env python3
"""
125_recuperar_nivel1.py — rejuzga SOLO las que faltan del rejuicio de nivel 1.

El script 124 dejo 1 lote fallido (medio_005: 8 fichas, 0 rejuzgadas por un fallo
transitorio del endpoint). Aqui se recuperan esas y se fusionan en el mismo
fichero `rejuicio_nivel1.json`, para no dejar hueco en la cobertura.

Idempotente: si se ejecuta dos veces, solo vuelve a pedir las que faltan.
"""
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

import psycopg2
from psycopg2.extras import DictCursor

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
ETIQ = ENTREG / "gt_etiquetas_v2.json"
GT = ENTREG / "ground_truth.jsonl"
REJ = ENTREG / "rejuicio_nivel1.json"

MODELO = "deepseek-v4.1-flash"
LOTE = 10

PROMPT = open(Path(__file__).resolve().parent / "124_rejuzgar_nivel1.py",
              encoding="utf-8").read().split('PROMPT = """')[1].split('"""')[0]


def leer_clave():
    for ruta in (Path.cwd() / ".env",
                 Path(__file__).resolve().parent / ".env"):
        if ruta.exists():
            for ln in ruta.read_text(encoding="utf-8").splitlines():
                if ln.startswith("OLLAMA_API_KEY="):
                    return ln.split("=", 1)[1].strip()
    return os.getenv("OLLAMA_API_KEY")


def juzga(casos, clave):
    lista = []
    for i, c in enumerate(casos, 1):
        lista.append(f'{i}. TITULO: {c["title"][:220]}\n'
                     f'   DESCRIPCION: {(c["description"] or "(sin descripcion)")[:600]}\n'
                     f'   TEMA: {c.get("theme_label") or "-"} | '
                     f'   TERRITORIO: {c.get("territory_label") or "-"}')
    prompt = PROMPT.format(query=casos[0]["_query"],
                           intencion=casos[0].get("_intencion") or "-",
                           lista="\n".join(lista))
    body = json.dumps({"model": MODELO,
                       "messages": [{"role": "user", "content": prompt}],
                       "options": {"temperature": 0}, "stream": False}).encode()
    req = urllib.request.Request("https://ollama.com/api/chat", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {clave}"})
    txt = json.loads(urllib.request.urlopen(req, timeout=300).read())["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("sin JSON")
    out = {}
    for j in json.loads(m.group(0)).get("juicios", []):
        try:
            i, niv = int(j["i"]), int(j["nivel"])
        except (KeyError, TypeError, ValueError):
            continue
        if 1 <= i <= len(casos) and niv in (0, 1, 2):
            out[i - 1] = (niv, str(j.get("razon", ""))[:200])
    return out


def main():
    clave = leer_clave()
    if not clave:
        print("ERROR: falta OLLAMA_API_KEY")
        return 1

    etiq = json.loads(ETIQ.read_text(encoding="utf-8"))["etiquetas"]
    rej = json.loads(REJ.read_text(encoding="utf-8"))
    consultas = {json.loads(l)["id"]: json.loads(l)
                 for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()}

    faltan = [k for k, v in etiq.items() if v == 1 and k not in rej["detalle"]]
    print("=" * 74)
    print("RECUPERACION DEL REJUICIO DE NIVEL 1")
    print("=" * 74)
    print(f"\n  nivel 1 totales : {sum(1 for v in etiq.values() if v == 1)}")
    print(f"  ya rejuzgadas   : {len(rej['detalle'])}")
    print(f"  FALTAN          : {len(faltan)}")
    if not faltan:
        print("\n  nada que recuperar.")
        return 0
    print()

    conn = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "postgres"),
                            dbname=os.getenv("POSTGRES_DB", "buscador"),
                            user=os.getenv("POSTGRES_USER", "postgres"),
                            password=os.getenv("POSTGRES_PASSWORD", "postgres"))
    por_q = {}
    for k in faltan:
        por_q.setdefault(k.split("|")[0], []).append(k.split("|")[1])

    nuevos, fallos = {}, []
    for qi, (qid, ids) in enumerate(sorted(por_q.items()), 1):
        q = consultas[qid]
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""SELECT dataset_id, title, description, theme_label,
                                  territory_label FROM datasets
                           WHERE dataset_id = ANY(%s)""", (ids,))
            meta = {r["dataset_id"]: dict(r) for r in cur.fetchall()}
        fichas = [{"dataset_id": d, "title": meta.get(d, {}).get("title") or "",
                   "description": (meta.get(d, {}).get("description") or "")[:800],
                   "theme_label": meta.get(d, {}).get("theme_label") or "",
                   "territory_label": meta.get(d, {}).get("territory_label") or "",
                   "_query": q["query"], "_intencion": q.get("descripcion")}
                  for d in ids if d in meta]
        ok = 0
        for ini in range(0, len(fichas), LOTE):
            grupo = fichas[ini:ini + LOTE]
            if not grupo:
                continue
            res = None
            for intento in range(3):
                try:
                    res = juzga(grupo, clave)
                    break
                except Exception as e:
                    res = None
                    if intento == 2:
                        fallos.append(f"{qid}: {str(e)[:70]}")
                    time.sleep(3 * (intento + 1))
            if not res:
                continue
            for j, f in enumerate(grupo):
                if j in res:
                    nuevos[f"{qid}|{f['dataset_id']}"] = {"nivel": res[j][0],
                                                          "razon": res[j][1],
                                                          "title": f["title"][:200]}
                    ok += 1
            time.sleep(0.4)
        print(f"  [{qi}/{len(por_q)}] {qid:14} {len(fichas):>2} -> {ok}")
    conn.close()

    rej["detalle"].update(nuevos)
    cnt = Counter(v["nivel"] for v in rej["detalle"].values())
    rej["rejuzgadas"] = len(rej["detalle"])
    rej["siguen_1"] = cnt.get(1, 0)
    rej["suben_a_2"] = cnt.get(2, 0)
    rej["bajan_a_0"] = cnt.get(0, 0)
    rej["fallos"] = rej.get("fallos", []) + fallos
    REJ.write_text(json.dumps(rej, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n### TOTAL TRAS LA RECUPERACION ###\n")
    print(f"  rejuzgadas : {len(rej['detalle'])}")
    print(f"  niveles    : {dict(sorted(cnt.items()))}")
    print(f"  fallos     : {len(fallos)}")
    print(f"\n  actualizado: {REJ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
