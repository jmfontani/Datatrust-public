#!/usr/bin/env python3
"""
118_juzgar_pendientes.py — juzga pares (consulta, ficha) que NO están en el pool.

El arreglo del bug de top_k cambió el ranking, así que aparecieron fichas en el
top-10 que nunca entraron al pool (medio_004: 6, dep_003: 3, edu_001: 1,
amb_003: 1). Sin juzgarlas, la cobertura declarada no corresponde al ranking que
se mide.

Reutiliza EXACTAMENTE el prompt canónico de 109_juzgar_pool.py: mezclar
redacciones rompería la comparabilidad (medido: la variante marca 63 % de
relevantes frente al 44 % del canónico).

Lee los pares de _pendientes_tras_bugfix.json, trae sus metadatos de la BD y los
añade a gt_etiquetas_v2.json sin tocar las etiquetas existentes.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

import psycopg2
from psycopg2.extras import DictCursor

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
PEND = ENTREG / "_pendientes_tras_bugfix.json"
GT = ENTREG / "ground_truth.jsonl"
ETIQ = ENTREG / "gt_etiquetas_v2.json"

MODELO = "deepseek-v4.1-flash"
LOTE = 10
MAX_DESC = 800

# --- prompt CANÓNICO: copiado literal de 109_juzgar_pool.py ---
PROMPT = """Eres evaluador de un buscador de datos abiertos espanol. Debes decidir
si cada conjunto de datos RESPONDE a la consulta del usuario.

NIVELES
2 = RESPONDE. Contiene la informacion que pide la consulta: el fenomeno Y el
    ambito (territorio, periodo, desglose) coinciden. Es lo que el usuario
    pondria como respuesta.
1 = TEMA CORRECTO, OTRO ALCANCE. Trata del mismo fenomeno, pero cambia el ambito
    (otra comunidad, otro municipio, otro pais, otro periodo) o el desglose
    (por sexo cuando se pedia por edad). Serviria como contexto, no como respuesta.
0 = NO RESPONDE. Otro fenomeno, o solo comparte alguna palabra del titulo.

CONSULTA DEL USUARIO: {query}
INTENCION DECLARADA: {intencion}

CONJUNTOS A EVALUAR:
{lista}

Responde SOLO con un JSON en una linea, con una entrada por conjunto, en el mismo
orden, usando su numero "i":
{{"juicios": [{{"i": 1, "nivel": 0, "razon": "..."}}, ...]}}
Cada razon: menos de 20 palabras. No anadas texto fuera del JSON."""


def leer_clave():
    for ruta in (Path.cwd() / ".env",
                 Path(__file__).resolve().parent / ".env"):
        if ruta.exists():
            for ln in ruta.read_text(encoding="utf-8").splitlines():
                if ln.startswith("OLLAMA_API_KEY="):
                    return ln.split("=", 1)[1].strip()
    return os.getenv("OLLAMA_API_KEY")


def juzga_lote(casos, clave):
    lista = []
    for i, c in enumerate(casos, 1):
        lista.append(f'{i}. TITULO: {c["title"][:220]}\n'
                     f'   DESCRIPCION: {(c["description"] or "(sin descripcion)")[:600]}\n'
                     f'   TEMA: {c.get("theme_label") or "-"} | '
                     f'TERRITORIO: {c.get("territory_label") or "-"}')
    prompt = PROMPT.format(query=casos[0]["_query"],
                           intencion=casos[0].get("_intencion") or "-",
                           lista="\n".join(lista))
    body = json.dumps({"model": MODELO,
                       "messages": [{"role": "user", "content": prompt}],
                       "options": {"temperature": 0},
                       "stream": False}).encode()
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=None)
    args = ap.parse_args()

    clave = leer_clave()
    if not clave:
        print("ERROR: falta OLLAMA_API_KEY")
        return 1

    pend = json.loads(PEND.read_text(encoding="utf-8"))
    consultas = {json.loads(l)["id"]: json.loads(l)
                 for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()}
    etiq_doc = json.loads(ETIQ.read_text(encoding="utf-8"))
    etiq = etiq_doc["etiquetas"]

    por_q = {}
    for p in pend:
        if f"{p['query_id']}|{p['dataset_id']}" not in etiq:
            por_q.setdefault(p["query_id"], []).append(p["dataset_id"])

    total = sum(len(v) for v in por_q.values())
    print("=" * 74)
    print("JUICIO DE LOS PENDIENTES (post-bugfix) · prompt canonico")
    print("=" * 74)
    print(f"\n  consultas: {len(por_q)}   pares sin juicio: {total}")
    for q, ids in por_q.items():
        print(f"     [{q}] {len(ids)}")
    if not total:
        print("\n  nada pendiente.")
        return 0

    conn = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "postgres"),
                            dbname=os.getenv("POSTGRES_DB", "buscador"),
                            user=os.getenv("POSTGRES_USER", "postgres"),
                            password=os.getenv("POSTGRES_PASSWORD", "postgres"))

    nuevos, fallos = {}, []
    for qi, (qid, ids) in enumerate(por_q.items(), 1):
        q = consultas.get(qid, {})
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""SELECT dataset_id, title, description, theme_label,
                                  territory_label
                           FROM datasets WHERE dataset_id = ANY(%s)""", (ids,))
            meta = {r["dataset_id"]: dict(r) for r in cur.fetchall()}
        fichas = [{"dataset_id": d, "title": (meta.get(d, {}).get("title") or ""),
                   "description": (meta.get(d, {}).get("description") or "")[:MAX_DESC],
                   "theme_label": meta.get(d, {}).get("theme_label") or "",
                   "territory_label": meta.get(d, {}).get("territory_label") or "",
                   "_query": q.get("query", ""), "_intencion": q.get("descripcion")}
                  for d in ids if d in meta]
        print(f"  [{qi}/{len(por_q)}] {qid:14} {len(fichas)}", end=" ")
        ok = 0
        for ini in range(0, len(fichas), LOTE):
            grupo = fichas[ini:ini + LOTE]
            if not grupo:
                continue
            try:
                res = juzga_lote(grupo, clave)
            except Exception as e:
                fallos.append({"query_id": qid, "error": str(e)[:120]})
                print(f"\n     fallo: {str(e)[:60]}")
                continue
            for k, f in enumerate(grupo):
                if k not in res:
                    continue
                niv, raz = res[k]
                nuevos[f"{qid}|{f['dataset_id']}"] = {
                    "nivel": niv, "razon": raz, "title": f["title"][:200],
                    "origen": "bugfix"}
                ok += 1
            time.sleep(0.4)
        print(f"-> {ok} juzgadas")
    conn.close()

    from collections import Counter
    print(f"\n  nuevas etiquetas: {len(nuevos)}")
    print(f"  distribucion    : {dict(sorted(Counter(v['nivel'] for v in nuevos.values()).items()))}")
    print(f"  fallos          : {len(fallos)}")

    if nuevos:
        det = etiq_doc.get("detalle", {})
        for k, v in nuevos.items():
            det[k] = v
            etiq[k] = v["nivel"]
        etiq_doc["etiquetas"] = etiq
        etiq_doc["detalle"] = det
        etiq_doc["meta"]["total"] = len(etiq)
        etiq_doc["meta"]["post_bugfix"] = len(nuevos)
        etiq_doc["meta"].setdefault("nota_bugfix",
            "11 pares anadidos tras corregir el bug de top_k (ranking estable). "
            "Mismo prompt canonico que la Fase B.")
        ETIQ.write_text(json.dumps(etiq_doc, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n  total de etiquetas ahora: {len(etiq)}")
        print(f"  actualizado: {ETIQ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
