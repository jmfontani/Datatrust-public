#!/usr/bin/env python3
"""
Routes API para Datasets Complementarios - Sprint 8 (#5)

Endpoints:
    POST /complementary/find - Encuentra datasets complementarios para un dataset dado
    GET /complementary/{dataset_id} - Obtiene complementariedad precalculada o dinámica
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import psycopg2
import ollama
import json
import os
import signal
import time

router_complementary = APIRouter(prefix="/complementary", tags=["complementary"])


DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", 5432)),
    "database": os.environ.get("POSTGRES_DB", "buscador"),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
}

# Handler de SIGALRM a nivel de módulo. Antes estaba definido DENTRO de
# generate_profile_for_dataset(), así que en find_complementary_logic() el
# nombre no existía y la rama LLM moría siempre con NameError -> fallback
# genérico. Cualquier ruta que use signal.alarm necesita este símbolo global.
def _timeout_handler(signum, frame):
    raise TimeoutError("LLM call exceeded timeout")


def _slug_from_territory(value: Optional[str]) -> str:
    """Extrae el nombre legible de un territorio.

    Acepta 'Alcobendas', una URI de datos.gob.es (.../Provincia/Madrid) o una
    lista JSON. Devuelve el último segmento con '/' como separador.
    """
    if not value:
        return ""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    text = str(value).strip()
    if not text:
        return ""
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list) and parsed:
                return _slug_from_territory(parsed[0])
        except Exception:
            pass
    if "/" in text:
        text = text.rstrip("/").rsplit("/", 1)[-1]
    return text.strip()


def _norm_geo(value, primary: bool = False) -> str:
    """Normaliza un nombre de territorio para comparar.

    Minúsculas, sin paréntesis y con espacios colapsados. Con primary=True toma
    el primer segmento de un campo multivaluado ('Alcobendas, Madrid' -> 'alcobendas'),
    salvo que lleve paréntesis ('Illes Balears (Calvià, Eivissa y Palma)'), donde la
    coma no separa territorios sino una aclaración.
    """
    text = str(value or "").strip().lower()
    if primary and "," in text and "(" not in text:
        text = text.split(",", 1)[0]
    for ch in "()":
        text = text.replace(ch, "")
    return " ".join(text.split())


def _first_theme_from_label(label) -> Optional[str]:
    """Devuelve el tema normalizado a partir de theme_label.

    theme_label llega en dos formatos incompatibles según la fuente:
        '["empleo"]'                                  (array JSON)
        'http://datos.gob.es/kos/.../sector/empleo'   (URI KOS)
    Antes se devolvía la URI completa, de modo que la búsqueda de candidatos
    temáticos (LIKE '%"<tema>"%') no encontraba nada para el 95% del catálogo.
    """
    if not label:
        return None
    if isinstance(label, (list, tuple)):
        return _slug_from_territory(label[0]) or None if label else None
    text = str(label).strip()
    if not text:
        return None
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list) and parsed:
                return _slug_from_territory(parsed[0]) or None
        except Exception:
            pass
    return _slug_from_territory(text) or None


class ComplementaryRequest(BaseModel):
    dataset_id: str
    limit: int = 5
    use_llm: bool = False


class ComplementaryResponse(BaseModel):
    dataset_id: str
    title: str
    complementary_datasets: list[dict]
    explanations: list[str]
    source: Optional[str] = None


class ComplementaryItem(BaseModel):
    dataset_id: str
    title: str
    reason: str
    join_key: str = ""
    potential_analysis: str = ""


PROMPT_FIND_COMPLEMENTARY = """
Eres un experto en análisis de datos abiertos.

Dado este dataset:
- Título: {title}
- Descripción: {description}
- Variables: {variables}
- Nivel geográfico: {geographic_level}
- Cobertura temporal: {temporal_coverage}

Y estos candidatos potenciales:
{candidates_json}

Identifica cuáles datasets serían COMPLEMENTARIOS para análisis conjunto.

Un dataset es complementario si:
1. Comparte clave de unión (territorio, periodo temporal)
2. Aporta variables diferentes pero relacionadas analíticamente
3. Permite crear indicadores derivados (ej: población + PIB → renta per cápita)

Responde SÓLO con JSON válido:
{{
    "complementary": [
        {{
            "dataset_id": "id del dataset",
            "title": "título",
            "reason": "explicación de por qué es complementario (1-2 frases)",
            "join_key": "clave de unión propuesta (ej: municipio, año)",
            "potential_analysis": "análisis que permitiría (ej: 'calcular renta per cápita')"
        }}
    ]
}}

Máximo 5 datasets complementarios. Si no hay ninguno, devuelve lista vacía.
"""


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


PROMPT_COMBINED = """
Eres un experto en documentación y metadatos de datos abiertos.

Para este dataset, genera UN RESUMEN TL;DR y EXTRAe su perfil estructurado.

Título: {title}
Descripción: {description}
Tema: {tema}
Territorio: {territorio}
Formatos disponibles: {formatos}

Responde SÓLO con JSON válido con esta estructura EXACTA:

{{
    "tldr": "Resumen de 2-3 frases (20-50 palabras). Debe decir qué datos contiene, cobertura territorial, periodo temporal si se infiere, y fuente/institución.",
    "variables_key": ["lista de 5-10 palabras clave conceptuales"],
    "temporal_coverage": "periodo o frecuencia (ej: '2005-2023', 'mensual', 'anual', 'desconocido')",
    "geographic_level": "nivel geográfico (nacional | autonómico | provincial | municipal | insular | desconocido)",
    "geographic_entity": "entidad específica si se menciona (ej: 'Canarias', 'España', 'Madrid')",
    "frecuencia": "frecuencia de actualización (mensual | trimestral | anual | puntual | desconocido)"
}}

Reglas:
- tldr: conciso, útil, sin comillas internas
- variables_key: conceptos medibles (no stop words)
- Si no se puede determinar algún campo, usar "desconocido"
"""


def generate_profile_for_dataset(dataset_id: str, modelo: str = "deepseek-v4.1-flash:cloud", timeout: int = 45) -> Optional[dict]:
    """Genera un perfil TL;DR bajo demanda para un dataset sin perfil previo."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT dataset_id, title, description, theme, territory, format
            FROM datasets
            WHERE dataset_id = %s
        """, (dataset_id,))
        row = cur.fetchone()
    conn.close()

    if not row:
        return None

    dataset = {
        "id": row[0],
        "title": row[1] or "",
        "description": row[2] or "",
        "tema": row[3] or "",
        "territorio": row[4] or "",
        "formato": row[5] or ""
    }

    prompt = PROMPT_COMBINED.format(
        title=dataset["title"][:200],
        description=dataset["description"][:500] if dataset["description"] else "Sin descripción",
        tema=dataset["tema"],
        territorio=dataset["territorio"],
        formatos=dataset["formato"]
    )

    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)

        response = ollama.chat(model=modelo, messages=[
            {"role": "system", "content": "Eres un experto en documentación de datos abiertos. Responde SÓLO con JSON válido."},
            {"role": "user", "content": prompt}
        ])

        signal.alarm(0)

        texto = response["message"]["content"].strip()
        if texto.startswith("```json"):
            texto = texto[7:]
        if texto.endswith("```"):
            texto = texto[:-3]
        texto = texto.strip()

        result = json.loads(texto)

        required = ["tldr", "variables_key", "temporal_coverage", "geographic_level"]
        if not all(field in result for field in required):
            return None

        tldr = result["tldr"].strip().strip('"\'')
        if len(tldr) < 10:
            return None

        result["tldr"] = tldr
        return result

    except TimeoutError:
        signal.alarm(0)
        return None
    except Exception:
        signal.alarm(0)
        return None


def save_profile_to_db(dataset_id: str, data: dict):
    """Guarda o actualiza un perfil generado bajo demanda."""
    conn = get_db_connection()
    upsert_query = """
        INSERT INTO dataset_profiles (
            dataset_id, tldr, tldr_generated_at,
            variables_key, temporal_coverage, geographic_level, geographic_entity, frecuencia,
            last_updated, profile_version
        ) VALUES (
            %s, %s, NOW(), %s, %s, %s, %s, %s, NOW(), 1
        )
        ON CONFLICT (dataset_id) DO UPDATE SET
            tldr = EXCLUDED.tldr,
            tldr_generated_at = EXCLUDED.tldr_generated_at,
            variables_key = EXCLUDED.variables_key,
            temporal_coverage = EXCLUDED.temporal_coverage,
            geographic_level = EXCLUDED.geographic_level,
            geographic_entity = EXCLUDED.geographic_entity,
            frecuencia = EXCLUDED.frecuencia,
            last_updated = NOW(),
            profile_version = dataset_profiles.profile_version + 1
    """
    try:
        with conn.cursor() as cur:
            cur.execute(upsert_query, (
                dataset_id,
                data.get("tldr"),
                data.get("variables_key"),
                data.get("temporal_coverage"),
                data.get("geographic_level"),
                data.get("geographic_entity"),
                data.get("frecuencia")
            ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error guardando perfil bajo demanda: {e}")
        conn.rollback()
        conn.close()
        return False


def get_or_create_profile(dataset_id: str, generate_if_missing: bool = True) -> Optional[dict]:
    """Obtiene perfil existente o lo genera bajo demanda si no existe."""
    profile = get_dataset_profile(dataset_id)
    if profile:
        return profile

    if not generate_if_missing:
        return None

    generated = generate_profile_for_dataset(dataset_id)
    if not generated:
        return None

    save_profile_to_db(dataset_id, generated)
    return get_dataset_profile(dataset_id)


def get_dataset_profile(dataset_id: str) -> Optional[dict]:
    """Obtiene perfil de un dataset desde la BD."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                dp.dataset_id, dp.tldr, dp.variables_key, dp.temporal_coverage,
                dp.geographic_level, dp.geographic_entity, dp.frecuencia, dp.formatos,
                dp.tema_principal, dp.combinable_with, dp.combinable_score,
                d.title, d.description, d.theme, d.theme_label, d.territory
            FROM dataset_profiles dp
            JOIN datasets d ON dp.dataset_id = d.dataset_id
            WHERE dp.dataset_id = %s
        """, (dataset_id,))
        row = cur.fetchone()
    conn.close()

    if not row:
        return None

    # Tema principal: dp.tema_principal (vacío en todo el catálogo actual) ->
    # d.theme (slug limpio: 'demografia') -> theme_label normalizado.
    # Antes se usaba theme_label tal cual, que en el 95% del catálogo es una URI
    # KOS completa; la búsqueda temática compara contra '"<tema>"' y no casaba.
    theme_label = row[14]
    tema_principal = row[8] or row[13]
    if not tema_principal:
        tema_principal = _first_theme_from_label(theme_label)

    return {
        "dataset_id": row[0],
        "tldr": row[1],
        "variables_key": row[2],
        "temporal_coverage": row[3],
        "geographic_level": row[4],
        "geographic_entity": row[5],
        "frecuencia": row[6],
        "formatos": row[7],
        "tema_principal": tema_principal,
        "combinable_with": row[9],
        "combinable_score": row[10],
        "title": row[11],
        "description": row[12],
        "theme_dataset": row[13],
        "theme_label": row[14],
        "territory_dataset": row[15]
    }


def find_candidates_ranked(profile: dict, dataset_id: str, limit: int = 12) -> list[dict]:
    """Candidatos ordenados por afinidad real, no por fecha de publicación.

    Prioridad: mismo tema + mismo territorio > mismo tema > mismo territorio.
    Sustituye a find_candidates_by_theme()/find_candidates_by_geography(), que
    (a) comparaban el tema contra '"<tema>"' y fallaban con theme_label en URI,
    (b) ordenaban por issued_date, casi siempre NULL, dejando el orden al azar
    físico de la tabla. Aquí el orden es determinista (desempate por dataset_id).
    """
    tema = (profile.get("tema_principal") or "").strip().lower()
    geo = (profile.get("geographic_entity") or "").strip()
    if not geo:
        geo = _slug_from_territory(profile.get("territory_dataset") or "")
        if geo.lower() in ("", "espana", "españa"):
            geo = ""

    conds = []
    params = {"did": dataset_id, "lim": limit, "vars": list(profile.get("variables_key") or [])}
    tema_match = "FALSE"
    geo_match = "FALSE"

    if tema:
        # d.theme es un slug limpio ('demografia'); theme_label puede ser URI KOS.
        tema_match = "(LOWER(d.theme) = %(tema)s OR LOWER(d.theme_label) LIKE %(tema_like)s)"
        conds.append(tema_match)
        params["tema"] = tema
        params["tema_like"] = f"%{tema}%"

    if geo:
        # geographic_entity es texto libre generado por el LLM: 'Alcobendas',
        # 'Alcobendas, Madrid', 'Madrid, Barcelona, Bilbao, Valencia'. La
        # igualdad exacta perdía los vecinos del mismo municipio cuando el campo
        # traía más de un nombre, así que se acepta también prefijo y cola
        # separada por coma (sin LIKE '%...%' para no cruzar 'Lugo' con 'Lugones').
        geo = _norm_geo(geo, primary=True)
        # Se normaliza también el lado almacenado: 'Alcobendas (Madrid)' -> 'alcobendas'.
        geo_expr = ("BTRIM(regexp_replace(LOWER(COALESCE(dp.geographic_entity,'')),"
                    " ' *[(].*[)] *$', ''))")
        geo_match = (
            f"({geo_expr} = %(geo)s"
            f" OR {geo_expr} LIKE %(geo_prefix)s"
            f" OR {geo_expr} LIKE %(geo_suffix)s)"
        )
        conds.append(geo_match)
        params["geo"] = geo
        params["geo_prefix"] = f"{geo},%"
        params["geo_suffix"] = f"%, {geo}"

    if not conds:
        return []

    query = f"""
        SELECT d.dataset_id, d.title, d.description, dp.variables_key,
               dp.temporal_coverage, dp.geographic_level, dp.geographic_entity,
               (dp.tldr IS NOT NULL AND dp.variables_key IS NOT NULL) AS has_profile,
               CASE
                   WHEN {tema_match} AND {geo_match} THEN 0
                   WHEN {tema_match} THEN 1
                   ELSE 2
               END AS prioridad,
               (SELECT count(*) FROM unnest(COALESCE(dp.variables_key, '{{}}'::text[])) v
                 WHERE v = ANY(%(vars)s)) AS solape
        FROM datasets d
        LEFT JOIN dataset_profiles dp ON d.dataset_id = dp.dataset_id
        WHERE d.dataset_id <> %(did)s
          AND ({' OR '.join(conds)})
        ORDER BY prioridad ASC, solape DESC, has_profile DESC, d.dataset_id ASC
        LIMIT %(lim)s
    """

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    conn.close()

    fuentes = {0: "theme_geo", 1: "theme", 2: "geo"}
    return [
        {
            "dataset_id": row[0],
            "title": row[1] or "",
            "description": row[2] or "",
            "variables_key": row[3],
            "temporal_coverage": row[4],
            "geographic_level": row[5],
            "geographic_entity": row[6],
            "_source": fuentes.get(int(row[8]), "geo")
        }
        for row in rows
    ]


def find_complementary_logic(dataset_id: str, use_llm: bool = False) -> dict:
    """
    Lógica interna para encontrar datasets complementarios.

    Returns:
        dict con dataset_id, title, tldr, complementary, source
    """
    def _items_from_ids(ids):
        """Reconstruye items con título desde una lista de IDs (columna TEXT[])."""
        ids = [i for i in (ids or []) if i]
        if not ids:
            return []
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT dataset_id, title FROM datasets WHERE dataset_id = ANY(%s)", (ids,))
            titles = dict(cur.fetchall())
        conn.close()
        return [{
            "dataset_id": i,
            "title": titles.get(i) or i,
            "reason": "Complementario identificado en el precálculo por afinidad temática y territorial.",
            "join_key": "",
            "potential_analysis": ""
        } for i in ids]

    # Precálculo offline. El LLM guarda en combinable_with_json (jsonb); la
    # columna combinable_with (TEXT[]) no se ha rellenado nunca, así que leer
    # solo esa dejaba el atajo inactivo y todo caía en la rama geográfica.
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT combinable_with, combinable_score, combinable_with_json
            FROM dataset_profiles
            WHERE dataset_id = %s
        """, (dataset_id,))
        row_precalc = cur.fetchone()
    conn.close()

    profile = get_or_create_profile(dataset_id, generate_if_missing=True)

    if not profile:
        raise HTTPException(status_code=404, detail="Dataset no encontrado o no se pudo generar el perfil")

    precalc_json = None
    precalc_ids = None
    precalc_score = None
    if row_precalc:
        precalc_ids = row_precalc[0]
        precalc_score = float(row_precalc[1]) if row_precalc[1] is not None else None
        precalc_json = row_precalc[2]
        if isinstance(precalc_json, str):
            try:
                precalc_json = json.loads(precalc_json)
            except Exception:
                precalc_json = None

    # Un [] guardado significa "el LLM no vio ninguna relación juzgada entre estos
    # candidatos". No se devuelve vacío: se cae al ranking por afinidad (razón
    # temática explícita), para no dejar sin vecinos a quien antes los tenía.
    if not use_llm and (precalc_json is not None or precalc_ids):
        if precalc_json is not None:
            complementary_data = precalc_json if isinstance(precalc_json, list) else []
        else:
            complementary_data = _items_from_ids(precalc_ids)
        if complementary_data:
            return {
                "dataset_id": dataset_id,
                "title": profile["title"],
                "tldr": profile["tldr"],
                "complementary": complementary_data,
                "score": precalc_score,
                "source": "precalculated"
            }

    # Candidatos ordenados por afinidad: tema+territorio > tema > territorio
    unique_candidates = find_candidates_ranked(profile, dataset_id, limit=12)

    if not unique_candidates:
        return {
            "dataset_id": dataset_id,
            "title": profile["title"],
            "tldr": profile["tldr"],
            "complementary": [],
            "source": "no_candidates"
        }

    tema = profile.get("tema_principal") or "temático"
    geo = (profile.get("geographic_entity")
           or _slug_from_territory(profile.get("territory_dataset") or "")
           or "el ámbito del dataset")

    def _basic_item(c: dict) -> dict:
        """Item con la razón ajustada al motivo real de la afinidad."""
        src = c.get("_source")
        if src == "theme_geo":
            reason = f"Mismo tema ({tema}) y mismo ámbito territorial ({geo}); comparten clave de unión."
            potential = f"Cruzar variables de '{tema}' a escala de {geo}."
            join_key = f"{geo} + periodo temporal"
        elif src == "theme":
            reason = f"Mismo tema ({tema}) en otro ámbito; permite comparar la misma dimensión."
            potential = f"Comparar indicadores de '{tema}' entre territorios."
            join_key = "periodo temporal + territorio"
        else:
            reason = f"Mismo ámbito territorial ({geo}) pero tema distinto: solo comparten la clave geográfica."
            potential = "Análisis conjunto de variables del mismo territorio."
            join_key = f"{geo} + periodo temporal"
        return {
            "dataset_id": c["dataset_id"],
            "title": c.get("title") or c["dataset_id"],
            "reason": reason,
            "join_key": join_key,
            "potential_analysis": potential
        }

    # Si no se pidió LLM, devolvemos candidatos como complementarios básicos
    if not use_llm:
        return {
            "dataset_id": dataset_id,
            "title": profile["title"],
            "tldr": profile["tldr"],
            "complementary": [_basic_item(c) for c in unique_candidates[:5]],
            "source": "basic_candidates"
        }

    # Usar LLM para encontrar complementariedad
    candidates_json = "\n".join([
        f"- ID: {c['dataset_id']}, Título: {(c['title'] or '')[:100]}, Variables: {c['variables_key']}, "
        f"Geo: {c['geographic_level']} {c['geographic_entity']}, Temporal: {c['temporal_coverage']}, "
        f"Afinidad detectada: {c.get('_source')}"
        for c in unique_candidates[:12]
    ])

    prompt = PROMPT_FIND_COMPLEMENTARY.format(
        title=profile["title"][:150],
        description=profile["description"][:300] if profile["description"] else "N/A",
        variables=", ".join(profile["variables_key"]) if profile["variables_key"] else "N/A",
        geographic_level=profile["geographic_level"] or "N/A",
        temporal_coverage=profile["temporal_coverage"] or "N/A",
        candidates_json=candidates_json
    )

    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(20)

        response = ollama.chat(model='deepseek-v4.1-flash:cloud', messages=[
            {"role": "system", "content": "Eres un experto en análisis de datos abiertos. Responde SÓLO con JSON válido."},
            {"role": "user", "content": prompt}
        ])

        signal.alarm(0)

        texto = response["message"]["content"].strip()
        if texto.startswith("```json"):
            texto = texto[7:]
        if texto.endswith("```"):
            texto = texto[:-3]
        texto = texto.strip()

        result = json.loads(texto)
        llm_complementary = result.get("complementary", [])

        # Si el LLM no ve relación, se devuelve vacío: el prompt permite
        # explícitamente "ninguno" y forzar candidatos era lo que producía
        # relaciones postizas.
        return {
            "dataset_id": dataset_id,
            "title": profile["title"],
            "tldr": profile["tldr"],
            "complementary": llm_complementary,
            "source": "llm" if llm_complementary else "llm_empty"
        }

    except Exception as e:
        signal.alarm(0)
        # Solo si el LLM falla (timeout, JSON inválido, servicio caído) se cae
        # al ranking determinista, dejando claro el origen en cada razón.
        print(f"[complementary] LLM no disponible ({type(e).__name__}: {e}); usando candidatos por afinidad")
        return {
            "dataset_id": dataset_id,
            "title": profile["title"],
            "tldr": profile["tldr"],
            "complementary": [_basic_item(c) for c in unique_candidates[:3]],
            "source": "llm_error_fallback"
        }


@router_complementary.get("/tldr")
async def get_dataset_tldr(dataset_id: str = Query(..., description="ID del dataset")):
    """
    Sprint 8 (#14): Obtiene solo el TL;DR de un dataset.
    """
    profile = get_or_create_profile(dataset_id, generate_if_missing=True)
    if not profile:
        raise HTTPException(status_code=404, detail="Dataset no encontrado o no se pudo generar el perfil")

    return {
        "dataset_id": dataset_id,
        "title": profile["title"],
        "tldr": profile["tldr"],
        "has_tldr": bool(profile.get("tldr"))
    }


@router_complementary.get("/info")
async def get_complementary_datasets(dataset_id: str = Query(..., description="ID del dataset"), use_llm: bool = False):
    """
    Obtiene datasets complementarios para un dataset dado.

    Si use_llm=True, usa LLM para encontrar complementariedad dinámica.
    Si use_llm=False, devuelve resultados precalculados en BD (o vacío si no existe).
    """
    return find_complementary_logic(dataset_id, use_llm=use_llm)


@router_complementary.post("/find", response_model=ComplementaryResponse)
async def find_complementary(request: ComplementaryRequest):
    """
    Encuentra datasets complementarios para un dataset específico.

    Por defecto use_llm=False: devuelve candidatos por tema/geografía de forma rápida.
    Con use_llm=True: evalúa con LLM y genera explicaciones más detalladas.
    """
    result = find_complementary_logic(request.dataset_id, use_llm=request.use_llm)

    complementary = result.get("complementary", [])[:request.limit]

    return ComplementaryResponse(
        dataset_id=request.dataset_id,
        title=result.get("title", request.dataset_id),
        complementary_datasets=[{
            "dataset_id": c.get("dataset_id", ""),
            "title": c.get("title", "Sin título"),
            "reason": c.get("reason", ""),
            "join_key": c.get("join_key", ""),
            "potential_analysis": c.get("potential_analysis", "")
        } for c in complementary],
        explanations=[c.get("reason", "") for c in complementary],
        source=result.get("source")
    )
