#!/usr/bin/env python3
"""
134_estratificar_por_vocabulario.py — ¿el ranking entre motores depende de cuánto
la consulta copia el vocabulario del catalogo?

HALLAZGO QUE MOTIVA ESTE CONTROL
Con las 47 consultas originales: semantico 0,5801 > lexico 0,4368.
Con las 169 nuevas:             semantico 0,3947 < lexico 0,6201.
El lexico sube +0,1834 y el semantico cae -0,1854 SOLO en las nuevas.

La causa probable: las 169 se generaron dando al LLM 40 titulos REALES del
catalogo, y el LLM reutilizo su vocabulario. Una consulta escrita en el idioma del
catalogo favorece al motor que casa palabras literales.

QUE HACE ESTE CONTROL
Si la contaminacion explica el vuelco, el ranking entre motores debe DEPENDER del
grado de solapamiento: en las consultas que NO copian el vocabulario (solapamiento
bajo) el semantico deberia recuperarse.

Se parte las 169 nuevas en tres tercios por solapamiento (bajo/medio/alto) y se
mide cada motor en cada tercio. Control adicional: cuantas fichas nivel 2 hay
disponibles por consulta, para separar "consultas mas dificiles" de "consultas
contaminadas" -- son explicaciones distintas y llevan a decisiones distintas.
"""
import json
import math
import re
import statistics
import sys
import urllib.request
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
GT_V3 = ENTREG / "gt_etiquetas_v3.json"
GT_VIEJO = ENTREG / "ground_truth.jsonl"
NUEVAS = ENTREG / "consultas_validadas.jsonl"
API = "http://localhost:8000/search"

SISTEMAS = {
    "actual": {"semantic_weight": 0.7, "lexical_weight": 0.3},
    "semantico": {"semantic_weight": 1.0, "lexical_weight": 0.0},
    "lexico": {"semantic_weight": 0.0, "lexical_weight": 1.0},
}
STOP = {"de", "la", "el", "los", "las", "en", "por", "para", "con", "que", "del",
        "al", "y", "o", "un", "una", "segun", "sobre", "su", "sus", "es", "the"}


def tokens(s):
    return {w for w in re.findall(r"[a-záéíóúüñ0-9]+", (s or "").lower())
            if len(w) > 3 and w not in STOP}


def busca(q, **kw):
    body = {"query": q, "top_k": 10}
    body.update(kw)
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=120).read())
    except Exception:
        return []
    return d.get("results") or d.get("datasets") or []


def mide(qs, gt):
    """Devuelve por consulta: nDCG por motor, solapamiento, nivel-2 disponibles."""
    out = []
    for q in qs:
        t = tokens(q["query"])
        n2 = sum(1 for k, v in gt.items() if k.startswith(f"{q['id']}|") and v == 2)
        fila = {"id": q["id"], "palabras": len(t), "nivel2_disponibles": n2}
        sol = []
        for nom, kw in SISTEMAS.items():
            res = busca(q["query"], **kw)
            niv = [gt.get(f"{q['id']}|{(r.get('dataset_id') or r.get('id'))}")
                   for r in res[:10]]
            dcg = sum((x or 0) / math.log2(i + 2) for i, x in enumerate(niv))
            todos = [int(v) for k, v in gt.items() if k.startswith(f"{q['id']}|")]
            idcg = sum(v / math.log2(i + 2)
                       for i, v in enumerate(sorted(todos, reverse=True)[:10])) if todos else 0
            fila[nom] = dcg / idcg if idcg else 0.0
            if res and t:
                tt = tokens(res[0].get("title", "")) | tokens(res[0].get("description", "")[:300])
                sol.append(len(t & tt) / len(t))
        # solapamiento del motor que mejor casa palabras: el lexico
        fila["solapamiento"] = max(sol) if sol else 0.0
        out.append(fila)
    return out


def main():
    gt = json.loads(GT_V3.read_text(encoding="utf-8"))["etiquetas"]
    viejas = [json.loads(l) for l in GT_VIEJO.read_text(encoding="utf-8").splitlines() if l.strip()]
    nuevas = [json.loads(l) for l in NUEVAS.read_text(encoding="utf-8").splitlines() if l.strip()]

    print("=" * 84)
    print("ESTRATIFICACION POR SOLAPAMIENTO DE VOCABULARIO")
    print("=" * 84)

    print(f"\n  midiendo 47 antiguas...")
    A = mide(viejas, gt)
    print(f"  midiendo 169 nuevas...")
    B = mide(nuevas, gt)
    A = [f for f in A if f["solapamiento"] >= 0]
    B = [f for f in B if f["solapamiento"] >= 0]

    print(f"\n### A) ¿SON MAS DIFICILES, O ESTAN CONTAMINADAS? ###\n")
    print(f"  {'grupo':12} {'solap.':>8} {'nivel-2 disp.':>14} {'palabras':>9}")
    print(f"  {'-'*12} {'-'*8} {'-'*14} {'-'*9}")
    for nom, G in (("47 antiguas", A), ("169 nuevas", B)):
        print(f"  {nom:12} {statistics.mean([f['solapamiento'] for f in G]):8.3f} "
              f"{statistics.mean([f['nivel2_disponibles'] for f in G]):14.1f} "
              f"{statistics.mean([f['palabras'] for f in G]):9.1f}")
    print(f"\n  (si 'nivel-2 disponibles' es mayor en las nuevas, NO son mas dificiles:")
    print(f"   el catalogo las responde mas, y sin embargo el semantico cae)")

    B2 = sorted(B, key=lambda f: f["solapamiento"])
    ter = len(B2) // 3
    grupos = {"solap. BAJO": B2[:ter],
              "solap. medio": B2[ter:2 * ter],
              "solap. ALTO": B2[2 * ter:]}

    print(f"\n### B) RANKING ENTRE MOTORES POR TERCIO DE SOLAPAMIENTO ###\n")
    print(f"  {'grupo':14} {'n':>4} {'solap':>7} {'actual':>8} {'semantico':>10} "
          f"{'lexico':>8}   {'gana':>10}")
    print(f"  {'-'*14} {'-'*4} {'-'*7} {'-'*8} {'-'*10} {'-'*8}   {'-'*10}")
    res = {}
    for nom, G in grupos.items():
        m = {s: statistics.mean([f[s] for f in G]) for s in SISTEMAS}
        gana = max(SISTEMAS, key=lambda s_: m[s_])
        res[nom] = {"n": len(G),
                    "solapamiento": round(statistics.mean([f["solapamiento"] for f in G]), 3),
                    **{s: round(m[s], 4) for s in SISTEMAS}, "gana": gana}
        print(f"  {nom:14} {len(G):4} {statistics.mean([f['solapamiento'] for f in G]):7.3f} "
              f"{m['actual']:8.4f} {m['semantico']:10.4f} {m['lexico']:8.4f}   {gana:>10}")

    print(f"\n  referencia · 47 antiguas: actual "
          f"{statistics.mean([f['actual'] for f in A]):.4f} · semantico "
          f"{statistics.mean([f['semantico'] for f in A]):.4f} · lexico "
          f"{statistics.mean([f['lexico'] for f in A]):.4f}")

    print(f"\n### C) VEREDICTO ###\n")
    bajo = res["solap. BAJO"]
    alto = res["solap. ALTO"]
    dif_b = bajo["semantico"] - bajo["lexico"]
    dif_a = alto["semantico"] - alto["lexico"]
    print(f"  semantico - lexico con solapamiento BAJO : {dif_b:+.4f}  -> gana {bajo['gana']}")
    print(f"  semantico - lexico con solapamiento ALTO : {dif_a:+.4f}  -> gana {alto['gana']}")
    if dif_b > dif_a + 0.05:
        print(f"\n  El semantico se recupera cuando la consulta NO copia el vocabulario")
        print(f"  del catalogo ({dif_b - dif_a:+.4f} de diferencia entre tercios).")
        print(f"  -> El vuelco se explica por la CONTAMINACION de las consultas,")
        print(f"     no por una superioridad real del motor lexico.")
        print(f"  -> La comparacion de motores con las 216 consultas NO es valida.")
    else:
        print(f"\n  El ranking no depende del solapamiento ({dif_b - dif_a:+.4f}).")
        print(f"  -> La caida del semantico NO se explica por contaminacion.")
        print(f"  -> Hay que buscar otra causa (el modelo, o el texto indexado).")

    (ENTREG / "estratificacion_vocabulario.json").write_text(
        json.dumps({"grupos": res,
                    "tercios": {k: [f["id"] for f in v] for k, v in grupos.items()}},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: entregables/estratificacion_vocabulario.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
