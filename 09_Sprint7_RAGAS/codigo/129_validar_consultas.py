#!/usr/bin/env python3
"""
129_validar_consultas.py — ¿puede el catálogo responder a estas consultas?

POR QUE ES EL PASO CRITICO
Una consulta que el catalogo NO puede responder no mide al recuperador: mide la
ausencia de datos. Si el pool no trae ninguna ficha relevante, esa consulta aporta
un nDCG cercano a 0 para todos los motores por igual, y lo unico que hace es meter
ruido en la media y ensanchar el intervalo.

El generador (128) recibio titulos reales para anclarse, pero eso NO garantiza que
cada consulta concreta tenga respuesta: el LLM puede inventar un fenomeno
plausible que el catalogo no tenga.

QUE MIDE
Para cada consulta nueva:
  - fichas que devuelve el motor hibrido en el top-10
  - solapamiento con la categoria: ¿las fichas traidas son del tema esperado?
  - si no devuelve NADA -> consulta invalida, se descarta
  - si devuelve fichas de otro tema -> consulta sospechosa, se revisa

SALIDA
  consultas_validadas.jsonl con las que pasan
  + informe de descartes
"""
import json
import re
import sys
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
NUEVAS = ENTREG / "consultas_nuevas.jsonl"
GT = ENTREG / "ground_truth.jsonl"
SALIDA = ENTREG / "consultas_validadas.jsonl"
API = "http://localhost:8000/search"

# categoria -> claves que deberian aparecer en las fichas traidas
CLAVES = {
    "empleo": ["empleo", "paro", "desempleo", "contrat", "ocupac", "laboral",
               "sepe", "afiliac", "salario", "cotizac"],
    "demografía": ["poblac", "censo", "habitante", "migrac", "residen", "padr",
                   "natalid", "mortalid", "edad", "demograf"],
    "economía": ["econ", "renta", "pib", "ipc", "inflac", "hacienda", "presupues",
                 "deuda", "fiscal", "financ", "precio"],
    "transporte": ["transport", "tr[aá]fic", "veh[ií]cul", "carreter", "aeropuert",
                   "ferroviar", "autobus", "movilidad", "accident"],
    "medio ambiente": ["ambient", "residu", "emision", "agua", "aire", "contamin",
                       "reciclaj", "energ[ií]a", "renovab", "clima"],
    "cultura": ["cultur", "bibliotec", "museo", "cine", "patrimoni", "libro",
                "espect[áa]cul", "art[ei]", "festival"],
    "deporte": ["deport", "federac", "licencia", "instalaci", "competic",
                "club", "piscina", "gimnasio"],
    "sanidad": ["salud", "sanitari", "hospital", "m[eé]dic", "camas", "enfermedad",
                "atenci[oó]n", "farmac", "vacun", "enfermer"],
    "educación": ["educac", "escolar", "universid", "alumn", "estudiant", "docente",
                  "centro", "beca", "formaci", "academ"],
    "ciencia y tecnología": ["cienc", "investigac", "tecnolog", "i+d", "innovac",
                             "digital", "datos abiertos", "software", "telecomunic",
                             "internet"],
    "sociedad y bienestar": ["social", "bienestar", "servici", "dependenc",
                             "familia", "igualdad", "vulnerab", "pobreza", "mayores",
                             "infancia", "discapac", "ayuda"],
    "ambigua": None,   # no se puede validar por tema: la ambiguedad es el proposito
}
GEN = {"empleo": "emp", "demografía": "dem", "economía": "eco", "transporte": "tra",
       "medio ambiente": "med", "cultura": "cul", "deporte": "dep", "sanidad": "san",
       "educación": "edu", "ciencia y tecnología": "cie",
       "sociedad y bienestar": "soc", "ambigua": "amb"}


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def busca(q, top_k=10):
    body = {"query": q, "top_k": top_k,
            "semantic_weight": 0.7, "lexical_weight": 0.3}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=90).read())
    return d.get("results") or []


def main():
    if not NUEVAS.exists():
        print("ERROR: falta consultas_nuevas.jsonl")
        return 1
    nuevas = [json.loads(l) for l in NUEVAS.read_text(encoding="utf-8").splitlines() if l.strip()]
    viejo = [json.loads(l) for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()]

    print("=" * 80)
    print("VALIDACION DE LAS CONSULTAS NUEVAS CONTRA EL CATALOGO REAL")
    print("=" * 80)
    print(f"\n  a validar: {len(nuevas)}\n")

    validas, sin_resultados, sospechosas = [], [], []
    for i, q in enumerate(nuevas, 1):
        try:
            res = busca(q["query"])
        except Exception as e:
            print(f"  [{i:3}/{len(nuevas)}] {q['id']:10} ERROR API: {str(e)[:50]}")
            continue

        if not res:
            sin_resultados.append(q)
            print(f"  [{i:3}/{len(nuevas)}] {q['id']:10} SIN RESULTADOS  «{q['query']}»")
            continue

        claves = CLAVES.get(q["categoria"])
        if claves is None:
            validas.append({**q, "_n_resultados": len(res),
                            "_coincide_tema": None, "_validacion": "ambigua (no validable por tema)"})
            print(f"  [{i:3}/{len(nuevas)}] {q['id']:10} OK {len(res):>2} res  «{q['query']}» (ambigua)")
            continue

        aciertos = 0
        for r in res:
            texto = norm(f"{r.get('title','')} {r.get('description','')} "
                         f"{r.get('theme_label','')}")
            if any(re.search(p, texto) for p in claves):
                aciertos += 1
        # Similitud del motor: es una senal DEL MOTOR, no de mis regex.
        sims = [float(r.get("score") or r.get("similarity") or 0) for r in res]
        top1 = sims[0] if sims else 0.0
        media = sum(sims) / len(sims) if sims else 0.0
        # El solapamiento lexico con palabras clave es SOLO INFORMATIVO.
        # Se probo como filtro y produce falsos positivos masivos: "mujeres en
        # puestos directivos" daba 0 % porque ninguna ficha contiene literalmente
        # "empleo"/"paro"/"laboral". Es el error de medir con patrones otra vez.
        ratio = aciertos / len(res)
        registro = {**q, "_n_resultados": len(res), "_coincide_tema": round(ratio, 2),
                    "_sim_top1": round(top1, 4), "_sim_media": round(media, 4),
                    "_validacion": "ok" if top1 >= 0.45 else "similitud_baja"}
        if top1 >= 0.45:
            validas.append(registro)
            print(f"  [{i:3}/{len(nuevas)}] {q['id']:10} OK {len(res):>2} res  "
                  f"sim {top1:.3f}  «{q['query']}»")
        else:
            sospechosas.append(registro)
            print(f"  [{i:3}/{len(nuevas)}] {q['id']:10} SIM BAJA {top1:.3f}  "
                  f"«{q['query']}»  -> {[r.get('title','')[:40] for r in res[:2]]}")

    print(f"\n### RESUMEN ###\n")
    print(f"  validas          : {len(validas)}")
    print(f"  sin resultados   : {len(sin_resultados)}  <- se descartan")
    print(f"  similitud baja   : {len(sospechosas)}  <- se revisan (no se descartan solas)")

    if sin_resultados:
        print(f"\n  consultas SIN RESULTADOS (descartadas):")
        for q in sin_resultados:
            print(f"     {q['id']:10} [{q['categoria']:22}] {q['query']}")

    if sospechosas:
        print(f"\n  consultas con SIMILITUD BAJA (top-1 < 0,45):")
        print(f"  -> no se descartan automaticamente: puede ser un termino poco")
        print(f"     frecuente pero con datos. La valida el juicio del pool.")
        for q in sospechosas:
            print(f"     {q['id']:10} [{q['categoria']:22}] sim {q['_sim_top1']:.3f}  {q['query']}")

    # el conjunto final: las validas + las viejas
    # Criterio final: pasan TODAS las que devuelven resultados. Descartar por un
    # umbral de similitud propio seria sustituir el juicio por una heuristica.
    # El unico descarte legitimo es "no devuelve nada" (0 casos).
    todas = validas + sospechosas
    validas = todas

    total = len(viejo) + len(validas)
    print(f"\n  GT quedaria: {len(viejo)} actuales + {len(validas)} nuevas = {total}")
    print(f"  reparto por categoria (total):")
    c = Counter([q["categoria"] for q in viejo] + [q["categoria"] for q in validas])
    for k, v in sorted(c.items(), key=lambda x: -x[1]):
        print(f"     {k:24} {v:>3}")
    print(f"\n  por dificultad:")
    d = Counter([q.get("dificultad") for q in viejo] + [q.get("dificultad") for q in validas])
    for k, v in sorted(d.items(), key=lambda x: -x[1]):
        print(f"     {str(k):12} {v:>3}")

    SALIDA.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in validas) + "\n",
                      encoding="utf-8")
    print(f"\n  guardado: {SALIDA}  ({len(validas)} consultas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
