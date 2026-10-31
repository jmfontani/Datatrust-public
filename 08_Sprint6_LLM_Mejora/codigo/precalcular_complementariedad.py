#!/usr/bin/env python3
"""
Precalcular complementariedad offline - Sprint 8 (Paquete A: #5)

Para cada dataset con perfil, busca candidatos con el MISMO criterio que la API
(find_candidates_ranked) y usa el LLM para generar el top-N de complementarios con
explicación. Guarda el resultado en dataset_profiles.combinable_with_json, que es
la columna que lee /complementary/*.

Uso:
    python precalcular_complementariedad.py \
        --source-table dataset_sample_2k \
        --model deepseek-v4.1-flash:cloud \
        --limit 3 \
        --batch-size 25 \
        --partitions 6 --partition 0

Notas:
  - Por defecto SALTA los datasets que ya tienen complementarios en BD
    (--reprocess para rehacerlos). Así se amplía la cobertura sin pisar
    resultados ya validados.
  - --partition/--partitions reparte el trabajo para lanzar varios procesos en
    paralelo, cada uno con su propio checkpoint.
"""

import json
import argparse
import os
import signal
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    import psycopg2
    import ollama
except ImportError:
    print("❌ Instalando dependencias: pip install ollama psycopg2-binary")
    sys.exit(1)

# El pool de candidatos NO se reimplementa aquí: se importa de la API para que el
# precálculo y la respuesta en caliente ordenen igual (tema+territorio > tema >
# territorio, desempate por solape de variables_key).
sys.path.insert(0, str(Path(__file__).resolve().parent / "api"))
try:
    from routes_complementary import find_candidates_ranked, _first_theme_from_label
except Exception as exc:  # pragma: no cover
    print(f"❌ No se pudo importar routes_complementary: {exc}")
    sys.exit(1)


DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "172.17.0.1"),
    "port": int(os.environ.get("POSTGRES_PORT", 5432)),
    "database": os.environ.get("POSTGRES_DB", "buscador"),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
}


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

NO es complementario si es una variante del mismo dato (otro año, otro formato,
otro desglose de la misma serie): eso es un sustituto, no un complemento.

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

Máximo {limit} datasets complementarios. Si no hay ninguno, devuelve lista vacía.
"""


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("LLM call exceeded timeout")


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def _filtro_extra(alias: str, only_missing: bool, partition, partitions):
    """Devuelve (sql_where, params) con los filtros opcionales."""
    where = []
    params = []
    if only_missing:
        where.append(f"({alias}.combinable_with_json IS NULL"
                     f" OR jsonb_array_length(COALESCE({alias}.combinable_with_json, '[]'::jsonb)) = 0)")
    if partition is not None and partitions:
        # '%%' porque psycopg2 interpreta '%' como marcador cuando hay parámetros.
        where.append(f"abs(hashtext({alias}.dataset_id)) %% %s = %s")
        params.extend([partitions, partition])
    return (" AND ".join(where), params)


def contar_pendientes(source_table: str, only_missing: bool, partition, partitions) -> int:
    filtro, params = _filtro_extra("p", only_missing, partition, partitions)
    query = f"""
        SELECT COUNT(*)
        FROM {source_table} s
        JOIN dataset_profiles p ON s.dataset_id = p.dataset_id
        WHERE 1=1 {('AND ' + filtro) if filtro else ''}
    """
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(query, params)
        total = cur.fetchone()[0]
    conn.close()
    return total


def fetch_profiles_batch(source_table: str, after_id: str, batch_size: int,
                         only_missing: bool, partition, partitions):
    """Siguiente lote por keyset (dataset_id > after_id).

    No se usa OFFSET: el filtro 'pendientes' encoge según se escriben resultados,
    así que paginar con OFFSET salta filas y el checkpoint deja de ser reanudable.
    """
    filtro, params_filtro = _filtro_extra("p", only_missing, partition, partitions)
    query = f"""
        SELECT
            p.dataset_id, d.title, d.description, p.variables_key,
            p.temporal_coverage, p.geographic_level, p.geographic_entity,
            d.theme, d.theme_label, d.territory
        FROM {source_table} s
        JOIN dataset_profiles p ON s.dataset_id = p.dataset_id
        JOIN datasets d ON p.dataset_id = d.dataset_id
        WHERE p.dataset_id > %s {('AND ' + filtro) if filtro else ''}
        ORDER BY p.dataset_id
        LIMIT %s
    """
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(query, [after_id] + params_filtro + [batch_size])
        rows = cur.fetchall()
    conn.close()

    profiles = []
    for row in rows:
        profiles.append({
            "dataset_id": row[0],
            "title": row[1] or "",
            "description": row[2] or "",
            "variables_key": row[3] or [],
            "temporal_coverage": row[4] or "desconocido",
            "geographic_level": row[5] or "desconocido",
            "geographic_entity": row[6] or "",
            "theme_dataset": row[7] or "",
            "theme_label": row[8] or "",
            "territory_dataset": row[9] or "",
            "tema_principal": row[7] or _first_theme_from_label(row[8])
        })
    return profiles


def generate_complementary_llm(profile: dict, candidates: list[dict], modelo: str,
                               limit: int = 3, timeout: int = 120) -> Optional[list[dict]]:
    """Llama al LLM para seleccionar complementarios entre los candidatos."""
    if not candidates:
        return []

    candidates_json = "\n".join([
        f"- ID: {c['dataset_id']}, Título: {(c['title'] or '')[:100]}, Variables: {c['variables_key']}, "
        f"Geo: {c['geographic_level']} {c['geographic_entity']}, Temporal: {c['temporal_coverage']}, "
        f"Afinidad detectada: {c.get('_source')}"
        for c in candidates[:12]
    ])

    prompt = PROMPT_FIND_COMPLEMENTARY.format(
        title=profile["title"][:150],
        description=profile["description"][:300] if profile["description"] else "N/A",
        variables=", ".join(profile["variables_key"]) if profile["variables_key"] else "N/A",
        geographic_level=profile["geographic_level"] or "N/A",
        temporal_coverage=profile["temporal_coverage"] or "N/A",
        candidates_json=candidates_json,
        limit=limit
    )

    texto = _chat(prompt, modelo, timeout, etiqueta=profile["dataset_id"][:35])
    if texto is None:
        return None

    try:
        result = json.loads(texto)
        return result.get("complementary", [])[:limit]
    except Exception as e:
        print(f"   ⚠️ JSON inválido en {profile['dataset_id'][:40]}: {str(e)[:80]}", flush=True)
        return None


def _limpiar_json(texto: str) -> str:
    texto = (texto or "").strip()
    if texto.startswith("```json"):
        texto = texto[7:]
    if texto.endswith("```"):
        texto = texto[:-3]
    return texto.strip()


def _chat(prompt: str, modelo: str, timeout: int = 120, etiqueta: str = "") -> Optional[str]:
    """Una llamada al LLM con reintentos ante 429 y razonamiento desactivado.

    think=False recorta la salida de ~5.700 a ~700 tokens (medido) sin degradar
    el JSON. Si la versión del cliente no acepta el kwarg, se reintenta sin él.
    """
    mensajes = [
        {"role": "system", "content": "Eres un experto en análisis de datos abiertos. Responde SÓLO con JSON válido."},
        {"role": "user", "content": prompt},
    ]
    for intento in range(5):
        try:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)
            try:
                response = ollama.chat(model=modelo, think=False, messages=mensajes)
            except TypeError:
                response = ollama.chat(model=modelo, messages=mensajes)
            signal.alarm(0)
            return _limpiar_json(response["message"]["content"])
        except Exception as e:
            signal.alarm(0)
            msg = str(e)
            # El proveedor limita las peticiones concurrentes: se reintenta con
            # espera creciente en vez de contar el dataset como fallido.
            if "429" in msg or "too many concurrent" in msg.lower():
                espera = 10 * (intento + 1)
                print(f"   ⏳ 429 en {etiqueta} — reintento en {espera}s", flush=True)
                time.sleep(espera)
                continue
            print(f"   ⚠️ Error LLM en {etiqueta}: {msg[:80]}", flush=True)
            return None
    print(f"   ⚠️ Agotados los reintentos en {etiqueta}", flush=True)
    return None


def save_complementary_to_db(dataset_id: str, complementary: list[dict], score: float,
                             overwrite: bool = False) -> bool:
    """Guarda el precálculo. Por defecto NO pisa un resultado ya existente.

    La condición protege el trabajo hecho: si dos pasadas se solapan o se relanza
    el script, lo que ya tenía complementarios se conserva.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            guarda = "" if overwrite else (
                " AND (combinable_with_json IS NULL"
                " OR jsonb_array_length(COALESCE(combinable_with_json, '[]'::jsonb)) = 0)")
            cur.execute("""
                UPDATE dataset_profiles
                SET combinable_with_json = %s::jsonb,
                    combinable_score = %s,
                    last_updated = NOW()
                WHERE dataset_id = %s
            """ + guarda, (json.dumps(complementary), score, dataset_id))
            actualizadas = cur.rowcount
        conn.commit()
        conn.close()
        return actualizadas > 0
    except Exception as e:
        print(f"  ❌ Error guardando en BD: {e}")
        conn.rollback()
        conn.close()
        return False


def load_checkpoint(checkpoint_path: Path) -> str:
    """Devuelve el último dataset_id procesado (keyset), o cadena vacía."""
    if checkpoint_path.exists():
        with open(checkpoint_path, "r") as f:
            data = json.load(f)
        return data.get("last_id") or ""
    return ""


def save_checkpoint(checkpoint_path: Path, last_id: str, processed: int, failed: int,
                    timeout_count: int, empty: int, total: int):
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path, "w") as f:
        json.dump({
            "last_id": last_id,
            "total_inicial": total,
            "processed": processed,
            "empty": empty,
            "failed": failed,
            "timeout_count": timeout_count,
            "last_updated": datetime.now().isoformat()
        }, f)


PROMPT_BATCH = """Eres un experto en análisis de datos abiertos.

Para CADA uno de los datasets de la lista, identifica hasta {limit} datasets COMPLEMENTARIOS para
análisis conjunto. Un dataset es complementario si:
1. Comparte clave de unión (territorio, periodo temporal).
2. Aporta variables distintas y relacionadas que permitan indicadores derivados.
NO es complementario si es una variante del mismo dato (otro año, otro formato, otro desglose de
la misma serie): eso es un sustituto.

{bloques}

Responde SÓLO con JSON válido, con una entrada por cada dataset del mismo orden que la lista:
{{"results": [{{"dataset_id": "<ID del dataset origen>", "complementary": [{{"dataset_id": "<ID candidato>",
"title": "título", "reason": "1-2 frases", "join_key": "clave de unión", "potential_analysis": "análisis"}}]}}]}}

Si un dataset no tiene complementarios, devuelve "complementary": [].
"""


def _bloque_dataset(n: int, perfil: dict, candidatos: list[dict]) -> str:
    candidatos_txt = "\n".join([
        f"  - ID: {c['dataset_id']}, Título: {(c['title'] or '')[:100]}, Variables: {c['variables_key']}, "
        f"Geo: {c['geographic_level']} {c['geographic_entity']}, Temporal: {c['temporal_coverage']}, "
        f"Afinidad: {c.get('_source')}"
        for c in candidatos[:12]
    ])
    return (
        f"### DATASET {n}\n"
        f"ID: {perfil['dataset_id']}\n"
        f"Título: {perfil['title'][:150]}\n"
        f"Descripción: {(perfil['description'] or 'N/A')[:250]}\n"
        f"Variables: {', '.join(perfil['variables_key'] or []) or 'N/A'}\n"
        f"Nivel: {perfil['geographic_level']} | Temporal: {perfil['temporal_coverage']}\n"
        f"Candidatos:\n{candidatos_txt}"
    )


def _score(complementary: list[dict]) -> float:
    """Score de completitud del registro (no mide la calidad de la relación)."""
    scores = []
    for c in complementary:
        s = 0
        if c.get("reason") and len(str(c.get("reason", "")).split()) >= 5:
            s += 1
        if c.get("join_key"):
            s += 1
        if c.get("potential_analysis"):
            s += 1
        scores.append(s / 3.0)
    return sum(scores) / len(scores) if scores else 0.0


def generate_batch_llm(grupo: list[dict], pools: dict, modelo: str, limit: int = 3,
                       timeout: int = 240) -> dict:
    """Una sola llamada para varios datasets.

    Devuelve {dataset_id: [items]} sólo para los datasets con entrada válida; los
    ausentes se reintentan en individual. Todo par propuesto se valida contra el
    pool real de candidatos de ese dataset, para que el modelo no pueda inventarse
    IDs ni cruzar candidatos entre datasets del lote.
    """
    bloques = "\n\n".join(_bloque_dataset(n, p, pools[p["dataset_id"]])
                          for n, p in enumerate(grupo, 1))
    prompt = PROMPT_BATCH.format(bloques=bloques, limit=limit)

    texto = _chat(prompt, modelo, timeout, etiqueta=f"lote de {len(grupo)}")
    if texto is None:
        return {}

    try:
        resultado = json.loads(texto)
    except Exception as e:
        print(f"   ⚠️ Lote con JSON inválido: {str(e)[:70]}", flush=True)
        return {}

    ids_origen = {p["dataset_id"] for p in grupo}
    salida = {}
    for entrada in resultado.get("results", []) or []:
        origen = entrada.get("dataset_id")
        if origen not in ids_origen:
            continue
        pool = {c["dataset_id"]: c for c in pools[origen]}
        items = []
        for c in entrada.get("complementary") or []:
            cid = c.get("dataset_id")
            if cid not in pool:
                continue
            reason = str(c.get("reason") or "").strip()
            if len(reason.split()) < 5:
                continue
            items.append({
                "dataset_id": cid,
                "title": c.get("title") or pool[cid].get("title") or cid,
                "reason": reason,
                "join_key": str(c.get("join_key") or "").strip(),
                "potential_analysis": str(c.get("potential_analysis") or "").strip(),
            })
        salida[origen] = items[:limit]
    return salida


def main():
    parser = argparse.ArgumentParser(description="Precalcular datasets complementarios")
    parser.add_argument("--source-table", type=str, default="dataset_sample_2k")
    parser.add_argument("--model", "-m", type=str, default="deepseek-v4.1-flash:cloud")
    parser.add_argument("--limit", "-l", type=int, default=3)
    parser.add_argument("--batch-size", "-b", type=int, default=25)
    parser.add_argument("--checkpoint-dir", "-c", type=str, default="checkpoints_complementary")
    parser.add_argument("--timeout", "-t", type=int, default=120)
    parser.add_argument("--reprocess", action="store_true",
                        help="Reprocesar también los datasets que ya tienen complementarios")
    parser.add_argument("--partition", type=int, default=None)
    parser.add_argument("--partitions", type=int, default=None)
    parser.add_argument("--batch-datasets", type=int, default=4,
                        help="Datasets por llamada al LLM (1 = una llamada por dataset)")
    args = parser.parse_args()

    only_missing = not args.reprocess
    etiqueta = f"p{args.partition}de{args.partitions}" if args.partition is not None else "todo"
    checkpoint_path = Path(args.checkpoint_dir) / f"checkpoint-{etiqueta}.json"

    total = contar_pendientes(args.source_table, only_missing, args.partition, args.partitions)

    print(f"📊 [{etiqueta}] pendientes en `{args.source_table}`: {total}", flush=True)
    print(f"🤖 Modelo: {args.model}")
    print(f"📦 Batch: {args.batch_size} | 🔢 Complementarios: {args.limit} | ⏱️ Timeout: {args.timeout}s")
    if only_missing:
        print("⏭️  Se saltan los datasets que ya tienen complementarios (--reprocess para rehacerlos)")
    print(flush=True)

    ultimo_id = load_checkpoint(checkpoint_path)
    if ultimo_id:
        print(f"↩️  Reanudando después de {ultimo_id[:70]}", flush=True)
    processed_total = failed_total = timeout_total = empty_total = preserved_total = 0
    start_time = datetime.now()

    while True:
        profiles = fetch_profiles_batch(args.source_table, ultimo_id, args.batch_size,
                                        only_missing, args.partition, args.partitions)
        if not profiles:
            break

        tam = max(1, args.batch_datasets)
        for inicio in range(0, len(profiles), tam):
            grupo = profiles[inicio:inicio + tam]
            pools = {p["dataset_id"]: find_candidates_ranked(p, p["dataset_id"], limit=12)
                     for p in grupo}

            resultados = {}
            if len(grupo) > 1:
                resultados = generate_batch_llm(grupo, pools, args.model,
                                                limit=args.limit, timeout=args.timeout)

            for profile in grupo:
                pid = profile["dataset_id"]
                complementary = resultados.get(pid)
                if complementary is None:
                    # Sin entrada válida en el lote: se reintenta en individual.
                    complementary = generate_complementary_llm(profile, pools[pid], args.model,
                                                               limit=args.limit, timeout=args.timeout)

                if complementary is None:
                    failed_total += 1
                    timeout_total += 1
                    continue

                if not complementary:
                    # [] = "evaluado, ninguno": la API cae entonces al ranking por afinidad.
                    guardado = save_complementary_to_db(pid, [], 0.0)
                else:
                    guardado = save_complementary_to_db(pid, complementary, _score(complementary))

                if guardado:
                    processed_total += 1
                    if not complementary:
                        empty_total += 1
                else:
                    # Ya tenía complementarios (no se pisa) o error de escritura.
                    preserved_total += 1

        ultimo_id = profiles[-1]["dataset_id"]
        save_checkpoint(checkpoint_path, ultimo_id, processed_total, failed_total,
                        timeout_total, empty_total, total)

        elapsed = (datetime.now() - start_time).total_seconds()
        velocidad = processed_total / elapsed if elapsed > 0 else 0
        eta = (total - processed_total) / velocidad if velocidad > 0 else 0
        print(f"   [{etiqueta}] {processed_total}/{total} | vacíos={empty_total} "
              f"preservados={preserved_total} fallidos={failed_total} | {velocidad:.2f}/s | "
              f"ETA={eta/60:.1f}min", flush=True)

    print(f"\n✅ [{etiqueta}] procesados={processed_total} vacíos={empty_total} "
          f"preservados={preserved_total} fallidos={failed_total} en "
          f"{(datetime.now()-start_time).total_seconds()/60:.1f}min")

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE combinable_with_json IS NOT NULL) AS con_json,
                COUNT(*) FILTER (WHERE jsonb_array_length(
                    COALESCE(combinable_with_json,'[]'::jsonb)) > 0) AS con_complementarios,
                COUNT(*) FILTER (WHERE combinable_with_json IS NOT NULL
                    AND jsonb_array_length(COALESCE(combinable_with_json,'[]'::jsonb)) = 0) AS vacios,
                AVG(combinable_score) AS avg_score
            FROM dataset_profiles
        """)
        row = cur.fetchone()
    conn.close()
    print(f"📊 Estado global: con_json={row[0]} con_complementarios={row[1]} "
          f"vacios={row[2]} score_medio={row[3]}")


if __name__ == "__main__":
    main()
