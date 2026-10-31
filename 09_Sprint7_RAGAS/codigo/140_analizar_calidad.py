#!/usr/bin/env python3
"""
140_analizar_calidad.py — interpretar la linea base: ¿es 0,48 bueno o malo?

POR QUE
El nDCG@10 de 0,4854 no se interpreta solo. Hacen falta tres cosas:

  1. TECHO: con top_k=10 y el ideal tomado del top-10 ideal del GT, 1.0 es
     alcanzable, pero hay que ver cual es el maximo REALMENTE alcanzable por
     cualquier motor (el mejor top-10 posible segun el GT). Ese es el techo.
  2. SUELO: que da un ranking al azar. Da el rango util.
  3. DESGLOSE: en cuantas consultas el motor acierta (nivel 2 en el top-5) y en
     cuantas falla del todo (ningun nivel 2 en el top-10). Eso dice si el 0,48
     es "mediocre en todas" o "bueno en muchas y muy malo en unas pocas".

Ademas mide P@5 y MRR con DOS umbrales (2=estricto, 1=tema correcto) para
separar "no encuentra el tema" de "encuentra el tema pero falla el alcance".

Guarda los resultados crudos de la API para poder reanalizar sin volver a llamar.

USO
  python3 140_analizar_calidad.py
  python3 140_analizar_calidad.py --reanalizar   (usa el cache, no llama a la API)
"""
import argparse
import json
import math
import urllib.request
from pathlib import Path

API = "http://localhost:8000/search"
ENT = Path(__file__).resolve().parent.parent / "entregables"


def busca(q, top_k=10):
    # OJO: hay que pasar los pesos explicitamente. Sin ellos la API aplica sus
    # valores por defecto, que NO son los del sistema en produccion: medido,
    # nDCG 0,41 y cobertura 89 % (vs 0,4854 y 100 % con 0.7/0.3).
    body = {"query": q, "top_k": top_k,
            "semantic_weight": 0.7, "lexical_weight": 0.3}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=120).read())
    except Exception as e:
        return [], str(e)[:80]
    return d.get("results") or d.get("datasets") or [], None


def ndcg_top10(niveles, niveles_consulta, k=10):
    dcg = sum((x or 0) / math.log2(i + 2) for i, x in enumerate(niveles[:k]))
    ideal = sorted(niveles_consulta, reverse=True)[:k]
    idcg = sum(v / math.log2(i + 2) for i, v in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reanalizar", action="store_true")
    ap.add_argument("--cache", default=str(ENT / "cache_resultados_api.json"))
    ap.add_argument("--salida", default=str(ENT / "analisis_calidad.json"))
    args = ap.parse_args()

    # OJO: hay DOS ficheros con las mismas 47 consultas humanas y NO son iguales:
    #   ground_truth.jsonl   -> "censo población 2024"          (canonico, §7)
    #   consultas_v2.jsonl   -> "censo población 2024 España"   (ambito en el texto)
    # 38 de las 47 difieren. El evaluador oficial (132) usa el primero, porque la
    # decision §7 del proyecto puso el ambito en el CRITERIO del juez, no en el
    # texto: con "España" dentro, la consulta deja de parecerse al pool juzgado.
    # Usar consultas_v2.jsonl hunde el nDCG a 0,41 y la cobertura al 89 %.
    consultas = ([json.loads(l) for l in (ENT / "ground_truth.jsonl")
                 .read_text(encoding="utf-8").splitlines() if l.strip()]
                 + [json.loads(l) for l in (ENT / "consultas_limpias.jsonl")
                    .read_text(encoding="utf-8").splitlines() if l.strip()])
    gt = json.loads((ENT / "gt_etiquetas_v4.json").read_text(encoding="utf-8"))["etiquetas"]
    print(f"  consultas: {len(consultas)} · etiquetas: {len(gt)}")

    cache = Path(args.cache)
    if args.reanalizar and cache.exists():
        res_cache = json.loads(cache.read_text(encoding="utf-8"))
        print(f"  usando cache ({len(res_cache)} consultas)")
    else:
        res_cache = {}
        for i, q in enumerate(consultas):
            res, err = busca(q["query"], 10)
            res_cache[q["id"]] = [r.get("dataset_id") or r.get("id") for r in res]
            if (i + 1) % 25 == 0:
                print(f"  {i+1}/{len(consultas)} consultas", flush=True)
        cache.write_text(json.dumps(res_cache, ensure_ascii=False), encoding="utf-8")
        print(f"  cache guardado: {cache}")

    # --- metricas ---
    filas = []
    for q in consultas:
        qid = q["id"]
        ids = res_cache.get(qid, [])
        niveles = [gt.get(f"{qid}|{d}") for d in ids]
        juzgados = [x for x in niveles if x is not None]
        niveles_consulta = [v for k, v in gt.items() if k.startswith(f"{qid}|")]

        top5 = niveles[:5]
        filas.append({
            "query_id": qid,
            "query": q["query"],
            "n_resultados": len(ids),
            "cobertura": len(juzgados) / len(niveles) if niveles else 0.0,
            "ndcg": ndcg_top10(niveles, niveles_consulta),
            "p5_estricto": sum(1 for x in top5 if x == 2) / min(5, len(ids) or 5),
            "p5_tema": sum(1 for x in top5 if x is not None and x >= 1) / min(5, len(ids) or 5),
            "mrr_estricto": next((1 / (i + 1) for i, x in enumerate(niveles) if x == 2), 0.0),
            "mrr_tema": next((1 / (i + 1) for i, x in enumerate(niveles)
                              if x is not None and x >= 1), 0.0),
            "n2_top5": sum(1 for x in top5 if x == 2),
            "n2_top10": sum(1 for x in niveles if x == 2),
            "n0_top5": sum(1 for x in top5 if x == 0),
            "n_nivel2_total_gt": niveles_consulta.count(2),
            # techo: el mejor top-10 posible con los juicios de esta consulta
            "techo": ndcg_top10(sorted(niveles_consulta, reverse=True)[:10],
                                niveles_consulta),
        })

    def media(k):
        return sum(f[k] for f in filas) / len(filas)

    print()
    print("### METRICAS DE CALIDAD (sistema actual, top_k=10) ###")
    print(f"  nDCG@10 ................ {media('ndcg'):.4f}")
    print(f"  P@5 estricto (nivel 2) . {media('p5_estricto'):.4f}")
    print(f"  P@5 tema (nivel >=1) ... {media('p5_tema'):.4f}")
    print(f"  MRR estricto ........... {media('mrr_estricto'):.4f}")
    print(f"  MRR tema (nivel >=1) ... {media('mrr_tema'):.4f}")
    print(f"  cobertura .............. {media('cobertura'):.1%}")
    print(f"  TECHO medio alcanzable . {media('techo'):.4f}")

    print()
    print("### DESGLOSE: donde acierta y donde falla ###")
    con2 = [f for f in filas if f["n2_top5"] >= 1]
    sin2_top5 = [f for f in filas if f["n2_top5"] == 0]
    sin2_top10 = [f for f in filas if f["n2_top10"] == 0]
    print(f"  con >=1 acierto nivel 2 en top-5 : {len(con2):3}/{len(filas)} ({len(con2)/len(filas):.0%})")
    print(f"  SIN ninguno en top-5             : {len(sin2_top5):3}/{len(filas)} ({len(sin2_top5)/len(filas):.0%})")
    print(f"  SIN ninguno en top-10 (fallo)    : {len(sin2_top10):3}/{len(filas)} ({len(sin2_top10)/len(filas):.0%})")
    print()
    print(f"  nDCG medio del grupo CON acierto : {sum(f['ndcg'] for f in con2)/max(1,len(con2)):.4f}")
    print(f"  nDCG medio del grupo SIN acierto : {sum(f['ndcg'] for f in sin2_top10)/max(1,len(sin2_top10)):.4f}")

    # cuantos nivel-2 hay en el GT: si hay 1 solo, el top-1 acierta?
    unico = [f for f in filas if f["n_nivel2_total_gt"] == 1]
    if unico:
        top1 = sum(1 for f in unico if res_cache.get(f["query_id"], [None])[0]
                   and gt.get(f"{f['query_id']}|{res_cache[f['query_id']][0]}") == 2)
        print()
        print(f"  consultas con UN SOLO nivel-2 en el GT: {len(unico)}")
        print(f"     de ellas, el top-1 es ese nivel-2   : {top1} ({top1/len(unico):.0%})")
        print(f"     (azar: si el nivel-2 esta entre ~50 candidatas, ~2 %)")

    # distribucion del nDCG
    import statistics
    vals = sorted(f["ndcg"] for f in filas)
    print()
    print("### DISTRIBUCION DEL nDCG ###")
    for p in (10, 25, 50, 75, 90):
        print(f"  p{p:<3} {vals[int(len(vals)*p/100)]:.3f}", end="")
    print(f"   ·  media {statistics.mean(vals):.3f}")
    print(f"  consultas con nDCG = 0: {sum(1 for v in vals if v == 0)}")
    print(f"  consultas con nDCG > 0,8: {sum(1 for v in vals if v > 0.8)}")

    # las peores, para inspeccion
    peores = sorted(filas, key=lambda f: f["ndcg"])[:10]
    print()
    print("### LAS 10 PEORES (para inspeccionar) ###")
    for f in peores:
        print(f"  {f['ndcg']:.3f}  {f['query'][:52]:54} "
              f"(nivel2 en GT: {f['n_nivel2_total_gt']}, en top10: {f['n2_top10']})")

    salida = {"n": len(filas),
              "metricas": {"ndcg_at_10": round(media("ndcg"), 4),
                           "p5_estricto": round(media("p5_estricto"), 4),
                           "p5_tema": round(media("p5_tema"), 4),
                           "mrr_estricto": round(media("mrr_estricto"), 4),
                           "mrr_tema": round(media("mrr_tema"), 4),
                           "cobertura": round(media("cobertura"), 4),
                           "techo_medio": round(media("techo"), 4)},
              "desglose": {"con_acierto_top5": len(con2),
                           "sin_acierto_top5": len(sin2_top5),
                           "sin_acierto_top10": len(sin2_top10)},
              "por_consulta": filas}
    Path(args.salida).write_text(json.dumps(salida, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
    print(f"\n  guardado: {args.salida}")


if __name__ == "__main__":
    main()
