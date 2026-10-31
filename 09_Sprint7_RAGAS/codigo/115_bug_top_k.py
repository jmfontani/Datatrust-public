#!/usr/bin/env python3
"""
115_bug_top_k.py — BUG DEL MOTOR: el ranking depende de top_k.

EVIDENCIA
  "consumo agua embalses" con top_k=5, 10, 20, 30 da CINCO PRIMEROS DISTINTOS.
  Un motor de recuperacion NUNCA deberia cambiar su orden segun cuantos
  resultados se pidan.

CAUSA (routes v07, main_v2_final_v07.py)
  Los dos motores recuperan con LIMIT top_k*3:

      LIMIT %s   ...   tuple(params + [request.top_k * 3])        (semantico)
      LIMIT %s   ...   request.top_k * 3                          (lexico)

  y despues NORMALIZAN por el maximo del conjunto recuperado:

      max_rank = max(rank de las filas traidas)                   (linea 847)
      r['rank'] = r['rank'] / max_rank                            (linea 850)
      max_lex_score = max(score del conjunto)                     (linea 789)

  El cociente r/max no es "la relevancia normalizada": es la relevancia
  RELATIVA AL MEJOR RESULTADO QUE HAYA ENTRADO EN EL CORTE. Al cambiar top_k
  cambia el corte, cambia el maximo, y cambia TODOS los scores.

  El maximo mismo no tiene sentido como normalizador: ts_rank_cd devuelve
  valores sin cota superior, y dividir por el maximo garantiza que el primero
  siempre valga 1,0 (o sea, se descarta la magnitud absoluta de la coincidencia).

CONSECUENCIA
  Si el ranking depende de top_k, cualquier metrica medida con top_k=10 no dice
  nada sobre el comportamiento con top_k=5 o 20. Y peor: el pool de juicio se
  construyo con top-20, pero se evalua con top-10, asi que se juzgaron
  documentos que la configuracion evaluada no devuelve y viceversa.
"""
import json
import sys
import urllib.request
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
GT = ENTREG / "ground_truth.jsonl"
API = "http://localhost:8000/search"
SALIDA = ENTREG / "bug_top_k.json"


def busca(q, k, w):
    b = {"query": q, "top_k": k}
    b.update(w)
    r = urllib.request.Request(API, data=json.dumps(b).encode(),
                               headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(r, timeout=90).read())
    return [(x.get("id"), x.get("score"), x.get("semantic_score"),
             x.get("lexical_score")) for x in (d.get("results") or [])]


def main():
    consultas = [json.loads(l) for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()]
    W = {"semantic_weight": 0.7, "lexical_weight": 0.3}
    KS = (5, 10, 20, 30)

    print("=" * 74)
    print("BUG: EL RANKING DEPENDE DE top_k")
    print("=" * 74)
    print(f"\n  consultas: {len(consultas)}   configuracion: 0.7/0.3")
    print(f"  top_k probados: {KS}\n")

    # ---- 1. ¿cuantas consultas cambian su primer resultado al cambiar top_k? ----
    cambios_1 = 0
    cambios_5 = 0
    incoherentes = 0
    detalle = []
    for q in consultas:
        primeros = {}
        cincos = {}
        scores = {}
        for k in KS:
            res = busca(q["query"], k, W)
            if res:
                primeros[k] = res[0][0]
                cincos[k] = tuple(r[0] for r in res[:5])
                scores[k] = res[0][1]
        if len(set(primeros.values())) > 1:
            cambios_1 += 1
        if len(set(cincos.values())) > 1:
            cambios_5 += 1
        # coherencia interna: el top-5 de top_k=5 deberia estar en el top-10
        if 5 in cincos and 10 in cincos:
            fuera = [x for x in cincos[5] if x not in [r[0] for r in busca(q["query"], 10, W)]]
            if fuera:
                incoherentes += 1
        detalle.append({
            "query_id": q["id"],
            "primeros": {str(k): v for k, v in primeros.items()},
            "scores_primero": {str(k): v for k, v in scores.items()},
            "cambia_primero": len(set(primeros.values())) > 1,
            "cambia_top5": len(set(cincos.values())) > 1,
        })

    n = len(consultas)
    print("### 1. IMPACTO ###\n")
    print(f"  consultas cuyo PRIMER resultado cambia al cambiar top_k : "
          f"{cambios_1}/{n} ({100*cambios_1/n:.0f} %)")
    print(f"  consultas cuyo TOP-5 cambia al cambiar top_k           : "
          f"{cambios_5}/{n} ({100*cambios_5/n:.0f} %)")
    print(f"  consultas donde el top-5 NO esta contenido en el top-10: "
          f"{incoherentes}/{n}")

    print("\n### 2. EJEMPLOS ###\n")
    for d in detalle[:4]:
        print(f"  [{d['query_id']}]")
        for k in KS:
            pid = d["primeros"].get(str(k))
            sc = d["scores_primero"].get(str(k))
            print(f"     top_k={k:<3} primero={str(pid).split('/')[-1][:22]:22} score={sc}")
        print()

    print("### 3. LA CAUSA EN EL CODIGO ###\n")
    print("  main_v2_final_v07.py")
    for ln, txt in (
        (741, "LIMIT %s   <- semantic: top_k * 3"),
        (843, "LIMIT %s   <- lexical:  top_k * 3"),
        (847, "max_rank = max(rank de las filas traidas)"),
        (850, "r['rank'] = r['rank'] / max_rank    <- normaliza por el maximo DEL CORTE"),
        (789, "max_lex_score = max(score del conjunto)  <- idem"),
        (792, "r['score'] = r['score'] / max_lex_score"),
    ):
        print(f"     linea {ln:>4}: {txt}")

    print("\n  El normalizador es el maximo de lo que entrego el corte, no una")
    print("  constante. Cambiar top_k mueve el corte, mueve el maximo y mueve")
    print("  todos los scores. Ademas, dividir por el maximo hace que el primero")
    print("  valga siempre 1,0: se tira la magnitud absoluta de la coincidencia.")

    print("\n### 4. CONSECUENCIA PARA LAS METRICAS ###\n")
    print("  * El pool se construyo con top-20 y se evalua con top-10: los")
    print("    conjuntos NO coinciden (medido: 10 de 235 fichas del top-10 no")
    print("    estaban en el pool de su consulta).")
    print("  * Toda cifra hay que leerla CON su top_k, y no se puede extrapolar")
    print("    de top-10 a top-5.")
    print("  * Arreglarlo cambia TODAS las cifras anteriores, para bien: el")
    print("    ranking seria estable y comparable entre experimentos.")

    SALIDA.write_text(json.dumps({
        "meta": {"consultas": n, "top_ks": list(KS),
                 "config": W, "n_cambia_primero": cambios_1,
                 "n_cambia_top5": cambios_5, "n_incoherentes": incoherentes},
        "detalle": detalle}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
