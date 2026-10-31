#!/usr/bin/env python3
"""
111_rejuzgar_muestra.py — FASE B, control de acuerdo REAL.

Motivo: 109_juzgar_pool.py designaba un 5 % para doble juicio, pero guardaba ambos
juicios bajo la MISMA clave, asi que el primero se perdia. Sin dos juicios
independientes no se puede medir el acuerdo.

Este script hace lo correcto:
  1. toma una muestra ALEATORIA de fichas del pool ya juzgado
  2. las rejuzga con el MISMO prompt pero en una ejecucion aparte
  3. las rejuzga tambien con un PROMPT ALTERNATIVO (redaccion distinta)
  4. compara: mismo juez+prompt (reproducibilidad) y prompt distinto (robustez)

Tres comparaciones, tres preguntas distintas:
  * mismo prompt, dos pasadas  -> ¿es determinista?
  * prompts distintos          -> ¿depende de la redaccion? (robustez)
  * Fase B vs junio            -> acuerdo entre jueces distintos

Uso:
  python 111_rejuzgar_muestra.py --n 60
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

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
V2 = ENTREG / "gt_etiquetas_v2.json"
V1 = ENTREG / "gt_etiquetas.json"
SALIDA = ENTREG / "acuerdo_jueces.json"
MODELO = "deepseek-v4.1-flash"

# Prompt alternativo: misma escala, OTRA redaccion. Si el juez es robusto, debe
# dar el mismo nivel.
PROMPT_ALT = """Clasifica si cada conjunto de datos sirve para responder a la
consulta. Usa esta escala de 0 a 2:

- 2: sirve como respuesta. El tema y el ambito (territorio, periodo, desglose)
     coinciden con lo pedido.
- 1: es del mismo tema pero de otro ambito o desglose. Sirve de contexto, no
     de respuesta.
- 0: no sirve. El tema es distinto.

CONSULTA: {query}

CONJUNTOS:
{lista}

Devuelve SOLO un JSON en una linea:
{{"juicios": [{{"i": 1, "nivel": 0, "razon": "..."}}]}}
Una entrada por conjunto, en el mismo orden."""


def leer_clave():
    """Busca la clave en .env (host) o en el entorno (contenedor)."""
    for ruta in (Path.cwd() / ".env",
                 Path(__file__).resolve().parent / ".env"):
        if ruta.exists():
            for ln in ruta.read_text(encoding="utf-8").splitlines():
                if ln.startswith("OLLAMA_API_KEY="):
                    return ln.split("=", 1)[1].strip()
    return os.getenv("OLLAMA_API_KEY")


def llama(prompt, clave):
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
        return {}
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    out = {}
    for j in d.get("juicios", []):
        try:
            out[int(j["i"]) - 1] = int(j["nivel"])
        except (KeyError, TypeError, ValueError):
            continue
    return {k: v for k, v in out.items() if v in (0, 1, 2)}


def kappa(a, b):
    n = len(a)
    if not n:
        return None
    obs = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    esp = sum((ca[k]/n)*(cb[k]/n) for k in set(ca) | set(cb))
    return 1.0 if esp >= 1 else (obs - esp) / (1 - esp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--lote", type=int, default=10)
    ap.add_argument("--fuente", choices=["nuevas", "junio"], default="nuevas",
                    help="nuevas = fichas juzgadas en la Fase B; "
                         "junio = pares YA juzgados en junio (acuerdo entre jueces)")
    args = ap.parse_args()

    clave = leer_clave()
    if not clave:
        print("ERROR: falta OLLAMA_API_KEY")
        return 1

    v2 = json.loads(V2.read_text(encoding="utf-8"))
    v1 = json.loads(V1.read_text(encoding="utf-8"))
    if args.fuente == "nuevas":
        det = {k: v for k, v in v2["detalle"].items() if v.get("origen") == "fase_b"}
        ref = {k: int(v["nivel"]) for k, v in det.items()}
        nom_fuente = "juicios de la Fase B (rejuzgado por el mismo juez)"
    else:
        ref = {k: int(v) for k, v in v1["etiquetas"].items()}
        nom_fuente = "juicios de JUNIO (rejuzgado con el prompt nuevo)"
    print("=" * 74)
    print("ACUERDO ENTRE JUECES · rejuzgado independiente")
    print("=" * 74)
    print(f"\n  fuente            : {nom_fuente}")
    print(f"  pares disponibles : {len(ref)}")
    det = {k: {"nivel": v} for k, v in ref.items()}

    random.seed(23)
    claves = random.sample(list(det), min(args.n, len(det)))
    print(f"  muestra a rejuzgar: {len(claves)}")

    # agrupar por consulta (el prompt lleva la consulta)
    por_q = {}
    for k in claves:
        por_q.setdefault(k.split("|")[0], []).append(k)

    # cargar el pool para tener titulo/descripcion
    pool = json.loads((ENTREG / "pool_a_juzgar.json").read_text(encoding="utf-8"))
    fichas = {}
    for c in pool["pool"]:
        for f in c["fichas"]:
            fichas[f"{c['query_id']}|{f['dataset_id']}"] = (f, c["query"], c.get("descripcion_intencion"))

    p1, p2, p3 = [], [], []      # pasada1, pasada2(mismo prompt), prompt alt
    detalle = []
    for qi, (qid, ks) in enumerate(por_q.items(), 1):
        faltan = [k for k in ks if k in fichas]
        if not faltan:
            continue
        print(f"  [{qi}/{len(por_q)}] {qid:14} {len(faltan):>3} rejuzgadas", end=" ")
        t0 = time.time()
        for ini in range(0, len(faltan), args.lote):
            grupo = faltan[ini:ini + args.lote]
            query = fichas[grupo[0]][1]
            inten = fichas[grupo[0]][2]
            lista = []
            for i, k in enumerate(grupo, 1):
                f = fichas[k][0]
                lista.append(f'{i}. TITULO: {f["title"][:220]}\n'
                             f'   DESCRIPCION: {(f["description"] or "-")[:600]}\n'
                             f'   TEMA: {f.get("theme_label") or "-"} | '
                             f'TERRITORIO: {f.get("territory_label") or "-"}')
            txt_lista = "\n".join(lista)

            # prompt ORIGINAL (identico al de 109)
            from importlib import util as _u
            prompt_orig = ("Eres evaluador de un buscador de datos abiertos espanol. "
                           "Debes decidir si cada conjunto de datos RESPONDE a la consulta.\n\n"
                           "NIVELES\n2 = RESPONDE. Fenomeno y ambito coinciden.\n"
                           "1 = TEMA CORRECTO, OTRO ALCANCE. Mismo fenomeno, distinto ambito "
                           "o desglose.\n0 = NO RESPONDE. Otro fenomeno.\n\n"
                           f"CONSULTA DEL USUARIO: {query}\n"
                           f"INTENCION DECLARADA: {inten or '-'}\n\n"
                           f"CONJUNTOS A EVALUAR:\n{txt_lista}\n\n"
                           'Responde SOLO con un JSON en una linea:\n'
                           '{"juicios": [{"i": 1, "nivel": 0, "razon": "..."}]}')
            alt = PROMPT_ALT.format(query=query, lista=txt_lista)

            try:
                r1 = llama(prompt_orig, clave)
                time.sleep(0.3)
                r2 = llama(prompt_orig, clave)
                time.sleep(0.3)
                r3 = llama(alt, clave)
            except Exception as e:
                print(f"\n     fallo: {str(e)[:60]}")
                continue
            for i, k in enumerate(grupo):
                base = int(ref[k])
                if i in r1 and i in r2:
                    p1.append(base); p2.append(r1[i])
                if i in r3:
                    p3.append((base, r3[i]))
                detalle.append({"clave": k, "base": base,
                                "mismo_prompt": r1.get(i), "mismo_prompt_2": r2.get(i),
                                "prompt_alt": r3.get(i)})
        print(f"({time.time()-t0:.0f} s)")

    print("\n### RESULTADOS ###\n")
    def _k(a_, b_):
        n = len(a_)
        if not n:
            return None
        obs = sum(1 for x, y in zip(a_, b_) if x == y) / n
        ca, cb = Counter(a_), Counter(b_)
        esp = sum((ca[k]/n)*(cb[k]/n) for k in set(ca) | set(cb))
        return 1.0 if esp >= 1 else (obs - esp) / (1 - esp)

    def _bin(x):
        return 2 if x >= 1 else 0

    res = {}

    # 1) REPRODUCIBILIDAD: las DOS pasadas del MISMO prompt (r1 vs r2)
    pares = [(x["mismo_prompt"], x["mismo_prompt_2"]) for x in detalle
             if x["mismo_prompt"] is not None and x["mismo_prompt_2"] is not None]
    if pares:
        a_ = [x for x, _ in pares]; b_ = [y for _, y in pares]
        ex = sum(1 for x, y in zip(a_, b_) if x == y)/len(a_)
        tol = sum(1 for x, y in zip(a_, b_) if abs(x-y) <= 1)/len(a_)
        k = _k(a_, b_)
        print("  1) REPRODUCIBILIDAD · mismo prompt, dos pasadas")
        print(f"     n={len(a_)}  exacto {ex:.3f}  +-1 {tol:.3f}  kappa {k:.3f}")
        res["reproducibilidad"] = {"n": len(a_), "exacto": ex, "tol1": tol, "kappa": k}

    # 2) ROBUSTEZ: mismo juez, prompt con OTRA redaccion (r1 vs alt)
    pares = [(x["mismo_prompt"], x["prompt_alt"]) for x in detalle
             if x["mismo_prompt"] is not None and x["prompt_alt"] is not None]
    if pares:
        a_ = [x for x, _ in pares]; b_ = [y for _, y in pares]
        ex = sum(1 for x, y in zip(a_, b_) if x == y)/len(a_)
        tol = sum(1 for x, y in zip(a_, b_) if abs(x-y) <= 1)/len(a_)
        k = _k(a_, b_)
        # binarizado: el nivel 1 es la frontera que la redaccion mueve
        bx = [_bin(x) for x in a_]; by = [_bin(y) for y in b_]
        exb = sum(1 for x, y in zip(bx, by) if x == y)/len(bx)
        print("\n  2) ROBUSTEZ A LA REDACCION · mismo juez, prompt alternativo")
        print(f"     n={len(a_)}  exacto {ex:.3f}  +-1 {tol:.3f}  kappa {k:.3f}")
        print(f"     binarizado exacto {exb:.3f}")
        print(f"     sesgo de severidad: r1 marca {sum(1 for x in bx if x==2)}/{len(bx)} "
              f"relevantes, alt {sum(1 for y in by if y==2)}/{len(by)}")
        res["robustez_prompt"] = {"n": len(a_), "exacto": ex, "tol1": tol,
                                  "kappa": k, "binarizado": exb}

    # 3) ACUERDO ENTRE JUECES DISTINTOS: el de junio vs el nuevo
    pares = [(x["base"], x["mismo_prompt"]) for x in detalle
             if x["base"] is not None and x["mismo_prompt"] is not None]
    if pares:
        a_ = [x for x, _ in pares]; b_ = [y for _, y in pares]
        ex = sum(1 for x, y in zip(a_, b_) if x == y)/len(a_)
        bx = [_bin(x) for x in b_]
        exb = sum(1 for x, y in zip(a_, bx) if x == y)/len(a_)
        k = _k(a_, bx)
        print("\n  3) ACUERDO ENTRE JUECES DISTINTOS · junio vs nuevo")
        print(f"     n={len(a_)}  exacto {ex:.3f}   <- NO es comparable: junio no")
        print(f"        tiene nivel 1, asi que el exacto esta topado por construccion")
        print(f"     binarizado {exb:.3f}  (el comparable)  kappa {k:.3f}")
        res["entre_jueces"] = {"n": len(a_), "exacto": ex, "binarizado": exb, "kappa": k}

    # ---------------- G2 ----------------
    print("\n" + "=" * 74)
    print("UMBRAL G2: acuerdo >= 0,80")
    print("=" * 74)
    rep = res.get("reproducibilidad", {}).get("exacto")
    rob = res.get("robustez_prompt", {}).get("binarizado")
    ent = res.get("entre_jueces", {}).get("binarizado")
    print(f"\n  reproducibilidad (mismo prompt) : {rep:.3f}" if rep else "")
    print(f"  robustez (prompt alternativo)   : {rob:.3f}" if rob else "")
    print(f"  entre jueces (junio vs nuevo)   : {ent:.3f}" if ent else "")
    print()
    print("  Las tres comparaciones miden cosas DISTINTAS y no se pueden reducir")
    print("  a un solo numero. Veredicto por separado:")
    if rep and rep >= 0.80:
        print(f"  * reproducibilidad {rep:.3f} >= 0,80 -> el juez es DETERMINISTA.")
    if ent and ent >= 0.80:
        print(f"  * entre jueces {ent:.3f} >= 0,80 -> el juicio es CONSISTENTE")
        print("    entre el juez de junio y el nuevo.")
    if rob and rob < 0.80:
        print(f"  * robustez {rob:.3f} < 0,80 -> la frontera del nivel 1 DEPENDE")
        print("    de la redaccion del prompt. Hay que fijar un prompt canonico")
        print("    y no cambiarlo, o el GT deja de ser comparable entre tandas.")

    SALIDA.write_text(json.dumps({
        "meta": {"generado": time.strftime("%Y-%m-%dT%H:%M:%S"),
                 "modelo": MODELO, "n_muestra": len(claves),
                 "nota": "rejuzgado independiente para medir acuerdo (G2)"},
        "resultados": res, "detalle": detalle,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
