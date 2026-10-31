#!/usr/bin/env python3
"""
113_sensibilidad_umbral.py — FASE B. ¿Cuenta el nivel "otro alcance" como acierto?

El nivel 1 ("mismo tema, otro alcance") es el 16 % del GT. Que cuente o no como
relevante es una DECISION, y mueve el resultado. Este script la cuantifica para
que la eleccion se haga sabiendo su efecto, no por costumbre.

Se mide el mismo sistema con las dos politicas:
  * severa  (umbral 2): solo "responde" cuenta
  * amplia  (umbral 1): "otro alcance" tambien cuenta
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.gt_metrics import EtiquetasGT, evaluar, intervalo_confianza

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
GT = ENTREG / "ground_truth.jsonl"
ETIQ_B = ENTREG / "gt_etiquetas_v2.json"
API = "http://localhost:8000/search"
SALIDA = ENTREG / "sensibilidad_umbral.json"

SISTEMAS = {
    "actual (0.7/0.3)": {"semantic_weight": 0.7, "lexical_weight": 0.3},
    "semantico (1.0/0.0)": {"semantic_weight": 1.0, "lexical_weight": 0.0},
    "lexico (0.0/1.0)": {"semantic_weight": 0.0, "lexical_weight": 1.0},
}


def busca(query, **kw):
    body = {"query": query, "top_k": 10}
    body.update(kw)
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=90).read())
    except Exception:
        return {}


def main():
    consultas = [json.loads(l) for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()]
    # cachear los rankings una sola vez: el umbral no cambia la busqueda
    print("=" * 74)
    print("SENSIBILIDAD AL UMBRAL DE RELEVANCIA")
    print("=" * 74)
    print(f"\n  consultas: {len(consultas)}")

    print("\n  recogiendo rankings de la API...")
    rankings = {}
    for nom, kw in SISTEMAS.items():
        rankings[nom] = {}
        for q in consultas:
            rankings[nom][q["id"]] = busca(q["query"], **kw).get("results", [])
        print(f"    {nom:22} listo")

    gt = EtiquetasGT(ETIQ_B)
    res = {}
    for nom in SISTEMAS:
        res[nom] = {}
        for polit, umbral in (("severa (solo 'responde')", 2), ("amplia ('otro alcance' cuenta)", 1)):
            # NO filtrar por "tiene resultados": una consulta que devuelve vacio
            # es un fallo del motor y debe contar como 0. Filtrarla infla la media.
            filas = [evaluar(q["id"], rankings[nom][q["id"]], gt, umbral=umbral)
                     for q in consultas]
            vacias = sum(1 for q in consultas if not rankings[nom][q["id"]])
            res[nom][polit] = {
                "n": len(filas),
                "vacias": vacias,
                "p5": intervalo_confianza([f["precision_at_5"] for f in filas]),
                "ndcg": intervalo_confianza([f["ndcg_at_10"] for f in filas]),
                "mrr": intervalo_confianza([f["mrr"] for f in filas]),
            }

    print("\n### RESULTADOS ###\n")
    print(f"  {'sistema':22} {'politica':30} {'P@5':>9} {'nDCG@10':>10} {'MRR':>9}")
    print("  " + "-" * 84)
    for nom in SISTEMAS:
        for polit in res[nom]:
            r = res[nom][polit]
            print(f"  {nom:22} {polit:30} {r['p5'][0]:>9.4f} {r['ndcg'][0]:>10.4f} "
                  f"{r['mrr'][0]:>9.4f}   vacias {r['vacias']:>2}")
        a = res[nom]["severa (solo 'responde')"]
        b = res[nom]["amplia ('otro alcance' cuenta)"]
        print(f"  {'':22} {'-> efecto de la politica':30} "
              f"{b['p5'][0]-a['p5'][0]:>+9.4f} {b['ndcg'][0]-a['ndcg'][0]:>+10.4f} "
              f"{b['mrr'][0]-a['mrr'][0]:>+9.4f}")
        print()

    print("### LECTURA ###\n")
    for nom in SISTEMAS:
        a = res[nom]["severa (solo 'responde')"]["ndcg"][0]
        b = res[nom]["amplia ('otro alcance' cuenta)"]["ndcg"][0]
        print(f"  {nom:22} el nivel 1 mueve el nDCG {b-a:+.4f}")
    print()
    print("  Consecuencia: si el efecto es grande, la politica hay que declararla")
    print("  junto a la cifra; si es pequeno, la eleccion es secundaria.")
    print()
    print("  RECOMENDACION: publicar la politica SEVERA (solo 'responde') como")
    print("  cifra principal (responde a '¿me da la respuesta?') y la AMPLIA como")
    print("  secundaria (mide si acierta el tema aunque falle el ambito).")

    SALIDA.write_text(json.dumps({"meta": {"fase": "B", "etiquetas": len(gt)},
                                  "resultados": res},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
