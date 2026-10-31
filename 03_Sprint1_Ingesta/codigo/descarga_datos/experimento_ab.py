#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experimento A/B: ¿mejora las respuestas del LLM disponer de los datos (esquema+muestra)?

Brazo A: solo metadatos (title, description, theme, territory, publisher, format)
Brazo B: metadatos + dataset_files (columnas, tipos, n_rows, valores de muestra)

10 preguntas reales sobre datasets. Mismo modelo, misma temperatura.
Scoring automático: columnas reales citadas, valores de muestra usados, longitud.
"""
import json
import time
import re
import sys

import psycopg2
import requests

OLLAMA = "http://localhost:11434/api/chat"
MODEL = "deepseek-v4.1-flash"
TEMP = 0.2

DB = dict(host="localhost", port=5432, user="postgres",
          password="postgres", dbname="buscador")

# (tema_busqueda_titulo, pregunta)
PREGUNTAS = [
    ("paro registrado", "¿Este dataset permite conocer la evolución mensual del paro por municipio? ¿Con qué granularidad temporal?"),
    ("museos", "¿Qué información tiene cada museo: horarios, tipo, dirección? ¿Podría filtrar por provincia?"),
    ("accidentes", "¿Permite saber cuántos accidentes con víctimas hubo por tipo de vía y año? ¿Qué columnas lo permiten?"),
    ("residuos", "¿Puedo saber cuántas toneladas de residuos se recogieron por municipio y año? ¿Qué variables hay?"),
    ("energía solar", "¿Qué variables incluye: potencia instalada, energía generada, número de instalaciones? ¿Desglose municipal?"),
    ("población", "¿Tiene desglose por sexo y edad? ¿A nivel de municipio o provincia?"),
    ("bibliotecas", "¿Qué datos tiene cada biblioteca: dirección, horario, teléfono? ¿Puedo filtrar por comunidad autónoma?"),
    ("pensiones", "¿Permite calcular la pensión media por régimen y provincia? ¿Qué periodos cubre?"),
    ("turismo", "¿Puedo saber el número de viajeros o pernoctaciones por mes y provincia? ¿Qué columnas hay?"),
    ("natalidad", "¿Tiene desglose por provincia y año de la madre? ¿Permite calcular tasas si lo cruzo con población?"),
]

PROMPT = """Eres un asistente que ayuda a un usuario a entender si un dataset de datos abiertos puede responder a su pregunta.

{contexto}

Pregunta del usuario: {pregunta}

Responde en español, máximo 6 frases. Sé concreto: menciona nombres reales de columnas si los conoces y, si dispones de valores de muestra, úsalos como ejemplo. Si no dispones de información suficiente para algo, dilo explícitamente."""


def conn():
    return psycopg2.connect(**DB)


def buscar_dataset(cur, tema):
    """Dataset con metadatos + fichero indexado (done, con columnas ricas)."""
    cur.execute("""
        SELECT d.dataset_id, d.title, d.description, d.theme, d.territory,
               d.publisher, d.format,
               f.columns, f.n_rows, f.n_columns, f.content_text
        FROM datasets d
        JOIN dataset_files f ON f.dataset_id = d.dataset_id
        WHERE d.title ILIKE %s AND f.status='done'
          AND f.n_columns BETWEEN 3 AND 25 AND f.n_rows >= 50
        ORDER BY LENGTH(d.description) DESC
        LIMIT 1
    """, (f"%{tema}%",))
    r = cur.fetchone()
    if not r:
        return None
    keys = ("dataset_id", "title", "description", "theme", "territory",
            "publisher", "format", "columns", "n_rows", "n_columns", "content_text")
    return dict(zip(keys, r))


def contexto_meta(d):
    return (
        "Metadatos del dataset:\n"
        f"- Título: {d['title']}\n"
        f"- Descripción: {(d['description'] or '')[:500]}\n"
        f"- Tema: {d['theme']} | Territorio: {d['territory']}\n"
        f"- Publicador: {d['publisher']} | Formato: {d['format']}"
    )


def contexto_datos(d):
    base = contexto_meta(d)
    cols = d["columns"] if isinstance(d["columns"], list) else []
    if not cols and d["columns"]:
        try:
            cols = json.loads(d["columns"])
        except Exception:
            cols = []
    líneas = []
    for c in cols[:25]:
        muestras = ", ".join(str(v) for v in (c.get("sample_values") or [])[:3])
        líneas.append(f"  - {c.get('name')} ({c.get('dtype')}): ej. {muestras}")
    extra = (
        "\n\nInformación del CONTENIDO real del fichero:\n"
        f"- Filas: {d['n_rows']} | Columnas: {d['n_columns']}\n"
        "- Esquema con valores de muestra:\n" + "\n".join(líneas)
    )
    if d.get("content_text"):
        extra += "\n- Muestra de las primeras filas:\n" + d["content_text"][:1200]
    return base + extra


def nombres_columnas(cols):
    if isinstance(cols, list):
        return [c.get("name", "") for c in cols]
    try:
        return [c.get("name", "") for c in json.loads(cols or "[]")]
    except Exception:
        return []


def llamar(prompt):
    last = ""
    for intento in range(3):
        r = requests.post(OLLAMA, json={
            "model": MODEL, "stream": False,
            "options": {"temperature": TEMP, "num_predict": 500},
            "messages": [{"role": "user", "content": prompt}],
        }, timeout=120)
        r.raise_for_status()
        last = r.json()["message"]["content"].strip()
        if last:
            return last
    return last


def puntuar(respuesta, cols_reales):
    """Cita columnas reales vs inventadas (heurística de substrings)."""
    low = respuesta.lower()
    reales = [c for c in cols_reales if c and len(c) > 2 and c.lower() in low]
    return reales


def main():
    out = open("experimento_ab_resultados.jsonl", "w", encoding="utf-8")
    informe = ["# Experimento A/B — ¿El LLM responde mejor con los datos?",
               "", f"Modelo: `{MODEL}` · temp {TEMP} · 10 preguntas",
               "", "| # | Pregunta | A (metadatos) | B (metadatos+datos) | Columnas citadas A | B |",
               "|---|---|---|---|---|---|"]
    c = conn()
    cur = c.cursor()
    for i, (tema, pregunta) in enumerate(PREGUNTAS, 1):
        d = buscar_dataset(cur, tema)
        if not d:
            print(f"[{i}] sin dataset para '{tema}' — skip")
            continue
        cols_reales = nombres_columnas(d["columns"])
        pA = PROMPT.format(contexto=contexto_meta(d), pregunta=pregunta)
        pB = PROMPT.format(contexto=contexto_datos(d), pregunta=pregunta)
        t0 = time.time(); a = llamar(pA); tA = time.time() - t0
        t0 = time.time(); b = llamar(pB); tB = time.time() - t0
        citA = puntuar(a, cols_reales)
        citB = puntuar(b, cols_reales)
        rec = {"n": i, "tema": tema, "dataset": d["title"][:70],
               "pregunta": pregunta, "respuesta_A": a, "respuesta_B": b,
               "n_cols_dataset": len(cols_reales), "citadas_A": citA, "citadas_B": citB,
               "seg_A": round(tA, 1), "seg_B": round(tB, 1)}
        out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush()
        informe.append(f"| {i} | {tema} | {len(citA)}/{len(cols_reales)} cols | "
                       f"{len(citB)}/{len(cols_reales)} cols | {', '.join(citA[:3]) or '—'} | "
                       f"{', '.join(citB[:3]) or '—'} |")
        print(f"[{i}] {tema}: dataset '{d['title'][:50]}' | A citó {len(citA)} cols, B citó {len(citB)} cols")
    out.close()
    c.close()
    informe += ["", "## Respuestas completas", ""]
    for line in open("experimento_ab_resultados.jsonl", encoding="utf-8"):
        r = json.loads(line)
        informe += [f"### {r['n']}. {r['tema']}", f"**Dataset**: {r['dataset']}",
                    f"**Pregunta**: {r['pregunta']}", "",
                    f"**A (metadatos)** ({r['seg_A']}s):", r["respuesta_A"], "",
                    f"**B (metadatos+datos)** ({r['seg_B']}s):", r["respuesta_B"], "", "---", ""]
    with open("experimento_ab_20260827.md", "w", encoding="utf-8") as f:
        f.write("\n".join(informe))
    print("OK → experimento_ab_20260827.md")


if __name__ == "__main__":
    main()