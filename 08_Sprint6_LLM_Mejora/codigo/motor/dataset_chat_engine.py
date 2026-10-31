#!/usr/bin/env python3
"""
Motor de chat para respuestas sobre datasets - Caso de Uso #10.

RAG basado en metadatos del dataset (título, descripción, TL;DR, perfil
estructurado) + ESTRUCTURA REAL del fichero descargado (tabla dataset_files):
n_rows, n_columns, esquema con tipos y valores de muestra, y head de filas.

Umbral de contexto: se inyectan como máximo MAX_COLS_IN_PROMPT columnas y
SAMPLE_ROWS_CHARS caracteres de muestra; para ficheros grandes se indica el
tamaño en MB en lugar de volcar contenido completo.
"""

import json
import time
import signal
from typing import Optional

import ollama
import psycopg2


DB_CONFIG = {
    "host": "172.17.0.1",
    "port": 5432,
    "database": "buscador",
    "user": "postgres",
    "password": "postgres"
}

# Umbrales del contexto de datos inyectado al LLM
MAX_COLS_IN_PROMPT = 30        # columnas del esquema inyectadas (con muestra de valores)
SAMPLE_ROWS_CHARS = 4000       # caracteres máx. de la muestra de primeras filas
LARGE_FILE_MB = 5              # a partir de aquí se avisa de "fichero grande"


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("LLM call exceeded timeout")


SYSTEM_PROMPT = """Eres un asistente experto en datos abiertos del portal datos.gob.es.
Responde preguntas SOBRE UN DATASET CONCRETO usando los metadatos Y, cuando estén
disponibles, la ESTRUCTURA REAL del fichero de datos (número de filas, columnas con
sus tipos y valores de ejemplo, y una muestra de las primeras filas).
La sección "ESTRUCTURA DEL FICHERO" describe el contenido real descargado del dataset:
apóyate en ella para responder con precisión (nombres de columnas exactos, número de
registros, granularidad, tipos de valores). Si preguntan por registros y hay n_filas,
esa es la respuesta. Distingue filas del fichero de registros teóricos de la fuente.
Si la respuesta no se puede inferir de la información proporcionada, di
"No puedo determinarlo a partir de la información disponible".
Responde de forma concisa, clara y útil en español. No inventes información."""


USER_PROMPT_TEMPLATE = """Información del dataset:

- ID: {dataset_id}
- Título: {title}
- Descripción: {description}
- TL;DR: {tldr}
- Variables principales: {variables}
- Cobertura temporal: {temporal_coverage}
- Nivel geográfico: {geographic_level}
- Entidad geográfica: {geographic_entity}
- Frecuencia de actualización: {frecuencia}
- Formatos disponibles: {formatos}
- Tema principal: {tema_principal}

Pregunta del usuario: {question}

{estructura_fichero}

Responde de forma directa y basada solo en la información anterior."""


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def _parse_columns(cols):
    """columns llega como jsonb ya parseado (lista) o como string JSON."""
    if isinstance(cols, list):
        return cols
    try:
        return json.loads(cols) if cols else []
    except Exception:
        return []


def get_file_structure(dataset_id: str) -> Optional[str]:
    """Devuelve el bloque 'ESTRUCTURA DEL FICHERO' para el prompt (con umbrales),
    o None si no hay fichero índexado."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT columns, n_rows, n_columns, content_text, size_bytes, format
            FROM dataset_files
            WHERE dataset_id = %s AND status = 'done'
        """, (dataset_id,))
        row = cur.fetchone()
    conn.close()
    if not row:
        return None

    cols, n_rows, n_cols, content_text, size_bytes = row[0], row[1], row[2], row[3], row[4]
    col_list = _parse_columns(cols) if cols else []

    partes = ["ESTRUCTURA DEL FICHERO (contenido real descargado del dataset):"]
    if size_bytes:
        mb = size_bytes / (1024 * 1024)
        if mb >= LARGE_FILE_MB:
            partes.append(f"- Tamaño del fichero: {mb:.1f} MB (fichero grande: la muestra "
                          f"de filas es solo ilustrativa, no representa todo el contenido)")
        else:
            partes.append(f"- Tamaño del fichero: {mb:.2f} MB")
    if n_rows:
        partes.append(f"- Número de filas (registros) del fichero: {n_rows:,}".replace(",", "."))
    if n_cols:
        partes.append(f"- Número de columnas: {n_cols}")

    if col_list:
        lineas = []
        for c in col_list[:MAX_COLS_IN_PROMPT]:
            muestras = ", ".join(str(v) for v in (c.get("sample_values") or [])[:3])
            lineas.append(f"  * {c.get('name')} ({c.get('dtype')}): ej. {muestras}")
        if len(col_list) > MAX_COLS_IN_PROMPT:
            lineas.append(f"  … y {len(col_list) - MAX_COLS_IN_PROMPT} columnas más")
        partes.append("- Esquema con valores de ejemplo:\n" + "\n".join(lineas))

    if content_text:
        partes.append("- Muestra de las primeras filas:\n" + content_text[:SAMPLE_ROWS_CHARS])

    return "\n".join(partes)


def get_dataset_context(dataset_id: str) -> Optional[dict]:
    """Recupera contexto de metadatos del dataset desde BD."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                d.dataset_id,
                d.title,
                d.description,
                p.tldr,
                p.variables_key,
                p.temporal_coverage,
                p.geographic_level,
                p.geographic_entity,
                p.frecuencia,
                p.formatos,
                d.theme_label,
                d.territory,
                d.format
            FROM datasets d
            LEFT JOIN dataset_profiles p ON d.dataset_id = p.dataset_id
            WHERE d.dataset_id = %s
        """, (dataset_id,))
        row = cur.fetchone()
    conn.close()

    if not row:
        return None

    # Extraer tema principal de theme_label si está como JSON
    theme_label = row[10]
    tema_principal = None
    if theme_label:
        try:
            if isinstance(theme_label, str):
                theme_label = json.loads(theme_label)
            tema_principal = theme_label[0] if theme_label else None
        except Exception:
            tema_principal = None

    return {
        "dataset_id": row[0],
        "title": row[1] or "",
        "description": row[2] or "",
        "tldr": row[3] or "",
        "variables_key": row[4] or [],
        "temporal_coverage": row[5] or "desconocido",
        "geographic_level": row[6] or "desconocido",
        "geographic_entity": row[7] or "desconocido",
        "frecuencia": row[8] or "desconocido",
        "formatos": row[9] or row[12] or [],
        "tema_principal": tema_principal or "desconocido",
        "territory": row[11] or ""
    }


def answer_question(
    dataset_id: str,
    question: str,
    modelo: str = "deepseek-v4.1-flash:cloud",
    timeout: int = 60,
    retries: int = 1
) -> dict:
    """
    Genera una respuesta a una pregunta sobre un dataset usando solo metadatos.

    Returns:
        dict con answer, dataset_id, question, model, latency_ms, source
    """
    context = get_dataset_context(dataset_id)
    if not context:
        return {
            "dataset_id": dataset_id,
            "question": question,
            "answer": "No se encontró información del dataset.",
            "source": "not_found",
            "model": modelo,
            "latency_ms": 0
        }

    prompt = USER_PROMPT_TEMPLATE.format(
        dataset_id=context["dataset_id"][:120],
        title=context["title"][:200],
        description=(context["description"] or "Sin descripción")[:500],
        tldr=(context["tldr"] or "Sin TL;DR")[:400],
        variables=", ".join(context["variables_key"]) if context["variables_key"] else "No disponibles",
        temporal_coverage=context["temporal_coverage"],
        geographic_level=context["geographic_level"],
        geographic_entity=context["geographic_entity"],
        frecuencia=context["frecuencia"],
        formatos=", ".join(context["formatos"]) if context["formatos"] else "No especificados",
        tema_principal=context["tema_principal"],
        question=question[:300],
        estructura_fichero=(get_file_structure(dataset_id)
                            or "(No disponible: el fichero del dataset no está indexado localmente; "
                               "responde solo con los metadatos e indícalo si la pregunta depende del contenido)")
    )

    start = time.time()

    for intento in range(retries + 1):
        try:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)

            response = ollama.chat(model=modelo, messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ])

            signal.alarm(0)
            answer = response["message"]["content"].strip()
            break

        except TimeoutError:
            signal.alarm(0)
            answer = "La respuesta ha tardado demasiado. Inténtalo de nuevo con una pregunta más específica."
            if intento == retries:
                break
            time.sleep(0.5)

        except Exception as e:
            signal.alarm(0)
            answer = f"Error generando respuesta: {str(e)}"
            if intento == retries:
                break
            time.sleep(0.5)

    elapsed_ms = int((time.time() - start) * 1000)
    estructura = get_file_structure(dataset_id)

    return {
        "dataset_id": dataset_id,
        "question": question,
        "answer": answer,
        "source": "llm_metadata+file_structure" if estructura else "llm_metadata",
        "model": modelo,
        "latency_ms": elapsed_ms,
        "dataset_title": context["title"]
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Uso: python dataset_chat_engine.py <dataset_id> <pregunta>")
        sys.exit(1)

    did = sys.argv[1]
    q = sys.argv[2]
    result = answer_question(did, q)
    print(json.dumps(result, indent=2, ensure_ascii=False))
