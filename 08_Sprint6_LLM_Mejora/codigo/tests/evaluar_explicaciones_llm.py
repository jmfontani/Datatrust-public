#!/usr/bin/env python3
"""
Evaluación Humana de Explicaciones LLM
======================================

Herramienta para evaluar la calidad de las explicaciones generadas
por el LLM en el sistema de re-ranking.

Genera un cuestionario interactivo donde el evaluador humano puntúa:
- Relevancia: ¿La explicación justifica correctamente la relevancia?
- Precisión: ¿Los datos mencionados son correctos?
- Utilidad: ¿Ayuda al usuario a entender por qué es relevante?
- Coherencia: ¿Tiene sentido la explicación con el dataset?

Uso:
    # 1. Activar entorno virtual (OBLIGATORIO)
    source ~/datos/PFM/Datatrust/venv/bin/activate

    # 2. Ejecutar script
    cd ~/datos/PFM/Datatrust/08_Sprint6_LLM_Mejora/codigo/tests
    python3 evaluar_explicaciones_llm.py

Requiere:
    - Entorno virtual activado (source venv/bin/activate)
    - API del buscador corriendo (para generar explicaciones nuevas)
    - Ollama disponible

Salida:
    - resultados/evaluacion_explicaciones_YYYY-MM-DD.json
    - resultados/evaluacion_explicaciones_YYYY-MM-DD.csv
    - Métricas agregadas en consola
"""

import json
import csv
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import random

# Añadir rutas necesarias
sys.path.insert(0, str(Path(__file__).parent / "resultados"))
sys.path.insert(0, str(Path(__file__).parent.parent / "motor"))
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuración
API_URL = "http://localhost:8000"
RESULTS_DIR = Path(__file__).parent / "resultados"


class ExplanationEvaluator:
    """Sistema de evaluación humana de explicaciones LLM."""

    def __init__(self):
        self.evaluaciones = []
        self.timestamp = datetime.now().isoformat()
        self.evaluator_name = input("👤 Introduce tu nombre/evaluador: ").strip() or "anonimo"

    def cargar_resultados_test(self) -> List[Dict]:
        """Carga los resultados del test comparativo v07 vs v08."""
        archivo = RESULTS_DIR / "test_v07_vs_v08_20queries_2025-05-26.json"

        if not archivo.exists():
            print(f"❌ No se encuentra {archivo}")
            return []

        with open(archivo) as f:
            data = json.load(f)

        # Extraer pares query-resultado
        casos = []
        for resultado in data.get("results", []):
            query = resultado["query"]
            categoria = resultado["categoria"]

            # Para cada resultado v08, crear un caso de evaluación
            for r in resultado.get("v08_results", [])[:5]:  # Top 5 de cada query
                casos.append({
                    "query": query,
                    "categoria": categoria,
                    "dataset_id": r["dataset_id"],
                    "title": r["title"],
                    "publisher": r.get("publisher", "N/A"),
                    "rank": r["rank"],
                    "score": r.get("score", 0)
                })

        return casos

    def generar_explicacion(self, query: str, dataset_id: str) -> Optional[Dict]:
        """Genera explicación usando el endpoint /llm/search/rerank.

        Nota: El endpoint /llm/search/explain no está cargado en la API.
        Las explicaciones vienen junto con el re-ranking.
        """
        try:
            # Llamar al endpoint de re-ranking (que incluye explicaciones)
            resp = requests.post(
                f"{API_URL}/llm/search/rerank",
                json={
                    "query": query,
                    "limit": 10,
                    "rerank_top_n": 15,
                    "use_llm": True
                },
                timeout=120,
                verify=False
            )
            resp.raise_for_status()
            data = resp.json()

            # Buscar el dataset en los resultados
            for r in data.get("results", []):
                if r["dataset_id"] == dataset_id:
                    return {
                        "explanation": r.get("explanation", "No hay explicación"),
                        "factors": [
                            {"factor": "Relevancia temática", "score": r.get("llm_relevance_score", 0) / 10,
                             "description": "Basado en re-ranking LLM"}
                        ],
                        "llm_relevance_score": r.get("llm_relevance_score", 0)
                    }

            # Si no se encontró el dataset específico
            return {
                "explanation": "Dataset no encontrado en Top 15 de re-ranking",
                "factors": [],
                "llm_relevance_score": 0
            }
        except Exception as e:
            print(f"   ⚠️  Error generando explicación: {e}")
            return None

    def mostrar_caso(self, caso: Dict, explicacion: Dict) -> None:
        """Muestra un caso de evaluación formateado."""
        print("\n" + "=" * 80)
        print(f"📊 QUERY: {caso['query']}")
        print(f"📁 DATASET: {caso['title'][:70]}...")
        print(f"🏛️  PUBLISHER: {caso['publisher']}")
        print(f"📈 RANK: #{caso['rank']} | Score: {caso['score']:.2f}")
        print(f"🏷️  CATEGORÍA: {caso['categoria']}")
        print("-" * 80)
        print("🤖 EXPLICACIÓN DEL LLM:")
        print(f"   {explicacion.get('explanation', 'No disponible')}")

        if explicacion.get('factors'):
            print("\n   Factores de relevancia:")
            for f in explicacion['factors']:
                print(f"   • {f['factor']}: {f['score']:.2f} - {f['description']}")
        print("=" * 80)

    def solicitar_puntuacion(self, dimension: str, descripcion: str, min_val: int = 1, max_val: int = 5) -> int:
        """Solicita una puntuación al evaluador humano."""
        while True:
            try:
                print(f"\n📋 {dimension}")
                print(f"   {descripcion}")
                val = input(f"   Puntuación ({min_val}-{max_val}, Enter=NS/NC): ").strip()

                if not val:
                    return -1  # No sabe/No contesta

                val = int(val)
                if min_val <= val <= max_val:
                    return val
                else:
                    print(f"   ⚠️  Debe ser entre {min_val} y {max_val}")
            except ValueError:
                print("   ⚠️  Introduce un número válido")

    def solicitar_comentario(self) -> str:
        """Solicita comentario opcional."""
        comentario = input("\n💬 Comentario opcional (Enter para saltar): ").strip()
        return comentario

    def evaluar_caso(self, caso: Dict) -> Optional[Dict]:
        """Realiza la evaluación de un caso específico."""
        # Generar explicación
        print(f"\n🔍 Generando explicación para: {caso['dataset_id'][:50]}...")
        explicacion = self.generar_explicacion(caso["query"], caso["dataset_id"])

        if not explicacion:
            print("   ❌ No se pudo generar explicación. Saltando...")
            return None

        # Mostrar caso
        self.mostrar_caso(caso, explicacion)

        # Solicitar evaluación
        print("\n" + "📝 EVALUACIÓN (1=Muy malo, 5=Excelente, Enter=NS/NC)")
        print("-" * 80)

        evaluacion = {
            "timestamp": datetime.now().isoformat(),
            "evaluador": self.evaluator_name,
            "query": caso["query"],
            "categoria": caso["categoria"],
            "dataset_id": caso["dataset_id"],
            "dataset_title": caso["title"],
            "dataset_publisher": caso["publisher"],
            "rank": caso["rank"],
            "score": caso["score"],
            "explicacion_llm": explicacion.get("explanation", ""),
            "explicacion_factores": explicacion.get("factors", []),
            "puntuaciones": {}
        }

        # Dimensiones de evaluación
        dimensiones = [
            ("relevancia", "¿La explicación justifica correctamente por qué el dataset es relevante para la query?"),
            ("precision", "¿Los datos/facts mencionados en la explicación son correctos según el dataset?"),
            ("utilidad", "¿Esta explicación ayudaría a un usuario a entender por qué este resultado es relevante?"),
            ("coherencia", "¿La explicación tiene sentido y está bien escrita?"),
            ("justificacion_score", "¿El score asignado por el LLM corresponde con la explicación dada?")
        ]

        for dim_key, dim_desc in dimensiones:
            puntuacion = self.solicitar_puntuacion(dim_key.upper(), dim_desc)
            evaluacion["puntuaciones"][dim_key] = puntuacion

        evaluacion["comentario"] = self.solicitar_comentario()

        return evaluacion

    def calcular_metricas_agregadas(self) -> Dict:
        """Calcula métricas agregadas de todas las evaluaciones."""
        if not self.evaluaciones:
            return {}

        # Agrupar por dimensión
        dimensiones = ["relevancia", "precision", "utilidad", "coherencia", "justificacion_score"]
        metricas = {}

        for dim in dimensiones:
            valores = [e["puntuaciones"].get(dim, -1) for e in self.evaluaciones]
            valores_validos = [v for v in valores if v > 0]

            if valores_validos:
                metricas[dim] = {
                    "media": sum(valores_validos) / len(valores_validos),
                    "mediana": sorted(valores_validos)[len(valores_validos)//2],
                    "min": min(valores_validos),
                    "max": max(valores_validos),
                    "n": len(valores_validos)
                }
            else:
                metricas[dim] = {"media": 0, "n": 0}

        # Calcular score global
        all_scores = []
        for e in self.evaluaciones:
            scores = [v for v in e["puntuaciones"].values() if v > 0]
            if scores:
                all_scores.extend(scores)

        metricas["global"] = {
            "media": sum(all_scores) / len(all_scores) if all_scores else 0,
            "n_total_respuestas": len(all_scores),
            "n_casos_evaluados": len(self.evaluaciones)
        }

        # Por categoría
        categorias = {}
        for cat in set(e["categoria"] for e in self.evaluaciones):
            cat_evals = [e for e in self.evaluaciones if e["categoria"] == cat]
            cat_scores = []
            for e in cat_evals:
                scores = [v for v in e["puntuaciones"].values() if v > 0]
                cat_scores.extend(scores)

            if cat_scores:
                categorias[cat] = {
                    "media": sum(cat_scores) / len(cat_scores),
                    "n": len(cat_evals)
                }

        metricas["por_categoria"] = categorias

        return metricas

    def guardar_resultados(self) -> None:
        """Guarda las evaluaciones en JSON y CSV."""
        if not self.evaluaciones:
            print("❌ No hay evaluaciones para guardar")
            return

        fecha = datetime.now().strftime("%Y-%m-%d_%H%M%S")

        # Guardar JSON completo
        archivo_json = RESULTS_DIR / f"evaluacion_explicaciones_{fecha}.json"
        with open(archivo_json, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "evaluador": self.evaluator_name,
                    "timestamp": self.timestamp,
                    "n_casos": len(self.evaluaciones),
                    "version": "1.0"
                },
                "metricas_agregadas": self.calcular_metricas_agregadas(),
                "evaluaciones": self.evaluaciones
            }, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Guardado JSON: {archivo_json}")

        # Guardar CSV resumido
        archivo_csv = RESULTS_DIR / f"evaluacion_explicaciones_{fecha}.csv"
        with open(archivo_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                "timestamp", "evaluador", "query", "categoria", "dataset_id",
                "dataset_title", "rank", "score", "explicacion_llm",
                "p_relevancia", "p_precision", "p_utilidad", "p_coherencia",
                "p_justificacion", "comentario"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for e in self.evaluaciones:
                writer.writerow({
                    "timestamp": e["timestamp"],
                    "evaluador": e["evaluador"],
                    "query": e["query"],
                    "categoria": e["categoria"],
                    "dataset_id": e["dataset_id"],
                    "dataset_title": e["dataset_title"][:100],
                    "rank": e["rank"],
                    "score": e["score"],
                    "explicacion_llm": e["explicacion_llm"][:200],
                    "p_relevancia": e["puntuaciones"].get("relevancia", -1),
                    "p_precision": e["puntuaciones"].get("precision", -1),
                    "p_utilidad": e["puntuaciones"].get("utilidad", -1),
                    "p_coherencia": e["puntuaciones"].get("coherencia", -1),
                    "p_justificacion": e["puntuaciones"].get("justificacion_score", -1),
                    "comentario": e.get("comentario", "")
                })

        print(f"💾 Guardado CSV: {archivo_csv}")

    def mostrar_resumen(self) -> None:
        """Muestra resumen de evaluaciones."""
        metricas = self.calcular_metricas_agregadas()

        print("\n" + "=" * 80)
        print("📊 RESUMEN DE EVALUACIÓN")
        print("=" * 80)

        global_data = metricas.get("global", {})
        print(f"\n🎯 SCORE GLOBAL: {global_data.get('media', 0):.2f}/5.0")
        print(f"   Casos evaluados: {global_data.get('n_casos_evaluados', 0)}")
        print(f"   Total respuestas: {global_data.get('n_total_respuestas', 0)}")

        print("\n📈 Por dimensión:")
        for dim in ["relevancia", "precision", "utilidad", "coherencia", "justificacion_score"]:
            if dim in metricas:
                m = metricas[dim]
                print(f"   {dim:20s}: {m.get('media', 0):.2f}/5.0 (n={m.get('n', 0)})")

        print("\n📊 Por categoría de query:")
        for cat, data in metricas.get("por_categoria", {}).items():
            print(f"   {cat:20s}: {data.get('media', 0):.2f}/5.0 (n={data.get('n', 0)})")

        print("=" * 80)

    def run(self, max_casos: int = 10) -> None:
        """Ejecuta el flujo completo de evaluación."""
        print("\n" + "=" * 80)
        print("🎯 EVALUACIÓN DE EXPLICACIONES LLM")
        print("=" * 80)
        print("\nEste cuestionario evalúa la calidad de las explicaciones")
        print("generadas por el LLM para justificar el re-ranking.")
        print(f"\nSe evaluarán hasta {max_casos} casos aleatorios.")
        print("Para cada caso, puntúa del 1 (muy malo) al 5 (excelente).")
        print("\nComandos especiales:")
        print("  'q' = salir y guardar")
        print("  's' = saltar caso")
        print("  Enter sin número = NS/NC")
        print("=" * 80)

        # Cargar casos
        casos = self.cargar_resultados_test()
        if not casos:
            print("❌ No se pudieron cargar casos de evaluación")
            return

        # Mezclar aleatoriamente
        random.shuffle(casos)

        # Evaluar casos
        for i, caso in enumerate(casos[:max_casos], 1):
            print(f"\n\n📌 CASO {i}/{min(max_casos, len(casos))}")

            evaluacion = self.evaluar_caso(caso)
            if evaluacion:
                self.evaluaciones.append(evaluacion)
                print(f"✅ Evaluación guardada ({len(self.evaluaciones)} total)")

            # Preguntar si continuar
            if i < max_casos and i < len(casos):
                cont = input("\n➡️  Continuar? (s/n/q): ").strip().lower()
                if cont == 'q':
                    break
                elif cont == 'n':
                    break

        # Guardar y mostrar resumen
        if self.evaluaciones:
            self.guardar_resultados()
            self.mostrar_resumen()
        else:
            print("\n❌ No se realizaron evaluaciones")


class EvaluacionBatch:
    """Evaluación automática de explicaciones sin interacción humana."""

    def __init__(self):
        self.resultados = []

    def analizar_explicaciones_existentes(self) -> Dict:
        """Analiza explicaciones ya generadas en tests anteriores."""
        # Buscar archivos de test que contengan explicaciones
        archivos = list(RESULTS_DIR.glob("test_*.json"))

        analisis = {
            "archivos_encontrados": len(archivos),
            "explicaciones_extraidas": 0,
            "longitud_promedio": 0,
            "factores_comunes": {}
        }

        longitudes = []

        for archivo in archivos:
            try:
                with open(archivo) as f:
                    data = json.load(f)

                # Extraer explicaciones si existen
                for resultado in data.get("results", []):
                    for r in resultado.get("v08_results", []):
                        if "explanation" in r:
                            longitudes.append(len(r["explanation"]))
                            analisis["explicaciones_extraidas"] += 1
            except:
                continue

        if longitudes:
            analisis["longitud_promedio"] = sum(longitudes) / len(longitudes)
            analisis["longitud_min"] = min(longitudes)
            analisis["longitud_max"] = max(longitudes)

        return analisis


def main():
    """Función principal."""
    print("\n" + "=" * 80)
    print("🤖 EVALUACIÓN DE EXPLICACIONES LLM")
    print("=" * 80)
    print("\n1. EVALUACIÓN HUMANA INTERACTIVA")
    print("   Evalúa casos reales con explicaciones del LLM")
    print("\n2. ANÁLISIS DE EXPLICACIONES EXISTENTES")
    print("   Analiza explicaciones ya generadas en tests")
    print("\n3. GENERAR CASOS DE EVALUACIÓN")
    print("   Crea nuevas explicaciones para datasets del test")

    opcion = input("\nSelecciona opción (1/2/3): ").strip()

    if opcion == "1":
        evaluator = ExplanationEvaluator()
        max_casos = input("\n¿Cuántos casos evaluar? (default: 10): ").strip()
        evaluator.run(max_casos=int(max_casos) if max_casos else 10)

    elif opcion == "2":
        batch = EvaluacionBatch()
        analisis = batch.analizar_explicaciones_existentes()
        print("\n📊 ANÁLISIS DE EXPLICACIONES EXISTENTES:")
        print(json.dumps(analisis, indent=2))

    elif opcion == "3":
        print("\n⚙️ Generando casos de evaluación...")
        evaluator = ExplanationEvaluator()
        casos = evaluator.cargar_resultados_test()

        if casos:
            print(f"Se cargaron {len(casos)} casos del test v07 vs v08")
            print("\nPara evaluar estos casos, ejecuta la opción 1.")
            print(f"Ubicación: {RESULTS_DIR}")

    else:
        print("❌ Opción no válida")


if __name__ == "__main__":
    main()
