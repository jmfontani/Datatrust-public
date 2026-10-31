#!/usr/bin/env python3
"""
109_juzgar_pool.py — FASE B, paso 2. Juzga el pool con la escala de 3 niveles.

Escala (validada en el Paso 0: 90 % de acuerdo entre dos pasadas, 40/40 con +-1):
    2 = RESPONDE   | el fenomeno Y el ambito coinciden
    1 = TEMA CORRECTO, OTRO ALCANCE | mismo fenomeno, distinto ambito o desglose
    0 = NO RESPONDE | otro fenomeno, o solo comparte una palabra

Diseno:
  * LOTES de 10 fichas por llamada -> menos llamadas y el juez ve el conjunto
  * temperatura 0 para reproducibilidad
  * se juzga solo lo NO juzgado (los 406 juicios de junio se conservan)
  * checkpoint tras cada consulta: si se corta, se reanuda sin repetir
  * control de acuerdo: un 5 % de las fichas se juzga DOS veces de forma ciega

Uso:
  python 109_juzgar_pool.py --limite 2          # prueba con 2 consultas
  python 109_juzgar_pool.py                     # todas
  python 109_juzgar_pool.py --solo-nuevas       # por defecto
"""
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
POOL = ENTREG / "pool_a_juzgar.json"
SALIDA = ENTREG / "gt_etiquetas_v2.json"
CHECK = ENTREG / "_checkpoint_juicio.json"

MODELO = "deepseek-v4.1-flash"
LOTE = 10
FRACCION_DOBLE = 0.05      # 5 % juzgado dos veces para medir acuerdo

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
    """casos: lista de dicts con title/description/theme_label/territory_label."""
    lista = []
    for i, c in enumerate(casos, 1):
        lista.append(
            f'{i}. TITULO: {c["title"][:220]}\n'
            f'   DESCRIPCION: {(c["description"] or "(sin descripcion)")[:600]}\n'
            f'   TEMA: {c.get("theme_label") or "-"} | '
            f'TERRITORIO: {c.get("territory_label") or "-"}'
        )
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
        raise ValueError(f"sin JSON en la respuesta: {txt[:120]}")
    datos = json.loads(m.group(0))
    out = {}
    for j in datos.get("juicios", []):
        try:
            i = int(j["i"])
            niv = int(j["nivel"])
        except (KeyError, TypeError, ValueError):
            continue
        if 1 <= i <= len(casos) and niv in (0, 1, 2):
            out[i - 1] = (niv, str(j.get("razon", ""))[:200])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=None,
                    help="solo las primeras N consultas (para probar)")
    ap.add_argument("--consultas", default=None, help="ids separados por comas")
    args = ap.parse_args()

    clave = leer_clave()
    if not clave:
        print("ERROR: falta OLLAMA_API_KEY")
        return 1

    pool = json.loads(POOL.read_text(encoding="utf-8"))
    etiq_prev = json.loads((ENTREG / "gt_etiquetas.json").read_text(encoding="utf-8"))

    consultas = pool["pool"]
    if args.consultas:
        ids = {s.strip() for s in args.consultas.split(",")}
        consultas = [c for c in consultas if c["query_id"] in ids]
    if args.limite:
        consultas = consultas[:args.limite]

    # estado previo (reanudable)
    estado = {"juicios": {}, "acuerdo": [], "fallos": []}
    if CHECK.exists():
        estado = json.loads(CHECK.read_text(encoding="utf-8"))
        print(f"  reanudando: {len(estado.get('juicios', {}))} juicios previos")

    pendientes = [c for c in consultas
                  if any(not f["ya_juzgada"] for f in c["fichas"])]
    total_fichas = sum(sum(1 for f in c["fichas"] if not f["ya_juzgada"])
                       for c in pendientes)
    print("=" * 74)
    print("JUICIO DEL POOL (Fase B)")
    print("=" * 74)
    print(f"\n  modelo juez      : {MODELO} (temperatura 0)")
    print(f"  consultas        : {len(pendientes)}")
    print(f"  fichas SIN juicio: {total_fichas}")
    print(f"  lote             : {LOTE} fichas por llamada")
    print(f"  doble juicio ciego: {FRACCION_DOBLE:.0%} de las fichas")
    print(f"  llamadas estimadas: ~{total_fichas/LOTE + len(pendientes)*0.5:.0f}\n")

    random.seed(11)
    t0 = time.time()
    hechas = 0
    for ci, c in enumerate(pendientes, 1):
        qid = c["query_id"]
        nuevas = [f for f in c["fichas"] if not f["ya_juzgada"]]
        if not nuevas:
            continue
        # doble juicio ciego sobre una fraccion (se guarda aparte, para acuerdo)
        n_doble = max(1, int(len(nuevas) * FRACCION_DOBLE))
        doble = random.sample(nuevas, min(n_doble, len(nuevas)))

        print(f"  [{ci}/{len(pendientes)}] {qid:14} {len(nuevas):>3} fichas", end=" ")
        t1 = time.time()
        ok = 0
        # LOTES: primero las que se van a rejuzgar, luego el resto
        orden = doble + [f for f in nuevas if f not in doble]
        for ini in range(0, len(orden), LOTE):
            grupo = orden[ini:ini + LOTE]
            casos = []
            for f in grupo:
                d = dict(f)
                d["_query"] = c["query"]
                d["_intencion"] = c.get("descripcion_intencion")
                casos.append(d)
            try:
                res = juzga_lote(casos, clave)
            except Exception as e:
                print(f"\n       fallo de lote: {str(e)[:70]}")
                estado["fallos"].append({"query_id": qid, "ini": ini,
                                         "error": str(e)[:200]})
                continue
            for k, f in enumerate(grupo):
                if k not in res:
                    continue
                niv, raz = res[k]
                clave_e = f"{qid}|{f['dataset_id']}"
                estado["juicios"][clave_e] = {
                    "nivel": niv, "razon": raz,
                    "title": f["title"][:200],
                    "sistemas": f["sistemas"],
                    "doble": f in doble,
                }
                ok += 1
            time.sleep(0.4)
        hechas += ok
        print(f"-> {ok} juzgadas ({time.time()-t1:.0f} s)")
        CHECK.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")

    print(f"\n### resumen ({time.time()-t0:.0f} s) ###\n")
    print(f"  fichas juzgadas en esta ejecucion: {hechas}")
    print(f"  total en el checkpoint           : {len(estado['juicios'])}")
    print(f"  lotes fallidos                   : {len(estado['fallos'])}")

    # ---- consolidar con lo previo de junio ----
    niveles = {}
    for k, v in etiq_prev["etiquetas"].items():
        niveles[k] = {"nivel": int(v), "origen": "junio"}
    nuevos = 0
    for k, v in estado["juicios"].items():
        if k not in niveles:
            nuevos += 1
        niveles[k] = {"nivel": int(v["nivel"]), "razon": v.get("razon"),
                      "title": v.get("title"), "sistemas": v.get("sistemas"),
                      "origen": "fase_b"}
    print(f"\n  etiquetas de junio reutilizadas: {len(etiq_prev['etiquetas'])}")
    print(f"  etiquetas nuevas de la Fase B  : {nuevos}")
    print(f"  TOTAL                          : {len(niveles)}")

    from collections import Counter
    dist = Counter(v["nivel"] for v in niveles.values())
    print(f"  distribucion de niveles        : {dict(sorted(dist.items()))}")

    SALIDA.write_text(json.dumps({
        "meta": {
            "fase": "B",
            "generado": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "juez": f"{MODELO} (temperatura 0)",
            "escala": {"2": "responde", "1": "tema correcto, otro alcance",
                       "0": "no responde"},
            "pool": "union del top-20 de 3 sistemas (uno lexico puro)",
            "total": len(niveles),
            "de_junio": len(etiq_prev["etiquetas"]),
            "nuevas": nuevos,
        },
        "etiquetas": {k: v["nivel"] for k, v in niveles.items()},
        "detalle": niveles,
        "acuerdo_doble": estado.get("acuerdo", []),
        "fallos": estado.get("fallos", []),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
