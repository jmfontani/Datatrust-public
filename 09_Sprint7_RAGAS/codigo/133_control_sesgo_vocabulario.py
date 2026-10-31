#!/usr/bin/env python3
"""
133_control_sesgo_vocabulario.py — ¿las consultas nuevas favorecen al lexico?

POR QUE ESTE CONTROL ES OBLIGATORIO
Las 169 consultas nuevas se generaron dando al LLM 40 TITULOS REALES del catalogo
de cada tema. Si el LLM reutilizo el vocabulario de esos titulos, las consultas
comparten palabras con los titulos de las fichas -> el motor LEXICO (que casa
palabras literalmente) sale favorecido por construccion, no por merito.

El sintoma que lo delata: el semantico pasa de 0,5801 (47 consultas) a 0,4350
(216). Si la causa es el sesgo, el derrumbe estara concentrado en las 169 nuevas.

QUÉ MIDE
  A) DESGLOSE: metricas de las 47 antiguas vs las 169 nuevas, por sistema.
     Si el semantico solo cae en las nuevas -> sesgo de generacion.
     Si cae en ambos -> es el modelo (MiniLM) y el hallazgo es real.
  B) SOLAPAMIENTO: fraccion de palabras significativas de cada consulta que
     aparecen literalmente en los titulos del catalogo. Compara los dos grupos.
  C) POSICION DEL ACIERTO: en que puesto aparece la primera ficha nivel 2.
"""
import json
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


def carga(qs, gt):
    """nDCG lineal igual que gt_metrics, mas el puesto del primer nivel 2."""
    import math
    out = {}
    for q in qs:
        fila = {}
        for nom, kw in SISTEMAS.items():
            res = busca(q["query"], **kw)
            niv = [gt.get(f"{q['id']}|{(r.get('dataset_id') or r.get('id'))}")
                   for r in res[:10]]
            dcg = sum((x or 0) / math.log2(i + 2) for i, x in enumerate(niv))
            todos = [int(v) for k, v in gt.items() if k.startswith(f"{q['id']}|")]
            if todos:
                idcg = sum(v / math.log2(i + 2)
                           for i, v in enumerate(sorted(todos, reverse=True)[:10]))
            else:
                idcg = 0
            puesto = next((i for i, x in enumerate(niv, 1) if x == 2), None)
            sol = 0.0
            if res:
                t = tokens(q["query"])
                tt = tokens(res[0].get("title", "")) | tokens(res[0].get("description", "")[:300])
                if t:
                    sol = len(t & tt) / len(t)
            fila[nom] = {"ndcg": dcg / idcg if idcg else 0.0, "puesto2": puesto,
                         "solapamiento": sol}
        out[q["id"]] = fila
    return out


def main():
    gt = json.loads(GT_V3.read_text(encoding="utf-8"))["etiquetas"]
    viejas = [json.loads(l) for l in GT_VIEJO.read_text(encoding="utf-8").splitlines() if l.strip()]
    nuevas = [json.loads(l) for l in NUEVAS.read_text(encoding="utf-8").splitlines() if l.strip()]

    print("=" * 84)
    print("CONTROL DE SESGO DE VOCABULARIO")
    print("=" * 84)
    print(f"\n  midiendo con las 47 antiguas...")
    a = carga(viejas, gt)
    print(f"  midiendo con las 169 nuevas...")
    b = carga(nuevas, gt)

    print(f"\n### A) DESGLOSE: 47 ANTIGUAS vs 169 NUEVAS ###\n")
    print(f"  {'sistema':10} {'nDCG 47':>9} {'nDCG 169':>9} {'delta':>9}   lectura")
    print(f"  {'-'*10} {'-'*9} {'-'*9} {'-'*9}   {'-'*40}")
    for nom in SISTEMAS:
        x4 = statistics.mean([v[nom]["ndcg"] for v in a.values()])
        x1 = statistics.mean([v[nom]["ndcg"] for v in b.values()])
        d = x1 - x4
        lectura = ("cae SOLO en las nuevas -> sesgo" if d < -0.05
                   else "sube o estable" if d >= -0.02 else "cae algo")
        print(f"  {nom:10} {x4:9.4f} {x1:9.4f} {d:+9.4f}   {lectura}")

    print(f"\n### B) SOLAPAMIENTO CON EL TITULO DEL TOP-1 ###\n")
    print(f"  fraccion de palabras significativas de la CONSULTA que estan")
    print(f"  literalmente en el titulo/descripcion del primer resultado\n")
    for nom in SISTEMAS:
        s4 = statistics.mean([v[nom]["solapamiento"] for v in a.values()])
        s1 = statistics.mean([v[nom]["solapamiento"] for v in b.values()])
        print(f"  {nom:10} 47 antiguas {s4:.3f}   169 nuevas {s1:.3f}   "
              f"delta {s1-s4:+.3f}")
    t4 = statistics.mean([len(tokens(q["query"])) for q in viejas])
    t1 = statistics.mean([len(tokens(q["query"])) for q in nuevas])
    print(f"\n  palabras significativas por consulta: antiguas {t4:.1f} | nuevas {t1:.1f}")

    print(f"\n### C) PUESTO DE LA PRIMERA FICHA NIVEL 2 ###\n")
    for nom in SISTEMAS:
        p4 = [v[nom]["puesto2"] for v in a.values() if v[nom]["puesto2"]]
        p1 = [v[nom]["puesto2"] for v in b.values() if v[nom]["puesto2"]]
        print(f"  {nom:10} antiguas: {statistics.mean(p4):.1f} en {len(p4)}/47 consultas"
              f" | nuevas: {statistics.mean(p1):.1f} en {len(p1)}/169")

    salida = {"desglose": {}, "solapamiento": {}, "n": {"antiguas": len(viejas), "nuevas": len(nuevas)}}
    for nom in SISTEMAS:
        salida["desglose"][nom] = {
            "n47": round(statistics.mean([v[nom]["ndcg"] for v in a.values()]), 4),
            "n169": round(statistics.mean([v[nom]["ndcg"] for v in b.values()]), 4)}
        salida["solapamiento"][nom] = {
            "n47": round(statistics.mean([v[nom]["solapamiento"] for v in a.values()]), 4),
            "n169": round(statistics.mean([v[nom]["solapamiento"] for v in b.values()]), 4)}
    (ENTREG / "control_sesgo_vocabulario.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: entregables/control_sesgo_vocabulario.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
