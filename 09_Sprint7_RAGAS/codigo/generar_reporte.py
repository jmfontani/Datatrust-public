#!/usr/bin/env python3
"""
Generar Reporte de Evaluación RAGAS.

Combina los resultados de múltiples evaluaciones y genera un reporte ejecutivo
en formato Markdown para incluir en la documentación del TFM.

Uso:
    python generar_reporte.py \
        --scores ../entregables/ragas_scores_*.json \
        --comparison ../entregables/frontend_comparison.json \
        --output ../entregables/reporte_evaluacion.md
"""

import json
import argparse
import glob
from pathlib import Path
from datetime import datetime


def cargar_resultados_json(pattern: str) -> list[dict]:
    """Carga múltiples archivos JSON que matchean un patrón."""
    resultados = []
    for path in glob.glob(pattern):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            data["_source_file"] = Path(path).name
            resultados.append(data)
    return resultados


def generar_tabla_metricas(resumen: dict, targets: dict = None) -> str:
    """Genera tabla Markdown con métricas y targets."""
    if targets is None:
        targets = {
            "precision_at_5": 0.80,
            "precision_at_10": 0.70,
            "ndcg_at_10": 0.75,
            "recall": 0.80,
        }

    lineas = [
        "| Métrica | Valor | Target | Estado |",
        "|---------|-------|--------|--------|",
    ]

    for metrica, target in targets.items():
        valor = resumen.get(metrica, 0)
        diff = valor - target
        estado = "✅" if valor >= target else "⚠️" if valor >= target * 0.8 else "❌"
        lineas.append(f"| {metrica.replace('_', ' ').title()} | {valor:.3f} | {target:.2f} | {estado} |")

    return "\n".join(lineas)


def generar_tabla_categoria(resumen: dict) -> str:
    """Genera tabla Markdown con métricas por categoría."""
    lineas = [
        "| Categoría | Precision@5 | NDCG@10 | Queries |",
        "|-----------|-------------|---------|---------|",
    ]

    for cat, metrics in sorted(resumen.items()):
        lineas.append(
            f"| {cat.title()} | {metrics.get('precision_at_5', 0):.3f} | "
            f"{metrics.get('ndcg_at_10', 0):.3f} | {metrics.get('n_queries', 0)} |"
        )

    return "\n".join(lineas)


def generar_tabla_dificultad(resumen: dict) -> str:
    """Genera tabla Markdown con métricas por dificultad."""
    lineas = [
        "| Dificultad | Precision@5 | NDCG@10 | Queries |",
        "|------------|-------------|---------|---------|",
    ]

    orden = {"fácil": 0, "media": 1, "difícil": 2}
    for dif, metrics in sorted(resumen.items(), key=lambda x: orden.get(x[0], 99)):
        lineas.append(
            f"| {dif.title()} | {metrics.get('precision_at_5', 0):.3f} | "
            f"{metrics.get('ndcg_at_10', 0):.3f} | {metrics.get('n_queries', 0)} |"
        )

    return "\n".join(lineas)


def generar_seccion_frontend_comparison(comparacion: dict) -> str:
    """Genera sección Markdown con comparación de frontends."""
    lineas = [
        "## 🖥️ Comparación de Frontends",
        "",
        "Se evaluaron los tres frontends del buscador usando las mismas queries:",
        "",
    ]

    # Tabla de frontends
    lineas.extend([
        "| Frontend | Descripción | Satisfacción | Tiempo Medio |",
        "|----------|-------------|--------------|--------------|",
    ])

    resumen = comparacion.get("resumen", {})
    for frontend, datos in resumen.items():
        nombre = datos.get("nombre", frontend)
        lineas.append(
            f"| {frontend} | {nombre} | {datos.get('satisfaccion_general_media', 0):.3f} | "
            f"{datos.get('tiempo_medio_seg', 0):.2f}s |"
        )

    # Ranking
    ranking = comparacion.get("ranking_por_satisfaccion", [])
    if ranking:
        lineas.extend([
            "",
            "### Ranking por Satisfacción General",
            "",
        ])
        for i, (frontend, score) in enumerate(ranking, 1):
            nombre = resumen.get(frontend, {}).get("nombre", frontend)
            lineas.append(f"{i}. **{nombre}** ({frontend}): {score:.3f}")

    return "\n".join(lineas)


SECCION_METODOLOGIA = """## 🔬 Metodología de cálculo de P@5 y P@10

### Qué miden

- **Precision@5 (P@5)**: proporción de resultados relevantes entre los 5 primeros devueltos por el buscador.
- **Precision@10 (P@10)**: proporción de resultados relevantes entre los 10 primeros.

Fórmula general:

```
P@K = relevantes_en_top_k / min(K, total_resultados)
```

En la práctica, el sistema siempre devuelve al menos 10 resultados cuando existen, por lo que el denominador es `K`.

### Ground truth: resultados reales, no ideales

El ground truth no se genera pidiendo al LLM que imagine datasets perfectos, sino que refleja lo que la API real devuelve:

1. Se ejecuta cada query contra la API real (`POST /search`, `top_k=10`).
2. Se toman esos **10 resultados reales**.
3. Un LLM (`deepseek-v4.1-flash:cloud`) clasifica cada resultado como `relevante` o `no_relevante` según la intención de la query.
4. Se extraen **patrones de palabras clave** de los títulos de los resultados clasificados como relevantes.

Este cambio de metodología fue clave: el primer ground truth idealizado daba P@5 cercana a 0, porque los datasets perfectos no existían en la base de datos. Usar resultados reales permite medir la calidad del ranking sobre el corpus disponible.

Ejemplo de ground truth para la query `"empleo juvenil"`:

```json
{
  "patrones_palabras_clave": [
    "población activa registrada",
    "16 a 24 años",
    "empleo juvenil",
    "jóvenes"
  ],
  "resultados_clasificados": [ ... ]
}
```

### Cómo se decide si un resultado es relevante

ACTUALIZADO (01-oct-2026): la relevancia la decide el **JUICIO del GT v5**
(`entregables/gt_etiquetas_v5.json`: 10.653 etiquetas de un LLM juez
(temperatura 0) sobre 214 consultas; escala 0/1/2; clave (query_id,
dataset_id)). El código vive en `codigo/utils/gt_metrics.py`; las funciones de
`codigo/utils/ragas_metrics.py` delegan en él.

```python
def nivel(query_id, dataset_id) -> int | None:   # utils/gt_metrics.py
    v = self._et.get(f"{query_id}|{dataset_id}")
    return None if v is None else int(v)
```

El criterio ANTERIOR — coincidencia de subcadena en el título (`any(patron in
titulo ...)`) — quedó RETIRADO: medido contra los 470 juicios humanos de la
Fase A, marcaba como relevante el 41 % de lo que el juicio rechaza. Los
resultados sin juicio se EXCLUYEN del cálculo (y se reportan como cobertura);
no cuentan como no relevantes.

### Sobre qué modo de búsqueda se evalúa

Los valores **P@5** y **P@10** de esta tabla se obtienen con el **motor de búsqueda híbrida básico**, sin intervención de LLM en el ranking:

| Parámetro | Valor |
|-----------|-------|
| Endpoint | `POST /search` |
| Modo | Búsqueda híbrida sin LLM |
| Peso semántico | 0.75 |
| Peso léxico | 0.25 |
| Ground truth | `ground_truth_real.jsonl` |

### Qué NO mide esta tabla

Esta métrica mide exclusivamente la **calidad del ranking de retrieval**. No evalúa otras capacidades del sistema, que se miden con protocolos diferentes:

| Capacidad | Protocolo/métrica usado |
|-----------|-------------------------|
| **Re-ranking con LLM** | P@5/P@10 con `/llm/search/rerank` |
| **TL;DR de datasets** | Evaluación de impacto en relevancia percibida (`08_Sprint6_LLM_Mejora/codigo/tests/evaluacion_tldr_impact.json`) |
| **Query Preprocessor (#3, #4, #12)** | Comparación con/without preproceso sobre queries de prueba |
| **Datasets complementarios (#5)** | Evaluación cualitativa de pertinencia de recomendaciones |
| **Chat sobre datasets (#10)** | Tests funcionales de coherencia y utilidad de respuestas |

### Limitaciones de esta medición

1. **Relevancia por JUICIO desde el 01-oct-2026** (GT v5, por dataset_id). El criterio antiguo por título tenía 96 falsos positivos de 232 no relevantes (41 %).
2. **Limitación histórica conservada del portal público**: datos.gob.es sirve SERPs *title-only* (sin dataset_id): contra él las métricas del GT del juez NO son aplicables (`eval_datosgobes_core.py` las deja a None explicitamente).
3. **Recall acotado**: el denominador son las fichas juzgadas con nivel ≥ umbral para esa consulta; la métrica no puede superar 1,0.
4. **Cobertura obligatoria**: `cobertura_top10` acompaña a toda métrica; por debajo de ~0,5 la comparación de métricas entre sistemas no es interpretable (poblaciones distintas).

### Archivos implicados

| Archivo | Rol |
|---------|-----|
| `codigo/utils/gt_metrics.py` | **Instrumento canónico**: métricas sobre el JUICIO (GT v5, escala 0/1/2, por dataset_id) |
| `codigo/utils/ragas_metrics.py` | Interfaz de métricas; delega en `gt_metrics` (y wrapper del framework RAGAS real) |
| `codigo/eval_ragas_core.py` | Ejecuta las queries contra `/search` con el GT del juez |
| `entregables/gt_etiquetas_v5.json` | Ground truth del juez usado en esta evaluación |
| `entregables/ragas_scores_basic.json` | Resultados numéricos |
"""


def generar_reporte(
    scores_basic: dict = None,
    scores_llm: dict = None,
    frontend_comparison: dict = None,
) -> str:
    """Genera reporte completo en Markdown."""

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lineas = [
        "# 📊 Informe de Evaluación RAGAS - Buscador Semántico de Datasets",
        "",
        f"**Fecha de generación**: {now}",
        "",
        "---",
        "",
        "## 🎯 Resumen Ejecutivo",
        "",
        "Este informe presenta los resultados de la evaluación sistemática del Buscador Semántico",
        "de Datasets Públicos utilizando métricas de retrieval inspiradas en **RAGAS** (Retrieval Augmented",
        "Generation Assessment) y comparativas entre los tres frontends disponibles.",
        "",
        SECCION_METODOLOGIA,
        "",
    ]

    # Sección: Evaluación Modo Básico
    if scores_basic:
        resumen_basic = scores_basic.get("resumen", {})
        metricas = resumen_basic.get("metricas", {})

        lineas.extend([
            "## 🔍 Evaluación: Modo Básico (sin LLM)",
            "",
            f"- **Queries evaluadas**: {resumen_basic.get('n_queries', 0)}",
            f"- **Tiempo total**: {resumen_basic.get('tiempo_total_seg', 0):.1f}s",
            f"- **Tiempo medio por query**: {resumen_basic.get('tiempo_medio_por_query_seg', 0):.2f}s",
            "",
            "### Métricas Principales",
            "",
            generar_tabla_metricas(metricas),
            "",
            "### Por Categoría",
            "",
            generar_tabla_categoria(resumen_basic.get("por_categoria", {})),
            "",
            "### Por Dificultad",
            "",
            generar_tabla_dificultad(resumen_basic.get("por_dificultad", {})),
            "",
        ])

    # Sección: Evaluación Modo LLM
    if scores_llm:
        resumen_llm = scores_llm.get("resumen", {})
        metricas_llm = resumen_llm.get("metricas", {})

        lineas.extend([
            "## 🤖 Evaluación: Modo LLM (con re-ranking)",
            "",
            f"- **Queries evaluadas**: {resumen_llm.get('n_queries', 0)}",
            f"- **Tiempo total**: {resumen_llm.get('tiempo_total_seg', 0):.1f}s",
            f"- **Tiempo medio por query**: {resumen_llm.get('tiempo_medio_por_query_seg', 0):.2f}s",
            "",
            "### Métricas Principales",
            "",
            generar_tabla_metricas(metricas_llm),
            "",
            "### Comparación: Básico vs LLM",
            "",
            "| Métrica | Básico | LLM | Mejora |",
            "|---------|--------|-----|--------|",
        ])

        if scores_basic:
            metricas_basic = scores_basic.get("resumen", {}).get("metricas", {})
            for m in ["precision_at_5", "precision_at_10", "ndcg_at_10", "recall"]:
                basic = metricas_basic.get(m, 0)
                llm = metricas_llm.get(m, 0)
                mejora = ((llm - basic) / basic * 100) if basic > 0 else 0
                lineas.append(f"| {m.replace('_', ' ').title()} | {basic:.3f} | {llm:.3f} | {mejora:+.1f}% |")

        lineas.append("")

    # Sección: Comparación de Frontends
    if frontend_comparison:
        lineas.extend([
            "",
            generar_seccion_frontend_comparison(frontend_comparison),
            "",
        ])

    # Conclusiones
    lineas.extend([
        "## 📝 Conclusiones",
        "",
    ])

    # Generar conclusiones automáticas
    conclusiones = []

    if scores_basic:
        metricas = scores_basic.get("resumen", {}).get("metricas", {})
        if metricas.get("precision_at_5", 0) >= 0.80:
            conclusiones.append("✅ El sistema **cumple el target de Precision@5** (>0.80), indicando que los primeros resultados son altamente relevantes.")
        else:
            conclusiones.append("⚠️ El sistema está **por debajo del target de Precision@5**. Se recomienda revisar el ranking semántico.")

        if scores_llm:
            metricas_llm = scores_llm.get("resumen", {}).get("metricas", {})
            mejora = metricas_llm.get("precision_at_5", 0) - metricas.get("precision_at_5", 0)
            if mejora > 0.05:
                conclusiones.append(f"✅ El **re-ranking con LLM mejora la precisión en {mejora*100:.1f}%**, justificando su uso en producción.")
            else:
                conclusiones.append(f"⚠️ El re-ranking con LLM no muestra mejora significativa ({mejora*100:.1f}%). Considerar ajustar prompts o modelo.")

    if frontend_comparison:
        ranking = frontend_comparison.get("ranking_por_satisfaccion", [])
        if ranking:
            mejor = ranking[0][0]
            conclusiones.append(f"🏆 El **Frontend {mejor}** obtiene la mayor satisfacción de usuario según la evaluación heurística.")

    for concl in conclusiones:
        lineas.append(f"- {concl}")

    lineas.extend([
        "",
        "---",
        "",
        "## 📁 Archivos de Resultados",
        "",
        "| Archivo | Descripción |",
        "|---------|-------------|",
    ])

    if scores_basic:
        lineas.append("| `ragas_scores_basic.json` | Evaluación modo básico (sin LLM) |")
    if scores_llm:
        lineas.append("| `ragas_scores_llm.json` | Evaluación modo LLM (con re-ranking) |")
    if frontend_comparison:
        lineas.append("| `frontend_comparison.json` | Comparación de frontends A/B/C |")

    lineas.extend([
        "",
        "---",
        "",
        "*Reporte generado automáticamente por `generar_reporte.py` - Sprint 11 RAGAS*",
    ])

    return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser(description="Generar reporte de evaluación RAGAS")
    parser.add_argument(
        "--scores-basic",
        type=str,
        default="../entregables/ragas_scores_basic.json",
        help="Archivo con scores modo básico"
    )
    parser.add_argument(
        "--scores-llm",
        type=str,
        default="../entregables/ragas_scores_llm.json",
        help="Archivo con scores modo LLM"
    )
    parser.add_argument(
        "--comparison",
        type=str,
        default="../entregables/frontend_comparison.json",
        help="Archivo con comparación de frontends"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="../entregables/reporte_evaluacion.md",
        help="Archivo de salida (Markdown)"
    )
    args = parser.parse_args()

    # Cargar resultados
    print("📖 Cargando resultados de evaluación...")

    scores_basic = None
    scores_llm = None
    frontend_comparison = None

    if Path(args.scores_basic).exists():
        with open(args.scores_basic, "r", encoding="utf-8") as f:
            scores_basic = json.load(f)
        print(f"   ✅ Cargado: {args.scores_basic}")
    else:
        print(f"   ⚠️  No encontrado: {args.scores_basic}")

    if Path(args.scores_llm).exists():
        with open(args.scores_llm, "r", encoding="utf-8") as f:
            scores_llm = json.load(f)
        print(f"   ✅ Cargado: {args.scores_llm}")
    else:
        print(f"   ⚠️  No encontrado: {args.scores_llm}")

    if Path(args.comparison).exists():
        with open(args.comparison, "r", encoding="utf-8") as f:
            frontend_comparison = json.load(f)
        print(f"   ✅ Cargado: {args.comparison}")
    else:
        print(f"   ⚠️  No encontrado: {args.comparison}")

    if not any([scores_basic, scores_llm, frontend_comparison]):
        print("❌ No hay datos para generar el reporte.")
        sys.exit(1)

    # Generar reporte
    print("\n📝 Generando reporte...")
    reporte = generar_reporte(scores_basic, scores_llm, frontend_comparison)

    # Guardar
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(reporte)

    print(f"\n✅ Reporte generado: {output_path}")
    print(f"   Líneas: {len(reporte.splitlines())}")


if __name__ == "__main__":
    main()
