#!/usr/bin/env python3
"""
Evaluar impacto del TL;DR en juicio de relevancia - Sprint 8 (#14)

Compara, para las mismas queries y los mismos resultados, cuántos resultados
son considerados relevantes cuando el evaluador LLM ve:
  A) título + descripción (baseline)
  B) título + TL;DR generado

Uso:
    python eval_ragas_tldr.py --sample-size 20
"""

import os
import json
import argparse
import sys
import time
import signal
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests
import psycopg2
import ollama


DB_CONFIG = {
    "host": "172.17.0.1",
    "port": 5432,
    "database": "buscador",
    "user": "postgres",
    "password": "postgres"
}

API_URL = "http://localhost:8001"


PROMPT_TLDR_EVAL = """
Eres un evaluador de sistemas de búsqueda de datos abiertos.

Query del usuario: {query}

A continuación te presento 5 resultados de búsqueda en DOS condiciones:
- Condición A (baseline): ves el título y la descripción original
- Condición B (TL;DR): ves el título y un resumen TL;DR generado automáticamente

Para cada condición, evalúa la relevancia de cada resultado para la query (1 = relevante, 0 = no relevante).

=== CONDICIÓN A: Título + Descripción ===
{cond_a}

=== CONDICIÓN B: Título + TL;DR ===
{cond_b}

Responde SÓLO con JSON válido:
{{
    "condicion_a": [1, 0, 1, 0, 1],
    "condicion_b": [1, 0, 1, 1, 1],
    "comentario": "breve análisis de diferencias observadas"
}}
"""


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("LLM call exceeded timeout")


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def load_ground_truth_queries(path: str, sample_size: int):
    """Carga queries del ground truth de Sprint 7."""
    queries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line.strip())
            queries.append({
                "id": item.get("id", ""),
                "query": item.get("query", ""),
                "categoria": item.get("categoria", ""),
                "dificultad": item.get("dificultad", "")
            })

    # Estratificar por dificultad para muestra representativa
    by_diff = {"fácil": [], "media": [], "difícil": []}
    for q in queries:
        d = q["dificultad"].lower()
        if d in by_diff:
            by_diff[d].append(q)
        else:
            by_diff["media"].append(q)

    selected = []
    per_bucket = sample_size // 3
    for diff in ["fácil", "media", "difícil"]:
        selected.extend(by_diff[diff][:per_bucket])

    # Rellenar si falta
    remaining = sample_size - len(selected)
    if remaining > 0:
        used_ids = {q["id"] for q in selected}
        for q in queries:
            if q["id"] not in used_ids and remaining > 0:
                selected.append(q)
                remaining -= 1

    return selected[:sample_size]


def search_api(query: str, top_k: int = 5):
    """Llama a la API de búsqueda."""
    try:
        response = requests.post(
            f"{API_URL}/search",
            json={
                "query": query,
                "top_k": top_k,
                "explain": False,
                "use_synonyms": True,
                "remove_stopwords": True
            },
            timeout=60
        )
        if response.status_code != 200:
            print(f"   ⚠️ Search error {response.status_code}: {response.text[:200]}")
            return []
        return response.json().get("results", [])
    except Exception as e:
        print(f"   ⚠️ Search exception: {e}")
        return []


def get_tldr(dataset_id: str):
    """Obtiene TL;DR de la base de datos."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT tldr FROM dataset_profiles WHERE dataset_id = %s", (dataset_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def evaluate_query(query_item: dict, results: list[dict], modelo: str = "qwen3-coder-next:cloud", timeout: int = 120) -> Optional[dict]:
    """Evalúa relevancia de resultados bajo dos condiciones."""
    if not results:
        return None

    cond_a_lines = []
    cond_b_lines = []

    for idx, r in enumerate(results, 1):
        title = r.get("title", "")[:120]
        description = r.get("description", "")[:300] or "Sin descripción"
        tldr = get_tldr(r.get("id")) or description[:200]

        cond_a_lines.append(f"[{idx}] Título: {title}\n    Descripción: {description}")
        cond_b_lines.append(f"[{idx}] Título: {title}\n    TL;DR: {tldr}")

    prompt = PROMPT_TLDR_EVAL.format(
        query=query_item["query"],
        cond_a="\n\n".join(cond_a_lines),
        cond_b="\n\n".join(cond_b_lines)
    )

    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)

        response = ollama.chat(model=modelo, messages=[
            {"role": "system", "content": "Eres un evaluador crítico de sistemas de búsqueda. Responde SÓLO con JSON válido."},
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

        a_scores = result.get("condicion_a", [])
        b_scores = result.get("condicion_b", [])

        # Normalizar a binario
        def to_binary(scores):
            return [1 if s and float(s) >= 0.5 else 0 for s in scores[:len(results)]]

        a_binary = to_binary(a_scores)
        b_binary = to_binary(b_scores)

        return {
            "query_id": query_item["id"],
            "query": query_item["query"],
            "condicion_a": a_binary,
            "condicion_b": b_binary,
            "precision_a": sum(a_binary) / len(a_binary) if a_binary else 0,
            "precision_b": sum(b_binary) / len(b_binary) if b_binary else 0,
            "comentario": result.get("comentario", "")
        }

    except TimeoutError:
        signal.alarm(0)
        print(f"   ⚠️ Timeout evaluando {query_item['id']}")
        return None
    except Exception as e:
        signal.alarm(0)
        print(f"   ⚠️ Error evaluando {query_item['id']}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Evaluar impacto de TL;DR en relevancia")
    parser.add_argument("--ground-truth", type=str,
                        default=os.path.expanduser("~/datos/PFM/Datatrust/09_Sprint7_RAGAS/entregables/ground_truth_real.jsonl"),
                        help="Ruta al ground truth de Sprint 7")
    parser.add_argument("--sample-size", type=int, default=20, help="Número de queries a evaluar")
    parser.add_argument("--model", type=str, default="qwen3-coder-next:cloud", help="Modelo evaluador")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout por evaluación")
    parser.add_argument("--top-k", type=int, default=5, help="Resultados por query")
    args = parser.parse_args()

    print(f"🎯 Evaluando impacto del TL;DR en juicio de relevancia")
    print(f"📊 Queries: {args.sample_size}")
    print(f"🤖 Modelo evaluador: {args.model}")
    print(f"🔢 Top-K: {args.top_k}")
    print()

    queries = load_ground_truth_queries(args.ground_truth, args.sample_size)
    print(f"✅ Queries cargadas: {len(queries)}")

    results = []
    start_time = time.time()

    for idx, q in enumerate(queries, 1):
        print(f"\n[{idx}/{len(queries)}] Query: {q['query']}")
        search_results = search_api(q["query"], top_k=args.top_k)
        if not search_results:
            print("   ⚠️ Sin resultados de búsqueda")
            continue

        print(f"   Resultados obtenidos: {len(search_results)}")
        eval_result = evaluate_query(q, search_results, modelo=args.model, timeout=args.timeout)
        if eval_result:
            results.append(eval_result)
            print(f"   ✓ P@5 baseline: {eval_result['precision_a']:.2f} | P@5 TL;DR: {eval_result['precision_b']:.2f}")
        else:
            print("   ✗ No se pudo evaluar")

    elapsed = time.time() - start_time

    if not results:
        print("\n❌ No se pudo evaluar ninguna query")
        sys.exit(1)

    avg_a = sum(r["precision_a"] for r in results) / len(results)
    avg_b = sum(r["precision_b"] for r in results) / len(results)
    improved = sum(1 for r in results if r["precision_b"] > r["precision_a"])
    worsened = sum(1 for r in results if r["precision_b"] < r["precision_a"])
    same = sum(1 for r in results if r["precision_b"] == r["precision_a"])

    print("\n" + "=" * 60)
    print("RESULTADOS EVALUACIÓN TL;DR")
    print("=" * 60)
    print(f"   Queries evaluadas: {len(results)}")
    print(f"   Precisión@5 media (baseline): {avg_a:.3f}")
    print(f"   Precisión@5 media (con TL;DR): {avg_b:.3f}")
    print(f"   Diferencia absoluta: {avg_b - avg_a:+.3f}")
    print(f"   Diferencia relativa: {(avg_b - avg_a) / avg_a * 100:+.1f}%")
    print(f"   Queries mejoradas: {improved} ({improved/len(results)*100:.1f}%)")
    print(f"   Queries empeoradas: {worsened} ({worsened/len(results)*100:.1f}%)")
    print(f"   Queries sin cambio: {same} ({same/len(results)*100:.1f}%)")
    print(f"   Tiempo total: {elapsed/60:.1f} min")

    output_path = Path("evaluacion_tldr_impact.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "fecha": datetime.now().isoformat(),
            "modelo_evaluador": args.model,
            "queries_evaluadas": len(results),
            "top_k": args.top_k,
            "metricas": {
                "precision_baseline_media": avg_a,
                "precision_tldr_media": avg_b,
                "diferencia_absoluta": avg_b - avg_a,
                "diferencia_relativa_pct": (avg_b - avg_a) / avg_a * 100,
                "queries_mejoradas": improved,
                "queries_empeoradas": worsened,
                "queries_iguales": same
            },
            "detalle": results
        }, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Detalle guardado en: {output_path}")


if __name__ == "__main__":
    main()
