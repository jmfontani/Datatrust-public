#!/usr/bin/env python3
"""
120_auditar_reescrituras.py — control de calidad del paso 1 de la Fase C.

POR QUE HACE FALTA
Reescribir la consulta cambia lo que se le muestra al juez. Si la reescritura
altera el FENOMENO (no solo el ambito), las 1.424 etiquetas dejan de ser validas
y el trabajo se pierde. El prompt lo prohibe, pero un LLM no siempre obedece:
hay que verificar, no confiar.

QUE COMPRUEBA
1. Longitud: sigue siendo una busqueda (3-7 palabras), no una frase.
2. Si solo se ha anadido ambito (caso limpio) o si hay mas cambios.
3. Presencia/ausencia de terminos del fenomeno original.
4. Casos donde el ambito era ya explicito (no debia cambiar nada).
5. Duplicados: dos consultas que quedarian identicas.
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
V2 = ENTREG / "consultas_v2.jsonl"

# terminos que indican ambito (no fenomeno)
AMBITO = {"espana", "espanol", "espanola", "espanoles", "nacional", "estatal",
          "andalucia", "cataluna", "madrid", "municipios", "comunidades",
          "autonomas", "autonomica", "provincias", "ciudades"}

STOP = {"de", "del", "la", "el", "los", "las", "en", "por", "y", "vs", "a", "e",
        "al", "un", "una"}


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def palabras(s):
    return [p for p in re.findall(r"[a-z0-9]+", norm(s)) if p not in STOP]


def main():
    if not V2.exists():
        print("ERROR: falta consultas_v2.jsonl")
        return 1
    qs = [json.loads(l) for l in V2.read_text(encoding="utf-8").splitlines() if l.strip()]

    print("=" * 80)
    print("AUDITORIA DE LAS REESCRITURAS DE CONSULTA (Fase C, paso 1)")
    print("=" * 80)
    print(f"\n  consultas: {len(qs)}\n")

    problemas = []
    largas, perdidas, ganadas, solo_ambito = [], [], [], []

    for q in qs:
        o, n = q.get("query_original", q["query"]), q["query"]
        if o == n:
            continue
        po, pn = palabras(o), palabras(n)
        wo, wn = len(n.split()), len(n.split())

        # 1. longitud
        if len(n.split()) > 8:
            largas.append((q["id"], n, len(n.split())))

        # 2. terminos del fenomeno que se pierden
        perdidos = [p for p in po if p not in pn and p not in AMBITO]
        anadidos = [p for p in pn if p not in po]

        if perdidos:
            perdidas.append((q["id"], o, n, perdidos))

        # 3. ¿solo se anadio ambito?
        if not perdidos:
            extra = [p for p in anadidos if p not in AMBITO]
            if extra:
                ganadas.append((q["id"], o, n, extra))
            else:
                solo_ambito.append(q["id"])

    print("### 1) LONGITUD ###\n")
    if largas:
        for i, t, n in largas:
            print(f"  LARGA ({n} palabras) [{i}] {t}")
    else:
        print("  ninguna supera 8 palabras (siguen siendo busquedas)")

    print(f"\n### 2) REESCRITURAS QUE SOLO AÑADEN AMBITO (limpias) — {len(solo_ambito)} ###\n")

    print(f"### 3) REESCRITURAS QUE AÑADEN ALGO MAS QUE AMBITO — {len(ganadas)} ###\n")
    print("  (revisar: puede ser una mejora de redaccion o un cambio de fenomeno)\n")
    for i, o, n, extra in ganadas:
        print(f"  [{i}] {o}")
        print(f"        -> {n}")
        print(f"        anadido: {extra}")

    print(f"\n### 4) TERMINOS DEL FENOMENO QUE DESAPARECEN — {len(perdidas)} ###\n")
    print("  (los mas peligrosos: el juez puede haber valorado el fenomeno viejo)\n")
    for i, o, n, p in perdidas:
        print(f"  [{i}] {o}")
        print(f"        -> {n}")
        print(f"        perdido: {p}")

    # 5. duplicados
    print(f"\n### 5) DUPLICADOS ###\n")
    c = Counter(norm(q["query"]) for q in qs)
    dups = {k: v for k, v in c.items() if v > 1}
    if dups:
        for k, v in dups.items():
            ids = [q["id"] for q in qs if norm(q["query"]) == k]
            print(f"  {v}x  {k}  -> {ids}")
    else:
        print("  ninguno")

    n_problemas = len(largas) + len(perdidas) + len(dups)
    print(f"\n{'=' * 80}")
    print(f"  resumen: {len(largas)} largas · {len(ganadas)} con algo mas que ambito · "
          f"{len(perdidas)} con terminos perdidos · {len(dups)} duplicados")
    print(f"  requieren revision manual: {n_problemas + len(ganadas)}")
    print(f"{'=' * 80}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
