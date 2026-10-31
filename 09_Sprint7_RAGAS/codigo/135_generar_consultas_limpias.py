#!/usr/bin/env python3
"""
135_generar_consultas_limpias.py — Fase C, paso 3bis: regenerar SIN anclar en titulos.

POR QUE SE REGENERA
Las 169 consultas de la version anterior se generaron mostrando al LLM 40 titulos
REALES del catalogo. El LLM copio su vocabulario y eso favorecio al motor lexico por
construccion: el semantico cayo -0,1854 y el lexico subio +0,1834 SOLO en las nuevas,
y el vuelco entre motores dependia del solapamiento (0,38 puntos de diferencia entre
tercios). Documentado en docs/FASE-C-PASO3-HALLAZGO-CONTAMINACION.md.

QUE CAMBIA
1. NO se le muestran titulos del catalogo. Ni uno. El LLM ve el tema y las facetas.
2. SI se le muestran las 47 consultas humanas del mismo tema, solo como EJEMPLO DE
   REGISTRO. Es el movimiento clave: calibra el estilo al de una persona (solapamiento
   0,571) en vez de al del catalogo (0,735). Y se le prohibe repetirlas.
3. La respondibilidad se valida DESPUES contra el motor, no primando el texto.

CRITERIO DE ACEPTACION (medido, no filtrado por consulta)
El solapamiento medio del conjunto debe quedar por debajo del de las 47 humanas.
No se descarta ninguna consulta por solapamiento: eso seria elegir el conjunto para
que favorezca una conclusion. El unico descarte legitimo es "no devuelve nada".
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
GT_VIEJO = ENTREG / "ground_truth.jsonl"
SALIDA = ENTREG / "consultas_limpias.jsonl"
CHECKPOINT = ENTREG / "_checkpoint_limpias.json"
CTRL = ENTREG / "control_solapamiento_limpias.json"
API = "http://localhost:8000/search"

MODELO = "deepseek-v4.1-flash"
STOP = {"de", "la", "el", "los", "las", "en", "por", "para", "con", "que", "del",
        "al", "y", "o", "un", "una", "segun", "sobre", "su", "sus", "es", "the"}

CATS = {
    "empleo": "empleo",
    "demografía": "demografia",
    "economía": "economia",
    "transporte": "transporte",
    "medio ambiente": "medio-ambiente",
    "cultura": "cultura",
    "deporte": "deporte",
    "sanidad": "salud",
    "educación": "educacion",
    "ciencia y tecnología": "ciencia-tecnologia",
    "sociedad y bienestar": "sociedad-bienestar",
    "ambigua": None,
}
OBJETIVO_POR_CAT = 18
DIFICULTAD = {"fácil": 0.23, "media": 0.57, "difícil": 0.19}

PROMPT = """Eres documentalista del portal de datos abiertos datos.gob.es.

TAREA: escribir {n} consultas de busqueda NUEVAS sobre el tema "{cat}".

EJEMPLOS DEL MISMO SISTEMA (consultas reales ya existentes sobre este tema).
Sirven SOLO para que copies su REGISTRO: asi escribe una persona cuando busca.
NO repitas ninguna ni escribas variaciones de ellas con las mismas palabras.
{ejemplos}

REGLAS OBLIGATORIAS
1. NO incluyas el pais ni el ambito territorial: nada de "Espana", "nacional" ni
   comunidades. Quien decide la relevancia ya sabe que el catalogo es espanol.
2. Longitud: entre 2 y 6 palabras. Estilo telegrafico de buscador, no frase.
3. NO anadas el periodo salvo que sea inequivoco (ej. "censo 2024").
4. Cada consulta debe apuntar a un FENOMENO concreto, con una palabra o dos que lo
   nombren de forma reconocible. Escribe como escribe un ciudadano, un periodista o
   un investigador; NO imites el lenguaje de un catalogo de datos ni de un informe
   administrativo.
5. Cubre FACETAS DISTINTAS del tema (colectivos, indicadores, servicios,
   infraestructuras, opinion...). No escribas 18 variaciones de lo mismo.

DIFICULTAD (reparto obligatorio de las {n}):
   ~23 % "facil": termino directo, 2-3 palabras
   ~57 % "media": fenomeno + una faceta o colectivo
   ~19 % "dificil": matiz, dos condiciones o termino poco frecuente

Responde SOLO con un JSON en una linea:
{{"consultas": [{{"query": "...", "dificultad": "facil|media|dificil",
                 "intencion": "que busca el usuario, en una frase",
                 "facetas": ["que desglose o matiz esperaria"]}}, ...]}}"""

PROMPT_AMBIGUA = """Eres documentalista del portal de datos abiertos datos.gob.es.

TAREA: escribir {n} consultas de busqueda AMBIGUAS en espanol: terminos que
significan cosas distintas segun el contexto, y que por tanto pueden traer
resultados de fenomenos diferentes.

EJEMPLOS DEL MISMO SISTEMA (no los repitas): {ejemplos}

REGLAS
1. Palabra o expresion corta (1-3 palabras) con DOS o mas significados claros.
2. NO incluyas ambito territorial ni periodo.
3. NO imites lenguaje de catalogo ni administrativo: como lo escribiria una persona.

Responde SOLO con un JSON en una linea:
{{"consultas": [{{"query": "...", "dificultad": "media",
                 "intencion": "que busca el usuario, en una frase",
                 "facetas": ["que desglose o matiz esperaria"], "sentidos": ["..."]}}]}}"""


def leer_clave():
    for ruta in (Path.cwd() / ".env",
                 Path(__file__).resolve().parent / ".env"):
        if ruta.exists():
            for ln in ruta.read_text(encoding="utf-8").splitlines():
                if ln.startswith("OLLAMA_API_KEY="):
                    return ln.split("=", 1)[1].strip()
    return os.getenv("OLLAMA_API_KEY")


def llama(prompt, clave):
    body = json.dumps({"model": MODELO, "messages": [{"role": "user", "content": prompt}],
                       "options": {"temperature": 0.7}, "stream": False}).encode()
    req = urllib.request.Request("https://ollama.com/api/chat", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {clave}"})
    txt = json.loads(urllib.request.urlopen(req, timeout=300).read())["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("sin JSON en la respuesta")
    return json.loads(m.group(0)).get("consultas", [])


def busca(q, top_k=10, **kw):
    body = {"query": q, "top_k": top_k}
    body.update(kw)
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=120).read())
    except Exception:
        return []
    return d.get("results") or d.get("datasets") or []


def tokens(s):
    return {w for w in re.findall(r"[a-záéíóúüñ0-9]+", (s or "").lower())
            if len(w) > 3 and w not in STOP}


def solapamiento(query, res):
    """Mismo calculo que el script 134, para que las cifras sean comparables."""
    t = tokens(query)
    if not t or not res:
        return 0.0
    vals = []
    for r in res[:1]:
        tt = tokens(r.get("title", "")) | tokens((r.get("description") or "")[:300])
        vals.append(len(t & tt) / len(t))
    return max(vals) if vals else 0.0


def norm_dif(d):
    d = (d or "").lower().replace("í", "i").replace("á", "a").replace("é", "e")
    return {"facil": "fácil", "media": "media", "dificil": "difícil"}.get(d, "media")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--categorias", default=None, help="subconjunto separado por comas")
    ap.add_argument("--simular", action="store_true", help="no llama al LLM")
    args = ap.parse_args()

    viejas = [json.loads(l) for l in GT_VIEJO.read_text(encoding="utf-8").splitlines() if l.strip()]
    por_cat = Counter(q.get("categoria", "?") for q in viejas)

    print("=" * 86)
    print("GENERACION LIMPIA · sin titulos del catalogo, estilo calibrado con las humanas")
    print("=" * 86)
    print(f"\n  consultas humanas existentes: {len(viejas)}")

    cats = list(CATS)
    if args.categorias:
        pedidas = {s.strip() for s in args.categorias.split(",")}
        cats = [c for c in cats if c in pedidas]

    plan = {}
    for c in cats:
        n = max(0, OBJETIVO_POR_CAT - por_cat.get(c, 0))
        if n:
            plan[c] = n
    print(f"  a generar: {sum(plan.values())} consultas en {len(plan)} categorias")
    for c, n in plan.items():
        print(f"     {c:22} {n:2}  (ya hay {por_cat.get(c,0)})")
    if args.simular:
        return 0

    clave = leer_clave()
    if not clave:
        print("ERROR: falta OLLAMA_API_KEY")
        return 1

    generadas = []
    if CHECKPOINT.exists():
        generadas = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        print(f"\n  reanudando: {len(generadas)} ya generadas")
    hechas = {g["categoria"] for g in generadas}
    # BUG CORREGIDO: este conjunto se reinicializaba en cada categoria, asi que dos
    # categorias distintas podian producir la misma consulta. Se inicializa UNA vez.
    usadas = {q["query"].lower().strip() for q in viejas} | \
             {g["query"].lower().strip() for g in generadas}

    for cat in plan:
        if cat in hechas:
            continue
        # EJEMPLOS: las consultas humanas de esa categoria (registro, no vocabulario)
        ej = [q["query"] for q in viejas if q.get("categoria") == cat]
        n = plan[cat]
        if cat == "ambigua":
            prompt = PROMPT_AMBIGUA.format(n=n, ejemplos=", ".join(f'"{e}"' for e in ej[:12]))
        else:
            prompt = PROMPT.format(n=n, cat=cat,
                                   ejemplos="\n".join(f'  - "{e}"' for e in ej[:14]))
        print(f"\n  [{cat}] pidiendo {n} consultas (sin titulos del catalogo)...")
        res = None
        for intento in range(3):
            try:
                res = llama(prompt, clave)
                break
            except Exception as e:
                print(f"     reintento {intento+1}: {str(e)[:70]}")
                time.sleep(4 * (intento + 1))
        if not res:
            print(f"     FALLO en {cat} — se deja para una segunda pasada")
            continue
        n_ok = 0
        for r in res:
            q = (r.get("query") or "").strip()
            if not q or len(q.split()) > 7 or q.lower() in usadas:
                continue
            usadas.add(q.lower())
            n_ok += 1
            generadas.append({
                "query": q, "categoria": cat, "dificultad": norm_dif(r.get("dificultad")),
                "descripcion": (r.get("intencion") or "")[:300],
                "criterios_relevancia": r.get("facetas") or [],
                "origen": "faseC_paso3bis_limpia"})
        print(f"     {n_ok} validas de {len(res)}")
        CHECKPOINT.write_text(json.dumps(generadas, ensure_ascii=False, indent=1),
                              encoding="utf-8")

    # ---- validacion contra el motor + solapamiento ----
    print(f"\n### VALIDACION CONTRA EL MOTOR ###\n")
    for i, g in enumerate(generadas, 1):
        res = busca(g["query"])
        g["_n_resultados"] = len(res)
        g["_sim_top1"] = round(res[0].get("score", 0), 4) if res else 0.0
        g["_solapamiento"] = round(solapamiento(g["query"], res), 4)
        if i % 25 == 0:
            print(f"  [{i}/{len(generadas)}]")
        time.sleep(0.05)

    con_res = [g for g in generadas if g["_n_resultados"] > 0]
    sin_res = [g for g in generadas if g["_n_resultados"] == 0]

    # solapamiento de las 47 humanas, con el MISMO calculo
    print(f"\n  midiendo el solapamiento de las 47 humanas (referencia)...")
    sol_h = []
    for q in viejas:
        sol_h.append(solapamiento(q["query"], busca(q["query"])))
    ref = sum(sol_h) / len(sol_h) if sol_h else 0

    sol_n = [g["_solapamiento"] for g in con_res]
    media_n = sum(sol_n) / len(sol_n) if sol_n else 0

    print(f"\n### CONTROL DE SOLAPAMIENTO (el que invalido la version anterior) ###\n")
    print(f"  {'conjunto':28} {'n':>4} {'solapamiento medio':>20}")
    print(f"  {'-'*28} {'-'*4} {'-'*20}")
    print(f"  {'47 humanas (referencia)':28} {len(sol_h):4} {ref:20.3f}")
    print(f"  {'169 nuevas (limpias)':28} {len(sol_n):4} {media_n:20.3f}")
    print(f"\n  anterior (con titulos): 0,735   <- el valor que delato el sesgo")
    veredicto = ("PASA" if media_n <= ref else "NO PASA: sigue por encima de las humanas")
    print(f"  criterio: <= {ref:.3f} (el de las humanas)  ->  {veredicto}")

    print(f"\n### RESUMEN ###\n")
    print(f"  generadas con resultado : {len(con_res)}")
    print(f"  sin ningun resultado    : {len(sin_res)}  (unico descarte legitimo)")
    print(f"  por dificultad          : {dict(Counter(g['dificultad'] for g in con_res))}")
    print(f"  por categoria           : {dict(Counter(g['categoria'] for g in con_res))}")

    with SALIDA.open("w", encoding="utf-8") as f:
        for g in con_res:
            f.write(json.dumps(g, ensure_ascii=False) + "\n")
    CTRL.write_text(json.dumps({
        "solapamiento_humanas": round(ref, 4),
        "solapamiento_limpias": round(media_n, 4),
        "solapamiento_version_contaminada": 0.735,
        "n_humanas": len(sol_h), "n_limpias": len(con_res),
        "pasa": bool(media_n <= ref),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    print(f"  guardado: {CTRL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
