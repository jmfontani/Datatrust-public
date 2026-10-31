#!/usr/bin/env python3
"""
Genera ground truth para datos.gob.es basado en los resultados reales de su web.

Uso:
    python generar_ground_truth_datosgobes.py \
        --input ../entregables/datosgobes_search_results.jsonl \
        --output ../entregables/ground_truth_datosgobes.jsonl

Proceso:
    1. Lee los top-N resultados web de datos.gob.es por query.
    2. Pasa los títulos a un LLM para clasificar relevancia y extraer patrones.
    3. Guarda ground truth compatible con utils/ragas_metrics.py.
"""

import json
import argparse
import sys
import time
from pathlib import Path

try:
    import ollama
except ImportError:
    print("❌ Instala ollama: pip install ollama")
    sys.exit(1)


PROMPT_CLASIFICAR_RELEVANCIA = """
Eres un experto en evaluación de buscadores de datos abiertos.

La query del usuario es: "{query}"
Categoría: {categoria}
Descripción: {descripcion}

A continuación tienes los RESULTADOS REALES que devolvió el buscador de datos.gob.es:

{resultados_json}

Tu tarea:
1. Clasificar CADA resultado como "relevante" o "no_relevante" según si satisface la query.
2. Explicar brevemente por qué.
3. Identificar patrones de palabras clave que caracterizan los resultados relevantes.

Responde SOLO con JSON válido con esta estructura EXACTA:

{{
    "query": "{query}",
    "categoria": "{categoria}",
    "ground_truth": {{
        "respuesta_ideal": "2-3 frases describiendo qué información busca el usuario",
        "resultados_clasificados": [
            {{
                "dataset_id": "id o URL del dataset (usa el número de orden si no hay id)",
                "title": "título completo",
                "relevancia": "relevante" | "no_relevante",
                "razon": "explicación de 1 frase"
            }}
        ],
        "patrones_palabras_clave": ["lista de palabras/frases que indican relevancia"],
        "criterios_evaluacion": {{
            "debe_contener": ["conceptos relevantes"],
            "no_debe_contener": ["conceptos no relevantes"],
            "minimo_relevantes_en_top5": 3
        }}
    }}
}}

Importante:
- Responde SÓLO el JSON, sin texto adicional.
- Sé generoso con la relevancia: si un resultado tiene relación, márcalo como relevante.
- Si no hay resultados, devuelve resultados_clasificados vacíos y patrones_palabras_clave vacíos.
"""


def cargar_resultados(path: Path) -> list[dict]:
    resultados = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                resultados.append(json.loads(line))
    return resultados


def generar_ground_truth(query_data: dict, resultados: list[dict], modelo: str = "deepseek-v4.1-flash:cloud", max_retries: int = 2) -> dict:
    """Genera ground truth para una query usando LLM."""

    resultados_json = "\n".join([
        f"{i+1}. {r.get('title', 'N/A')[:200]}"
        for i, r in enumerate(resultados)
    ])

    if not resultados:
        # Sin resultados: ground truth vacío pero válido
        return {
            **query_data,
            "ground_truth": {
                "respuesta_ideal": f"No se encontraron datasets para '{query_data['query']}' en datos.gob.es.",
                "resultados_clasificados": [],
                "patrones_palabras_clave": [],
                "criterios_evaluacion": {
                    "debe_contener": [],
                    "no_debe_contener": [],
                    "minimo_relevantes_en_top5": 0,
                },
            },
            "resultados_reales": resultados,
            "source": "datos.gob.es web",
        }

    prompt = PROMPT_CLASIFICAR_RELEVANCIA.format(
        query=query_data["query"],
        categoria=query_data.get("categoria", "unknown"),
        descripcion=query_data.get("descripcion", ""),
        resultados_json=resultados_json,
    )

    for intento in range(max_retries + 1):
        try:
            response = ollama.chat(
                model=modelo,
                messages=[
                    {"role": "system", "content": "Eres un experto en evaluación de buscadores. Responde SÓLO con JSON válido."},
                    {"role": "user", "content": prompt},
                ],
            )
            texto = response["message"]["content"].strip()
            if texto.startswith("```json"):
                texto = texto[7:]
            if texto.endswith("```"):
                texto = texto[:-3]
            texto = texto.strip()

            ground_truth = json.loads(texto)
            return {
                **query_data,
                "ground_truth": ground_truth["ground_truth"],
                "resultados_reales": resultados,
                "source": "datos.gob.es web",
            }
        except (json.JSONDecodeError, KeyError) as e:
            if intento < max_retries:
                print(f"⚠️  Reintentando (error JSON: {e})...", end=" ", flush=True)
            else:
                print(f"❌ Falló tras {max_retries + 1} intentos")
                return None
        except Exception as e:
            print(f"❌ Error LLM: {e}")
            return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", type=str, default="../entregables/datosgobes_search_results.jsonl")
    parser.add_argument("--output", "-o", type=str, default="../entregables/ground_truth_datosgobes.jsonl")
    parser.add_argument("--model", "-m", type=str, default="deepseek-v4.1-flash:cloud")
    parser.add_argument("--resume", "-r", action="store_true")
    parser.add_argument("--limit", "-l", type=int, default=None)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    resultados = cargar_resultados(input_path)
    if args.limit:
        resultados = resultados[:args.limit]

    # Reanudar
    procesados = set()
    if args.resume and output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    procesados.add(obj["id"])
        print(f"🔄 Reanudando: {len(procesados)} queries ya procesadas")
        resultados = [r for r in resultados if r["id"] not in procesados]

    if not resultados:
        print("✅ No hay queries pendientes")
        return

    print(f"🤖 Generando ground truth para datos.gob.es ({len(resultados)} queries)...")

    with open(output_path, "a" if args.resume else "w", encoding="utf-8") as out_f:
        for i, res in enumerate(resultados, 1):
            print(f"   [{i}/{len(resultados)}] {res['id']}: {res['query'][:50]}... ({len(res.get('titles', []))} resultados)", end=" ", flush=True)

            query_data = {
                "id": res["id"],
                "query": res["query"],
                "categoria": res.get("categoria", "unknown"),
                "dificultad": res.get("dificultad", "unknown"),
                "descripcion": res.get("descripcion", ""),
            }

            # Convertir títulos a formato de resultados con 'title'
            resultados_formateados = [{"title": t} for t in res.get("titles", [])]

            gt = generar_ground_truth(query_data, resultados_formateados, args.model)
            if gt:
                out_f.write(json.dumps(gt, ensure_ascii=False) + "\n")
                out_f.flush()
                print("✅")
            else:
                print("❌")

            time.sleep(0.5)

    print(f"\n✅ Ground truth guardado en: {output_path}")


if __name__ == "__main__":
    main()
