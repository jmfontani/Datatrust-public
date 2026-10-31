#!/usr/bin/env python3
"""
124_rejuzgar_nivel1.py — aplicar el criterio de ambito corregido (docs/FASE-C-PASO1-HALLAZGO.md §7).

QUE CAMBIA RESPECTO AL CRITERIO CANONICO
El prompt canonico definia el nivel 1 como "mismo tema, OTRO ALCANCE" y enumeraba
como equivalentes: otra comunidad, otro municipio, otro pais, otro periodo, otro
desglose. El hallazgo de la Fase C midio que tratar "otra comunidad autonoma" como
nivel 1 es INCORRECTO en este catalogo: datos.gob.es es mayoritariamente autonomico
y municipal (solo el 11,4 % de las fichas es de ambito "Espana"), asi que exigir
ambito nacional castiga al 88,6 % del catalogo y hace caer la metrica sin que el
motor haya empeorado.

CRITERIO NUEVO (el ambito entra en el CRITERIO, no en el texto de la consulta)
  2 = RESPONDE: mismo fenomeno, territorio espanol O SIN ESPECIFICAR, y el
      desglose coincide con lo pedido.
  1 = TEMA CORRECTO, ALCANCE INCOMPATIBLE: territorio de OTRO PAIS, periodo que no
      encaja, o desglose distinto al pedido (por sexo cuando se pedia por edad,
      por municipios cuando se pedia por comunidades...).
  0 = NO RESPONDE: otro fenomeno.

POR QUE SOLO HAY QUE REJUZGAR EL NIVEL 1
El criterio nuevo es MAS PERMISIVO en territorio (acepta cualquier ambito
espanol). Por tanto:
  - lo que ya era 2 sigue siendo 2 (ya satisfacia la exigencia mas estricta),
  - lo que era 0 sigue siendo 0 (es otro fenomeno, el territorio no interviene),
  - solo el nivel 1 puede moverse, y solo hacia arriba.
Rejuzgar los 0 y los 2 gastaria llamadas sin poder cambiar nada.

NO SE TOCA EL TEXTO DE LA CONSULTA
Se usa `ground_truth.jsonl` (la consulta ORIGINAL), no `consultas_v2.jsonl`. Asi
las etiquetas siguen siendo comparables con las de junio: mismo texto, solo cambia
el criterio aplicado.
"""
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

import psycopg2
from psycopg2.extras import DictCursor

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
ETIQ = ENTREG / "gt_etiquetas_v2.json"
GT = ENTREG / "ground_truth.jsonl"
SALIDA = ENTREG / "rejuicio_nivel1.json"

MODELO = "deepseek-v4.1-flash"
LOTE = 10

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


def juzga(casos, clave):
    lista = []
    for i, c in enumerate(casos, 1):
        lista.append(f'{i}. TITULO: {c["title"][:220]}\n'
                     f'   DESCRIPCION: {(c["description"] or "(sin descripcion)")[:600]}\n'
                     f'   TEMA: {c.get("theme_label") or "-"} | '
                     f'TERRITORIO: {c.get("territory_label") or "-"}')
    prompt = PROMPT.format(query=casos[0]["_query"],
                           intencion=casos[0].get("_intencion") or "-",
                           lista="\n".join(lista))
    body = json.dumps({"model": MODELO,
                       "messages": [{"role": "user", "content": prompt}],
                       "options": {"temperature": 0}, "stream": False}).encode()
    req = urllib.request.Request("https://ollama.com/api/chat", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {clave}"})
    txt = json.loads(urllib.request.urlopen(req, timeout=300).read())["message"]["content"]
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
    clave = leer_clave()
    if not clave:
        print("ERROR: falta OLLAMA_API_KEY")
        return 1

    doc = json.loads(ETIQ.read_text(encoding="utf-8"))
    etiq, det = doc["etiquetas"], doc.get("detalle", {})
    consultas = {json.loads(l)["id"]: json.loads(l)
                 for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()}

    nivel1 = {k: v for k, v in etiq.items() if v == 1}
    print("=" * 80)
    print("REJUICIO DEL NIVEL 1 CON EL CRITERIO DE AMBITO CORREGIDO")
    print("=" * 80)
    print(f"\n  etiquetas de nivel 1 a revisar: {len(nivel1)}")
    print(f"  consulta usada: la ORIGINAL (sin cambios de texto)")
    print(f"  el criterio nuevo solo puede SUBIR el nivel (acepta ambito autonomico)\n")

    conn = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "postgres"),
                            dbname=os.getenv("POSTGRES_DB", "buscador"),
                            user=os.getenv("POSTGRES_USER", "postgres"),
                            password=os.getenv("POSTGRES_PASSWORD", "postgres"))

    por_q = {}
    for k in nivel1:
        qid, did = k.split("|")
        por_q.setdefault(qid, []).append(did)
    print(f"  consultas implicadas: {len(por_q)}   lotes previstos: "
          f"{sum((len(v)//LOTE)+1 for v in por_q.values())}\n")

    nuevos, fallos = {}, []
    for qi, (qid, ids) in enumerate(sorted(por_q.items()), 1):
        q = consultas[qid]
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""SELECT dataset_id, title, description, theme_label,
                                  territory_label FROM datasets
                           WHERE dataset_id = ANY(%s)""", (ids,))
            meta = {r["dataset_id"]: dict(r) for r in cur.fetchall()}
        fichas = [{"dataset_id": d, "title": meta.get(d, {}).get("title") or "",
                   "description": (meta.get(d, {}).get("description") or "")[:800],
                   "theme_label": meta.get(d, {}).get("theme_label") or "",
                   "territory_label": meta.get(d, {}).get("territory_label") or "",
                   "_query": q["query"], "_intencion": q.get("descripcion")}
                  for d in ids if d in meta]
        ok = 0
        for ini in range(0, len(fichas), LOTE):
            grupo = fichas[ini:ini + LOTE]
            if not grupo:
                continue
            try:
                res = juzga(grupo, clave)
            except Exception as e:
                fallos.append(f"{qid}: {str(e)[:70]}")
                continue
            for j, f in enumerate(grupo):
                if j in res:
                    nuevos[f"{qid}|{f['dataset_id']}"] = {"nivel": res[j][0],
                                                          "razon": res[j][1],
                                                          "title": f["title"][:200]}
                    ok += 1
            time.sleep(0.4)
        print(f"  [{qi:2}/{len(por_q)}] {qid:14} {len(fichas):>2} fichas -> {ok} rejuzgadas")
    conn.close()

    comunes = [k for k in nuevos if k in etiq]
    print(f"\n### RESULTADO ###\n")
    print(f"  rejuzgadas : {len(comunes)}   fallos de lote: {len(fallos)}")
    cnt = Counter(nuevos[k]["nivel"] for k in comunes)
    print(f"  niveles nuevos: {dict(sorted(cnt.items()))}")
    suben = [k for k in comunes if nuevos[k]["nivel"] == 2]
    bajan = [k for k in comunes if nuevos[k]["nivel"] == 0]
    igual = [k for k in comunes if nuevos[k]["nivel"] == 1]
    print(f"\n  SIGUEN en nivel 1 : {len(igual)}")
    print(f"  SUBEN a nivel 2   : {len(suben)}  <- eran ambito autonomico/municipal")
    print(f"  BAJAN a nivel 0   : {len(bajan)}  (revisar: contradice el criterio mas permisivo)")

    if suben:
        print(f"\n  muestras de los que suben:")
        for k in suben[:6]:
            print(f"     [{k.split('|')[0]:12}] {nuevos[k]['title'][:56]}")
            print(f"        {nuevos[k]['razon'][:84]}")
    if bajan:
        print(f"\n  ** los que bajan (deberian ser 0, revisar):")
        for k in bajan[:5]:
            print(f"     [{k.split('|')[0]:12}] {nuevos[k]['razon'][:80]}")

    SALIDA.write_text(json.dumps({
        "nivel1_revisadas": len(nivel1), "rejuzgadas": len(comunes),
        "siguen_1": len(igual), "suben_a_2": len(suben), "bajan_a_0": len(bajan),
        "fallos": fallos, "detalle": nuevos}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    print(f"\n  (la actualizacion del GT no se aplica aqui: primero se revisa este informe)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
