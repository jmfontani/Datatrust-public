#!/usr/bin/env python3
"""
Evaluar calidad de complementariedad precalculada - Sprint 8 (#5)

Usa LLM-as-judge para evaluar:
  - Relevancia del dataset complementario
  - Validez de la clave de unión
  - Utilidad del análisis propuesto

Uso:
    python evaluar_complementariedad.py --sample-size 30
"""

import json
import argparse
import sys
import time
import signal
from pathlib import Path
from datetime import datetime
from typing import Optional

import psycopg2
import ollama


DB_CONFIG = {
    "host": "172.17.0.1",
    "port": 5432,
    "database": "buscador",
    "user": "postgres",
    "password": "postgres"
}


PROMPT_JUDGE = """
Eres un evaluador experto en datos abiertos y análisis de datos.

Dataset original:
- ID: {source_id}
- Título: {source_title}
- Descripción: {source_description}
- Variables: {source_variables}
- Nivel geográfico: {source_geo_level}
- Cobertura temporal: {source_temporal}

Dataset propuesto como complementario:
- ID: {comp_id}
- Título: {comp_title}
- Descripción: {comp_description}
- Variables: {comp_variables}

Explicación del sistema:
- Razón: {reason}
- Clave de unión propuesta: {join_key}
- Análisis potencial: {potential_analysis}

Evalúa la propuesta en las siguientes dimensiones (1-5):

1. **relevancia**: ¿Es realmente complementario? ¿Aporta variables diferentes pero relacionadas? ¿Comparte clave de unión plausible? (1=irrelevante, 5=muy complementario)
2. **join_key_valid**: ¿La clave de unión propuesta es técnicamente plausible? (1=imposible, 5=muy plausible)
3. **analysis_useful**: ¿El análisis propuesto es útil y tiene sentido con ambos datasets? (1=inútil, 5=muy útil)

Responde SÓLO con JSON válido:
{{
    "relevancia": 4,
    "join_key_valid": 4,
    "analysis_useful": 3,
    "comentario": "breve justificación"
}}
"""


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("LLM call exceeded timeout")


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def fetch_sample_with_complementaries(sample_size: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            p.dataset_id,
            d.title,
            d.description,
            p.variables_key,
            p.geographic_level,
            p.temporal_coverage,
            p.combinable_with_json
        FROM dataset_profiles p
        JOIN dataset_sample_2k s ON p.dataset_id = s.dataset_id
        JOIN datasets d ON p.dataset_id = d.dataset_id
        WHERE p.combinable_with_json IS NOT NULL
          AND p.combinable_with_json != '[]'
        ORDER BY RANDOM()
        LIMIT %s
    """, (sample_size,))
    rows = cur.fetchall()
    conn.close()
    return rows


def fetch_candidate_info(dataset_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.title, d.description, dp.variables_key, dp.geographic_level, dp.temporal_coverage
        FROM datasets d
        LEFT JOIN dataset_profiles dp ON d.dataset_id = dp.dataset_id
        WHERE d.dataset_id = %s
    """, (dataset_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "title": row[0] or "",
        "description": row[1] or "",
        "variables": row[2] or [],
        "geo_level": row[3] or "desconocido",
        "temporal": row[4] or "desconocido"
    }


def judge_complementary(source: dict, comp: dict, modelo: str = "qwen3-coder-next:cloud", timeout: int = 120) -> Optional[dict]:
    """Evalúa un complementario con LLM-as-judge."""
    prompt = PROMPT_JUDGE.format(
        source_id=source["dataset_id"][:120],
        source_title=source["title"][:200],
        source_description=(source["description"] or "")[:400],
        source_variables=source["variables"],
        source_geo_level=source["geo_level"],
        source_temporal=source["temporal"],
        comp_id=comp["dataset_id"][:120],
        comp_title=comp["title"][:200],
        comp_description=(comp["description"] or "")[:400],
        comp_variables=comp["variables"],
        reason=comp.get("reason", "")[:300],
        join_key=comp.get("join_key", "")[:100],
        potential_analysis=comp.get("potential_analysis", "")[:300]
    )

    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)

        response = ollama.chat(model=modelo, messages=[
            {"role": "system", "content": "Eres un evaluador crítico de análisis de datos abiertos. Responde SÓLO con JSON válido."},
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
        for k in ["relevancia", "join_key_valid", "analysis_useful"]:
            if k not in result:
                return None
            if not isinstance(result[k], (int, float)):
                return None
        return result

    except TimeoutError:
        signal.alarm(0)
        print(f"   ⚠️ Timeout evaluando {comp['dataset_id'][:40]}")
        return None
    except Exception as e:
        signal.alarm(0)
        print(f"   ⚠️ Error evaluando {comp['dataset_id'][:40]}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Evaluar calidad de complementariedad")
    parser.add_argument("--sample-size", type=int, default=30, help="Número de datasets a evaluar")
    parser.add_argument("--model", type=str, default="qwen3-coder-next:cloud", help="Modelo juez")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout por evaluación")
    args = parser.parse_args()

    print(f"🎯 Evaluando calidad de complementariedad")
    print(f"📊 Muestra: {args.sample_size} datasets")
    print(f"🤖 Modelo juez: {args.model}")
    print()

    rows = fetch_sample_with_complementaries(args.sample_size)
    print(f"✅ Datasets con complementarios: {len(rows)}")

    results = []
    total_complementaries = 0
    start_time = time.time()

    for idx, row in enumerate(rows, 1):
        source = {
            "dataset_id": row[0],
            "title": row[1],
            "description": row[2],
            "variables": row[3],
            "geo_level": row[4],
            "temporal": row[5]
        }
        complementary_list = row[6] if isinstance(row[6], list) else json.loads(row[6])

        print(f"\n[{idx}/{len(rows)}] {source['dataset_id'][:60]}")
        print(f"   Complementarios: {len(complementary_list)}")

        for comp in complementary_list:
            total_complementaries += 1
            candidate_info = fetch_candidate_info(comp["dataset_id"])
            if not candidate_info:
                print(f"   ⚠️ No se encontró info del candidato {comp['dataset_id'][:40]}")
                continue

            judge_result = judge_complementary(source, {**candidate_info, "dataset_id": comp["dataset_id"]}, modelo=args.model, timeout=args.timeout)
            if judge_result:
                results.append({
                    "source_id": source["dataset_id"],
                    "comp_id": comp["dataset_id"],
                    "title_comp": comp.get("title", "")[:80],
                    "reason": comp.get("reason", "")[:100],
                    **judge_result
                })
                print(f"   ✓ relevancia={judge_result['relevancia']}, join={judge_result['join_key_valid']}, análisis={judge_result['analysis_useful']}")
            else:
                print(f"   ✗ No se pudo evaluar")

    elapsed = time.time() - start_time

    if not results:
        print("\n❌ No se pudieron evaluar complementarios")
        sys.exit(1)

    # Métricas agregadas
    relevancia_scores = [r["relevancia"] for r in results]
    join_scores = [r["join_key_valid"] for r in results]
    analysis_scores = [r["analysis_useful"] for r in results]
    overall = [(r["relevancia"] + r["join_key_valid"] + r["analysis_useful"]) / 3 for r in results]

    print("\n" + "=" * 60)
    print("RESULTADOS EVALUACIÓN COMPLEMENTARIEDAD")
    print("=" * 60)
    print(f"   Complementarios evaluados: {len(results)} / {total_complementaries}")
    print(f"   Relevancia media: {sum(relevancia_scores)/len(relevancia_scores):.2f}/5")
    print(f"   Validez clave unión media: {sum(join_scores)/len(join_scores):.2f}/5")
    print(f"   Utilidad análisis media: {sum(analysis_scores)/len(analysis_scores):.2f}/5")
    print(f"   Calidad general media: {sum(overall)/len(overall):.2f}/5")
    print(f"   % con calidad >= 4/5: {sum(1 for x in overall if x >= 4)/len(overall)*100:.1f}%")
    print(f"   % con calidad >= 3/5: {sum(1 for x in overall if x >= 3)/len(overall)*100:.1f}%")
    print(f"   Tiempo total: {elapsed/60:.1f} min")

    # Guardar resultados
    output_path = Path("evaluacion_complementariedad.json")
    with open(output_path, "w") as f:
        json.dump({
            "fecha": datetime.now().isoformat(),
            "modelo_juez": args.model,
            "datasets_evaluados": len(rows),
            "complementarios_evaluados": len(results),
            "complementarios_totales": total_complementaries,
            "metricas": {
                "relevancia_media": sum(relevancia_scores)/len(relevancia_scores),
                "join_key_valid_media": sum(join_scores)/len(join_scores),
                "analysis_useful_media": sum(analysis_scores)/len(analysis_scores),
                "calidad_general_media": sum(overall)/len(overall),
                "pct_calidad_alta": sum(1 for x in overall if x >= 4)/len(overall),
                "pct_calidad_aceptable": sum(1 for x in overall if x >= 3)/len(overall)
            },
            "detalle": results
        }, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Detalle guardado en: {output_path}")


if __name__ == "__main__":
    main()
