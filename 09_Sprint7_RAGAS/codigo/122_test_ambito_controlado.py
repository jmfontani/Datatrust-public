#!/usr/bin/env python3
"""
122_test_ambito_controlado.py — aisla el efecto de anadir "Espana".

EL PROBLEMA DEL TEST ANTERIOR (121)
El test 121 rejuzgo 90 pares con el texto NUEVO y vio que 29 cambiaban de nivel
(el 32 %), con un patron sospechoso: 20 de ellos bajaban de 2 a 1. Ademas, las
fichas que bajaban tenian territorio de una comunidad autonoma (Zaragoza,
Navarra, Pais Vasco) y las que se mantenian en 2 tenian territorio "Espana".

Pero el juez tiene una reproducibilidad medida del 0,881, asi que parte de esos
29 cambios podria ser RUIDO. Con un solo juicio no se puede distinguir el efecto
del ruido.

ESTE TEST
Ida y vuelta sobre los mismos pares:
  A) juicio historico (texto viejo, con el que se etiquetaron)  -> nivel X
  B) texto nuevo (anadido "Espana")                             -> nivel Y
  C) texto viejo OTRA VEZ (control de reproducibilidad)         -> nivel Z

Si Z == X (el juez reproduce), entonces A->B es efecto real del texto y no ruido.
Si Z != X, el juez es inestable en ese par y no se puede concluir nada de el.

SALIDA
Separa los cambios ATRIBUIBLES AL TEXTO de los atribuibles a la INESTABILIDAD.
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
SALIDA = ENTREG / "test_ambito_controlado.json"
MODELO = "deepseek-v4.1-flash"
LOTE = 10

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


def juzga(casos, clave):
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
            out[i - 1] = niv
    return out


def main():
    clave = leer_clave()
    if not clave:
        print("ERROR: falta OLLAMA_API_KEY")
        return 1

    efecto = json.loads((ENTREG / "efecto_ambito.json").read_text(encoding="utf-8"))
    det = efecto["detalle"]
    v2 = {json.loads(l)["id"]: json.loads(l)
          for l in (ENTREG / "consultas_v2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    o1 = {json.loads(l)["id"]: json.loads(l)
          for l in (ENTREG / "ground_truth.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}

    # los que SI cambiaron de nivel con el texto nuevo (= candidatos a efecto)
    cambiados = {k: v for k, v in det.items() if v["viejo"] != v["nuevo"]}
    print("=" * 80)
    print("TEST CONTROLADO · ¿el cambio de nivel lo causa «España» o el ruido del juez?")
    print("=" * 80)
    print(f"\n  pares que cambiaron de nivel en el test anterior: {len(cambiados)}")
    print(f"  se rejuzgan AHORA con el texto VIEJO (control de reproducibilidad)\n")

    conn = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "postgres"),
                            dbname=os.getenv("POSTGRES_DB", "buscador"),
                            user=os.getenv("POSTGRES_USER", "postgres"),
                            password=os.getenv("POSTGRES_PASSWORD", "postgres"))
    por_q = {}
    for k in cambiados:
        qid, did = k.split("|")
        por_q.setdefault(qid, []).append(did)

    control, fallos = {}, []
    for qi, (qid, ids) in enumerate(por_q.items(), 1):
        o = o1[qid]
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""SELECT dataset_id, title, description, theme_label,
                                  territory_label FROM datasets
                           WHERE dataset_id = ANY(%s)""", (ids,))
            meta = {r["dataset_id"]: dict(r) for r in cur.fetchall()}
        fichas = [{"dataset_id": d, "title": meta.get(d, {}).get("title") or "",
                   "description": (meta.get(d, {}).get("description") or "")[:800],
                   "theme_label": meta.get(d, {}).get("theme_label") or "",
                   "territory_label": meta.get(d, {}).get("territory_label") or "",
                   "_query": o["query"], "_intencion": o.get("descripcion")}
                  for d in ids if d in meta]
        print(f"  [{qi}/{len(por_q)}] {qid:14} {len(fichas):>2} fichas  «{o['query']}»")
        for ini in range(0, len(fichas), LOTE):
            grupo = fichas[ini:ini + LOTE]
            if not grupo:
                continue
            try:
                res = juzga(grupo, clave)
            except Exception as e:
                fallos.append(f"{qid}: {str(e)[:80]}")
                continue
            for j, f in enumerate(grupo):
                if j in res:
                    control[f"{qid}|{f['dataset_id']}"] = res[j]
            time.sleep(0.4)
    conn.close()

    # ---- analisis de ida y vuelta ----
    filas = []
    for k, v in cambiados.items():
        z = control.get(k)
        if z is None:
            continue
        filas.append({"clave": k, "query_id": k.split("|")[0],
                      "historico": v["viejo"], "con_espana": v["nuevo"], "control": z,
                      "reproduce": v["viejo"] == z,
                      "efecto_texto": v["viejo"] == z and v["nuevo"] != v["viejo"]})

    print(f"\n### IDA Y VUELTA ###\n")
    print(f"  pares con las tres medidas: {len(filas)}")
    rep = [f for f in filas if f["reproduce"]]
    efecto_real = [f for f in filas if f["efecto_texto"]]
    ruido = [f for f in filas if not f["reproduce"]]

    print(f"\n  el juez REPRODUCE el nivel historico : {len(rep)}/{len(filas)} "
          f"({100*len(rep)/len(filas):.0f} %)")
    print(f"  cambio ATRIBUIBLE AL TEXTO «España» : {len(efecto_real)}/{len(filas)} "
          f"({100*len(efecto_real)/len(filas):.0f} %)")
    print(f"  inestable (no reproduce)             : {len(ruido)}/{len(filas)} "
          f"({100*len(ruido)/len(filas):.0f} %)")

    print(f"\n  transiciones (historico -> con España -> control):")
    trans = Counter((f["historico"], f["con_espana"], f["control"]) for f in filas)
    for (a, b, c), n in trans.most_common():
        etiqueta = "EFECTO TEXTO" if (a == c and b != a) else ("ruido" if a != c else "sin cambio")
        print(f"     {a} -> {b} -> {c}   {n:>3}   {etiqueta}")

    # ---- el dato clave: ¿que territorio tienen los que bajan a 1? ----
    ids_bajan = [f["clave"].split("|")[1] for f in efecto_real if f["con_espana"] == 1]
    if ids_bajan:
        arr = ",".join(f"'{i}'" for i in ids_bajan)
        conn2 = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "postgres"),
                                 dbname=os.getenv("POSTGRES_DB", "buscador"),
                                 user=os.getenv("POSTGRES_USER", "postgres"),
                                 password=os.getenv("POSTGRES_PASSWORD", "postgres"))
        with conn2.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(f"""SELECT coalesce(nullif(territory_label,''),'(vacio)') AS t,
                                   count(*) AS n
                            FROM datasets WHERE dataset_id IN ({arr})
                            GROUP BY 1 ORDER BY 2 DESC""")
            tcs = cur.fetchall()
        conn2.close()
        print(f"\n### TERRITORIO DE LAS FICHAS QUE BAJAN 2 -> 1 (efecto texto) ###\n")
        for r in tcs:
            print(f"     {r['t'][:52]:54} {r['n']}")

    print(f"\n### VEREDICTO ###\n")
    if len(filas) == 0:
        print("     sin datos")
    elif len(efecto_real) >= 5 and len(efecto_real) > len(ruido):
        print(f"     El efecto es REAL: anadir «España» degrada sistematicamente")
        print(f"     datasets de ambito autonomico o municipal de 2 a 1.")
        print(f"     {len(efecto_real)} casos atribuibles al texto frente a {len(ruido)} de ruido.")
        print(f"\n     CONSECUENCIA: el paso 1 de la Fase C, TAL COMO ESTABA PLANTEADO,")
        print(f"     es contraproducente. En datos.gob.es el catalogo es mayoritariamente")
        print(f"     autonomico y municipal: el usuario que busca un fenomeno NO rechaza")
        print(f"     la version de su comunidad. Fijar «España» como unico ambito valido")
        print(f"     castiga a la mayoria del catalogo.")
    else:
        print(f"     No se puede concluir: el efecto ({len(efecto_real)}) no supera")
        print(f"     claramente la inestabilidad del juez ({len(ruido)}).")

    SALIDA.write_text(json.dumps({
        "n": len(filas), "reproducen": len(rep),
        "efecto_texto": len(efecto_real), "ruido": len(ruido),
        "transiciones": {f"{a}-{b}-{c}": n for (a, b, c), n in trans.items()},
        "filas": filas, "fallos": fallos},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
