#!/usr/bin/env python3
"""
107_acuerdo_jueces.py — FASE A, paso 4. Control de fiabilidad del juicio.

Los 470 juicios existentes se generaron en junio con UN solo juez y sin control
de calidad. Si el juicio es ruidoso, toda metrica construida sobre el no vale.

Que mide este script:
  1. COHERENCIA INTERNA del juicio existente
     - ¿la razon del LLM concuerda con la etiqueta? (la razon "no trata sobre X"
       deberia acompanar a 'no_relevante')
     - ¿hay razones copiadas/plantilla?
  2. CONSISTENCIA: mismo TITULO juzgado en dos consultas distintas.
     Si el mismo dataset aparece en dos consultas y recibe etiquetas opuestas,
     hay ruido (o bien el juicio es dependiente de la consulta, que es correcto:
     el mismo dataset puede responder a una consulta y no a otra).

El juicio ES dependiente de la consulta, asi que (2) no es un error per se.
El control real de acuerdo entre jueces exige volver a juzgar una muestra con un
juez independiente: eso es lo que hace 108_doble_juicio.py.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

GT = Path(__file__).resolve().parent.parent / "entregables" / "ground_truth.jsonl"

# Una razon que empieza asi deberia acompanar a 'relevante'
INDICIOS_POSITIVOS = [
    r"^contiene", r"^incluye", r"^trata (sobre |de )?(el |la |los |las )?(datos|informaci)",
    r"^proporciona", r"^es (un |una )?(conjunto|dataset|estad)",
    r"^el conjunto (de datos )?(trata|contiene|incluye|proporciona)",
    r"^los datos", r"^ofrece",
]
INDICIOS_NEGATIVOS = [
    r"^no (trata|es|se refiere|contiene|incluye|corresponde)",
    r"^trata (sobre |de )?otro", r"^se refiere a ot(r|ra)",
    r"^aunque", r"^menciona pero", r"^no proporciona",
]


def main():
    entradas = []
    for ln in GT.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            entradas.append(json.loads(ln))

    print("=" * 74)
    print("CONTROL DE CALIDAD DEL JUICIO EXISTENTE")
    print("=" * 74)

    juicios = []
    for q in entradas:
        for c in (q.get("ground_truth", {}).get("resultados_clasificados") or []):
            juicios.append({"query_id": q.get("id"), "query": q.get("query"),
                            "title": c.get("title") or "",
                            "rel": c.get("relevancia"),
                            "razon": (c.get("razon") or "").strip()})
    print(f"\n  juicios: {len(juicios)}")
    print(f"  distribucion: {dict(Counter(j['rel'] for j in juicios))}")

    # ---------- 1. coherencia razon <-> etiqueta ----------
    print("\n### 1. COHERENCIA entre la razon y la etiqueta ###\n")
    incoherentes_pos = []   # etiqueta no_relevante pero razon positiva
    incoherentes_neg = []   # etiqueta relevante pero razon negativa
    for j in juicios:
        r = j["razon"].lower()
        es_pos = any(re.search(p, r) for p in INDICIOS_POSITIVOS)
        es_neg = any(re.search(p, r) for p in INDICIOS_NEGATIVOS)
        if j["rel"] == "no_relevante" and es_pos and not es_neg:
            incoherentes_pos.append(j)
        if j["rel"] == "relevante" and es_neg:
            incoherentes_neg.append(j)

    print(f"  'no_relevante' con razon que empieza en positivo: {len(incoherentes_pos)}"
          f" ({100*len(incoherentes_pos)/len(juicios):.1f} %)")
    for j in incoherentes_pos[:4]:
        print(f"     [{j['query_id']}] {j['razon'][:110]}")
    print(f"\n  'relevante' con razon que empieza en negativo : {len(incoherentes_neg)}"
          f" ({100*len(incoherentes_neg)/len(juicios):.1f} %)")
    for j in incoherentes_neg[:4]:
        print(f"     [{j['query_id']}] {j['razon'][:110]}")

    # ---------- 2. razones repetidas (plantilla) ----------
    print("\n### 2. RAZONES REPETIDAS (indicio de juicio mecanico) ###\n")
    reps = Counter(j["razon"] for j in juicios if j["razon"])
    repetidas = {r: n for r, n in reps.items() if n > 1}
    print(f"  razones distintas: {len(reps)} de {len(juicios)} juicios")
    print(f"  razones repetidas: {len(repetidas)}")
    for r, n in sorted(repetidas.items(), key=lambda kv: -kv[1])[:6]:
        print(f"     {n:>2}x  \"{r[:95]}\"")

    # ---------- 3. longitud ----------
    print("\n### 3. LONGITUD DE LAS RAZONES ###\n")
    L = [len(j["razon"]) for j in juicios]
    L.sort()
    print(f"  media {sum(L)/len(L):.0f}  mediana {L[len(L)//2]}  "
          f"min {L[0]}  max {L[-1]}")
    muy_cortas = sum(1 for x in L if x < 20)
    print(f"  razones < 20 caracteres: {muy_cortas} "
          f"(no argumentan nada, son etiquetas disfrazadas)")
    for j in juicios:
        if len(j["razon"]) < 20:
            print(f"     [{j['query_id']}] \"{j['razon']}\" -> {j['rel']}")

    # ---------- 4. mismo titulo en dos consultas ----------
    print("\n### 4. MISMO TITULO JUZGADO EN VARIAS CONSULTAS ###\n")
    por_titulo = defaultdict(list)
    for j in juicios:
        por_titulo[j["title"].lower().strip()].append(j)
    multi = {t: v for t, v in por_titulo.items() if len(set(x["query_id"] for x in v)) > 1}
    print(f"  titulos juzgados en mas de una consulta: {len(multi)}")
    discrep = 0
    for t, v in multi.items():
        etiquetas = {x["rel"] for x in v}
        if len(etiquetas) > 1:
            discrep += 1
    print(f"  de esos, con etiquetas CONTRADICTORIAS: {discrep}")
    print(f"\n  IMPORTANTE: el juicio depende de la CONSULTA, asi que un mismo")
    print(f"  dataset puede responder a una y no a otra. No es un error.")
    n_ej = 0
    for t, v in multi.items():
        if len({x["rel"] for x in v}) > 1 and n_ej < 3:
            n_ej += 1
            print(f"\n     \"{t[:75]}\"")
            for x in v:
                print(f"        [{x['query_id']}] {x['query']} -> {x['rel']}")

    # ---------- 5. resumen ----------
    print("\n" + "=" * 74)
    print("RESUMEN")
    print("=" * 74)
    problemas = []
    if len(incoherentes_pos) / len(juicios) > 0.05:
        problemas.append(f"{len(incoherentes_pos)} razones positivas con etiqueta "
                         f"no_relevante ({100*len(incoherentes_pos)/len(juicios):.1f} %)")
    if len(repetidas) > 5:
        problemas.append(f"{len(repetidas)} razones repetidas (plantilla)")
    if muy_cortas > len(juicios) * 0.05:
        problemas.append(f"{muy_cortas} razones vacias de contenido")

    if problemas:
        print("\n  El juicio existente tiene indicios de ruido:")
        for p in problemas:
            print(f"     - {p}")
        print("\n  => conviene rejuzgar una muestra con un juez independiente")
        print("     (108_doble_juicio.py) antes de confiar en las metricas.")
    else:
        print("\n  El juicio existente es internamente coherente:")
        print(f"     - {len(incoherentes_pos)} incoherencias razon/etiqueta")
        print(f"     - {len(repetidas)} razones repetidas")
        print(f"     - {muy_cortas} razones vacias")
        print("\n  No hay indicios de juicio mecanico.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
