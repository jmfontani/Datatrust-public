#!/usr/bin/env python3
"""
Batch Generate Profiles PARALELO V2 - Sprint 8 (Paquete A: #5 + #14)

OPTIMIZADO: Una sola llamada LLM por dataset genera TL;DR + perfil estructurado.

Uso:
    python batch_generate_profiles_parallel_v2.py \
        --workers 3 \
        --batch-size 100 \
        --resume
"""

import json
import argparse
import sys
import os
import time
import multiprocessing as mp
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

mp.set_start_method("spawn", force=True)

try:
    import ollama
    import psycopg2
except ImportError:
    print("❌ Instalando dependencias: pip install ollama psycopg2-binary")
    sys.exit(1)


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


def fetch_datasets_batch(offset: int, batch_size: int, source_table: str = "datasets"):
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


def generate_profile_combined(dataset: dict, modelo: str = "deepseek-v4.1-flash:cloud", retries: int = 2) -> Optional[dict]:
    """Genera TL;DR + perfil en una sola llamada LLM."""
    prompt = PROMPT_COMBINED.format(
        title=dataset["title"][:200],
        description=dataset["description"][:500] if dataset["description"] else "Sin descripción",
        tema=dataset["tema"],
        territorio=dataset["territorio"],
        formatos=dataset["formato"]
    )

    for intento in range(retries + 1):
        try:
            response = ollama.chat(model=modelo, messages=[
                {"role": "system", "content": "Eres un experto en documentación de datos abiertos. Responde SÓLO con JSON válido."},
                {"role": "user", "content": prompt}
            ])

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

        except Exception as e:
            if intento == retries:
                return None
            time.sleep(0.5)

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


def load_checkpoint(checkpoint_path: Path) -> tuple[int, int, int]:
    if checkpoint_path.exists():
        with open(checkpoint_path, "r") as f:
            data = json.load(f)
            return (
                data.get("offset", 0),
                data.get("processed", 0),
                data.get("failed", 0)
            )
    return 0, 0, 0


def save_checkpoint(checkpoint_path: Path, offset: int, processed: int, failed: int):
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path, "w") as f:
        json.dump({
            "offset": offset,
            "processed": processed,
            "failed": failed,
            "last_updated": datetime.now().isoformat()
        }, f)


def process_worker(args):
    """Función ejecutada por cada worker."""
    worker_id = args["worker_id"]
    start_offset = args["start_offset"]
    end_offset = args["end_offset"]
    batch_size = args["batch_size"]
    modelo = args["modelo"]
    source_table = args["source_table"]
    checkpoint_dir = Path(args["checkpoint_dir"])
    rate_limit_delay = args["rate_limit_delay"]

    checkpoint_path = checkpoint_dir / f"checkpoint_worker_{worker_id}.json"

    offset, processed_total, failed_total = load_checkpoint(checkpoint_path)
    if offset < start_offset:
        offset = start_offset

    print(f"👷 Worker {worker_id}: inicio offset={offset}, fin={end_offset}")

    batch_num = 0

    while offset < end_offset:
        batch_num += 1
        current_batch_size = min(batch_size, end_offset - offset)
        datasets = fetch_datasets_batch(offset, current_batch_size, source_table)

        if not datasets:
            print(f"   Worker {worker_id}: no hay más datasets")
            break

        for dataset in datasets:
            data = generate_profile_combined(dataset, modelo)

            if data:
                success = save_profile_to_db(dataset["id"], data)
                if success:
                    processed_total += 1
                else:
                    failed_total += 1
            else:
                failed_total += 1

            time.sleep(rate_limit_delay)

        offset += len(datasets)
        save_checkpoint(checkpoint_path, offset, processed_total, failed_total)

        if batch_num % 10 == 0:
            print(f"   Worker {worker_id}: offset={offset}, procesados={processed_total}, fallidos={failed_total}")

    print(f"✅ Worker {worker_id} completado: {processed_total} procesados, {failed_total} fallidos")
    return {
        "worker_id": worker_id,
        "processed": processed_total,
        "failed": failed_total
    }


def main():
    parser = argparse.ArgumentParser(description="Generar perfiles de datasets en paralelo V2 (1 LLM por dataset)")
    parser.add_argument("--workers", "-w", type=int, default=3, help="Número de workers paralelos")
    parser.add_argument("--batch-size", "-b", type=int, default=100, help="Tamaño de lote por worker")
    parser.add_argument("--resume", "-r", action="store_true", help="Reanudar desde checkpoints")
    parser.add_argument("--checkpoint-dir", "-c", type=str, default="checkpoints_parallel_v2", help="Directorio de checkpoints")
    parser.add_argument("--model", "-m", type=str, default="deepseek-v4.1-flash:cloud", help="Modelo LLM")
    parser.add_argument("--rate-limit-delay", type=float, default=0.1, help="Segundos entre datasets")
    parser.add_argument("--source-table", type=str, default="datasets", help="Tabla origen de datasets")
    args = parser.parse_args()

    checkpoint_dir = Path(args.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {args.source_table}")
        total_datasets = cur.fetchone()[0]
    conn.close()

    print(f"📊 Total de datasets en fuente `{args.source_table}`: {total_datasets}")
    print(f"🚀 Workers: {args.workers}")
    print(f"📦 Batch size: {args.batch_size}")
    print(f"🤖 Modelo: {args.model}")
    print(f"⏱️  Rate limit delay: {args.rate_limit_delay}s")
    print(f"📝 1 LLM por dataset (TL;DR + perfil combinado)")
    print()

    chunk_size = total_datasets // args.workers
    worker_args = []

    for i in range(args.workers):
        start_offset = i * chunk_size
        end_offset = (i + 1) * chunk_size if i < args.workers - 1 else total_datasets

        worker_args.append({
            "worker_id": i,
            "start_offset": start_offset,
            "end_offset": end_offset,
            "batch_size": args.batch_size,
            "modelo": args.model,
            "source_table": args.source_table,
            "checkpoint_dir": str(checkpoint_dir),
            "rate_limit_delay": args.rate_limit_delay
        })

    start_time = time.time()

    with mp.Pool(processes=args.workers) as pool:
        results = pool.map(process_worker, worker_args)

    elapsed = time.time() - start_time

    total_processed = sum(r["processed"] for r in results)
    total_failed = sum(r["failed"] for r in results)

    print("\n" + "=" * 60)
    print("✅ PROCESAMIENTO PARALELO V2 COMPLETADO")
    print("=" * 60)
    print(f"   Total procesados: {total_processed}")
    print(f"   Total fallidos: {total_failed}")
    print(f"   Tasa de éxito: {total_processed / (total_processed + total_failed) * 100:.1f}%")
    print(f"   Tiempo total: {elapsed / 3600:.2f} horas")
    print(f"   Velocidad: {total_processed / elapsed:.2f} datasets/segundo")

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
