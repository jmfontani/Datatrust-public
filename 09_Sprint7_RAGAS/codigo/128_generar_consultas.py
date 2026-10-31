#!/usr/bin/env python3
"""
128_generar_consultas.py — Fase C, paso 2: ampliar a ~215 consultas.

OBJETIVO
47 consultas -> 216. Con 47 la mejora minima detectable es 0,106; con 216 baja a
~0,050. Es lo que permite que la comparacion MiniLM vs BGE-M3 (Fase E) pueda
concluir algo en vez de salir "no distinguible del ruido".

PRINCIPIO DE DISENO: LA CONSULTA DEBE PODER TENER RESPUESTA
Una consulta que el catalogo no puede responder no mide al recuperador: mide la
ausencia de datos. Por eso cada llamada al LLM recibe TITULOS REALES del tema
sacados de la base de datos, y se le pide que genere consultas que ese material
PUEDA responder. Despues se valida contra la API (script 129).

EL AMBITO NO SE FUERZA EN EL TEXTO
Es la conclusion del paso 1 (docs/FASE-C-PASO1-HALLAZGO.md): el ambito va en el
criterio del juez. Aqui se aplica al generar la `descripcion` (la intencion
declarada que ve el juez): describe el FENOMENO y la faceta, nunca exige ambito
nacional.

REPARTO
12 categorias x 18 = 216. Se conserva el nombre de las 10 categorias existentes y
se anaden dos con masa real en el catalogo (ciencia-tecnologia, sociedad-bienestar).
La dificultad se mantiene en la proporcion medida del GT actual (23/57/19 %).
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
GT = ENTREG / "ground_truth.jsonl"
SALIDA = ENTREG / "consultas_nuevas.jsonl"
CHECKPOINT = ENTREG / "_checkpoint_consultas.json"

MODELO = "deepseek-v4.1-flash"
OBJETIVO_POR_CAT = 18

# categoria -> clave de tema en la BD (None = sin anclaje tematico)
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

PROMPT_TEMA = """Eres documentalista del portal de datos abiertos datos.gob.es.

TAREA: escribir {n} consultas de busqueda NUEVAS sobre el tema "{cat}", del tipo
que escribiria un ciudadano, un periodista o un investigador.

MATERIAL REAL DEL CATALOGO (titulos de conjuntos de datos que SI existen sobre
este tema). Las consultas deben poder responderse con material como este:
{titulos}

REGLAS OBLIGATORIAS
1. NO repitas ninguna de estas consultas ya existentes: {existentes}
2. NO incluyas el pais ni el ambito territorial en el texto. Nada de "Espana",
   "nacional" ni comunidades. Quien decide la relevancia ya sabe que el catalogo
   es espanol. Escribela como la escribiria un usuario real.
3. Longitud: entre 2 y 6 palabras. Estilo telegrafico de buscador, no frase.
4. NO anadas el periodo salvo que sea inequivoco (ej. "censo 2024").
5. Cada consulta debe apuntar a un FENOMENO concreto que exista en el catalogo.
   Si dudas de que haya datos, elige otro.
6. Variedad: no escribas 18 variaciones de lo mismo. Cubre facetas distintas del
   tema (colectivos, indicadores, servicios, infraestructuras, opinion...).

DIFICULTAD (reparto obligatorio de las {n}):
   ~23 % "facil": termino directo, 2-3 palabras (ej. "paro registrado")
   ~57 % "media": fenomeno + una faceta o colectivo (ej. "paro juvenil por sexo")
   ~19 % "dificil": matiz, dos condiciones o termino poco frecuente

Responde SOLO con un JSON en una linea:
{{"consultas": [{{"query": "...", "dificultad": "facil|media|dificil",
                 "intencion": "que busca el usuario, en una frase",
                 "facetas": ["que desglose o matiz esperaria"]}}, ...]}}"""

PROMPT_AMBIGUA = """Eres documentalista del portal de datos abiertos datos.gob.es.

TAREA: escribir {n} consultas de busqueda AMBIGUAS en espanol: terminos que
significan cosas distintas segun el contexto, y que por tanto pueden traer
resultados de fenomenos diferentes.

EJEMPLOS DEL GT ACTUAL (no los repitas): {existentes}

REGLAS
1. Palabra o expresion corta (1-3 palabras) con DOS o mas significados claros en
   el ambito de los datos publicos. Ejemplos del tipo de termino: "banco"
   (entidad financiera / banco de peces / banco de datos), "planta"
   (vegetal / instalacion industrial / planta de edificio).
2. El catalogo DEBE tener datos de al menos una de las acepciones. Se listan
   titulos reales para que compruebes que hay material:
{titulos}
3. NO repitas ninguna de las ya existentes.
4. La ambiguedad es DELIBERADA: sirve para medir la robustez del recuperador ante
   consultas vagas. No la resuelvas anadiendo contexto.

Responde SOLO con un JSON en una linea:
{{"consultas": [{{"query": "...", "dificultad": "dificil",
                 "intencion": "las dos acepciones, separadas por ' / '",
                 "facetas": ["acepcion 1", "acepcion 2"]}}, ...]}}"""


def leer_clave():
    for ruta in (Path.cwd() / ".env",
                 Path(__file__).resolve().parent / ".env"):
        if ruta.exists():
            for ln in ruta.read_text(encoding="utf-8").splitlines():
                if ln.startswith("OLLAMA_API_KEY="):
                    return ln.split("=", 1)[1].strip()
    return os.getenv("OLLAMA_API_KEY")


def llama(prompt, clave):
    body = json.dumps({"model": MODELO,
                       "messages": [{"role": "user", "content": prompt}],
                       "options": {"temperature": 0.4},
                       "stream": False}).encode()
    req = urllib.request.Request("https://ollama.com/api/chat", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {clave}"})
    txt = json.loads(urllib.request.urlopen(req, timeout=600).read())["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("sin JSON en la respuesta")
    return json.loads(m.group(0)).get("consultas", [])


def titulos_de(conn, tema, n=40):
    """Titulos reales del tema. Son la prueba de que el material existe."""
    if tema is None:
        # para ambiguas: titulos cortos y genericos, que es donde vive la ambiguedad
        sql = """SELECT title FROM datasets
                 WHERE title IS NOT NULL AND length(title) BETWEEN 25 AND 70
                 ORDER BY random() LIMIT %s"""
        args = (n,)
    else:
        sql = """SELECT title FROM datasets
                 WHERE title IS NOT NULL AND length(title) >= 35
                   AND theme ILIKE %s
                 ORDER BY random() LIMIT %s"""
        args = (f"%{tema}%", n)
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(sql, args)
        return [r["title"][:130] for r in cur.fetchall()]


def main():
    clave = leer_clave()
    if not clave:
        print("ERROR: falta OLLAMA_API_KEY")
        return 1

    existentes = [json.loads(l) for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()]
    por_cat = Counter(q["categoria"] for q in existentes)
    ya = {q["query"].lower().strip() for q in existentes}

    print("=" * 80)
    print("FASE C · PASO 2 · GENERAR LAS CONSULTAS NUEVAS")
    print("=" * 80)
    print(f"\n  existentes: {len(existentes)}")
    print(f"  objetivo  : {OBJETIVO_POR_CAT} por categoria x {len(CATS)} = "
          f"{OBJETIVO_POR_CAT*len(CATS)}")
    print(f"\n  deficits:")
    deficits = {}
    for cat in CATS:
        n_ya = por_cat.get(cat, 0)
        deficits[cat] = max(0, OBJETIVO_POR_CAT - n_ya)
        print(f"     {cat:24} tiene {n_ya:>2}  -> faltan {deficits[cat]:>2}")
    total = sum(deficits.values())
    print(f"\n  a generar: {total}   total quedaria: {len(existentes)+total}")

    conn = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "postgres"),
                            dbname=os.getenv("POSTGRES_DB", "buscador"),
                            user=os.getenv("POSTGRES_USER", "postgres"),
                            password=os.getenv("POSTGRES_PASSWORD", "postgres"))

    # checkpoint: permite reanudar sin repetir llamadas
    estado = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.exists() else {}
    nuevas = list(estado.get("generadas", []))
    hechas_cat = Counter(n["categoria"] for n in nuevas)
    if nuevas:
        print(f"\n  reanudando: ya hay {len(nuevas)} generadas")

    for cat, falta in deficits.items():
        pendientes = falta - hechas_cat.get(cat, 0)
        if pendientes <= 0:
            print(f"\n  [{cat}] ya completo")
            continue

        titulos = titulos_de(conn, CATS[cat])
        ejemplos_cat = [q["query"] for q in existentes if q["categoria"] == cat]
        if cat == "ambigua":
            prompt = PROMPT_AMBIGUA.format(n=pendientes,
                                           existentes=", ".join(f'"{e}"' for e in ejemplos_cat),
                                           titulos="\n".join(f"  - {t}" for t in titulos[:30]))
        else:
            prompt = PROMPT_TEMA.format(n=pendientes, cat=cat,
                                        titulos="\n".join(f"  - {t}" for t in titulos),
                                        existentes=", ".join(f'"{e}"' for e in ejemplos_cat))

        print(f"\n  [{cat}] pidiendo {pendientes} consultas (con {len(titulos)} titulos reales)...")
        try:
            res = llama(prompt, clave)
        except Exception as e:
            print(f"     fallo: {str(e)[:70]}")
            continue

        validas = 0
        for r in res:
            q = str(r.get("query", "")).strip().strip('"')
            if not q or q.lower() in ya:
                continue
            if len(q.split()) > 8:
                continue
            ya.add(q.lower())
            idx = len(existentes) + len(nuevas) + 1
            pref = {"empleo": "emp", "demografía": "dem", "economía": "eco",
                    "transporte": "tra", "medio ambiente": "med", "cultura": "cul",
                    "deporte": "dep", "sanidad": "san", "educación": "edu",
                    "ciencia y tecnología": "cie", "sociedad y bienestar": "soc",
                    "ambigua": "amb"}[cat]
            dif = str(r.get("dificultad", "media")).lower()
            dif = {"facil": "fácil", "fácil": "fácil", "media": "media",
                   "dificil": "difícil", "difícil": "difícil"}.get(dif, "media")
            nuevas.append({
                "id": f"{pref}_{900+len(nuevas)}",
                "query": q,
                "categoria": cat,
                "dificultad": dif,
                "descripcion": str(r.get("intencion", ""))[:240],
                "criterios_relevancia": [str(f)[:120] for f in (r.get("facetas") or [])][:5],
                "origen": "faseC_paso2",
            })
            validas += 1
        print(f"     -> {validas} validas (total acumulado {len(nuevas)})")

        CHECKPOINT.write_text(json.dumps({"generadas": nuevas}, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        time.sleep(1)
    conn.close()

    print(f"\n### RESUMEN ###\n")
    print(f"  nuevas generadas: {len(nuevas)}")
    print(f"  por categoria    : {dict(sorted(Counter(n['categoria'] for n in nuevas).items()))}")
    print(f"  por dificultad   : {dict(sorted(Counter(n['dificultad'] for n in nuevas).items()))}")
    largas = [n["query"] for n in nuevas if len(n["query"].split()) > 6]
    # OJO con la comprobacion: "nacionalidad" CONTIENE "nacional" y no es ambito.
    # Hay que comparar palabras completas, no subcadenas (error detectado al usarlo).
    _AMB = {"españa", "espana", "nacional", "estatal", "estatales"}
    def _tiene_ambito(q):
        return bool(_AMB & set(re.findall(r"[a-záéíóúñ]+", q.lower())))
    amb = [n["query"] for n in nuevas if _tiene_ambito(n["query"])]
    print(f"\n  consultas largas (>6 pal.): {len(largas)}")
    for q in largas[:5]:
        print(f"     {q}")
    print(f"  con ambito en el texto    : {len(amb)}  (deberia ser 0)")
    for q in amb[:5]:
        print(f"     {q}")

    SALIDA.write_text("\n".join(json.dumps(n, ensure_ascii=False) for n in nuevas) + "\n",
                      encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
