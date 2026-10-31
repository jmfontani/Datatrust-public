#!/usr/bin/env python3
"""
Generar Ground Truth para Evaluación RAGAS.

Usa LLM (Ollama) para generar respuestas "golden" y datasets relevantes esperados
para cada query del dataset de evaluación.

Uso:
    python generar_ground_truth.py \
        --input ../entregables/dataset_evaluacion.jsonl \
        --output ../entregables/ground_truth.jsonl
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    import ollama
except ImportError:
    print("❌ Instalando ollama: pip install ollama")
    sys.exit(1)


PROMPT_GENERAR_GROUND_TRUTH = """
Eres un experto en evaluación de sistemas de búsqueda de datos abiertos.

Para la siguiente query de búsqueda, genera información de ground truth que sirva
para evaluar la calidad del sistema de recuperación de datasets.

Query: "{query}"

Categoría: {categoria}
Dificultad: {dificultad}
Descripción: {descripcion}

Criterios de relevancia existentes:
{criterios}

Genera una respuesta JSON con la siguiente estructura EXACTA:

{{
    "query": "{query}",
    "categoria": "{categoria}",
    "dificultad": "{dificultad}",
    "ground_truth": {{
        "respuesta_ideal": "Descripción de 2-3 frases de qué información debería encontrar el usuario",
        "datasets_relevantes": [
            {{
                "titulo_patron": "Patrón o palabras clave del título esperado",
                "tema": "Tema DCAT esperado (ej: Empleo, Demografía, Economía)",
                "territorio": "Cobertura territorial esperada (España, Andalucía, etc.)",
                "razon_relevancia": "Por qué este dataset es relevante para la query"
            }}
        ],
        "criterios_evaluacion": {{
            "debe_contener": ["Conceptos que DEBE mencionar la respuesta"],
            "no_debe_contener": ["Conceptos que NO son relevantes para esta query"],
            "minimo_datasets_relevantes": 3
        }}
    }}
}}

Importante:
- La respuesta debe ser SÓLO el JSON, sin texto adicional
- Los datasets_relevantes deben ser realistas para datos.gob.es
- Incluye al menos 3 datasets relevantes
- Sé específico con los patrones de título
"""


def cargar_queries(input_path: Path) -> list[dict]:
    """Carga queries desde archivo JSONL."""
    queries = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))
    return queries


def generar_ground_truth_query(query_data: dict, modelo: str = "deepseek-v4-pro:cloud") -> Optional[dict]:
    """
    Genera ground truth para una query usando LLM.

    Returns:
        dict con la query original + ground_truth generado, o None si falla
    """
    prompt = PROMPT_GENERAR_GROUND_TRUTH.format(
        query=query_data["query"],
        categoria=query_data["categoria"],
        dificultad=query_data["dificultad"],
        descripcion=query_data["descripcion"],
        criterios="\n".join(f"  - {c}" for c in query_data["criterios_relevancia"])
    )

    try:
        response = ollama.chat(model=modelo, messages=[
            {"role": "system", "content": "Eres un experto en evaluación de sistemas de búsqueda. Responde SOLO con JSON válido."},
            {"role": "user", "content": prompt}
        ])

        # Extraer JSON de la respuesta
        texto = response["message"]["content"].strip()

        # Limpiar posibles bloques de código markdown
        if texto.startswith("```json"):
            texto = texto[7:]
        if texto.endswith("```"):
            texto = texto[:-3]
        texto = texto.strip()

        ground_truth = json.loads(texto)

        # Validar estructura mínima
        if "ground_truth" not in ground_truth:
            print(f"  ⚠️  Warning: Falta 'ground_truth' en respuesta")
            return None

        gt = ground_truth["ground_truth"]
        if "respuesta_ideal" not in gt or "datasets_relevantes" not in gt:
            print(f"  ⚠️  Warning: Faltan campos requeridos en ground_truth")
            return None

        # Merge con datos originales
        result = {**query_data, "ground_truth": gt}
        return result

    except json.JSONDecodeError as e:
        print(f"  ❌ Error parsing JSON: {e}")
        print(f"     Respuesta raw: {texto[:200]}...")
        return None
    except Exception as e:
        print(f"  ❌ Error generando ground truth: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Generar ground truth con LLM para evaluación RAGAS")
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="../entregables/dataset_evaluacion.jsonl",
        help="Archivo de entrada con queries"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="../entregables/ground_truth.jsonl",
        help="Archivo de salida con ground truth"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="deepseek-v4.1-flash:cloud",
        help="Modelo Ollama a usar (debe coincidir con el backend)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Límite de queries a procesar (para testing)"
    )
    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Reanudar desde archivo existente (si existe output)"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Cargar queries
    print(f"📖 Cargando queries desde {input_path}...")
    queries = cargar_queries(input_path)

    if args.limit:
        queries = queries[:args.limit]
        print(f"   Limitado a {len(queries)} queries (modo testing)")

    # Reanudar si existe output
    procesados = []
    if args.resume and output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    procesados.append(json.loads(line))
        print(f"🔄 Reanudando: {len(procesados)} queries ya procesadas")
        ids_procesados = {p["id"] for p in procesados}
        queries = [q for q in queries if q["id"] not in ids_procesados]
        print(f"   Faltan {len(queries)} queries por procesar")

    if not queries:
        print("✅ No hay queries pendientes. ¡Todo completado!")
        return

    # Probar conexión con Ollama
    print(f"\n🔌 Probando conexión con Ollama ({args.model})...")
    try:
        ollama.chat(model=args.model, messages=[{"role": "user", "content": "di solo 'ok'"}])
        print("   ✅ Ollama disponible")
    except Exception as e:
        print(f"   ❌ Error conectando a Ollama: {e}")
        print("   Asegúrate de tener Ollama corriendo: ollama serve")
        sys.exit(1)

    # Generar ground truth
    print(f"\n🤖 Generando ground truth con {args.model}...")
    print(f"   Progreso: 0/{len(queries)} queries", end="", flush=True)

    with open(output_path, "a", encoding="utf-8") as out_f:
        for i, query in enumerate(queries, 1):
            print(f"\r   Progreso: {i}/{len(queries)} queries - {query['id']}", end="", flush=True)

            gt = generar_ground_truth_query(query, args.model)

            if gt:
                out_f.write(json.dumps(gt, ensure_ascii=False) + "\n")
                out_f.flush()
            else:
                # Reintentar una vez
                print(f"\n   ⚠️  Reintentando {query['id']}...")
                gt = generar_ground_truth_query(query, args.model)
                if gt:
                    out_f.write(json.dumps(gt, ensure_ascii=False) + "\n")
                    out_f.flush()
                else:
                    print(f"   ❌ Falló {query['id']} - se salta")

    print(f"\r   ✅ Completado: {len(queries)} queries procesadas")

    # Resumen
    total = len(procesados) + len(queries)
    print(f"\n📊 Resumen:")
    print(f"   Total queries: {total}")
    print(f"   Ground truths generados: {len(procesados) + len(queries)}")
    print(f"   Archivo: {output_path}")


if __name__ == "__main__":
    main()
