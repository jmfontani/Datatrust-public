#!/usr/bin/env python3
"""
Evaluación Automática de Explicaciones LLM
==========================================

Analiza la calidad de las explicaciones del LLM mediante heurísticas automáticas:
- Longitud adecuada
- Presencia de keywords relevantes
- Coherencia léxica con query y dataset
- Diversidad de vocabulario

Uso:
    # 1. Activar entorno virtual (OBLIGATORIO)
    source ~/datos/PFM/Datatrust/venv/bin/activate

    # 2. Ejecutar
    python3 evaluacion_automatica_explicaciones.py

Salida:
    - Métricas por explicación
    - Score agregado de calidad
    - Recomendaciones de mejora
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter
import sys

sys.path.insert(0, str(Path(__file__).parent / "resultados"))

RESULTS_DIR = Path(__file__).parent / "resultados"


class AutomaticExplanationEvaluator:
    """Evaluador automático de calidad de explicaciones."""

    def __init__(self):
        self.metricas = []

    def extraer_keywords(self, text: str) -> set:
        """Extrae palabras significativas de un texto."""
        # Limpiar y tokenizar
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()

        # Filtrar stopwords español
        stopwords = {
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'y', 'o', 'pero',
            'de', 'del', 'al', 'a', 'en', 'con', 'por', 'para', 'desde', 'hasta',
            'sobre', 'entre', 'bajo', 'sobre', 'tras', 'durante', 'mediante',
            'que', 'como', 'cuando', 'donde', 'quien', 'cuyo', 'cuya', 'este',
            'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas', 'aquel',
            'aquella', 'aquellos', 'aquellas', 'es', 'son', 'fue', 'ha', 'han',
            'muy', 'más', 'menos', 'mucho', 'poco', 'tanto', 'todo', 'nada',
            'uno', 'dos', 'sobre', 'todo', 'también', 'sin', 'embargo', 'porque'
        }

        return set(w for w in words if len(w) > 3 and w not in stopwords)

    def evaluar_longitud(self, explicacion: str) -> Tuple[float, str]:
        """Evalúa si la longitud es adecuada (ni muy corta ni muy larga)."""
        longitud = len(explicacion)

        if longitud < 30:
            return 1.0, "Muy corta (< 30 caracteres)"
        elif longitud < 60:
            return 2.0, "Corta (30-60 caracteres)"
        elif longitud < 150:
            return 5.0, "Adecuada (60-150 caracteres)"
        elif longitud < 300:
            return 4.0, "Larga (150-300 caracteres)"
        else:
            return 3.0, "Muy larga (> 300 caracteres)"

    def evaluar_relevancia_keywords(self, explicacion: str, query: str, title: str) -> Tuple[float, str]:
        """Evalúa si la explicación menciona conceptos de la query y el dataset."""
        exp_keywords = self.extraer_keywords(explicacion)
        query_keywords = self.extraer_keywords(query)
        title_keywords = self.extraer_keywords(title)

        if not query_keywords:
            return 3.0, "No se pudieron extraer keywords de la query"

        # Calcular overlap
        overlap_query = len(exp_keywords & query_keywords) / len(query_keywords)
        overlap_title = len(exp_keywords & title_keywords) / len(title_keywords) if title_keywords else 0

        overlap_total = (overlap_query + overlap_title) / 2

        if overlap_total >= 0.5:
            return 5.0, f"Excelente overlap ({overlap_total:.0%})"
        elif overlap_total >= 0.3:
            return 4.0, f"Buen overlap ({overlap_total:.0%})"
        elif overlap_total >= 0.1:
            return 3.0, f"Overlap moderado ({overlap_total:.0%})"
        else:
            return 2.0, f"Bajo overlap ({overlap_total:.0%})"

    def evaluar_especificidad(self, explicacion: str) -> Tuple[float, str]:
        """Evalúa si la explicación es específica o genérica."""
        frases_genericas = [
            "dataset relevante", "contiene información", "proporciona datos",
            "relacionado con", "sobre el tema", "información sobre",
            "datos de", "relacionado", "información de", "contiene datos"
        ]

        exp_lower = explicacion.lower()

        # Contar frases genéricas
        genericas_encontradas = sum(1 for f in frases_genericas if f in exp_lower)

        if genericas_encontradas == 0:
            return 5.0, "Muy específica, sin frases genéricas"
        elif genericas_encontradas <= 1:
            return 4.0, "Mayormente específica"
        elif genericas_encontradas <= 2:
            return 3.0, "Algo genérica"
        else:
            return 2.0, f"Muy genérica ({genericas_encontradas} frases genéricas)"

    def evaluar_legibilidad(self, explicacion: str) -> Tuple[float, str]:
        """Evalúa la legibilidad básica."""
        palabras = explicacion.split()

        if not palabras:
            return 1.0, "Vacía"

        longitud_promedio = sum(len(w) for w in palabras) / len(palabras)

        if longitud_promedio > 15:
            return 2.0, f"Palabras muy largas ({longitud_promedio:.1f} caracteres)"
        elif longitud_promedio > 12:
            return 3.0, f"Palabras algo largas ({longitud_promedio:.1f} caracteres)"
        elif longitud_promedio > 8:
            return 4.0, f"Longitud adecuada ({longitud_promedio:.1f} caracteres)"
        else:
            return 5.0, f"Muy legible ({longitud_promedio:.1f} caracteres)"

    def evaluar_diversidad(self, explicacion: str) -> Tuple[float, str]:
        """Evalúa diversidad léxica (ratio palabras únicas / total)."""
        palabras = explicacion.lower().split()

        if len(palabras) < 5:
            return 3.0, "Texto muy corto"

        unicas = len(set(palabras))
        total = len(palabras)
        ratio = unicas / total

        if ratio >= 0.8:
            return 5.0, f"Alta diversidad léxica ({ratio:.0%})"
        elif ratio >= 0.6:
            return 4.0, f"Buena diversidad léxica ({ratio:.0%})"
        elif ratio >= 0.4:
            return 3.0, f"Diversidad aceptable ({ratio:.0%})"
        else:
            return 2.0, f"Baja diversidad léxica ({ratio:.0%})"

    def evaluar_caso(self, query: str, dataset: Dict, explicacion: str) -> Dict:
        """Evalúa un caso completo."""
        title = dataset.get("title", "")

        scores = {
            "longitud": self.evaluar_longitud(explicacion),
            "relevancia": self.evaluar_relevancia_keywords(explicacion, query, title),
            "especificidad": self.evaluar_especificidad(explicacion),
            "legibilidad": self.evaluar_legibilidad(explicacion),
            "diversidad": self.evaluar_diversidad(explicacion)
        }

        # Calcular score global
        valores = [s[0] for s in scores.values()]
        score_global = sum(valores) / len(valores)

        return {
            "query": query,
            "dataset_title": title[:80],
            "explicacion": explicacion[:150],
            "explicacion_completa": explicacion,
            "scores": {k: {"valor": v[0], "comentario": v[1]} for k, v in scores.items()},
            "score_global": score_global,
            "calidad": "Excelente" if score_global >= 4.5 else
                      "Buena" if score_global >= 3.5 else
                      "Mejorable" if score_global >= 2.5 else
                      "Deficiente"
        }

    def generar_ejemplos_explicaciones(self) -> List[Dict]:
        """Genera ejemplos realistas de explicaciones basadas en el patrón del LLM."""
        # Simular explicaciones que el LLM generaría
        casos = [
            {
                "query": "paro juvenil desempleo jóvenes",
                "dataset": {
                    "title": "Población parada registrada de 16 a 24 años de edad"
                },
                "explicacion": "Directamente relacionado con empleo juvenil. Incluye datos de población parada en el rango de edad 16-24 años, que corresponde exactamente a la definición de juventud en el contexto laboral."
            },
            {
                "query": "sostenibilidad urbana",
                "dataset": {
                    "title": "Indicadores de calidad del aire por municipios"
                },
                "explicacion": "Dataset relevante que proporciona información sobre calidad del aire. Contiene datos que pueden relacionarse con sostenibilidad."
            },
            {
                "query": "turismo Canarias 2023",
                "dataset": {
                    "title": "Movimientos turísticos en Canarias"
                },
                "explicacion": "Dataset específico sobre turismo en Canarias con datos de 2023."
            },
            {
                "query": "emisiones CO2",
                "dataset": {
                    "title": "Estadísticas de contaminación atmosférica"
                },
                "explicacion": "Muy relevante. Contiene mediciones detalladas de emisiones de CO2 y otros gases de efecto invernadero desglosados por sectores industriales y municipios."
            },
            {
                "query": "brecha digital educación",
                "dataset": {
                    "title": "Encuesta de equipamiento tecnológico en hogares"
                },
                "explicacion": "Relevante. Proporciona datos sobre acceso a tecnología en hogares que permite inferir brechas digitales en el ámbito educativo."
            }
        ]

        return casos

    def run(self) -> None:
        """Ejecuta evaluación automática."""
        print("\n" + "=" * 80)
        print("🤖 EVALUACIÓN AUTOMÁTICA DE EXPLICACIONES LLM")
        print("=" * 80)
        print("\nDimensiones evaluadas:")
        print("  📏 Longitud adecuada")
        print("  🔗 Relevancia con query/dataset")
        print("  🎯 Especificidad (vs genéricidad)")
        print("  📖 Legibilidad")
        print("  🌈 Diversidad léxica")
        print("-" * 80)

        casos = self.generar_ejemplos_explicaciones()
        resultados = []

        for caso in casos:
            resultado = self.evaluar_caso(
                caso["query"],
                caso["dataset"],
                caso["explicacion"]
            )
            resultados.append(resultado)
            self.metricas.append(resultado)

        # Mostrar resultados
        print("\n📊 RESULTADOS:")
        print("-" * 80)

        for i, r in enumerate(resultados, 1):
            print(f"\n📝 CASO {i}:")
            print(f"   Query: {r['query']}")
            print(f"   Dataset: {r['dataset_title']}")
            print(f"   Explicación: {r['explicacion']}...")
            print(f"\n   Scores:")
            for dim, data in r['scores'].items():
                print(f"     {dim:15s}: {data['valor']:.1f}/5.0 - {data['comentario']}")
            print(f"\n   🎯 GLOBAL: {r['score_global']:.2f}/5.0 - {r['calidad']}")

        # Resumen agregado
        print("\n" + "=" * 80)
        print("📈 RESUMEN AGREGADO:")
        print("=" * 80)

        scores_globales = [r['score_global'] for r in resultados]
        print(f"\n   Score medio: {sum(scores_globales)/len(scores_globales):.2f}/5.0")
        print(f"   Mejor caso: {max(scores_globales):.2f}")
        print(f"   Peor caso: {min(scores_globales):.2f}")

        # Por dimensión
        print("\n   Por dimensión:")
        for dim in ["longitud", "relevancia", "especificidad", "legibilidad", "diversidad"]:
            valores = [r['scores'][dim]['valor'] for r in resultados]
            media = sum(valores) / len(valores)
            print(f"     {dim:15s}: {media:.2f}/5.0")

        # Distribución de calidad
        calidades = Counter(r['calidad'] for r in resultados)
        print("\n   Distribución de calidad:")
        for cal, count in calidades.most_common():
            print(f"     {cal:15s}: {count} casos")

        # Recomendaciones
        print("\n" + "=" * 80)
        print("💡 RECOMENDACIONES:")
        print("=" * 80)

        media_relevancia = sum(r['scores']['relevancia']['valor'] for r in resultados) / len(resultados)
        media_especificidad = sum(r['scores']['especificidad']['valor'] for r in resultados) / len(resultados)

        if media_relevancia < 3.5:
            print("   ⚠️  Las explicaciones deberían incluir más keywords de la query")
            print("      → Ajustar prompt para forzar mención de términos de búsqueda")

        if media_especificidad < 3.5:
            print("   ⚠️  Demasiadas frases genéricas detectadas")
            print("      → Añadir ejemplos de explicaciones específicas en el prompt")

        if any(r['scores']['longitud']['valor'] < 3 for r in resultados):
            print("   ⚠️  Algunas explicaciones son demasiado cortas")
            print("      → Especificar longitud mínima en el prompt")

        print("\n   ✅ Las explicaciones con mejor calidad son las que:")
        print("      - Mencionan datos concretos del dataset")
        print("      - Conectan explícitamente con la query del usuario")
        print("      - Evitan frases genéricas como 'proporciona información'")

        # Guardar resultados
        archivo_salida = RESULTS_DIR / "evaluacion_automatica_explicaciones.json"
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump({
                "evaluacion": "automatica_heuristica",
                "n_casos": len(resultados),
                "resultados": resultados
            }, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Guardado en: {archivo_salida}")


if __name__ == "__main__":
    evaluator = AutomaticExplanationEvaluator()
    evaluator.run()
