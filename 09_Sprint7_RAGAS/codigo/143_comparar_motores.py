#!/usr/bin/env python3
"""
143_comparar_motores.py — FASE F: ¿BGE-M3 es mejor que MiniLM?

PREGUNTA QUE RESPONDE
La del principio: con el mismo instrumento (214 consultas, GT v4, criterio de
ambito corregido), ¿un motor de recuperacion es mejor que otro?

COMO SE MIDE SIN CAMBIAR LA API
No se despliega BGE-M3 en la API. Se hace la busqueda A MANO con cada modelo:

  1. vectoriza la CONSULTA con el modelo (mismo texto que el documento)
  2. coseno contra la columna de ese modelo (embedding / embedding_bge) en la BD
  3. top-10 -> se evalua con utils/gt_metrics (el instrumento canonico)

Ventaja: los dos motores se miden en la MISMA sesion, misma maquina, mismo codigo,
mismo GT y mismas consultas. No hay ventana en la que el buscador este roto, y la
comparacion es motor contra motor, sin nada mas moviendose.

SIMETRIA (importante)
La consulta se vectoriza CRUDA (el texto tal cual) para LOS DOS modelos, que es lo
que hace hoy la API en produccion con MiniLM (`get_embedding(expanded_query)`).
No se anade esquema a la consulta: anadirlo seria un cambio de metodo, y aplicarlo
solo a un modelo contaminaria la comparacion. La asimetria consulta-cruda vs
documento-estructurado es la del sistema actual y se mantiene identica en los dos,
para que la unica variable sea el modelo.

USO
  python3 143_comparar_motores.py
  python3 143_comparar_motores.py --top-k 10 --salida ../entregables/fase_e_BGE_vs_MiniLM.json
"""
import argparse
import json
import math
import statistics
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import psycopg2
from psycopg2.extras import DictCursor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.gt_metrics import EtiquetasGT, evaluar, intervalo_confianza   # noqa: E402

ENT = Path(__file__).resolve().parent.parent / "entregables"
DB = dict(host="buscador_postgres", port=5432, dbname="buscador",
          user="postgres", password="postgres")
OLLAMA = "http://172.17.0.1:11434/api/embed"

MINILM = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MINILM_REV = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
BGE = "bge-m3"


def emb_bge(textos):
    body = json.dumps({"model": BGE, "input": textos,
                       "options": {"num_ctx": 1024}}).encode()
    req = urllib.request.Request(OLLAMA, data=body,
                                 headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=1800).read())
    return np.array(d["embeddings"], dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--etiquetas", default=str(ENT / "gt_etiquetas_v4.json"),
                    help="GT a usar: v4 (pool del motor actual) o v5 (pool conjunto)")
    ap.add_argument("--col-minilm", default="embedding",
                    help="columna de MiniLM: 'embedding' (texto de la limpieza) o "
                         "'embedding_minilm_aprox' (MISMO texto que BGE -> sin confound)")
    ap.add_argument("--salida", default=str(ENT / "fase_e_BGE_vs_MiniLM.json"))
    args = ap.parse_args()

    consultas = ([json.loads(l) for l in (ENT / "ground_truth.jsonl")
                  .read_text(encoding="utf-8").splitlines() if l.strip()]
                 + [json.loads(l) for l in (ENT / "consultas_limpias.jsonl")
                    .read_text(encoding="utf-8").splitlines() if l.strip()])
    gt = EtiquetasGT(args.etiquetas)
    print(f"  consultas: {len(consultas)} · etiquetas: {len(gt)}")

    # modelo viejo (el que genero la columna `embedding`)
    from sentence_transformers import SentenceTransformer
    print(f"  cargando {MINILM}@{MINILM_REV[:8]} ...", flush=True)
    m_old = SentenceTransformer(MINILM, revision=MINILM_REV)

    conn = psycopg2.connect(**DB)
    resultados = {}
    t0 = time.time()

    with conn.cursor(cursor_factory=DictCursor) as cur:
        # comprobar que la columna nueva esta completa
        cur.execute("SELECT COUNT(*) AS n FROM datasets WHERE embedding_bge IS NULL")
        nulos = cur.fetchone()["n"]
        if nulos:
            print(f"  AVISO: {nulos} fichas sin embedding_bge; se excluyen del top-k de BGE")
        cur.execute("SELECT COUNT(*) AS n FROM datasets WHERE embedding IS NULL")
        print(f"  fichas sin embedding (MiniLM): {cur.fetchone()['n']}")

        for i, q in enumerate(consultas):
            qid, texto_q = q["id"], q["query"]
            par = []
            for nom in ("minilm", "bge"):
                col = args.col_minilm if nom == "minilm" else "embedding_bge"
                if nom == "minilm":
                    qv = m_old.encode(texto_q, normalize_embeddings=True).tolist()
                    lit = "[" + ",".join(map(str, qv)) + "]"
                    sql = (f"SELECT dataset_id, 1 - ({col} <=> %s::vector) AS sim "
                           f"FROM datasets WHERE {col} IS NOT NULL "
                           f"ORDER BY {col} <=> %s::vector LIMIT %s")
                    cur.execute(sql, (lit, lit, args.top_k))
                else:
                    qv = emb_bge([texto_q])[0].tolist()
                    lit = "[" + ",".join(map(str, qv)) + "]"
                    sql = (f"SELECT dataset_id, 1 - ({col} <=> %s::vector) AS sim "
                           f"FROM datasets WHERE {col} IS NOT NULL "
                           f"ORDER BY {col} <=> %s::vector LIMIT %s")
                    cur.execute(sql, (lit, lit, args.top_k))
                filas = cur.fetchall()
                # list(...) y no un generador: un generador se agota al evaluar y
                # captura `filas` por referencia (se reasigna cada consulta)
                par.append([{"dataset_id": r["dataset_id"], "sim": float(r["sim"])}
                            for r in filas])
            resultados[qid] = {"query": texto_q, "minilm": par[0], "bge": par[1]}
            if (i + 1) % 25 == 0:
                print(f"  {i+1}/{len(consultas)} ({time.time()-t0:.0f}s)", flush=True)

    # --- CONTROL DE INSTRUMENTO: cobertura y sesgo de pool ---
    # Si el pool de juicios se construyo SOLO con el motor actual, un motor nuevo
    # trae fichas sin juzgar. El nDCG las puntua como 0, pero eso mide la falta de
    # juicio, NO que el motor falle. Hay que medirlo antes de interpretar.
    cob_por_motor, pares_nuevos, sesgo = {}, {}, {}
    for nom in ("minilm", "bge"):
        juz = nojuz = 0
        nuevos = set()
        for qid, dd in resultados.items():
            for f in dd[nom]:
                if gt.nivel(qid, f["dataset_id"]) is None:
                    nojuz += 1; nuevos.add((qid, f["dataset_id"]))
                else:
                    juz += 1
        cob_por_motor[nom] = {"juzgados": juz, "no_juzgados": nojuz,
                              "cobertura": juz / (juz + nojuz) if (juz + nojuz) else 0.0}
        pares_nuevos[nom] = nuevos
    union = pares_nuevos["minilm"] | pares_nuevos["bge"]
    solo_bge = pares_nuevos["bge"] - pares_nuevos["minilm"]
    solo_min = pares_nuevos["minilm"] - pares_nuevos["bge"]
    sesgo = {"pares_sin_juzgar_union": len(union),
             "solo_BGE_aporta": len(solo_bge),
             "solo_MiniLM_aporta": len(solo_min),
             "solapamiento_top10": (len(pares_nuevos["minilm"] & pares_nuevos["bge"])
                                    / len(union) if union else 0.0)}
    print()
    print("### CONTROL DE INSTRUMENTO (antes de interpretar) ###")
    for nom in ("minilm", "bge"):
        c = cob_por_motor[nom]
        print(f"  {nom:7}: cobertura {c['cobertura']:6.1%} "
              f"({c['juzgados']} juzgados, {c['no_juzgados']} SIN juzgar)")
    print(f"  pares sin juzgar en la union     : {sesgo['pares_sin_juzgar_union']}")
    print(f"  pares que SOLO aporta BGE        : {sesgo['solo_BGE_aporta']}")
    print(f"  pares que SOLO aporta MiniLM     : {sesgo['solo_MiniLM_aporta']}")
    print(f"  solapamiento de los top-10       : {sesgo['solapamiento_top10']:.1%}")
    if cob_por_motor["bge"]["cobertura"] < 0.9:
        print()
        print("  AVISO: cobertura baja en BGE. El pool de juicios se construyo con")
        print("  otros motores, asi que parte de lo que BGE devuelve NUNCA se juzgo.")
        print("  El nDCG la puntua como 0 y el motor parece peor de lo que es.")
        print("  Comparacion NO valida hasta juzgar el pool conjunto.")

    # --- evaluacion con el instrumento canonico ---
    met = {}
    print()
    print("### METRICAS (mismo GT, mismas consultas, mismo top_k) ###\n")
    print(f"  {'motor':22} {'nDCG@10':>8} {'IC95':>20} {'P@5':>7} {'MRR':>7} {'cob':>6}")
    print(f"  {'-'*22} {'-'*8} {'-'*20} {'-'*7} {'-'*7} {'-'*6}")
    for nom in ("minilm", "bge"):
        nd, p5, mr, cb = [], [], [], []
        for qid, d in resultados.items():
            res = [{"dataset_id": f["dataset_id"]} for f in d[nom]]
            m = evaluar(qid, res, gt, k_precision=5, k_ndcg=args.top_k)
            nd.append(m["ndcg_at_10"]); p5.append(m["precision_at_5"])
            mr.append(m["mrr"]); cb.append(m["cobertura_top10"])
        mu, lo, hi = intervalo_confianza(nd)
        met[nom] = {"ndcg": mu, "ic95": [lo, hi], "p5": statistics.mean(p5),
                    "mrr": statistics.mean(mr), "cobertura": statistics.mean(cb),
                    "por_consulta": nd}
        etq = "MiniLM (actual)" if nom == "minilm" else "BGE-M3 (candidato)"
        print(f"  {etq:22} {mu:8.4f} [{lo:.4f} · {hi:.4f}] "
              f"{statistics.mean(p5):7.4f} {statistics.mean(mr):7.4f} "
              f"{statistics.mean(cb):5.1%}")

    # --- comparacion PAREADA (elimina la varianza entre consultas) ---
    print()
    print("### COMPARACION PAREADA ###\n")
    dif = [a - b for a, b in zip(met["bge"]["por_consulta"], met["minilm"]["por_consulta"])]
    mu, lo, hi = intervalo_confianza(dif)
    n = len(dif)
    ee = statistics.stdev(dif) / math.sqrt(n)
    mmd = 1.96 * ee
    cruza = (lo is None or hi is None) or (lo < 0 < hi)
    print(f"  BGE-M3 - MiniLM : {mu:+.4f}  IC95 [{lo:+.4f} · {hi:+.4f}]")
    print(f"  mejora minima detectable (n={n}): {mmd:.4f}")
    print()
    if cruza:
        print("  VEREDICTO: NO se puede concluir que BGE-M3 sea mejor")
    elif mu > mmd:
        print("  VEREDICTO: BGE-M3 ES MEJOR (la diferencia supera lo detectable)")
    else:
        print(f"  VEREDICTO: mejora en la direccion esperada, pero {mu:.4f} < umbral "
              f"{mmd:.4f}: no concluyente con este tamano de muestra")
    print()
    print(f"  consultas donde BGE-M3 gana : {sum(1 for d in dif if d > 0.001)}")
    print(f"  consultas donde empata      : {sum(1 for d in dif if abs(d) <= 0.001)}")
    print(f"  consultas donde MiniLM gana : {sum(1 for d in dif if d < -0.001)}")

    salida = {"consultas": len(consultas), "top_k": args.top_k,
              "columna_minilm": args.col_minilm,
              "modelos": {"minilm": f"{MINILM}@{MINILM_REV}", "bge": BGE},
              "metricas": {k: {kk: vv for kk, vv in v.items() if kk != "por_consulta"}
                           for k, v in met.items()},
              "comparacion": {"diff": mu, "ic95": [lo, hi], "mmd": mmd,
                              "cruza_cero": cruza, "n": n},
              "por_consulta": {q: d["query"] for q, d in resultados.items()},
              "resultados": {q: {n2: [f["dataset_id"] for f in d[n2]]
                                 for n2 in ("minilm", "bge")}
                             for q, d in resultados.items()},
              "cobertura_por_motor": cob_por_motor,
              "sesgo_de_pool": sesgo}
    Path(args.salida).write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")
    print(f"\n  guardado: {args.salida}")


if __name__ == "__main__":
    main()
