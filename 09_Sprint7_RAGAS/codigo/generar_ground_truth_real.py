#!/usr/bin/env python3
"""
Generar Ground Truth BASADO EN RESULTADOS REALES.

En vez de pedir al LLM que invente patrones ideales, este script:
1. Ejecuta cada query contra la API real
2. Pasa los top 10 resultados reales al LLM
3. El LLM clasifica cuáles son relevantes y por qué
4. El ground truth resultante refleja la realidad de la BD

Uso:
    python generar_ground_truth_real.py \
        --input ../entregables/dataset_evaluacion.jsonl \
        --output ../entregables/ground_truth_real.jsonl
"""

import json
import argparse
import sys
from pathlib import Path

try:
    import ollama
    import requests
except ImportError:
    print("❌ Instalando dependencias: pip install ollama requests")
    sys.exit(1)


API_URL = "http://localhost:8000"


PROMPT_CLASIFICAR_RELEVANCIA = """
Eres un experto en evaluación de buscadores de datos abiertos.

La query del usuario es: "{query}"
Categoría: {categoria}
Descripción: {descripcion}

A continuación tienes los TOP 10 resultados que el buscador devolvió REALMENTE:

{resultados_json}

Tu tarea:
1. Clasificar CADA resultado como "relevante" o "no_relevante" según si satisface la query
2. Explicar brevemente por qué
3. Identificar patrones de palabras clave que caracterizan los resultados relevantes

Responde SOLO con JSON válido con esta estructura EXACTA:

{{
    "query": "{query}",
    "categoria": "{categoria}",
    "ground_truth": {{
        "respuesta_ideal": "2-3 frases describiendo qué información busca el usuario",
        "resultados_clasificados": [
            {{
                "dataset_id": "id del dataset",
                "title": "título completo",
                "relevancia": "relevante" | "no_relevante",
                "razon": "explicación de 1 frase por qué es relevante o no"
            }}
        ],
        "patrones_palabras_clave": ["lista de palabras/frases que indican relevancia"],
        "criterios_evaluacion": {{
            "debe_contener": ["conceptos que un resultado relevante DEBE mencionar"],
            "no_debe_contener": ["conceptos que NO son relevantes"],
            "minimo_relevantes_en_top5": 3
        }}
    }}
}}

Importante:
- Responde SÓLO el JSON, sin texto adicional
- Sé generoso con la relevancia: si un resultado tiene relación aunque no sea perfecto, márcalo como relevante
- Los patrones de palabras clave deben ser específicos pero no demasiado estrechos
"""


def buscar_datasets_api(query: str, top_k: int = 10) -> list[dict]:
    """Busca datasets usando la API real."""
    try:
        response = requests.post(
            f"{API_URL}/search",
            json={"query": query, "top_k": top_k},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if "results" in data:
            return data["results"]
        elif isinstance(data, list):
            return data
        else:
            print(f"⚠️  Respuesta inesperada: {data}")
            return []
    except Exception as e:
        print(f"❌ Error en búsqueda: {e}")
        return []


def generar_ground_truth_real(query_data: dict, resultados: list[dict], modelo: str = "deepseek-v4.1-flash:cloud", max_retries: int = 2) -> dict:
    """
    Genera ground truth basado en resultados reales.

    Returns:
        dict con query original + ground_truth basado en resultados reales, o None si falla tras retries
    """
    # Formatear resultados para el prompt (solo títulos, más corto)
    resultados_json = "\n".join([
        f"{i+1}. {r.get('title', 'N/A')[:150]}"  # Truncar títulos largos
        for i, r in enumerate(resultados)
    ])

    prompt = PROMPT_CLASIFICAR_RELEVANCIA.format(
        query=query_data["query"],
        categoria=query_data["categoria"],
        descripcion=query_data["descripcion"],
        resultados_json=resultados_json
    )

    for intento in range(max_retries + 1):
        try:
            response = ollama.chat(model=modelo, messages=[
                {"role": "system", "content": "Eres un experto en evaluación de buscadores. Responde SÓLO con JSON válido."},
                {"role": "user", "content": prompt}
            ])

            texto = response["message"]["content"].strip()

            # Limpiar markdown
            if texto.startswith("```json"):
                texto = texto[7:]
            if texto.endswith("```"):
                texto = texto[:-3]
            texto = texto.strip()

            ground_truth = json.loads(texto)

            # Merge con datos originales
            result = {**query_data, "ground_truth": ground_truth["ground_truth"], "resultados_reales": resultados}
            return result

        except (json.JSONDecodeError, KeyError) as e:
            if intento < max_retries:
                print(f"⚠️  Reintentando (error JSON: {e})...", end=" ", flush=True)
            else:
                print(f"❌ Falló tras {max_retries + 1} intentos")
                return None


def main():
    parser = argparse.ArgumentParser(description="Generar ground truth basado en resultados reales")
    parser.add_argument("--input", "-i", type=str, default="../entregables/dataset_evaluacion.jsonl")
    parser.add_argument("--output", "-o", type=str, default="../entregables/ground_truth_real.jsonl")
    parser.add_argument("--model", "-m", type=str, default="deepseek-v4.1-flash:cloud")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Límite para testing")
    parser.add_argument("--resume", "-r", action="store_true", help="Reanudar desde archivo existente")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Cargar queries
    print(f"📖 Cargando queries desde {input_path}...")
    queries = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line))

    if args.limit:
        queries = queries[:args.limit]
        print(f"   Limitado a {len(queries)} queries")

    # Reanudar si existe
    procesados = []
    if args.resume and output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    procesados.append(json.loads(line))
        print(f"🔄 Reanudando: {len(procesados)} queries ya procesadas")
        ids_procesados = {p["id"] for p in procesados}
        queries = [q for q in queries if q["id"] not in ids_procesados]

    if not queries:
        print("✅ No hay queries pendientes")
        return

    # Verificar API
    print(f"\n🔌 Verificando API en {API_URL}...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ API disponible")
        else:
            print(f"   ❌ API respondió {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"   ❌ Error conectando a API: {e}")
        sys.exit(1)

    # Generar ground truth
    print(f"\n🤖 Generando ground truth basado en resultados reales...")

    with open(output_path, "a", encoding="utf-8") as out_f:
        for i, query in enumerate(queries, 1):
            print(f"   [{i}/{len(queries)}] {query['id']}: {query['query'][:50]}...", end=" ", flush=True)

            # Buscar en API real
            resultados = buscar_datasets_api(query["query"], top_k=10)

            if not resultados:
                print(f"❌ Sin resultados")
                continue

            print(f"({len(resultados)} resultados)", end=" ", flush=True)

            # Generar ground truth con LLM
            gt = generar_ground_truth_real(query, resultados, args.model)

            if gt:
                out_f.write(json.dumps(gt, ensure_ascii=False) + "\n")
                out_f.flush()
                print("✅")
            else:
                print("❌ Falló generación")

    print(f"\n✅ Completado: {len(queries)} queries procesadas")
    print(f"📊 Archivo: {output_path}")


if __name__ == "__main__":
    main()
