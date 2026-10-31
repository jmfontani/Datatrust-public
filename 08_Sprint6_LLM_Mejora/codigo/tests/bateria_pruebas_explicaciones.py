#!/usr/bin/env python3
"""
Batería de Pruebas - Evaluación de Explicaciones LLM
====================================================

Ejecuta automáticamente una batería de casos de prueba y genera
un archivo de resultados para evaluación humana.

Uso:
    # 1. Activar entorno virtual (OBLIGATORIO)
    source ~/datos/PFM/Datatrust/venv/bin/activate

    # 2. Ejecutar batería
    cd ~/datos/PFM/Datatrust/08_Sprint6_LLM_Mejora/codigo/tests
    python3 bateria_pruebas_explicaciones.py

Salida:
    - resultados/bateria_pruebas_YYYY-MM-DD_HHMMSS.json (datos completos)
    - resultados/bateria_pruebas_YYYY-MM-DD_HHMMSS_para_evaluar.csv (para ti)

El archivo CSV incluye columnas vacías para tu evaluación:
    - puntuacion_1_5: Tu puntuación (1=muy mala, 5=excelente)
    - comentario: Tu feedback opcional
"""

import json
import csv
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import time

sys.path.insert(0, str(Path(__file__).parent))

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuración
API_URL = "http://localhost:8000"
RESULTS_DIR = Path(__file__).parent / "resultados"


class BateriaPruebasExplicaciones:
    """Genera una batería de pruebas para evaluar explicaciones del LLM."""

    # Casos de prueba predefinidos (query + dataset esperado)
    CASOS_PRUEBA = [
        {
            "id": "S1",
            "categoria": "sinonimia",
            "query": "paro juvenil desempleo jóvenes",
            "descripcion": "Query con sinónimos (paro/desempleo, juvenil/jóvenes)"
        },
        {
            "id": "S2",
            "categoria": "sinonimia",
            "query": "renta ingresos salarios",
            "descripcion": "Sinónimos económicos"
        },
        {
            "id": "C1",
            "categoria": "conceptual",
            "query": "vulnerabilidad económica juventud",
            "descripcion": "Concepto abstracto que requiere interpretación"
        },
        {
            "id": "C2",
            "categoria": "conceptual",
            "query": "sostenibilidad urbana",
            "descripcion": "Concepto multidimensional"
        },
        {
            "id": "T1",
            "categoria": "territorial",
            "query": "turismo Canarias 2023",
            "descripcion": "Query con ubicación y temporalidad"
        },
        {
            "id": "T2",
            "categoria": "territorial",
            "query": "tráfico Madrid centro",
            "descripcion": "Ubicación específica"
        },
        {
            "id": "TM1",
            "categoria": "temporal",
            "query": "emisiones CO2 2022 2023",
            "descripcion": "Rango temporal explícito"
        },
        {
            "id": "TM2",
            "categoria": "temporal",
            "query": "calidad aire Madrid 2023",
            "descripcion": "Año específico"
        },
        {
            "id": "F1",
            "categoria": "facetada",
            "query": "datasets medio ambiente Canarias",
            "descripcion": "Tema + ubicación"
        },
        {
            "id": "M1",
            "categoria": "metadatos",
            "query": "padrón municipal completo",
            "descripcion": "Tipo específico de dataset"
        }
    ]

    def __init__(self):
        self.resultados = []
        self.timestamp = datetime.now()

    def buscar_con_llm(self, query: str, limit: int = 3) -> Optional[Dict]:
        """Ejecuta búsqueda con LLM y devuelve resultados con explicaciones."""
        try:
            resp = requests.post(
                f"{API_URL}/llm/search/rerank",
                json={
                    "query": query,
                    "limit": limit,
                    "rerank_top_n": 15,
                    "use_llm": True
                },
                timeout=120,
                verify=False
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"   ❌ Error en búsqueda: {e}")
            return None

    def ejecutar_prueba(self, caso: Dict) -> List[Dict]:
        """Ejecuta una prueba individual y devuelve resultados."""
        print(f"\n🔍 Caso {caso['id']}: {caso['query']}")
        print(f"   Categoría: {caso['categoria']}")
        print(f"   {caso['descripcion']}")
        print("   ⏳ Consultando API...")

        inicio = time.time()
        data = self.buscar_con_llm(caso['query'])
        tiempo = time.time() - inicio

        if not data:
            print("   ⚠️  Sin resultados")
            return []

        print(f"   ✅ {len(data['results'])} resultados en {tiempo:.1f}s")

        resultados_caso = []
        for i, r in enumerate(data['results'], 1):
            resultado = {
                "caso_id": caso['id'],
                "categoria": caso['categoria'],
                "query": caso['query'],
                "descripcion_caso": caso['descripcion'],
                "posicion": i,
                "dataset_id": r['dataset_id'],
                "dataset_titulo": r['title'],
                "dataset_publisher": r.get('publisher', 'N/A'),
                "dataset_descripcion": r.get('description', 'N/A')[:200],
                "score_llm": r.get('llm_relevance_score', 0),
                "rank_original": r.get('original_rank', i),
                "rank_nuevo": r.get('new_rank', i),
                "explicacion": r.get('explanation', 'No disponible'),
                "tiempo_respuesta": round(tiempo, 2),
                "modelo": data.get('metadata', {}).get('model', 'unknown'),
                "timestamp": datetime.now().isoformat()
            }
            resultados_caso.append(resultado)

        return resultados_caso

    def ejecutar_bateria(self) -> None:
        """Ejecuta toda la batería de pruebas."""
        print("=" * 80)
        print("🔬 BATERÍA DE PRUEBAS - EXPLICACIONES LLM")
        print("=" * 80)
        print(f"\nEjecutando {len(self.CASOS_PRUEBA)} casos de prueba...")
        print("Cada caso devuelve Top 3 resultados con explicaciones.")
        print("=" * 80)

        for caso in self.CASOS_PRUEBA:
            resultados = self.ejecutar_prueba(caso)
            self.resultados.extend(resultados)

        print("\n" + "=" * 80)
        print(f"✅ Batería completada: {len(self.resultados)} resultados totales")
        print("=" * 80)

    def guardar_resultados_json(self) -> Path:
        """Guarda resultados completos en JSON."""
        fecha = self.timestamp.strftime("%Y-%m-%d_%H%M%S")
        archivo = RESULTS_DIR / f"bateria_pruebas_{fecha}.json"

        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "fecha": self.timestamp.isoformat(),
                    "n_casos": len(self.CASOS_PRUEBA),
                    "n_resultados": len(self.resultados),
                    "api_url": API_URL
                },
                "resultados": self.resultados
            }, f, indent=2, ensure_ascii=False)

        return archivo

    def generar_csv_para_evaluacion(self) -> Path:
        """Genera CSV con columnas para evaluación manual."""
        fecha = self.timestamp.strftime("%Y-%m-%d_%H%M%S")
        archivo = RESULTS_DIR / f"bateria_pruebas_{fecha}_para_evaluar.csv"

        with open(archivo, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                "id_fila", "caso_id", "categoria", "query",
                "posicion", "dataset_titulo", "dataset_publisher",
                "score_llm", "explicacion",
                "puntuacion_1_5", "comentario"  # Columnas para completar
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for i, r in enumerate(self.resultados, 1):
                writer.writerow({
                    "id_fila": i,
                    "caso_id": r['caso_id'],
                    "categoria": r['categoria'],
                    "query": r['query'],
                    "posicion": r['posicion'],
                    "dataset_titulo": r['dataset_titulo'][:80],
                    "dataset_publisher": r['dataset_publisher'][:50],
                    "score_llm": r['score_llm'],
                    "explicacion": r['explicacion'],
                    "puntuacion_1_5": "",  # Vacío para completar
                    "comentario": ""       # Vacío para completar
                })

        return archivo

    def generar_resumen_visual(self) -> None:
        """Muestra resumen en consola."""
        print("\n" + "=" * 80)
        print("📊 RESUMEN DE LA BATERÍA")
        print("=" * 80)

        # Por categoría
        categorias = {}
        for r in self.resultados:
            cat = r['categoria']
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append(r)

        print("\n📈 Resultados por categoría:")
        for cat, items in categorias.items():
            scores = [r['score_llm'] for r in items]
            media = sum(scores) / len(scores) if scores else 0
            print(f"   {cat:15s}: {len(items):2d} resultados | Score medio: {media:.1f}/10")

        print("\n⏱️  Tiempos de respuesta:")
        tiempos = [r['tiempo_respuesta'] for r in self.resultados]
        if tiempos:
            print(f"   Media: {sum(tiempos)/len(tiempos):.1f}s")
            print(f"   Mín: {min(tiempos):.1f}s | Máx: {max(tiempos):.1f}s")

        print("\n📋 Ejemplos de explicaciones generadas:")
        for r in self.resultados[:3]:
            print(f"\n   [{r['caso_id']}] {r['query']}")
            print(f"   Explicación: \"{r['explicacion'][:100]}...\"")

    def run(self) -> None:
        """Ejecuta todo el flujo de la batería."""
        self.ejecutar_bateria()

        # Guardar archivos
        json_file = self.guardar_resultados_json()
        csv_file = self.generar_csv_para_evaluacion()

        self.generar_resumen_visual()

        print("\n" + "=" * 80)
        print("💾 ARCHIVOS GENERADOS")
        print("=" * 80)
        print(f"\n1. Datos completos (JSON):")
        print(f"   {json_file}")
        print(f"\n2. PARA TU EVALUACIÓN (CSV):")
        print(f"   {csv_file}")
        print("\n" + "=" * 80)
        print("📋 INSTRUCCIONES PARA EVALUAR:")
        print("=" * 80)
        print("""
1. Abre el archivo CSV con Excel/LibreOffice/VSCode
2. Para cada fila, completa:
   - puntuacion_1_5: Tu puntuación (1=muy mala, 3=aceptable, 5=excelente)
   - comentario: Tu feedback (opcional)

3. Guarda el archivo como: bateria_pruebas_EVALUADO.csv

4. Envíame el archivo CSV evaluado y generaré el informe de resultados.

💡 Criterios de evaluación:
   1 = Explicación incorrecta o irrelevante
   2 = Poco relevante, generica o confusa
   3 = Aceptable, correcta pero genérica
   4 = Buena, específica y útil
   5 = Excelente, muy específica y valiosa
        """)
        print("=" * 80)


def main(skip_confirm=False):
    """Función principal."""
    print("\n" + "=" * 80)
    print("🤖 BATERÍA DE PRUEBAS - EXPLICACIONES LLM")
    print("=" * 80)
    print("\n⚠️  Asegúrate de tener:")
    print("   ✅ API corriendo en localhost:8000")
    print("   ✅ Ollama disponible con modelos cargados")
    print("   ✅ Entorno virtual activado")
    print("\n" + "=" * 80)

    if not skip_confirm:
        confirmar = input("\n¿Continuar? (s/n): ").strip().lower()
        if confirmar != 's':
            print("❌ Cancelado")
            return
    else:
        print("\n⚡ Modo automático activado (sin confirmación)")

    bateria = BateriaPruebasExplicaciones()
    bateria.run()

    print("\n✅ ¡Batería completada! Revisa el archivo CSV para evaluar.")


if __name__ == "__main__":
    import sys
    skip = "--auto" in sys.argv
    main(skip_confirm=skip)
