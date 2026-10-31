#!/usr/bin/env python3
"""
119_fijar_ambito.py — Fase C, paso 1: quitar la ambigüedad de la consulta.

PROBLEMA QUE RESUELVE
Las consultas actuales omiten el ámbito: "pasajeros aeropuerto" no dice de qué
país. El juicio de relevancia tuvo que adivinar la intención, y eso fue el origen
de TODAS las discrepancias medidas en la escala de 3 niveles (el nivel 1
"mismo tema, otro ámbito" existe justo por esta ambigüedad).

REGLA DE ORO (verificada antes de escribir esto)
La consulta es lo que se le muestra al juez. Si cambia el texto, cambia el juicio.
Por eso:
  - Se conserva el `id` (empleo_001 sigue siendo empleo_001) para no perder las
    1.424 etiquetas ya obtenidas.
  - La `descripcion` (la INTENCION DECLARADA que va al prompt del juez) NO se
    toca: es la que hizo válido el juicio existente.
  - Se guarda el texto original en `query_original` para trazabilidad y para
    poder medir el efecto del cambio.
  - Las 3 consultas de la categoría "ambigua" NO se tocan: su ambigüedad es
    deliberada, miden la robustez ante consultas vagas. Reescribirlas las
    destruiría.

SALIDA
entregables/consultas_v2.jsonl — misma estructura + query_original + ambito
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
GT = ENTREG / "ground_truth.jsonl"
SALIDA = ENTREG / "consultas_v2.jsonl"
MODELO = "deepseek-v4.1-flash"

PROMPT = """Eres documentalista de un portal de datos abiertos espanol (datos.gob.es).

Tu tarea: reescribir UNA consulta de busqueda para que el AMBITO quede explicito,
sin cambiar el fenomeno que pide.

PROBLEMA ACTUAL: consultas como "pasajeros aeropuerto" son ambiguas. No dicen de
que pais, ni de que periodo. Eso obliga a quien decide la relevancia a adivinar,
y provoca que se marquen como relevantes datos de otros paises.

QUE DEBES HACER
1. Anadir el ambito SOLO si falta: el pais ("Espana") o el territorio implicito.
   Si la consulta ya dice el ambito, apenas toques nada.
2. NO anadas el periodo salvo que sea inequivoco y estable (ej. "censo 2024").
   Un periodo inventado descartaria datos validos.
3. NO conviertas la consulta en una frase larga. Sigue siendo una busqueda:
   entre 3 y 7 palabras. El usuario real escribe telegraficamente.
4. NO cambies el fenomeno. "consumo agua" no puede volverse "consumo energia".
5. NO anadas desgloses (por sexo, por edad) que el usuario no haya pedido.
6. Manten el idioma espanol y el estilo natural de busqueda.

CONSULTA ORIGINAL: "{query}"
INTENCION QUE SE LE PRESUPONE: {descripcion}
CATEGORIA: {categoria}

Responde SOLO con un JSON en una linea:
{{"query": "la consulta reescrita", "ambito": "el ambito que has fijado, o 'ya explicito'", "cambio": "que has cambiado, en menos de 15 palabras"}}"""


def leer_clave():
    for ruta in (Path.cwd() / ".env",
                 Path(__file__).resolve().parent / ".env"):
        if ruta.exists():
            for ln in ruta.read_text(encoding="utf-8").splitlines():
                if ln.startswith("OLLAMA_API_KEY="):
                    return ln.split("=", 1)[1].strip()
    return os.getenv("OLLAMA_API_KEY")


def consulta_llm(prompt, clave, intentos=3):
    body = json.dumps({"model": MODELO,
                       "messages": [{"role": "user", "content": prompt}],
                       "options": {"temperature": 0},
                       "stream": False}).encode()
    req = urllib.request.Request("https://ollama.com/api/chat", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {clave}"})
    for n in range(intentos):
        try:
            txt = json.loads(urllib.request.urlopen(req, timeout=180).read())["message"]["content"]
            m = re.search(r"\{.*\}", txt, re.S)
            if m:
                return json.loads(m.group(0))
        except Exception as e:
            if n == intentos - 1:
                raise
            time.sleep(2 * (n + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--salida", default=str(SALIDA))
    ap.add_argument("--simular", action="store_true",
                    help="no llama al LLM; solo comprueba el reparto")
    args = ap.parse_args()

    consultas = [json.loads(l) for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limite:
        consultas = consultas[:args.limite]

    intocables = [q["id"] for q in consultas if q["categoria"] == "ambigua"]

    print("=" * 78)
    print("FASE C · PASO 1 · FIJAR EL AMBITO EN LAS CONSULTAS")
    print("=" * 78)
    print(f"\n  consultas a procesar : {len(consultas)}")
    print(f"  intocables (ambiguas): {len(intocables)} -> {', '.join(intocables)}")
    print(f"  ambiguas: su vaguedad es DELIBERADA (miden robustez), no se reescriben\n")

    if args.simular:
        for q in consultas:
            marca = "SALTAR " if q["categoria"] == "ambigua" else "reescr."
            print(f"  {marca} {q['id']:14} {q['query']}")
        print(f"\n  (simulacion: sin llamadas al LLM)")
        return 0

    clave = leer_clave()
    if not clave:
        print("ERROR: falta OLLAMA_API_KEY")
        return 1

    salida, cambios, sin_cambio = [], [], []
    for i, q in enumerate(consultas, 1):
        nueva = dict(q)
        nueva["query_original"] = q["query"]

        if q["categoria"] == "ambigua":
            nueva["ambito"] = "deliberadamente ambiguo"
            nueva["cambio"] = "no se toca (ambiguedad intencional)"
            salida.append(nueva)
            print(f"  [{i:2}/{len(consultas)}] {q['id']:14} SALTADA (ambigua intencional)")
            continue

        try:
            r = consulta_llm(PROMPT.format(query=q["query"],
                                           descripcion=q.get("descripcion") or "-",
                                           categoria=q["categoria"]), clave)
        except Exception as e:
            r = None
            print(f"     fallo: {str(e)[:60]}")

        if not r or not r.get("query"):
            nueva["ambito"] = "ERROR: sin respuesta"
            sin_cambio.append(q["id"])
            salida.append(nueva)
            print(f"  [{i:2}/{len(consultas)}] {q['id']:14} FALLO -> se conserva el original")
            continue

        texto = str(r["query"]).strip().strip('"')
        nueva["query"] = texto
        nueva["ambito"] = str(r.get("ambito", ""))[:120]
        nueva["cambio"] = str(r.get("cambio", ""))[:160]

        if texto.lower() == q["query"].lower():
            sin_cambio.append(q["id"])

        marca = "=" if texto.lower() == q["query"].lower() else "->"
        print(f"  [{i:2}/{len(consultas)}] {q['id']:14} {q['query']}")
        print(f"                     {marca} {texto}")
        if marca == "->":
            cambios.append(q["id"])
        salida.append(nueva)
        time.sleep(0.3)

    p = Path(args.salida)
    with p.open("w", encoding="utf-8") as f:
        for q in salida:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    # CONTROL DE INTEGRIDAD: el fichero debe tener tantas lineas como consultas.
    # Sirve para no repetir el fallo del 25-sep: una rama sin `salida.append`
    # escribio 3 lineas de 47 y el script dijo "38 reescritas" tan tranquilo.
    escritas = sum(1 for _ in p.open(encoding="utf-8"))
    print(f"\n### CONTROL DE INTEGRIDAD ###\n")
    print(f"  consultas de entrada : {len(consultas)}")
    print(f"  lineas escritas      : {escritas}")
    if escritas != len(consultas):
        print(f"  ** FALLO: se han perdido {len(consultas) - escritas} consultas **")
        return 2
    print(f"  OK: no se ha perdido ninguna consulta")

    print(f"\n### RESUMEN ###\n")
    print(f"  reescritas     : {len(cambios)}")
    print(f"  sin cambio     : {len(sin_cambio)}")
    print(f"  fallos         : {len([q for q in salida if str(q.get('ambito','')).startswith('ERROR')])}")
    print(f"  ambiguas puras : {len(intocables)}")
    print(f"\n  guardado: {p}")
    print(f"\n  IMPORTANTE: la `descripcion` (intencion declarada) NO se ha tocado,")
    print(f"  asi que el juicio de las 1.424 etiquetas sigue siendo valido.")
    print(f"  La consulta SI cambia -> el ranking cambia -> hay que re-medir")
    print(f"  y cerrar el hueco de cobertura que aparezca.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
