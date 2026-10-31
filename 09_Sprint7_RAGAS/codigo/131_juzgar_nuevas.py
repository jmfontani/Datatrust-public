#!/usr/bin/env python3
"""
131_juzgar_nuevas.py — juicio del pool de las 169 consultas nuevas (Fase C, paso 3).

PROMPT: usa el CRITERIO DE AMBITO CORREGIDO, no el canonico viejo.
Es deliberado: las 225 etiquetas de nivel 1 ya se rejuzgaron con ese criterio
(docs/FASE-C-PASO1-EJECUTADO.md). Si aqui se usara el prompt viejo, el GT quedaria
con dos criterios distintos y las cifras no serian comparables.

CARACTERISTICAS
  - checkpoint: se puede reanudar sin repetir llamadas (clave: se guarda el pool
    pendiente, no el juicio suelto, porque el juicio se fusiona al final)
  - lotes de 10, temperatura 0
  - reintentos con espera creciente
  - no sobrescribe el GT: escribe `gt_etiquetas_v3.json`
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
POOL = ENTREG / "pool_nuevas.json"  # valor por defecto; se puede sobreescribir con --pool
ETIQ = ENTREG / "gt_etiquetas_v2.json"
SALIDA = ENTREG / "gt_etiquetas_v3.json"
CHECKPOINT = ENTREG / "_checkpoint_nuevas.json"

MODELO = "deepseek-v4.1-flash"
LOTE = 10

# --- prompt con el CRITERIO DE AMBITO CORREGIDO (identico al 124) ---
PROMPT = """Eres evaluador de un buscador de datos abiertos espanol. Debes decidir
si cada conjunto de datos RESPONDE a la consulta del usuario.

IMPORTANTE SOBRE EL AMBITO TERRITORIAL
Este portal es el catalogo de las administraciones publicas espanolas. La mayor
parte de sus conjuntos de datos son de ambito autonomicos o municipal, no nacional.
POR ESO: un conjunto de datos de una comunidad autonoma o de un municipio SI
RESPONDE a la consulta, siempre que mida el fenomeno que se pide. NO lo penalices
por no ser de ambito estatal.

NIVELES
2 = RESPONDE. Mide el fenomeno que pide la consulta, y el desglose coincide con lo
    pedido. El territorio puede ser nacional, de una comunidad autonoma o de un
    municipio: en cualquiera de los casos es valido.
1 = TEMA CORRECTO, ALCANCE INCOMPATIBLE. Solo en estos tres casos:
      a) el territorio es de OTRO PAIS (no espanol);
      b) el desglose pedido NO esta (se pedia por comunidades y el dato es por
         municipios; se pedia por edad y el dato es por sexo; se pedia por sector
         y el dato es global...);
      c) el periodo no puede servir para lo que se pide.
0 = NO RESPONDE. Es otro fenomeno, o solo comparte alguna palabra del titulo.

CONSULTA DEL USUARIO: {query}
INTENCION DECLARADA: {intencion}
FACETAS QUE SE ESPERAN: {facets}

CONJUNTOS A EVALUAR:
{lista}

Responde SOLO con un JSON en una linea, con una entrada por conjunto, en el mismo
orden, usando su numero "i":
{{"juicios": [{{"i": 1, "nivel": 0, "razon": "..."}}, ...]}}
Cada razon: menos de 20 palabras, y si bajas a nivel 1 di CUAL de los tres casos
(a, b o c) aplica. No anadas texto fuera del JSON."""


def leer_clave():
    for ruta in (Path.cwd() / ".env",
                 Path(__file__).resolve().parent / ".env"):
        if ruta.exists():
            for ln in ruta.read_text(encoding="utf-8").splitlines():
                if ln.startswith("OLLAMA_API_KEY="):
                    return ln.split("=", 1)[1].strip()
    return os.getenv("OLLAMA_API_KEY")


def juzga_lote(casos, clave):
    lista = []
    for i, c in enumerate(casos, 1):
        lista.append(f'{i}. TITULO: {c["title"][:220]}\n'
                     f'   DESCRIPCION: {c["description"][:600] or "(sin descripcion)"}\n'
                     f'   TEMA: {c.get("theme_label") or "-"} | '
                     f'TERRITORIO: {c.get("territory_label") or "-"}')
    prompt = PROMPT.format(query=casos[0]["_query"],
                           intencion=casos[0].get("_intencion") or "-",
                           facets="; ".join(casos[0].get("_criterios") or []) or "-",
                           lista="\n".join(lista))
    body = json.dumps({"model": MODELO,
                       "messages": [{"role": "user", "content": prompt}],
                       "options": {"temperature": 0}, "stream": False}).encode()
    req = urllib.request.Request("https://ollama.com/api/chat", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {clave}"})
    txt = json.loads(urllib.request.urlopen(req, timeout=150).read())["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("sin JSON")
    out = {}
    for j in json.loads(m.group(0)).get("juicios", []):
        try:
            i, niv = int(j["i"]), int(j["nivel"])
        except (KeyError, TypeError, ValueError):
            continue
        if 1 <= i <= len(casos) and niv in (0, 1, 2):
            out[i - 1] = (niv, str(j.get("razon", ""))[:200])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--consultas", default=None, help="ids separados por comas")
    ap.add_argument("--limite-consultas", type=int, default=None)
    # parametrizado para poder juzgar pools distintos SIN duplicar el juez
    ap.add_argument("--pool", default=str(POOL))
    ap.add_argument("--etiquetas", default=str(ETIQ), help="GT base sobre el que fusionar")
    ap.add_argument("--salida", default=str(SALIDA))
    ap.add_argument("--checkpoint", default=str(CHECKPOINT))
    args = ap.parse_args()
    pool_ruta = Path(args.pool)
    etiq_ruta = Path(args.etiquetas)
    salida_ruta = Path(args.salida)
    ckpt_ruta = Path(args.checkpoint)

    clave = leer_clave()
    if not clave:
        print("ERROR: falta OLLAMA_API_KEY")
        return 1

    pool = json.loads(pool_ruta.read_text(encoding="utf-8"))
    if args.consultas:
        ids = {s.strip() for s in args.consultas.split(",") if s.strip()}
        pool = {k: v for k, v in pool.items() if k in ids}
    elif args.limite_consultas:
        pool = dict(list(pool.items())[:args.limite_consultas])

    total = sum(len(v) for v in pool.values())
    print("=" * 78)
    print("JUICIO DEL POOL DE LAS CONSULTAS NUEVAS · criterio de ambito corregido")
    print("=" * 78)
    print(f"\n  consultas : {len(pool)}")
    print(f"  pares     : {total}")
    print(f"  lotes     : ~{total // LOTE + len(pool)}")

    # checkpoint: lo ya juzgado
    hecho = {}
    if ckpt_ruta.exists():
        hecho = json.loads(ckpt_ruta.read_text(encoding="utf-8"))
        print(f"  reanudando: {len(hecho)} pares ya juzgados")
    pendiente = {q: {d: v for d, v in fichas.items() if f"{q}|{d}" not in hecho}
                 for q, fichas in pool.items()}
    pendiente = {q: f for q, f in pendiente.items() if f}
    n_pend = sum(len(v) for v in pendiente.values())
    print(f"  pendientes: {n_pend}\n")
    if not n_pend:
        print("  nada pendiente.")
        return 0

    t0 = time.time()
    fallos = []
    n_ok = 0
    for qi, (qid, fichas) in enumerate(sorted(pendiente.items()), 1):
        items = list(fichas.values())
        for inp in range(0, len(items), LOTE):
            grupo = items[inp:inp + LOTE]
            grupo = [{**g, "_query": fichas[g["dataset_id"]]["query"],
                      "_intencion": fichas[g["dataset_id"]].get("intencion"),
                      "_criterios": fichas[g["dataset_id"]].get("criterios")}
                     for g in grupo]
            res = None
            for intento in range(3):
                try:
                    res = juzga_lote(grupo, clave)
                    break
                except Exception as e:
                    print(f"     fallo lote ({qid} intento {intento+1}): {str(e)[:80]}", flush=True)
                    if intento == 2:
                        fallos.append({"query_id": qid, "error": str(e)[:100]})
                    time.sleep(3 * (intento + 1))
            if not res:
                continue
            for j, g in enumerate(grupo):
                if j not in res:
                    continue
                niv, raz = res[j]
                hecho[f"{qid}|{g['dataset_id']}"] = {
                    "nivel": niv, "razon": raz, "title": g["title"][:200],
                    "origen": "faseC_paso3"}
                n_ok += 1
            time.sleep(0.3)

        if qi % 5 == 0 or qi == len(pendiente):
            trans = time.time() - t0
            vel = n_ok / trans if trans else 0
            rest = (n_pend - n_ok) / vel / 60 if vel else 0
            print(f"  [{qi:3}/{len(pendiente)}] {n_ok} juzgadas  "
                  f"({vel:.2f}/s, restan ~{rest:.0f} min)", flush=True)
            ckpt_ruta.write_text(json.dumps(hecho, ensure_ascii=False), encoding="utf-8")

    ckpt_ruta.write_text(json.dumps(hecho, ensure_ascii=False), encoding="utf-8")

    print(f"\n### RESULTADO ###\n")
    print(f"  juzgadas : {len(hecho)}   fallos de lote: {len(fallos)}")
    cnt = Counter(v["nivel"] for v in hecho.values())
    print(f"  distribucion: {dict(sorted(cnt.items()))}")
    print(f"  tiempo total: {(time.time()-t0)/60:.1f} min")

    if fallos:
        print(f"\n  lotes fallidos (recuperar con --consultas):")
        c = Counter(f["query_id"] for f in fallos)
        print(f"     {dict(c)}")

    # fusion con el GT existente -> v3 (no sobrescribe el v2)
    doc = json.loads(etiq_ruta.read_text(encoding="utf-8"))
    etiq, det = doc["etiquetas"], doc.setdefault("detalle", {})
    antes = Counter(etiq.values())
    nuevos = 0
    for k, v in hecho.items():
        if k not in etiq:
            nuevos += 1
        etiq[k] = v["nivel"]
        det[k] = v
    doc["meta"]["total"] = len(etiq)
    doc["meta"]["fase_c_paso3"] = nuevos
    doc["meta"]["consulta_v3"] = (
        "25-sep-2026: pool de las 169 consultas nuevas de la Fase C (216 en total), "
        "juzgado con el criterio de ambito corregido.")
    doc["meta"]["distribucion"] = dict(sorted(Counter(etiq.values()).items()))
    salida_ruta.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n  etiquetas nuevas anadidas: {nuevos}")
    print(f"  distribucion ANTES: {dict(sorted(antes.items()))}")
    print(f"  distribucion AHORA: {doc['meta']['distribucion']}")
    print(f"  total: {len(etiq)}")
    print(f"\n  guardado: {salida_ruta}   (el fichero base NO se ha tocado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
