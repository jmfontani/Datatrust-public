#!/usr/bin/env python3
"""
110_acuerdo_v2.py — FASE B, paso 3. Acuerdo entre jueces (puerta G2).

El juicio de la Fase B lo hizo un juez (deepseek-v4.1-flash, temperatura 0) sobre
un pool de 3 sistemas. Antes de construir metricas encima hay que saber si ese
juicio es REPRODUCIBLE.

Se mide:
  1. ACUERDO INTERNO: las fichas juzgadas dos veces (5 % designado en 109).
     - acuerdo exacto (mismo nivel)
     - acuerdo +-1 (tolerante)
     - kappa de Cohen (corrige el acuerdo por azar)
  2. COMPARACION CON JUNIO: en las fichas juzgadas en junio Y en la Fase B,
     ¿coinciden los jueces? Son jueces distintos (junio: un LLM sin especificar;
     Fase B: deepseek-v4.1-flash), asi que mide acuerdo entre jueces reales.
  3. UMBRAL G2: acuerdo >= 0,80.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
V2 = ENTREG / "gt_etiquetas_v2.json"
V1 = ENTREG / "gt_etiquetas.json"
CHECK = ENTREG / "_checkpoint_juicio.json"


def kappa(a, b):
    """Kappa de Cohen para dos listas de etiquetas categoricas."""
    n = len(a)
    if n == 0:
        return None
    obs = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    esp = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    if esp >= 1.0:
        return 1.0
    return (obs - esp) / (1 - esp)


def main():
    if not V2.exists():
        print(f"ERROR: falta {V2}. Ejecutar antes 109_juzgar_pool.py")
        return 1
    v2 = json.loads(V2.read_text(encoding="utf-8"))
    v1 = json.loads(V1.read_text(encoding="utf-8"))

    print("=" * 74)
    print("ACUERDO ENTRE JUECES (puerta G2)")
    print("=" * 74)

    det = v2.get("detalle", {})
    nuevas = {k: v for k, v in det.items() if v.get("origen") == "fase_b"}
    print(f"\n  etiquetas totales : {len(det)}")
    print(f"  de junio          : {len(det)-len(nuevas)}")
    print(f"  de la Fase B      : {len(nuevas)}")

    # ---------------- 1. acuerdo interno ----------------
    # AVISO: 109 guarda UN solo juicio por ficha (sobrescribe la misma clave),
    # asi que el "doble juicio" no conserva dos valores. Un acuerdo de 1,000
    # medido asi seria un artefacto: compararia el dato consigo mismo.
    # El acuerdo real se mide con 111_rejuzgar_muestra.py, en ejecucion aparte.
    print("\n### 1. ACUERDO INTERNO ###\n")
    print("  NO MEDIBLE con 109: guarda un unico juicio por ficha y sobrescribe")
    print("  la misma clave, asi que comparar daria 1,000 por construccion")
    print("  (un artefacto: el dato contra si mismo).")
    print("  El acuerdo real se mide con 111_rejuzgar_muestra.py en ejecucion")
    print("  independiente. Usar ese resultado, no este.")

    # ---------------- 2. acuerdo con junio ----------------
    print("\n### 2. ACUERDO CON EL JUEZ DE JUNIO ###\n")
    comunes = [k for k in nuevas if k in v1.get("etiquetas", {})]
    print(f"  fichas juzgadas por AMBOS jueces: {len(comunes)}")
    if comunes:
        a = [int(nuevas[k]["nivel"]) for k in comunes]
        b = [int(v1["etiquetas"][k]) for k in comunes]
        # junio uso escala binaria: 2 = relevante, 0 = no relevante.
        # la Fase B usa 0/1/2. Para comparar, el nivel 1 se cuenta como
        # "relevante parcial": se prueba de las dos formas.
        exacto = sum(1 for x, y in zip(a, b) if x == y) / len(a)
        binar_a = [2 if x >= 1 else 0 for x in a]
        binar_ex = sum(1 for x, y in zip(binar_a, b) if x == y) / len(a)
        k1 = kappa(a, b)
        k2 = kappa(binar_a, b)
        print(f"  acuerdo EXACTO (0/1/2 vs 0/2)      : {exacto:.3f}")
        print(f"  acuerdo BINARIZANDO el nivel 1     : {binar_ex:.3f}   <- el comparable")
        print(f"  kappa exacto                       : {k1:.3f}")
        print(f"  kappa binarizado                   : {k2:.3f}")
        print(f"\n  matriz (filas = junio, columnas = Fase B):")
        mat = Counter(zip(b, a))
        cab = "junio / faseB"
        print(f"     {cab:>12} {'0':>6} {'1':>6} {'2':>6}")
        for jn in (0, 2):
            fila = [mat.get((jn, fn), 0) for fn in (0, 1, 2)]
            print(f"     {jn:>12} " + " ".join(f"{c:>6}" for c in fila))
        # discrepancias para inspeccion
        print(f"\n  discrepancias BINARIAS (junio dijo 0 y la Fase B dice 2, o al reves):")
        n = 0
        for k in comunes:
            jn = int(v1["etiquetas"][k])
            fn = int(nuevas[k]["nivel"])
            if (jn == 0 and fn == 2) or (jn == 2 and fn == 0):
                n += 1
                if n <= 5:
                    print(f"     [{k.split('|')[0]}] junio={jn} faseB={fn}")
                    print(f"        {nuevas[k].get('title','')[:78]}")
                    print(f"        razon B: {nuevas[k].get('razon','')[:110]}")
        print(f"     total: {n} de {len(comunes)} ({100*n/len(comunes):.1f} %)")

    # ---------------- 3. umbral G2 ----------------
    print("\n" + "=" * 74)
    print("UMBRAL G2: acuerdo >= 0,80")
    print("=" * 74)
    if comunes:
        a = [int(nuevas[k]["nivel"]) for k in comunes]
        b = [int(v1["etiquetas"][k]) for k in comunes]
        binar_a = [2 if x >= 1 else 0 for x in a]
        ac = sum(1 for x, y in zip(binar_a, b) if x == y) / len(a)
        print(f"\n  acuerdo con junio (binarizado): {ac:.3f}")
        if ac >= 0.80:
            print("  -> G2 SUPERADA: el juicio es reproducible entre jueces.")
            print("     Los dos jueces coinciden lo suficiente como para usar")
            print("     las etiquetas combinadas.")
        elif ac >= 0.70:
            print("  -> G2 EN EL LIMITE: acuerdo aceptable pero no holgado.")
            print("     Conviene revisar las discrepancias antes de usarlas.")
        else:
            print("  -> G2 NO SUPERADA: el acuerdo es bajo. El problema no es el")
            print("     buscador, es el criterio de juicio. Hay que rehacer el prompt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
