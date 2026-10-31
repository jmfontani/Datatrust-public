#!/usr/bin/env python3
"""
121_efecto_ambito_en_etiquetas.py — control CRITICO de la Fase C.

PREGUNTA QUE RESPONDE
El plan asume que se pueden reutilizar las 1.424 etiquetas de las 47 consultas
aunque se reescriba el texto ("Reutilizar el juicio de las 47 actuales: no se
repite el trabajo"). Pero la consulta ES lo que se le muestra al juez. Si anadir
"Espana" cambia el juicio, las etiquetas viejas NO son reutilizables y todo el
trabajo de juicio habria que rehacerlo.

POR QUE HAY QUE MEDIRLO Y NO ASUMIRLO
Es exactamente el error ya cometido dos veces en este proyecto: dar por buena una
propiedad (que el juicio es estable) sin medirla. La medida de robustez al prompt
ya salio MAL (0,780): el juez no es tan estable como parecia.

QUE HACE
Toma una muestra de pares (consulta, ficha) ya etiquetados, los vuelve a juzgar
CON EL TEXTO NUEVO (mismo prompt y misma descripcion) y compara:
  - acuerdo global
  - CAMBIOS PELIGROSOS: 0->2 o 2->0 (de "no responde" a "responde" y al reves).
    Esos son los que romperian las metricas.
  - kappa de Cohen
"""
import argparse
import json
import os
import random
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
V2 = ENTREG / "consultas_v2.jsonl"
SALIDA = ENTREG / "efecto_ambito.json"

MODELO = "deepseek-v4.1-flash"
LOTE = 10

# --- prompt CANONICO, identico al de 109/118 ---
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


def kappa(a, b):
    """kappa de Cohen sobre niveles 0/1/2."""
    if not a:
        return 0.0
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in set(ca) | set(cb)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=90, help="pares a rejuzgar")
    ap.add_argument("--semilla", type=int, default=7)
    args = ap.parse_args()

    clave = leer_clave()
    if not clave:
        print("ERROR: falta OLLAMA_API_KEY")
        return 1

    doc = json.loads(ETIQ.read_text(encoding="utf-8"))
    etiq = doc["etiquetas"]
    det = doc.get("detalle", {})
    consultas = {json.loads(l)["id"]: json.loads(l)
                 for l in V2.read_text(encoding="utf-8").splitlines() if l.strip()}
    orig = {json.loads(l)["id"]: json.loads(l)
            for l in (ENTREG / "ground_truth.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()}

    # solo pares cuya consulta CAMBIO de texto (los demas no aportan nada al test)
    cambiadas = {i for i, q in consultas.items() if q.get("query_original") != q["query"]}
    cand = [(k, v) for k, v in etiq.items() if k.split("|")[0] in cambiadas]
    print("=" * 78)
    print("¿EL AMBITO AÑADIDO CAMBIA EL JUICIO? (control de la Fase C)")
    print("=" * 78)
    print(f"\n  consultas con texto nuevo : {len(cambiadas)}")
    print(f"  pares etiquetados de esas : {len(cand)}")

    random.seed(args.semilla)
    # estratificado: mitad de los que hoy son 0 y mitad de 2/1, para que el test
    # tenga poder sobre los flips peligrosos
    por_nivel = {}
    for k, v in cand:
        por_nivel.setdefault(v, []).append(k)
    muestra = []
    for niv in (0, 1, 2):
        n = max(10, args.n // 3)
        muestra += random.sample(por_nivel.get(niv, []), min(n, len(por_nivel.get(niv, []))))
    random.shuffle(muestra)
    print(f"  muestra                   : {len(muestra)}  "
          f"(estratos {dict(sorted(Counter(etiq[k] for k in muestra).items()))})\n")

    conn = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "postgres"),
                            dbname=os.getenv("POSTGRES_DB", "buscador"),
                            user=os.getenv("POSTGRES_USER", "postgres"),
                            password=os.getenv("POSTGRES_PASSWORD", "postgres"))

    por_q = {}
    for k in muestra:
        qid, did = k.split("|")
        por_q.setdefault(qid, []).append(did)

    nuevos, fallos = {}, []
    for qi, (qid, ids) in enumerate(por_q.items(), 1):
        q, o = consultas[qid], orig[qid]
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""SELECT dataset_id, title, description, theme_label,
                                  territory_label FROM datasets
                           WHERE dataset_id = ANY(%s)""", (ids,))
            meta = {r["dataset_id"]: dict(r) for r in cur.fetchall()}
        fichas = [{"dataset_id": d, "title": meta.get(d, {}).get("title") or "",
                   "description": (meta.get(d, {}).get("description") or "")[:800],
                   "theme_label": meta.get(d, {}).get("theme_label") or "",
                   "territory_label": meta.get(d, {}).get("territory_label") or "",
                   "_query": q["query"], "_intencion": o.get("descripcion")}
                  for d in ids if d in meta]
        print(f"  [{qi}/{len(por_q)}] {qid:14} {len(fichas):>2}  "
              f"«{o['query']}» -> «{q['query']}»")
        for ini in range(0, len(fichas), LOTE):
            grupo = fichas[ini:ini + LOTE]
            if not grupo:
                continue
            try:
                res = juzga_lote(grupo, clave)
            except Exception as e:
                fallos.append(f"{qid}: {str(e)[:80]}")
                continue
            for j, f in enumerate(grupo):
                if j in res:
                    nuevos[f"{qid}|{f['dataset_id']}"] = res[j][0]
            time.sleep(0.4)
    conn.close()

    comunes = [k for k in nuevos if k in etiq]
    a = [etiq[k] for k in comunes]
    b = [nuevos[k] for k in comunes]

    print(f"\n### RESULTADO ###\n")
    print(f"  pares rejuzgados con el texto nuevo: {len(nuevos)}")
    print(f"  comparables                        : {len(comunes)}")
    print(f"  fallos de lote                     : {len(fallos)}")
    if not comunes:
        print("\n  sin datos comparables")
        return 1

    acuerdo = sum(1 for x, y in zip(a, b) if x == y) / len(comunes)
    exacto = acuerdo
    flips = [k for k in comunes
             if {etiq[k], nuevos[k]} == {0, 2}]
    cambios = [k for k in comunes if etiq[k] != nuevos[k]]

    print(f"\n  ACUERDO (mismo nivel)   : {acuerdo:.3f}")
    print(f"  kappa de Cohen          : {kappa(a, b):.3f}")
    print(f"  cambian de nivel        : {len(cambios)}/{len(comunes)} "
          f"({100*len(cambios)/len(comunes):.1f} %)")
    print(f"  CAMBIOS PELIGROSOS 0<->2: {len(flips)}/{len(comunes)} "
          f"({100*len(flips)/len(comunes):.1f} %)")
    print(f"\n  matriz (viejo -> nuevo):")
    print(f"     {'':>7} " + " ".join(f"{n:>6}" for n in (0, 1, 2)))
    for x in (0, 1, 2):
        fila = [sum(1 for k in comunes if etiq[k] == x and nuevos[k] == y) for y in (0, 1, 2)]
        print(f"     {x:>7} " + " ".join(f"{v:>6}" for v in fila))

    if flips:
        print(f"\n  ejemplos de cambio peligroso:")
        for k in flips[:8]:
            qid = k.split("|")[0]
            t = (det.get(k, {}).get("title") or "")[:60]
            print(f"     [{qid}] {etiq[k]} -> {nuevos[k]}  {t}")
            print(f"        antes: {orig[qid]['query']}")
            print(f"        ahora: {consultas[qid]['query']}")

    print(f"\n  Veredicto:")
    if len(flips) / len(comunes) <= 0.05 and acuerdo >= 0.80:
        print("     REUTILIZABLES: el ambito anadido cambia el juicio poco.")
        print("     Las 1.424 etiquetas se conservan, con el hueco de cobertura")
        print("     del ranking nuevo cerrado aparte.")
    else:
        print("     ** NO REUTILIZABLES sin revisar **: el texto nuevo cambia")
        print("     el juicio en una proporcion que afecta a las metricas.")
        print("     Habria que rejuzgar, no reutilizar.")

    SALIDA.write_text(json.dumps({
        "n_muestra": len(muestra), "n_comparables": len(comunes),
        "acuerdo": round(exacto, 4), "kappa": round(kappa(a, b), 4),
        "cambian": len(cambios), "flips_peligrosos": len(flips),
        "matriz": {str(x): {str(y): sum(1 for k in comunes if etiq[k] == x and nuevos[k] == y)
                            for y in (0, 1, 2)} for x in (0, 1, 2)},
        "fallos": fallos,
        "detalle": {k: {"viejo": etiq[k], "nuevo": nuevos[k],
                        "query_vieja": orig[k.split("|")[0]]["query"],
                        "query_nueva": consultas[k.split("|")[0]]["query"]}
                    for k in comunes},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
