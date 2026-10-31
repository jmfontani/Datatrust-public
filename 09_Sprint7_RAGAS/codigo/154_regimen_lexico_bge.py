#!/usr/bin/env python3
"""154_regimen_lexico_bge.py — re-verifica con BGE el hallazgo de la Fase C.

LA TESIS A PROBAR (Fase C, con MiniLM y otro instrumento)
  "el hibrido es el unico que no pierde en ningun regimen":
    - consultas que COPIAN vocabulario del catalogo (solapamiento alto):
      gana el canal lexico (0,7331 vs 0,5468)
    - consultas que NO lo copian (solapamiento bajo): lexico y semantico empatan
      (0,3517/0,3533) y el HIBRIDO gana (0,4223)
Si se mantiene con BGE, sostiene conservar el peso lexico.

COMO SE MIDE (misma logica que la Fase C)
  Regimen = solapamiento de vocabulario consulta-catalogo:
    token de la consulta presente en el texto de la ficha (título + descripcion),
    sobre el top-10 de cada sistema; tercios del solapamiento por consulta.

  Sistemas: con BGE en produccion, los tres repartos por pesos en /search:
    actual (0,7/0,3) · semantico (1,0/0,0) · lexico (0,0/1,0)
  Consultas GT: las 214 (47 humanas + 167 limpias), instrumento canonico.

USO
  python3 154_regimen_lexico_bge.py
"""
import json
import statistics
import time
import urllib.request
from pathlib import Path

sys_path = str(Path(__file__).resolve().parent)
import sys
sys.path.insert(0, sys_path)
from utils.gt_metrics import EtiquetasGT, evaluar, intervalo_confianza  # noqa: E402

E = Path(__file__).resolve().parent.parent / "entregables"
API = "http://localhost:8000/search"
TOP_K = 10
SISTEMAS = {
    "actual (0.7/0.3)": (0.7, 0.3),
    "semantico (1.0/0.0)": (1.0, 0.0),
    "lexico (0.0/1.0)": (0.0, 1.0),
}


def busca(q, sem, lex):
    body = {"query": q, "top_k": TOP_K, "semantic_weight": sem, "lexical_weight": lex}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=300).read())
    return d.get("results") or []


def main():
    consultas = ([json.loads(l) for l in (E / "ground_truth.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
                 + [json.loads(l) for l in (E / "consultas_limpias.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()])
    gt = EtiquetasGT(E / "gt_etiquetas_v5.json")
    print(f"  consultas: {len(consultas)} · etiquetas: {len(gt)}", flush=True)

    # ---------------------------------------------------------------
    # 1. una sola pasada por consulta/sistema: resultados + ndcg + solapamiento
    # ---------------------------------------------------------------
    R = {k: [] for k in SISTEMAS}          # ids por consulta
    S = {k: [] for k in SISTEMAS}          # solapamiento por consulta
    nd = {k: [] for k in SISTEMAS}
    t0 = time.time()

    for i, q in enumerate(consultas):
        qid, qtext = q["id"], q["query"]
        for nom, (sem, lex) in SISTEMAS.items():
            try:
                filas = busca(qtext, sem, lex)
            except Exception:
                filas = []
            res = [{"dataset_id": f["id"]} for f in filas]
            m = evaluar(qid, res, gt, k_precision=5, k_ndcg=TOP_K)
            nd[nom].append(m["ndcg_at_10"])
            R[nom].append([f["id"] for f in filas])
            # solapamiento: tokens de la consulta presentes en title+description del top-10
            texto_pool = " ".join(((f.get("title") or "") + " " + (f.get("description") or "")).lower()
                                  for f in filas)
            toks = [w for w in qtext.lower().split() if len(w) > 3]
            ov = (sum(1 for w in toks if w in texto_pool) / len(toks)) if toks else 0.0
            S[nom].append(ov)
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(consultas)} ({time.time()-t0:.0f}s)", flush=True)

    # ---------------------------------------------------------------
    # 2. regimen por tercios de solapamiento (indice del sistema actual)
    # ---------------------------------------------------------------
    print("\n### REGIMEN POR SOLAPAMIENTO (tercios) - BGE-M3 ###")
    print(f"  {'regimen':7} {'n':>4} " + " ".join(f"{k.split()[0]:>12}" for k in SISTEMAS))
    reg = {}
    idx_actual = list(SISTEMAS)[0]
    orden = sorted(range(len(consultas)), key=lambda i: S[idx_actual][i])
    t = len(consultas) // 3
    tercios = {"bajo": orden[:t], "medio": orden[t:2*t], "alto": orden[2*t:]}
    for regn, ids_terc in tercios.items():
        fila = {}
        for nom in SISTEMAS:
            vals = [nd[nom][i] for i in ids_terc]
            fila[nom] = statistics.mean(vals)
        sol_med = statistics.mean([S[idx_actual][i] for i in ids_terc])
        reg[regn] = {"n": len(ids_terc), "solapamiento_medio": sol_med, "ndcg": fila,
                     "consultas_ids": [consultas[i]["id"] for i in ids_terc]}
        print(f"  {regn:7} {len(ids_terc):>4} " + " ".join(f"{fila[k]:>12.4f}" for k in SISTEMAS)
              + f"   (solap. medio {sol_med:.2f})")

    # ---------------------------------------------------------------
    # 3. donde pierde el hibrido? (tesis de la Fase C)
    # ---------------------------------------------------------------
    nom_actual, nom_sem, nom_lex = list(SISTEMAS)
    print("\n### TESIS 'EL HIBRIDO NO PIERDE EN NINGUN REGIMEN' ###")
    ok = True
    for regn, d_ in reg.items():
        h, s_, l_ = d_["ndcg"][nom_actual], d_["ndcg"][nom_sem], d_["ndcg"][nom_lex]
        pierde_sem = h < s_ - 0.01
        pierde_lex = h < l_ - 0.01
        print(f"  {regn:7}: hibrido {h:.4f} vs sem {s_:.4f} ({'PIERDE' if pierde_sem else 'no pierde'}) "
              f"· vs lex {l_:.4f} ({'PIERDE' if pierde_lex else 'no pierde'})")
        ok = ok and not pierde_sem and not pierde_lex
    print(f"\n  VEREDICTO: {'SE MANTIENE la tesis' if ok else 'NO SE MANTIENE'} (con BGE)")

    # pareada global lexico vs semantico por regimen (la comparacion clave)
    print("\n### PAREADA lexico - semantico POR REGIMEN ###")
    for regn, ids_terc in tercios.items():
        dif = [nd[nom_lex][i] - nd[nom_sem][i] for i in ids_terc]
        mu, lo, hi = intervalo_confianza(dif)
        cruza = (lo is None or hi is None) or (lo < 0 < hi)
        print(f"  {regn:7}: {mu:+.4f} IC95 [{lo:+.4f} · {hi:+.4f}] "
              f"{'empate' if cruza else ('lexico mejor' if mu > 0 else 'semantico mejor')}")

    (E / "fase_h_REGIMEN_LEXICO.json").write_text(json.dumps(
        {"consultas": len(consultas), "sistemas": list(SISTEMAS),
         "metricas_global": {k: statistics.mean(v) for k, v in nd.items()},
         "regimenes": {k: {kk: vv for kk, vv in d_.items() if kk != "consultas_ids"}
                       for k, d_ in reg.items()},
         "tesis_se_mantiene": ok}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n  guardado: entregables/fase_h_REGIMEN_LEXICO.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())