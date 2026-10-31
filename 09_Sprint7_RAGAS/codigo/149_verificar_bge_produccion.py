#!/usr/bin/env python3
"""
149_verificar_bge_produccion.py — verificacion PRE/POST del despliegue de BGE-M3
y del arreglo de determinismo, contra PRODUCCION (no el clon).

POR QUE
El despliegue de BGE-M3 y el arreglo `sorted(expanded)` tocan el buscador EN
SERVICIO. Antes de darlos por buenos hay que poder demostrar:

  1. Que la imagen nueva sirve BGE-M3 de verdad (no un fallback silencioso).
  2. Que el ranking cambia donde debe: las consultas CON sinonimos son las que el
     bug del `set` afectaba (14/214 medidas en Fase G). Las que no tienen sinonimos
     solo deberian cambiar por el cambio de motor.
  3. Que las metricas se mueven en la direccion medida en el clon
     (con BGE: nDCG ~0,5621, P@5 ~0,4224, P@10 ~0,3879).

QUE HACE
  --fase antes   -> consulta la API de produccion (:8000) y guarda rankings
  --fase despues -> idem tras el redespliegue
  --comparar     -> compara los dos snapshots y calcula metricas de ambos

Guarda los rankings completos por consulta: con eso se recalcula cualquier metrica
sin volver a consultar (mismo criterio que 147).
"""
import argparse
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from utils.gt_metrics import EtiquetasGT, cobertura, evaluar, intervalo_confianza  # noqa: E402

ENTREG = AQUI.parent / "entregables"
GT_V5 = ENTREG / "gt_etiquetas_v5.json"
GT_VIEJO = ENTREG / "ground_truth.jsonl"
NUEVAS = ENTREG / "consultas_limpias.jsonl"
SINONIMOS_JSON = AQUI.parent.parent / "08_Sprint6_LLM_Mejora" / "codigo" / "motor" / "sinonimos.json"
TOP_K = 10


def cargar_consultas():
    """Las 214 = 47 humanas (con id en ground_truth.jsonl) + 167 nuevas limpias."""
    out = []
    for ruta in (GT_VIEJO, NUEVAS):
        for l in ruta.read_text(encoding="utf-8").splitlines():
            if l.strip():
                out.append(json.loads(l))
    return out


def cargar_sinonimos():
    if not SINONIMOS_JSON.exists():
        return {}
    with open(SINONIMOS_JSON, encoding="utf-8") as f:
        return json.load(f)


def consultas_con_sinonimos(consultas, sinonimos):
    """Las que el bug del `set` afectaba: su texto expandido cambia de orden."""
    ids = []
    for q in consultas:
        for w in q["query"].lower().split():
            if w in sinonimos:
                ids.append(q["id"])
                break
    return set(ids)


def busca(api, q, top_k=TOP_K):
    body = {"query": q, "top_k": top_k}
    req = urllib.request.Request(api, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=300).read())
    return [{"dataset_id": x["id"], "score": x.get("score")} for x in (d.get("results") or [])]


def recolectar(api, consultas, etiqueta):
    print(f"Consultando {api} ({len(consultas)} consultas)...", flush=True)
    ran, t0, fallos = {}, time.time(), 0
    for i, q in enumerate(consultas):
        try:
            ran[q["id"]] = busca(api, q["query"])
        except Exception as e:
            fallos += 1
            print(f"  fallo en {q['id']}: {str(e)[:80]}", flush=True)
            ran[q["id"]] = []
        if (i + 1) % 40 == 0:
            print(f"  {i+1}/{len(consultas)} ({time.time()-t0:.0f}s)", flush=True)
    print(f"  hecho en {time.time()-t0:.0f}s, {fallos} fallos", flush=True)
    return {"api": api, "etiqueta": etiqueta, "rankings": ran,
            "cuando": time.strftime("%Y-%m-%dT%H:%M:%S")}


def metricas(rankings, gt, consultas):
    """Metricas con el instrumento canonico, mismas reglas que fases E/F/G."""
    filas = []
    for q in consultas:
        res = rankings.get(q["id"]) or []
        if not res:
            continue
        m = evaluar(q["id"], res, gt, k_precision=5, k_ndcg=10)
        m["_id"] = q["id"]
        m["_cob5"] = cobertura(res[:5], gt, q["id"])
        m["_cob10"] = cobertura(res[:10], gt, q["id"])
        # P@10: el instrumento canonico usa k_precision=5, asi que se calcula aparte.
        m["_p10"] = sum(1 for x in res[:10]
                        if gt.nivel(q["id"], x["dataset_id"]) == 2) / 10
        filas.append(m)

    def vals(k):
        return [f[k] for f in filas if f.get(k) is not None]

    def media(k):
        v = vals(k)
        return round(statistics.mean(v), 4) if v else None

    def ic(k):
        lo, hi = intervalo_confianza(vals(k))[1:]
        return [lo, hi]

    return {"n": len(filas),
            "ndcg": media("ndcg_at_10"), "ndcg_ic": ic("ndcg_at_10"),
            "p5": media("precision_at_5"), "p5_ic": ic("precision_at_5"),
            "p10": media("_p10"), "p10_ic": ic("_p10"),
            "mrr": media("mrr"), "mrr_ic": ic("mrr"),
            "cob5": media("_cob5"), "cob10": media("_cob10")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fase", required=True, choices=["antes", "despues", "comparar"])
    ap.add_argument("--api", default="http://localhost:8000/search")
    args = ap.parse_args()

    consultas = cargar_consultas()
    print(f"consultas: {len(consultas)}")

    if args.fase in ("antes", "despues"):
        snap = recolectar(args.api, consultas, args.fase)
        salida = ENTREG / f"fase_h_SNAPSHOT_{args.fase.upper()}.json"
        salida.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"guardado: {salida}")
        return

    a = json.loads((ENTREG / "fase_h_SNAPSHOT_ANTES.json").read_text(encoding="utf-8"))
    b = json.loads((ENTREG / "fase_h_SNAPSHOT_DESPUES.json").read_text(encoding="utf-8"))
    gt = EtiquetasGT(GT_V5)

    ma = metricas(a["rankings"], gt, consultas)
    mb = metricas(b["rankings"], gt, consultas)

    print("\n=== METRICAS (GT v5, 214 consultas) ===")
    for nom, m in (("ANTES", ma), ("DESPUES", mb)):
        print(f"  {nom:7} nDCG {m['ndcg']} [{m['ndcg_ic'][0]}·{m['ndcg_ic'][1]}]  "
              f"P@5 {m['p5']}  P@10 {m['p10']}  MRR {m['mrr']}  "
              f"cob@5 {m['cob5']}  cob@10 {m['cob10']}")

    pares = []
    for q in consultas:
        ra = a["rankings"].get(q["id"]) or []
        rb = b["rankings"].get(q["id"]) or []
        if not ra or not rb:
            continue
        ia = [x["dataset_id"] for x in ra[:10]]
        ib = [x["dataset_id"] for x in rb[:10]]
        aa = sum(1 for d in ia if gt.nivel(q["id"], d) == 2)
        ab = sum(1 for d in ib if gt.nivel(q["id"], d) == 2)
        pares.append((q["id"], aa, ab, ia == ib))

    dif = [y - x for _, x, y, _ in pares]
    identicas = sum(1 for *_, igual in pares if igual)
    gana = sum(1 for d in dif if d > 0)
    pierde = sum(1 for d in dif if d < 0)
    print(f"\n=== RANKINGS ===")
    print(f"  comparadas {len(pares)} | top-10 identico {identicas}/{len(pares)}")
    print(f"  nivel-2 en top-10: media {statistics.mean(dif):+.3f}")
    print(f"  mejora {gana} | empeora {pierde} | empata {len(dif)-gana-pierde}")

    sinon_ids = consultas_con_sinonimos(consultas, cargar_sinonimos())
    if sinon_ids:
        con = [p for p in pares if p[0] in sinon_ids]
        sin_ = [p for p in pares if p[0] not in sinon_ids]
        print(f"\n=== BUG DEL `set` (aislamiento) ===")
        print(f"  con sinonimos {len(con)} | sin sinonimos {len(sin_)}")
        print(f"  ranking cambiado -> con sinonimos "
              f"{sum(1 for *_, ig in con if not ig)}/{len(con)} | "
              f"sin sinonimos {sum(1 for *_, ig in sin_ if not ig)}/{len(sin_)}")

    salida = ENTREG / "fase_h_VERIFICACION.json"
    salida.write_text(json.dumps({
        "antes": a["cuando"], "despues": b["cuando"],
        "metricas_antes": ma, "metricas_despues": mb,
        "rankings_identicos": identicas, "total": len(pares),
        "gana": gana, "pierde": pierde,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nguardado: {salida}")


if __name__ == "__main__":
    main()
