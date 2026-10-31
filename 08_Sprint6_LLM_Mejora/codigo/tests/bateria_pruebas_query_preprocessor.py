#!/usr/bin/env python3
"""
Batería de Pruebas Comparativa - Query Preprocessor (#3, #4, #12)
===============================================================

Compara búsqueda NORMAL vs MEJORADA con pre-procesamiento LLM.

Uso:
    source ~/datos/PFM/Datatrust/venv/bin/activate
    python3 bateria_pruebas_query_preprocessor.py

Salida:
    - resultados/bateria_query_preprocessor_YYYY-MM-DD_HHMMSS.csv
    - Consola con resumen comparativo
"""

import json
import csv
import sys
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "motor"))

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from query_preprocessor import QueryPreprocessor

API_URL = "http://localhost:8000"
RESULTS_DIR = Path(__file__).parent / "resultados"

# Casos de prueba diseñados para evaluar expansión semántica
CASOS_PRUEBA = [
    {
        "id": "T1",
        "categoria": "temporalidad_explicita",
        "query": "paro en 2022",
        "descripcion": "Query con año explícito - debería expandir a rangos temporales"
    },
    {
        "id": "C1",
        "categoria": "conceptual_abstracto",
        "query": "vulnerabilidad económica",
        "descripcion": "Concepto abstracto - debería expandir a términos relacionados (AROPE, pobreza)"
    },
    {
        "id": "G1",
        "categoria": "geografico_explicito",
        "query": "turismo Barcelona",
        "descripcion": "Lugar específico - debería expandir a variantes territoriales"
    },
    {
        "id": "A1",
        "categoria": "ambiguo",
        "query": "banco España",
        "descripcion": "Término ambiguo - validar que entiende contexto (financiero vs mueble)"
    },
    {
        "id": "S1",
        "categoria": "siglas_tecnicas",
        "query": "EPA jóvenes",
        "descripcion": "Siglas técnicas - debería expandir a nombre completo y relacionados"
    },
    {
        "id": "D1",
        "categoria": "demografico_edad",
        "query": "población mayor 65 años",
        "descripcion": "Rango de edad - debería expandir a términos demográficos"
    },
    {
        "id": "I1",
        "categoria": "indicador_economico",
        "query": "PIB per cápita",
        "descripcion": "Indicador económico - debería expandir a variantes (renta, ingresos)"
    },
    {
        "id": "E1",
        "categoria": "educacion",
        "query": "tasa abandono escolar",
        "descripcion": "Tema educativo - debería expandir a terminología sectorial"
    },
]


def buscar_normal(query: str, limit: int = 10) -> Tuple[List[Dict], float, float]:
    """
    Búsqueda normal sin pre-procesamiento.

    Returns:
        (resultados, tiempo_ms, total_hits)
    """
    try:
        inicio = time.time()
        resp = requests.post(
            f"{API_URL}/search",
            json={"query": query, "limit": limit},
            timeout=30,
            verify=False
        )
        tiempo = (time.time() - inicio) * 1000
        resp.raise_for_status()
        data = resp.json()

        return (
            data.get("results", []),
            tiempo,
            data.get("total_results", 0)
        )
    except Exception as e:
        print(f"   ❌ Error en búsqueda normal: {e}")
        return [], 0, 0


def buscar_mejorada(query: str, preprocessor: QueryPreprocessor, limit: int = 10) -> Tuple[List[Dict], Dict, float, float]:
    """
    Búsqueda mejorada con pre-procesamiento.

    Returns:
        (resultados, metadata_expansion, tiempo_total_ms, total_hits)
    """
    try:
        # Pre-procesar
        inicio = time.time()
        preprocessed = preprocessor.process(query, apply_strict_filters=False)

        if not preprocessed.validation.is_valid:
            return [], {"error": "Query inválida"}, 0, 0

        query_expandida = preprocessed.expansion.query_expandida

        # Buscar con query expandida
        resp = requests.post(
            f"{API_URL}/search",
            json={"query": query_expandida, "limit": limit},
            timeout=30,
            verify=False
        )
        tiempo = (time.time() - inicio) * 1000
        resp.raise_for_status()
        data = resp.json()

        metadata = {
            "query_original": query,
            "query_expandida": query_expandida,
            "temas": preprocessed.structure.temas,
            "territorio": preprocessed.structure.territorio,
            "años": preprocessed.structure.años,
            "conceptos_implicitos": preprocessed.structure.conceptos_implicitos,
            "terminos_añadidos": preprocessed.expansion.terminos_añadidos,
            "duracion_preprocesamiento_ms": preprocessed.metadata.get("duration_ms", 0)
        }

        return (
            data.get("results", []),
            metadata,
            tiempo,
            data.get("total_results", 0)
        )
    except Exception as e:
        print(f"   ❌ Error en búsqueda mejorada: {e}")
        return [], {"error": str(e)}, 0, 0


def analizar_overlap(resultados_normal: List[Dict], resultados_mejorada: List[Dict]) -> Dict:
    """
    Analiza el overlap entre resultados normal y mejorada.

    Returns:
        Dict con métricas de overlap
    """
    ids_normal = {r.get("id", r.get("dataset_id", "")) for r in resultados_normal}
    ids_mejorada = {r.get("id", r.get("dataset_id", "")) for r in resultados_mejorada}

    ids_comunes = ids_normal & ids_mejorada
    ids_solo_mejorada = ids_mejorada - ids_normal
    ids_solo_normal = ids_normal - ids_mejorada

    return {
        "comunes": len(ids_comunes),
        "solo_mejorada": len(ids_solo_mejorada),
        "solo_normal": len(ids_solo_normal),
        "ids_comunes_lista": list(ids_comunes)[:5],
        "ids_solo_mejorada_lista": list(ids_solo_mejorada)[:5]
    }


def main():
    print("=" * 80)
    print("🔬 BATERÍA DE PRUEBAS - Query Preprocessor (#3, #4, #12)")
    print("=" * 80)
    print("\nComparación: Búsqueda NORMAL vs MEJORADA con expansión semántica")
    print("=" * 80)

    # Verificar API
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5, verify=False)
        if resp.status_code == 200:
            print("✅ API disponible")
        else:
            print(f"⚠️  API responde con código {resp.status_code}")
    except Exception as e:
        print(f"❌ API no disponible: {e}")
        print("   Asegúrate de que el servidor FastAPI esté corriendo en :8000")
        return

    # Inicializar pre-procesador
    print("\n🔄 Inicializando Query Preprocessor...")
    preprocessor = QueryPreprocessor(verbose=False)
    print("✅ Pre-procesador listo")

    resultados = []
    timestamp = datetime.now()

    for caso in CASOS_PRUEBA:
        print(f"\n{'='*80}")
        print(f"🔍 Caso {caso['id']}: {caso['query']}")
        print(f"   Categoría: {caso['categoria']}")
        print(f"   Descripción: {caso['descripcion']}")
        print("=" * 80)

        # Búsqueda normal
        print("\n   📊 Búsqueda NORMAL...")
        resultados_normal, tiempo_normal, total_normal = buscar_normal(caso['query'])
        print(f"   ✅ {len(resultados_normal)} resultados en {tiempo_normal:.0f}ms (total: {total_normal})")

        # Búsqueda mejorada
        print("\n   ✨ Búsqueda MEJORADA (con expansión)...")
        resultados_mejorada, metadata, tiempo_mejorada, total_mejorada = buscar_mejorada(
            caso['query'], preprocessor
        )

        if "error" in metadata:
            print(f"   ⚠️  Error: {metadata['error']}")
            continue

        print(f"   ✅ {len(resultados_mejorada)} resultados en {tiempo_mejorada:.0f}ms (total: {total_mejorada})")
        print(f"   📝 Expansión: {metadata['query_expandida'][:80]}...")
        print(f"   🔍 Términos añadidos: {metadata['terminos_añadidos'][:8]}")

        # Análisis de overlap
        overlap = analizar_overlap(resultados_normal, resultados_mejorada)

        print(f"\n   📈 Análisis de Overlap:")
        print(f"      • Comunes: {overlap['comunes']}")
        print(f"      • Solo en mejorada: {overlap['solo_mejorada']} (nuevos)")
        print(f"      • Solo en normal: {overlap['solo_normal']}")

        # Métricas
        ganancia = total_mejorada - total_normal
        ratio = total_mejorada / total_normal if total_normal > 0 else 0
        overhead = tiempo_mejorada - tiempo_normal

        print(f"\n   📊 Métricas:")
        print(f"      • Ganancia en resultados: {ganancia:+d} ({ratio:.1f}x)")
        print(f"      • Overhead de tiempo: {overhead:.0f}ms")
        print(f"      • Nuevos datasets: {overlap['solo_mejorada']}")

        # Guardar resultado
        resultado = {
            "caso_id": caso['id'],
            "categoria": caso['categoria'],
            "query": caso['query'],
            "query_expandida": metadata['query_expandida'],
            "resultados_normal": len(resultados_normal),
            "total_normal": total_normal,
            "resultados_mejorada": len(resultados_mejorada),
            "total_mejorada": total_mejorada,
            "ganancia_total": ganancia,
            "ratio": round(ratio, 2),
            "overlap_comunes": overlap['comunes'],
            "nuevos_resultados": overlap['solo_mejorada'],
            "tiempo_normal_ms": round(tiempo_normal, 1),
            "tiempo_mejorada_ms": round(tiempo_mejorada, 1),
            "overhead_ms": round(overhead, 1),
            "temas_detectados": ", ".join(metadata['temas']),
            "terminos_añadidos": ", ".join(metadata['terminos_añadidos']),
            "conceptos_implicitos": ", ".join(metadata['conceptos_implicitos'])
        }
        resultados.append(resultado)

    # Guardar CSV
    RESULTS_DIR.mkdir(exist_ok=True)
    fecha = timestamp.strftime("%Y-%m-%d_%H%M%S")
    csv_file = RESULTS_DIR / f"bateria_query_preprocessor_{fecha}.csv"

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            "caso_id", "categoria", "query", "query_expandida",
            "resultados_normal", "total_normal", "resultados_mejorada", "total_mejorada",
            "ganancia_total", "ratio", "overlap_comunes", "nuevos_resultados",
            "tiempo_normal_ms", "tiempo_mejorada_ms", "overhead_ms",
            "temas_detectados", "terminos_añadidos", "conceptos_implicitos"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(resultados)

    # Resumen final
    print("\n\n" + "=" * 80)
    print("📊 RESUMEN FINAL")
    print("=" * 80)

    total_normal = sum(r['total_normal'] for r in resultados)
    total_mejorada = sum(r['total_mejorada'] for r in resultados)
    total_nuevos = sum(r['nuevos_resultados'] for r in resultados)
    tiempo_promedio_overhead = sum(r['overhead_ms'] for r in resultados) / len(resultados)

    print(f"\n📈 Métricas Agregadas:")
    print(f"   • Total resultados (normal): {total_normal}")
    print(f"   • Total resultados (mejorada): {total_mejorada}")
    print(f"   • Ganancia total: {total_mejorada - total_normal:+d} ({(total_mejorada/total_normal if total_normal else 0):.1f}x)")
    print(f"   • Nuevos datasets únicos: {total_nuevos}")
    print(f"   • Overhead promedio: {tiempo_promedio_overhead:.0f}ms por query")

    print(f"\n📁 Archivo guardado: {csv_file}")

    # Mejores casos
    print("\n🏆 Mejores Casos (más ganancia):")
    mejores = sorted(resultados, key=lambda x: x['nuevos_resultados'], reverse=True)[:3]
    for i, r in enumerate(mejores, 1):
        print(f"   {i}. {r['caso_id']}: '{r['query'][:30]}...' → +{r['nuevos_resultados']} nuevos resultados")

    print("\n" + "=" * 80)
    print("✅ Batería completada")
    print("=" * 80)


if __name__ == "__main__":
    main()
