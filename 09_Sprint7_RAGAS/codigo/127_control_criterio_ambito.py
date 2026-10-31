#!/usr/bin/env python3
"""
127_control_criterio_ambito.py — ¿el cambio es del CRITERIO o del JUEZ?

POR QUE HACE FALTA (es la regla §32 del skill)
El rejuicio del nivel 1 (script 124) cambio 194 de 225 etiquetas: 146 subieron a 2
y 48 bajaron a 0. Pero ese rejuicio uso un PROMPT DISTINTO. Por tanto el cambio
mezcla dos causas:
  1. el criterio de ambito corregido (lo que queremos medir),
  2. la inestabilidad del juez (reproducibilidad medida: 0,881 = ~12 % de ruido).

Sin separarlo, no se puede afirmar que el criterio explique el cambio.

METODO: IDA Y VUELTA
  1. juicio ORIGINAL, prompt canonico      -> nivel 1 (por construccion)
  2. juicio NUEVO, criterio de ambito      -> nivel X  (el del script 124)
  3. CONTROL: prompt canonico OTRA VEZ     -> nivel Z

Interpretacion:
  Z == 1  -> el juez reproduce el nivel 1 original: el cambio a X lo causo el
             CRITERIO. Es efecto real.
  Z == X  -> el juez ahora dice X con el prompt viejo tambien: el "1" original
             era la parte inestable, no el criterio.
  otro    -> inestable, no concluyente.
"""
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
GT = ENTREG / "ground_truth.jsonl"
REJ = ENTREG / "rejuicio_nivel1.json"
SALIDA = ENTREG / "control_criterio_ambito.json"
MODELO = "deepseek-v4.1-flash"
LOTE = 10

# prompt CANONICO (el viejo, el que produjo el nivel 1 original)
PROMPT_VIEJO = """Eres evaluador de un buscador de datos abiertos espanol. Debes decidir
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


def juzga(casos, clave, prompt_tpl):
    lista = []
    for i, c in enumerate(casos, 1):
        lista.append(f'{i}. TITULO: {c["title"][:220]}\n'
                     f'   DESCRIPCION: {(c["description"] or "(sin descripcion)")[:600]}\n'
                     f'   TEMA: {c.get("theme_label") or "-"} | '
                     f'   TERRITORIO: {c.get("territory_label") or "-"}')
    prompt = prompt_tpl.format(query=casos[0]["_query"],
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
    ap = __import__("argparse").ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--semilla", type=int, default=11)
    args = ap.parse_args()

    clave = leer_clave()
    if not clave:
        print("ERROR: falta OLLAMA_API_KEY")
        return 1

    rej = json.loads(REJ.read_text(encoding="utf-8"))["detalle"]
    consultas = {json.loads(l)["id"]: json.loads(l)
                 for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()}

    cambiadas = {k: v for k, v in rej.items() if v["nivel"] != 1}
    print("=" * 80)
    print("CONTROL: ¿el cambio del nivel 1 lo causa el CRITERIO o el JUEZ?")
    print("=" * 80)
    print(f"\n  cambiadas en el rejuicio: {len(cambiadas)}")
    print(f"  (a nivel 2: {sum(1 for v in cambiadas.values() if v['nivel']==2)}, "
          f"a nivel 0: {sum(1 for v in cambiadas.values() if v['nivel']==0)})")

    random.seed(args.semilla)
    # estratificado por destino, para tener poder en las dos direcciones
    a2 = [k for k, v in cambiadas.items() if v["nivel"] == 2]
    a0 = [k for k, v in cambiadas.items() if v["nivel"] == 0]
    mitad = args.n // 2
    muestra = (random.sample(a2, min(mitad, len(a2))) +
               random.sample(a0, min(mitad, len(a0))))
    random.shuffle(muestra)
    print(f"  muestra: {len(muestra)} "
          f"({sum(1 for k in muestra if cambiadas[k]['nivel']==2)} fueron a 2, "
          f"{sum(1 for k in muestra if cambiadas[k]['nivel']==0)} fueron a 0)\n")

    conn = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "postgres"),
                            dbname=os.getenv("POSTGRES_DB", "buscador"),
                            user=os.getenv("POSTGRES_USER", "postgres"),
                            password=os.getenv("POSTGRES_PASSWORD", "postgres"))
    por_q = {}
    for k in muestra:
        por_q.setdefault(k.split("|")[0], []).append(k.split("|")[1])

    control, fallos = {}, []
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
        for ini in range(0, len(fichas), LOTE):
            grupo = fichas[ini:ini + LOTE]
            if not grupo:
                continue
            res = None
            for intento in range(3):
                try:
                    res = juzga(grupo, clave, PROMPT_VIEJO)
                    break
                except Exception as e:
                    if intento == 2:
                        fallos.append(f"{qid}: {str(e)[:60]}")
                    time.sleep(3 * (intento + 1))
            if not res:
                continue
            for j, f in enumerate(grupo):
                if j in res:
                    control[f"{qid}|{f['dataset_id']}"] = res[j]
            time.sleep(0.4)
    conn.close()

    filas = []
    for k in muestra:
        z = control.get(k)
        if z is None:
            continue
        x = cambiadas[k]["nivel"]
        filas.append({"clave": k, "original": 1, "criterio_nuevo": x, "control": z,
                      "efecto_criterio": z == 1,
                      "el_1_era_ruido": z == x})

    print(f"\n### IDA Y VUELTA (original=1 -> criterio nuevo -> prompt viejo otra vez) ###\n")
    print(f"  pares con las tres medidas: {len(filas)}")
    ef = [f for f in filas if f["efecto_criterio"]]
    ruido = [f for f in filas if f["el_1_era_ruido"]]
    otro = [f for f in filas if not f["efecto_criterio"] and not f["el_1_era_ruido"]]
    print(f"\n  el juez REPRODUCE el nivel 1 (efecto del CRITERIO) : {len(ef):>3}"
          f"  ({100*len(ef)/len(filas):.0f} %)")
    print(f"  el nivel 1 original era RUIDO (ahora da X tambien): {len(ruido):>3}"
          f"  ({100*len(ruido)/len(filas):.0f} %)")
    print(f"  inestable / no concluyente                       : {len(otro):>3}"
          f"  ({100*len(otro)/len(filas):.0f} %)")

    print(f"\n  transiciones (1 -> nuevo -> control):")
    for (a, b), n in Counter((f["criterio_nuevo"], f["control"]) for f in filas).most_common():
        et = "EFECTO CRITERIO" if b == 1 else ("el 1 era ruido" if b == a else "inestable")
        print(f"     1 -> {a} -> {b}   {n:>3}   {et}")

    pct = len(ef) / len(filas) if filas else 0
    print(f"\n### VEREDICTO ###\n")
    print(f"  proporcion de cambios ATRIBUIBLES AL CRITERIO: {pct*100:.0f} %")
    print(f"  extrapolado a las 225 del nivel 1 -> ~{round(pct*225)} cambios reales")
    print(f"  el resto (~{225-round(pct*225)}) es inestabilidad del juez")
    if pct >= 0.6:
        print(f"\n  El criterio explica la mayoria del cambio: la correccion es REAL.")
    else:
        print(f"\n  ** El criterio NO explica la mayoria del cambio: revisar antes de")
        print(f"     dar por bueno el nuevo GT. **")

    SALIDA.write_text(json.dumps({
        "n": len(filas), "efecto_criterio": len(ef), "el_1_era_ruido": len(ruido),
        "inestable": len(otro), "pct_efecto": round(pct, 3),
        "extrapolado_225": round(pct * 225), "filas": filas, "fallos": fallos},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
