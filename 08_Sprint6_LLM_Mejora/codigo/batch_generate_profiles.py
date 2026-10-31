#!/usr/bin/env python3
"""
Batch Generate Profiles - Sprint 8 (Paquete A: #5 + #14)

Genera perfiles precalculados para todos los datasets:
  #14: TL;DR (resumen de 2-3 frases)
  #5:  Perfil para detección de complementariedad

Uso:
    python batch_generate_profiles.py \
        --limit 1000 \      # Para testing
        --batch-size 100 \  # Procesar en lotes
        --resume            # Reanudar desde checkpoint
"""

import json
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

try:
    import ollama
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:
    print("❌ Instalando dependencias: pip install ollama psycopg2-binary")
    sys.exit(1)


# Configuración de base de datos
DB_CONFIG = {
    "host": "172.17.0.1",
    "port": 5432,
    "database": "buscador",
    "user": "postgres",
    "password": "postgres"
}


PROMPT_TLDR = """
Eres un experto en documentación de datos abiertos.

Genera un resumen TL;DR (Too Long; Didn't Read) de 2-3 frases para este dataset.

Título: {title}
Descripción: {description}
Tema: {tema}
Territorio: {territorio}
Formatos disponibles: {formatos}

El TL;DR debe:
1. Ser conciso (20-50 palabras)
2. Mencionar: qué datos contiene, cobertura territorial, periodo temporal (si disponible)
3. Incluir fuente o institución (si se infiere del título)
4. Ser útil para que un usuario decida rápidamente si le interesa

Responde SÓLO con el texto del TL;DR, sin comillas ni texto adicional.
"""


PROMPT_EXTRACT_PROFILE = """
Extrae información estructurada de este dataset para un perfil de metadatos.

Título: {title}
Descripción: {description}
Tema: {tema}

Responde SÓLO con JSON válido con esta estructura:

{{
    "variables_key": ["lista de 5-10 palabras clave que representan las variables del dataset"],
    "temporal_coverage": "periodo o frecuencia (ej: '2005-2023', 'mensual', 'anual')",
    "geographic_level": "nivel geográfico (nacional | autonómico | provincial | municipal | insular)",
    "geographic_entity": "entidad específica si se menciona (ej: 'Canarias', 'España', 'Madrid')",
    "frecuencia": "frecuencia de actualización (mensual | trimestral | anual | puntual)"
}}

Reglas:
- variables_key: extraer conceptos medibles (ej: ["paro", "desempleo", "tasa", "jóvenes"] para empleo juvenil)
- geographic_level: usar una de las opciones indicadas
- Si no se puede determinar, usar "desconocido"
"""


def get_db_connection():
    """Obtiene conexión a PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)


def fetch_datasets_batch(limit: Optional[int] = None, offset: int = 0, batch_size: int = 100):
    """Obtiene lotes de datasets de la BD."""
    conn = get_db_connection()

    query = """
        SELECT
            dataset_id, title, description, theme, territory, format
        FROM datasets
        ORDER BY id
        LIMIT %s OFFSET %s
    """

    with conn.cursor() as cur:
        cur.execute(query, (batch_size, offset))
        rows = cur.fetchall()

    conn.close()

    if not rows:
        return []

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


def generate_tldr(dataset: dict, modelo: str = "deepseek-v4.1-flash:cloud") -> Optional[str]:
    """Genera TL;DR para un dataset."""
    prompt = PROMPT_TLDR.format(
        title=dataset["title"][:200],  # Truncar si es muy largo
        description=dataset["description"][:500] if dataset["description"] else "Sin descripción",
        tema=dataset["tema"],
        territorio=dataset["territorio"],
        formatos=dataset["formato"]
    )

    try:
        response = ollama.chat(model=modelo, messages=[
            {"role": "system", "content": "Eres un experto en documentación de datos abiertos. Responde SÓLO con el texto solicitado."},
            {"role": "user", "content": prompt}
        ])

        tldr = response["message"]["content"].strip()

        # Limpiar posibles comillas o markdown
        tldr = tldr.strip('"\'')
        if tldr.startswith("```"):
            tldr = tldr.split("\n", 1)[-1].split("```")[0].strip()

        return tldr if len(tldr) > 10 else None

    except Exception as e:
        print(f"  ❌ Error generando TL;DR: {e}")
        return None


def extract_profile(dataset: dict, modelo: str = "deepseek-v4-pro:cloud") -> Optional[dict]:
    """Extrae perfil estructurado de un dataset."""
    prompt = PROMPT_EXTRACT_PROFILE.format(
        title=dataset["title"][:200],
        description=dataset["description"][:500] if dataset["description"] else "Sin descripción",
        tema=dataset["tema"]
    )

    try:
        response = ollama.chat(model=modelo, messages=[
            {"role": "system", "content": "Eres un experto en metadatos. Responde SÓLO con JSON válido."},
            {"role": "user", "content": prompt}
        ])

        texto = response["message"]["content"].strip()

        # Limpiar markdown
        if texto.startswith("```json"):
            texto = texto[7:]
        if texto.endswith("```"):
            texto = texto[:-3]
        texto = texto.strip()

        profile = json.loads(texto)

        # Validar campos mínimos
        required_fields = ["variables_key", "temporal_coverage", "geographic_level"]
        if not all(field in profile for field in required_fields):
            print(f"  ⚠️  Perfil incompleto")
            return None

        return profile

    except Exception as e:
        print(f"  ❌ Error extrayendo perfil: {e}")
        return None


def save_profile_to_db(dataset_id: str, tldr: Optional[str], profile: Optional[dict]):
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
                tldr,
                datetime.now(timezone.utc) if tldr else None,
                profile.get("variables_key") if profile else None,
                profile.get("temporal_coverage") if profile else None,
                profile.get("geographic_level") if profile else None,
                profile.get("geographic_entity") if profile else None,
                profile.get("frecuencia") if profile else None
            ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"  ❌ Error guardando en BD: {e}")
        conn.rollback()
        conn.close()
        return False


def load_checkpoint(checkpoint_path: Path) -> tuple[int, int]:
    """Carga checkpoint de procesamiento."""
    if checkpoint_path.exists():
        with open(checkpoint_path, "r") as f:
            data = json.load(f)
            return data.get("offset", 0), data.get("processed", 0)
    return 0, 0


def save_checkpoint(checkpoint_path: Path, offset: int, processed: int, failed: int):
    """Guarda checkpoint de procesamiento."""
    with open(checkpoint_path, "w") as f:
        json.dump({
            "offset": offset,
            "processed": processed,
            "failed": failed,
            "last_updated": datetime.now().isoformat()
        }, f)


def main():
    parser = argparse.ArgumentParser(description="Generar perfiles de datasets (TL;DR + perfil estructurado)")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Límite de datasets a procesar")
    parser.add_argument("--batch-size", "-b", type=int, default=100, help="Tamaño de lote")
    parser.add_argument("--resume", "-r", action="store_true", help="Reanudar desde checkpoint")
    parser.add_argument("--checkpoint", "-c", type=str, default="checkpoint_profiles.json", help="Archivo de checkpoint")
    parser.add_argument("--model-tldr", type=str, default="deepseek-v4.1-flash:cloud", help="Modelo para TL;DR")
    parser.add_argument("--model-profile", type=str, default="deepseek-v4-pro:cloud", help="Modelo para perfil")
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)

    # Obtener total de datasets
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM datasets")
        total_datasets = cur.fetchone()[0]
    conn.close()

    print(f"📊 Total de datasets en BD: {total_datasets}")

    # Cargar checkpoint
    offset = 0
    processed_total = 0
    failed_total = 0

    if args.resume and checkpoint_path.exists():
        offset, processed_total = load_checkpoint(checkpoint_path)
        print(f"🔄 Reanudando desde offset={offset}, procesados={processed_total}")

    # Límite
    max_offset = offset + args.limit if args.limit else total_datasets

    print(f"\n🚀 Iniciando generación de perfiles...")
    print(f"   Offset inicial: {offset}")
    print(f"   Offset máximo: {max_offset}")
    print(f"   Batch size: {args.batch_size}")
    print(f"   Modelo TL;DR: {args.model_tldr}")
    print(f"   Modelo perfil: {args.model_profile}")
    print()

    batch_num = 0

    while offset < max_offset:
        batch_num += 1
        print(f"📦 Lote {batch_num}: datasets {offset + 1} - {min(offset + args.batch_size, max_offset)}")

        # Obtener lote
        datasets = fetch_datasets_batch(limit=args.limit, offset=offset, batch_size=args.batch_size)

        if not datasets:
            print("   No hay más datasets")
            break

        print(f"   Obtenidos: {len(datasets)} datasets")

        # Procesar lote
        for i, dataset in enumerate(datasets, 1):
            print(f"   [{i}/{len(datasets)}] {dataset['id'][:20]}... ", end="", flush=True)

            # Generar TL;DR
            tldr = generate_tldr(dataset, args.model_tldr)
            print(f"TL;DR={'✅' if tldr else '❌'} ", end="", flush=True)

            # Extraer perfil
            profile = extract_profile(dataset, args.model_profile)
            print(f"Perfil={'✅' if profile else '❌'}", end="", flush=True)

            # Guardar en BD
            if tldr or profile:
                success = save_profile_to_db(dataset["id"], tldr, profile)
                if success:
                    processed_total += 1
                    print(" ✅", end="")
                else:
                    failed_total += 1
                    print(" ❌", end="")
            else:
                failed_total += 1
                print(" ❌", end="")

            print()

        # Actualizar offset
        offset += len(datasets)

        # Guardar checkpoint
        save_checkpoint(checkpoint_path, offset, processed_total, failed_total)
        print(f"   💾 Checkpoint guardado: offset={offset}, procesados={processed_total}, fallidos={failed_total}")
        print()

    # Resumen final
    print("\n" + "=" * 60)
    print("✅ PROCESAMIENTO COMPLETADO")
    print("=" * 60)
    print(f"   Total procesados: {processed_total}")
    print(f"   Total fallidos: {failed_total}")
    print(f"   Tasa de éxito: {processed_total / (processed_total + failed_total) * 100:.1f}%")
    print(f"   Checkpoint: {checkpoint_path}")

    # Verificar en BD
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
