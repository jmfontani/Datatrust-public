#!/usr/bin/env python3
"""156_juzgar_pendientes_top10.py — B1: cierra los pares (consulta, ficha) SIN JUICIO.

Motivo: el snapshot de produccion (motor BGE-M3) recupera fichas que el pool de la
Fase B/C no vio, asi que el top-10 tiene 158 pares sin etiquetar (54 de ellos en el
top-5). El instrumento cuenta "sin juicio" como no-interpretable y penaliza la
metrica, asi que juzgarlos (a) sube la cobertura a ~100 % y (b) solo puede subir el
P@5: hoy una ficha no juzgada ocupa un puesto y no suma.

QUE NO HACE
  * no sobrescribe `gt_etiquetas_v5.json` (se verifica su sha256 antes y despues)
  * no toca el producto, ni la API, ni el motor
  * no re-juzga nada ya juzgado

QUE ESCRIBE (todo NUEVO)
  entregables/gt_etiquetas_v6.json         v5 + las etiquetas nuevas
  entregables/juicio_pendientes.json       detalle: nivel, razon, doble ciego, modelo, fecha
  entregables/_checkpoint_pendientes.json  reanudable (se puede borrar)

JUEZ: mismo prompt canonico de la Fase B (`109_juzgar_pool.py`), deepseek-v4.1-flash,
temperatura 0, lotes de <=10 fichas, una llamada por consulta. Solo cambia el
paralelismo (6 llamadas en vuelo), que no afecta a la etiqueta.

Uso:
  python 156_juzgar_pendientes_top10.py --dry-run        # plan, sin llamadas
  python 156_juzgar_pendientes_top10.py --limite 3       # prueba con 3 consultas
  python 156_juzgar_pendientes_top10.py                  # todo
"""
import argparse
import csv
import hashlib
import io
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
SNAPSHOT = ENTREG / "fase_h_SNAPSHOT_DESPUES.json"
GT_V5 = ENTREG / "gt_etiquetas_v5.json"
GT_V6 = ENTREG / "gt_etiquetas_v6.json"
DETALLE = ENTREG / "juicio_pendientes.json"
CHECK = ENTREG / "_checkpoint_pendientes.json"
POOLS = ("pool_a_juzgar.json", "pool_limpias.json", "pool_conjunto.json")
CONTENEDOR_BD = "buscador_postgres"

MODELO = "deepseek-v4.1-flash"
LOTE = 10
MAX_DESC = 800
OBREROS = 6
FRACCION_DOBLE = 0.10

# ---------------------------------------------------------------------------
# PROMPT CANONICO — copiado VERBATIM de 109_juzgar_pool.py. No editar: cambiarlo
# invalida la comparabilidad con las 10.653 etiquetas ya juzgadas.
# ---------------------------------------------------------------------------
PROMPT = """Eres evaluador de un buscador de datos abiertos espanol. Debes decidir
si cada conjunto de datos RESPONDE a la consulta del usuario.

NIVELES
2 = RESPONDE. Contiene la informacion que pide la consulta: el fenomeno Y el
    ambito (territorio, periodo, desglose) coinciden. Es lo que el usuario
    pondria como respuesta.
1 = TEMA CORRECTO, OTRO ALCANCE. Trata del mismo fenomeno, pero cambia el ambito
    (otra comunidad, otro municipio, otro pais, otro periodo) o el desglose
    (por sexo cuando se pedia por edad). Serviria como contexto, no como respuesta.
0 = NO RESPONDE. Otro fenomeno, o solo comparte alguna palabra del titulo.

CONSULTA DEL USUARIO: {query}
INTENCION DECLARADA: {intencion}

CONJUNTOS A EVALUAR:
{lista}

Responde SOLO con un JSON en una linea, con una entrada por conjunto, en el mismo
orden, usando su numero "i":
{{"juicios": [{{"i": 1, "nivel": 0, "razon": "..."}}, ...]}}
Cada razon: menos de 20 palabras. No anadas texto fuera del JSON."""


def leer_clave():
    for ruta in (Path.cwd() / ".env",
                 Path(__file__).resolve().parent / ".env"):
        if ruta.exists():
            for ln in ruta.read_text(encoding="utf-8").splitlines():
                if ln.startswith("OLLAMA_API_KEY="):
                    return ln.split("=", 1)[1].strip()
    return os.getenv("OLLAMA_API_KEY")


def juzga_lote(casos, clave):
    """casos: fichas con title/description/theme_label/territory_label + _query/_intencion."""
    lista = []
    for i, c in enumerate(casos, 1):
        lista.append(
            f'{i}. TITULO: {c["title"][:220]}\n'
            f'   DESCRIPCION: {(c["description"] or "(sin descripcion)")[:600]}\n'
            f'   TEMA: {c.get("theme_label") or "-"} | '
            f'TERRITORIO: {c.get("territory_label") or "-"}'
        )
    prompt = PROMPT.format(query=casos[0]["_query"],
                           intencion=casos[0].get("_intencion") or "-",
                           lista="\n".join(lista))
    body = json.dumps({"model": MODELO,
                       "messages": [{"role": "user", "content": prompt}],
                       "options": {"temperature": 0},
                       "stream": False}).encode()
    req = urllib.request.Request("https://ollama.com/api/chat", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {clave}"})
    txt = json.loads(urllib.request.urlopen(req, timeout=300).read())["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError(f"sin JSON en la respuesta: {txt[:120]}")
    datos = json.loads(m.group(0))
    out = {}
    for j in datos.get("juicios", []):
        try:
            i = int(j["i"])
            niv = int(j["nivel"])
        except (KeyError, TypeError, ValueError):
            continue
        if 1 <= i <= len(casos) and niv in (0, 1, 2):
            out[i - 1] = (niv, str(j.get("razon", ""))[:200])
    return out


def sha(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def metadatos_de_pools():
    """Metadatos tal y como los vio el juez en su momento, si estan en los pools."""
    meta = {}
    for f in POOLS:
        ruta = ENTREG / f
        if not ruta.exists():
            continue
        d = json.loads(ruta.read_text(encoding="utf-8"))
        cont = d.get("pool", d)
        if isinstance(cont, dict):
            for qid, fs in cont.items():
                for did, v in fs.items():
                    if isinstance(v, dict) and v.get("title") is not None:
                        meta.setdefault(did, {
                            "title": v.get("title", ""),
                            "description": (v.get("description") or "")[:MAX_DESC],
                            "theme_label": v.get("theme_label") or v.get("tema") or "",
                            "territory_label": v.get("territory_label") or v.get("territorio") or "",
                            "fuente": f})
        else:
            for c in cont:
                for fi in c["fichas"]:
                    meta.setdefault(fi["dataset_id"], {
                        "title": fi.get("title", ""),
                        "description": (fi.get("description") or "")[:MAX_DESC],
                        "theme_label": fi.get("theme_label", ""),
                        "territory_label": fi.get("territory_label", ""),
                        "fuente": f})
    return meta


def metadatos_de_bd(ids):
    """Los que no estan en ningun pool: misma consulta que 108_construir_pool.py."""
    if not ids:
        return {}
    lista = ", ".join("'" + str(d).replace("'", "''") + "'" for d in sorted(ids))
    sql = ("COPY (SELECT dataset_id, title, COALESCE(description,'') AS description, "
           "COALESCE(theme_label,'') AS theme_label, COALESCE(territory_label,'') AS territory_label "
           f"FROM datasets WHERE dataset_id = ANY(ARRAY[{lista}])) "
           "TO STDOUT WITH CSV HEADER")
    p = subprocess.run(["docker", "exec", "-i", CONTENEDOR_BD, "psql", "-U", "postgres",
                        "-d", "buscador", "-q", "-f", "-"],
                       input=sql, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"fallo consultando la BD: {p.stderr[:300]}")
    out = {}
    for fila in csv.DictReader(io.StringIO(p.stdout)):
        out[fila["dataset_id"]] = {
            "title": fila["title"],
            "description": (fila["description"] or "")[:MAX_DESC],
            "theme_label": fila["theme_label"],
            "territory_label": fila["territory_label"],
            "fuente": "bd:datasets"}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=None, help="solo las primeras N consultas")
    ap.add_argument("--consultas", default=None, help="ids separados por comas")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--obreros", type=int, default=OBREROS)
    args = ap.parse_args()

    t0 = time.time()
    h_v5_antes = sha(GT_V5)
    print("=" * 78)
    print("B1 · JUICIO DE LOS PARES SIN ETIQUETAR EN EL TOP-10 DE PRODUCCION")
    print("=" * 78)
    print(f"\n  gt base          : {GT_V5.name}  sha256 {h_v5_antes[:16]}…")

    et_v5 = json.loads(GT_V5.read_text(encoding="utf-8"))["etiquetas"]
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["rankings"]

    pendientes = {}
    for qid, ranking in snap.items():
        faltan = [r["dataset_id"] for r in ranking[:10] if f"{qid}|{r['dataset_id']}" not in et_v5]
        if faltan:
            pendientes[qid] = faltan
    if args.consultas:
        ids = {s.strip() for s in args.consultas.split(",")}
        pendientes = {k: v for k, v in pendientes.items() if k in ids}
    if args.limite:
        pendientes = dict(list(pendientes.items())[:args.limite])

    n_pares = sum(len(v) for v in pendientes.values())
    print(f"  pares sin juicio : {n_pares} en {len(pendientes)} consultas")

    # --- metadatos: primero los pools (lo que el juez vio), luego la BD
    meta = metadatos_de_pools()
    ids_tot = {d for v in pendientes.values() for d in v}
    faltan_bd = ids_tot - set(meta)
    print(f"  metadatos        : {len(ids_tot) - len(faltan_bd)} desde los pools · {len(faltan_bd)} desde la BD")
    for did, m in metadatos_de_bd(faltan_bd).items():
        meta[did] = m

    # --- consulta + intencion declarada
    qmeta = {}
    p = json.loads((ENTREG / "pool_a_juzgar.json").read_text(encoding="utf-8"))["pool"]
    for c in p:
        qmeta[c["query_id"]] = {"query": c["query"], "intencion": c.get("descripcion_intencion")}
    for ln in (ENTREG / "consultas_limpias.jsonl").read_text(encoding="utf-8").splitlines():
        o = json.loads(ln)
        qmeta[o["id"]] = {"query": o["query"], "intencion": o.get("descripcion")}
    sin_meta = [q for q in pendientes if q not in qmeta]
    if sin_meta:
        print(f"  ERROR: consultas sin texto/intencion: {sin_meta[:5]}")
        return 1

    if args.dry_run:
        print("\n  DRY RUN · primeras consultas del plan:")
        for qid, ds in list(pendientes.items())[:6]:
            q = qmeta[qid]["query"]
            print(f"    {qid:14} {len(ds):>2} pares · «{q}»")
        print(f"\n  llamadas estimadas: {len(pendientes)} (+ ~{max(1, int(n_pares * FRACCION_DOBLE / LOTE))} de doble ciego)")
        print("  nada ejecutado.")
        return 0

    clave = leer_clave()
    if not clave:
        print("  ERROR: falta OLLAMA_API_KEY")
        return 1

    estado = {"juicios": {}, "fallos": []}
    if CHECK.exists():
        estado = json.loads(CHECK.read_text(encoding="utf-8"))
        print(f"  reanudando        : {len(estado.get('juicios', {}))} juicios previos del checkpoint")

    # --- doble ciego (10 %): se juzga una segunda vez, en otra llamada
    random.seed(7)
    todos = [(q, d) for q, v in pendientes.items() for d in v]
    muestra_doble = set(random.sample(todos, max(1, int(round(len(todos) * FRACCION_DOBLE)))))

    def tarea(item):
        qid, ds = item
        pend_q = [d for d in ds if f"{qid}|{d}" not in estado["juicios"]]
        if not pend_q:
            return qid, {}, []
        q = qmeta[qid]
        casos = []
        for d in pend_q:
            m = dict(meta[d])
            m["_query"] = q["query"]
            m["_intencion"] = q["intencion"]
            m["_dataset_id"] = d
            casos.append(m)
        for intento in (1, 2):
            try:
                res = juzga_lote(casos, clave)
                return qid, res, casos
            except Exception as e:
                if intento == 2:
                    return qid, None, str(e)[:160]
                time.sleep(2)
        return qid, None, "sin respuesta"

    print(f"\n  modelo juez      : {MODELO} (T=0) · {args.obreros} llamadas en vuelo")
    print(f"  doble ciego      : {len(muestra_doble)} pares ({FRACCION_DOBLE:.0%})\n")

    hechos = 0
    with ThreadPoolExecutor(max_workers=args.obreros) as ex:
        for qid, res, extra in ex.map(tarea, list(pendientes.items())):
            if res is None:
                estado["fallos"].append({"query_id": qid, "error": extra})
                print(f"  {qid:14} FALLO: {str(extra)[:60]}")
            else:
                for k, (niv, raz) in res.items():
                    c = extra[k]
                    estado["juicios"][f"{qid}|{c['_dataset_id']}"] = {
                        "nivel": niv, "razon": raz, "title": c["title"][:200],
                        "doble": (qid, c["_dataset_id"]) in muestra_doble,
                        "fuente_meta": c.get("fuente", "?"),
                    }
                hechos += len(res)
                print(f"  {qid:14} {len(res):>2} juzgadas · acumulado {hechos}/{n_pares}")
            CHECK.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")

    # --- acuerdo del doble ciego: segunda pasada sobre la muestra
    doble = [k for k, v in estado["juicios"].items() if v.get("doble")]
    acuerdos = []
    if doble:
        print(f"\n  segunda pasada ciega sobre {len(doble)} pares…")
        por_q = {}
        for k in doble:
            qid, did = k.split("|", 1)
            por_q.setdefault(qid, []).append(did)
        for qid, ds in por_q.items():
            q = qmeta[qid]
            casos = []
            for d in ds:
                m = dict(meta[d])
                m.update({"_query": q["query"], "_intencion": q["intencion"], "_dataset_id": d})
                casos.append(m)
            try:
                res = juzga_lote(casos, clave)
            except Exception as e:
                print(f"    {qid}: fallo en la segunda pasada ({str(e)[:50]})")
                continue
            for k, (niv, _) in res.items():
                did = casos[k]["_dataset_id"]
                clave_e = f"{qid}|{did}"
                prev = estado["juicios"][clave_e]["nivel"]
                estado["juicios"][clave_e]["doble_nivel"] = niv
                acuerdos.append((prev, niv))
            time.sleep(0.3)
        CHECK.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")

    # --- fusion con v5 -> v6
    v5 = json.loads(GT_V5.read_text(encoding="utf-8"))
    etiquetas6 = dict(v5["etiquetas"])
    nuevas = 0
    for k, v in estado["juicios"].items():
        if k not in etiquetas6:
            etiquetas6[k] = v["nivel"]
            nuevas += 1
    v6 = {
        "meta": dict(v5.get("meta", {})),
        "etiquetas": etiquetas6,
        "detalle": v5.get("detalle", {}),
        "acuerdo_doble": v5.get("acuerdo_doble", {}),
        "fallos": v5.get("fallos", []),
    }
    v6["meta"]["b1_top10_pendientes"] = {
        "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "motivo": "cierre de los pares sin juicio en el top-10 del snapshot de produccion (BGE-M3)",
        "etiquetas_previas": len(v5["etiquetas"]),
        "etiquetas_nuevas": nuevas,
        "total": len(etiquetas6),
        "modelo_juez": MODELO,
        "prompt": "canonico de 109_juzgar_pool.py (verbatim)",
        "pares": n_pares,
        "consultas": len(pendientes),
        "gt_origen_sha256": h_v5_antes,
    }
    GT_V6.write_text(json.dumps(v6, ensure_ascii=False), encoding="utf-8")
    DETALLE.write_text(json.dumps({
        "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "modelo": MODELO, "pares": n_pares, "consultas": len(pendientes),
        "juicios": estado["juicios"], "fallos": estado["fallos"],
        "acuerdo_doble": {
            "n": len(acuerdos),
            "exacto": (round(sum(1 for a, b in acuerdos if a == b) / len(acuerdos), 4) if acuerdos else None),
            "con_tolerancia_1": (round(sum(1 for a, b in acuerdos if abs(a - b) <= 1) / len(acuerdos), 4) if acuerdos else None),
        },
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    h_v5_despues = sha(GT_V5)
    print("\n" + "=" * 78)
    print(f"  etiquetas v5    : {len(v5['etiquetas'])}  ({'INTACTO' if h_v5_antes == h_v5_despues else '¡MODIFICADO!'})")
    print(f"  etiquetas v6    : {len(etiquetas6)}  (+{nuevas})")
    if acuerdos:
        ex = sum(1 for a, b in acuerdos if a == b) / len(acuerdos)
        tol = sum(1 for a, b in acuerdos if abs(a - b) <= 1) / len(acuerdos)
        print(f"  doble ciego     : exacto {ex:.3f} · +-1 {tol:.3f}  (n={len(acuerdos)})")
    if estado["fallos"]:
        print(f"  fallos          : {len(estado['fallos'])} (ver juicio_pendientes.json)")
    print(f"  escritos        : gt_etiquetas_v6.json · juicio_pendientes.json")
    print(f"  tiempo          : {time.time() - t0:.0f} s")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
