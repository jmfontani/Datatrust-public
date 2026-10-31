#!/usr/bin/env python3
"""
Batch Generate Profiles SECUENCIAL - Sprint 8 (Paquete A: #5 + #14)

Versión secuencial simple para evitar problemas de multiprocessing con ollama.
Procesa datasets uno a uno, con reanudación por checkpoint.

Uso:
    python batch_generate_profiles_sequential.py \
        --source-table dataset_sample_2k_remaining \
        --model qwen3-coder-next:cloud \
        --limit 1000
"""

import json
import argparse
import sys
import time
import signal
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

try:
    import ollama
    import psycopg2
except ImportError:
    print("❌ Instalando dependencias: pip install ollama psycopg2-binary")
    sys.exit(1)


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("LLM call exceeded timeout")


DB_CONFIG = {
    "host": "172.17.0.1",
    "port": 5432,
    "database": "buscador",
    "user": "postgres",
    "password": "postgres"
}


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


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def fetch_datasets_batch(source_table: str, offset: int, batch_size: int):
    conn = get_db_connection()
    query = f"""
        SELECT dataset_id, title, description, theme, territory, format
        FROM {source_table}
        ORDER BY dataset_id
        LIMIT %s OFFSET %s
    """
    with conn.cursor() as cur:
        cur.execute(query, (batch_size, offset))
        rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "title": row[1],
            "description": row[2] or "",
            "tema": row[3] or "",
            "territorio": row[4] or "",
            "formato": row[5] or ""
        }
        for row in rows
    ]


def generate_profile_combined(dataset: dict, modelo: str = "qwen3-coder-next:cloud", retries: int = 2, timeout: int = 60) -> Optional[dict]:
    """Genera TL;DR + perfil en una sola llamada LLM con timeout."""
    prompt = PROMPT_COMBINED.format(
        title=dataset["title"][:200],
        description=dataset["description"][:500] if dataset["description"] else "Sin descripción",
        tema=dataset["tema"],
        territorio=dataset["territorio"],
        formatos=dataset["formato"]
    )

    for intento in range(retries + 1):
        try:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)

            response = ollama.chat(model=modelo, messages=[
                {"role": "system", "content": "Eres un experto en documentación de datos abiertos. Responde SÓLO con JSON válido."},
                {"role": "user", "content": prompt}
            ])

            signal.alarm(0)

            texto = response["message"]["content"].strip()

            # Limpiar markdown
            if texto.startswith("```json"):
                texto = texto[7:]
            if texto.endswith("```"):
                texto = texto[:-3]
            texto = texto.strip()

            result = json.loads(texto)

            # Validar campos mínimos
            required = ["tldr", "variables_key", "temporal_coverage", "geographic_level"]
            if not all(field in result for field in required):
                return None

            # Limpiar TL;DR
            tldr = result["tldr"].strip().strip('"\'')
            if len(tldr) < 10:
                return None

            result["tldr"] = tldr
            return result

        except TimeoutError:
            print(f"   ⚠️ Timeout en dataset {dataset['id'][:20]} intento {intento+1}")
            if intento == retries:
                signal.alarm(0)
                return None
            time.sleep(1)

        except Exception as e:
            if intento == retries:
                signal.alarm(0)
                return None
            time.sleep(0.5)

    signal.alarm(0)
    return None


def save_profile_to_db(dataset_id: str, data: dict):
    """Guarda perfil en la base de datos."""
    conn = get_db_connection()

    upsert_query = """
        INSERT INTO dataset_profiles (
            dataset_id, tldr, tldr_generated_at,
            variables_key, temporal_coverage, geographic_level, geographic_entity, frecuencia,
            last_updated, profile_version
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 1
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
                datetime.now(timezone.utc),
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
        print(f"  ❌ Error guardando en BD: {e}")
        conn.rollback()
        conn.close()
        return False


def load_checkpoint(checkpoint_path: Path) -> int:
    if checkpoint_path.exists():
        with open(checkpoint_path, "r") as f:
            data = json.load(f)
            return data.get("offset", 0)
    return 0


def save_checkpoint(checkpoint_path: Path, offset: int, processed: int, failed: int):
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path, "w") as f:
        json.dump({
            "offset": offset,
            "processed": processed,
            "failed": failed,
            "last_updated": datetime.now().isoformat()
        }, f)


def main():
    parser = argparse.ArgumentParser(description="Generar perfiles de datasets de forma secuencial")
    parser.add_argument("--source-table", type=str, default="datasets", help="Tabla origen de datasets")
    parser.add_argument("--model", "-m", type=str, default="qwen3-coder-next:cloud", help="Modelo LLM")
    parser.add_argument("--batch-size", "-b", type=int, default=50, help="Tamaño de lote para fetch")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Máximo número de datasets a procesar")
    parser.add_argument("--checkpoint-dir", "-c", type=str, default="checkpoints_sequential", help="Directorio de checkpoints")
    parser.add_argument("--rate-limit-delay", type=float, default=0, help="Segundos entre datasets")
    args = parser.parse_args()

    checkpoint_dir = Path(args.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / "checkpoint.json"

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {args.source_table}")
        total_datasets = cur.fetchone()[0]
    conn.close()

    if args.limit:
        total_datasets = min(total_datasets, args.limit)

    print(f"📊 Total datasets en `{args.source_table}`: {total_datasets}")
    print(f"🤖 Modelo: {args.model}")
    print(f"📦 Batch size: {args.batch_size}")
    print(f"⏱️  Rate limit delay: {args.rate_limit_delay}s")
    print()

    offset = load_checkpoint(checkpoint_path)
    processed_total = 0
    failed_total = 0
    start_time = time.time()
    last_report_time = start_time
    last_report_processed = 0

    while offset < total_datasets:
        current_batch_size = min(args.batch_size, total_datasets - offset)
        datasets = fetch_datasets_batch(args.source_table, offset, current_batch_size)

        if not datasets:
            print("   No hay más datasets")
            break

        for dataset in datasets:
            data = generate_profile_combined(dataset, args.model)

            if data:
                success = save_profile_to_db(dataset["id"], data)
                if success:
                    processed_total += 1
                else:
                    failed_total += 1
            else:
                failed_total += 1

            time.sleep(args.rate_limit_delay)

        offset += len(datasets)
        save_checkpoint(checkpoint_path, offset, processed_total, failed_total)

        # Reporte cada ~30 segundos
        now = time.time()
        if now - last_report_time >= 30:
            elapsed = now - start_time
            speed = processed_total / elapsed
            interval_speed = (processed_total - last_report_processed) / (now - last_report_time)
            eta = (total_datasets - processed_total) / speed if speed > 0 else 0
            print(f"   offset={offset} | procesados={processed_total} | fallidos={failed_total} | "
                  f"vel={speed:.2f}/s (último intervalo {interval_speed:.2f}/s) | ETA={eta/60:.1f}min")
            last_report_time = now
            last_report_processed = processed_total

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("✅ PROCESAMIENTO SECUENCIAL COMPLETADO")
    print("=" * 60)
    print(f"   Total procesados: {processed_total}")
    print(f"   Total fallidos: {failed_total}")
    print(f"   Tasa de éxito: {processed_total / (processed_total + failed_total) * 100:.1f}%")
    print(f"   Tiempo total: {elapsed / 3600:.2f} horas")
    print(f"   Velocidad: {processed_total / elapsed:.2f} datasets/segundo")

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), COUNT(tldr), COUNT(variables_key) FROM dataset_profiles")
        row = cur.fetchone()
        print(f"\n📊 Estado en base de datos:")
        print(f"   Total perfiles: {row[0]}")
        print(f"   Con TL;DR: {row[1]}")
        print(f"   Con variables: {row[2]}")
    conn.close()


if __name__ == "__main__":
    main()
