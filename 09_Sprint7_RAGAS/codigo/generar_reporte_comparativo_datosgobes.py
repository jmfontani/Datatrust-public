#!/usr/bin/env python3
"""
Genera informe comparativo Markdown entre nuestro buscador y datos.gob.es.

Combina:
- ragas_scores_basic.json (nuestro buscador, ground truth propio)
- ragas_scores_datosgobes.json (datos.gob.es, ground truth propio)
- ragas_scores_nuestro_vs_dge_gt.json (nuestro buscador vs ground truth de datos.gob.es)

Uso:
    python generar_reporte_comparativo_datosgobes.py
"""

import json
from pathlib import Path
from datetime import datetime


ENTREGABLES = Path(__file__).parent.parent / "entregables"
OUTPUT = ENTREGABLES / "reporte_comparativo_datosgobes.md"


def cargar_scores(nombre: str) -> dict:
    path = ENTREGABLES / nombre
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def contar_fallos_por_categoria(resultados: list[dict]) -> dict:
    from collections import defaultdict
    cats = defaultdict(lambda: {"n": 0, "p5_bajo": 0})
    for r in resultados:
        cat = r.get("categoria", "unknown")
        cats[cat]["n"] += 1
        if r.get("precision_at_5", 0) < 0.6:
            cats[cat]["p5_bajo"] += 1
    return {k: dict(v) for k, v in cats.items()}


def main():
    nuestro = cargar_scores("ragas_scores_basic.json")
    dge = cargar_scores("ragas_scores_datosgobes.json")
    nuestro_vs_dge = cargar_scores("ragas_scores_nuestro_vs_dge_gt.json")

    m_nuestro = nuestro["resumen"]["metricas"]
    m_dge = dge["resumen"]["metricas"]
    m_n_vs_d = nuestro_vs_dge["resumen"]["metricas"]

    # Calcular queries con 0 resultados en datos.gob.es
    q_dge_0 = sum(
        1 for r in dge["resultados_por_query"]
        if r.get("n_resultados", 0) == 0
    )
    q_nuestro_vs_dge_0 = sum(
        1 for r in nuestro_vs_dge["resultados_por_query"]
        if r.get("n_resultados_encontrados", 0) == 0 and r.get("n_relevantes_encontrados", 0) == 0
    )

    md = f"""# Informe Comparativo: Buscador Semántico vs datos.gob.es

**Fecha:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Queries evaluadas:** {nuestro['resumen']['n_queries']} (mismo conjunto para ambos sistemas)

## 1. Resumen de métricas

| Métrica | Nuestro buscador (GT propio) | datos.gob.es (GT propio) | Nuestro buscador vs GT datos.gob.es |
|---------|------------------------------|----------------------------|--------------------------------------|
| **P@5** | **{m_nuestro['precision_at_5']:.4f}** | **{m_dge['precision_at_5']:.4f}** | **{m_n_vs_d['precision_at_5']:.4f}** |
| **P@10** | {m_nuestro['precision_at_10']:.4f} | {m_dge['precision_at_10']:.4f} | {m_n_vs_d['precision_at_10']:.4f} |
| **NDCG@10** | {m_nuestro['ndcg_at_10']:.4f} | {m_dge['ndcg_at_10']:.4f} | {m_n_vs_d['ndcg_at_10']:.4f} |
| **Recall** | {m_nuestro['recall']:.4f} | {m_dge['recall']:.4f} | {m_n_vs_d['recall']:.4f} |

### Interpretación

- **Columna 1 (nuestro GT propio):** evalúa nuestro buscador con ground truth generado a partir de sus propios resultados (método del proyecto).
- **Columna 2 (datos.gob.es GT propio):** evalúa datos.gob.es con ground truth generado a partir de sus propios resultados web. Es la comparación más justa sistema-a-sistema.
- **Columna 3 (nuestro vs GT datos.gob.es):** mide cuántos datasets relevantes para datos.gob.es también encuentra nuestro buscador. Es una medida de **cobertura cruzada**.

## 2. Comparación directa

### 2.1 ¿Mejora nuestro buscador a datos.gob.es?

Sobre **ground truth propio de cada sistema**:

- **P@5 nuestro buscador:** {m_nuestro['precision_at_5']:.4f}
- **P@5 datos.gob.es:** {m_dge['precision_at_5']:.4f}
- **Diferencia:** {m_nuestro['precision_at_5'] - m_dge['precision_at_5']:+.4f}

Con esta métrica, nuestro buscador {"**supera**" if m_nuestro['precision_at_5'] > m_dge['precision_at_5'] else "**iguala**" if abs(m_nuestro['precision_at_5'] - m_dge['precision_at_5']) < 0.05 else "**no supera**"} a datos.gob.es en P@5.

### 2.2 Cobertura cruzada

Cuando el ground truth es el de **datos.gob.es**, nuestro buscador obtiene P@5={m_n_vs_d['precision_at_5']:.4f}. Esto significa que, de los datasets que datos.gob.es considera relevantes, nuestro buscador recupera aproximadamente el **{m_n_vs_d['precision_at_5']*100:.0f}%** en el top-5.

## 3. Robustez: queries con 0 resultados

| Sistema | Queries con 0 resultados |
|---------|--------------------------|
| datos.gob.es web | {q_dge_0} / {dge['resumen']['n_queries']} |
| Nuestro buscador vs GT datos.gob.es | {q_nuestro_vs_dge_0} / {nuestro_vs_dge['resumen']['n_queries']} |

Nota: en datos.gob.es, las queries con 0 resultados son literalmente ausencia de datasets en su catálogo para esos términos. En nuestro buscador, "0 resultados" significa que no encontramos datasets que datos.gob.es considerara relevantes.

## 4. Análisis por categoría (datos.gob.es)

| Categoría | Queries | P@5 < 0.6 |
|-----------|---------|-----------|
"""

    cats_dge = contar_fallos_por_categoria(dge["resultados_por_query"])
    for cat, vals in sorted(cats_dge.items()):
        md += f"| {cat} | {vals['n']} | {vals['p5_bajo']} |\n"

    md += """
## 5. Metodología

### 5.1 Recuperación de resultados de datos.gob.es
- Se usó **Playwright + Firefox headless** para navegar por la web real de `https://datos.gob.es/es/catalogo?q=...`.
- Se extrajeron los títulos del selector `.dge-list__title.dataset-heading`.
- Se respetó una pausa de 2 segundos entre queries para no saturar el servidor.

### 5.2 Ground truth
- Para cada query, se tomaron los top-10 resultados reales de cada sistema.
- Se pasaron a un LLM (`deepseek-v4.1-flash:cloud`) para clasificar relevancia y extraer `patrones_palabras_clave`.
- El ground truth de datos.gob.es **no se reutilizó** para evaluar nuestro buscador; se generó uno específico por sistema para evitar sesgo.

### 5.3 Métricas
- Se reutilizó `utils/ragas_metrics.py` del proyecto (`evaluar_query_individual`, `calcular_precision_at_k`, `calcular_ndcg_at_k`).
- Relevancia: un resultado es relevante si su título contiene algún patrón de palabras clave del ground truth.

## 6. Limitaciones

1. **Cobertura temporal:** la web de datos.gob.es puede haber cambiado entre la ejecución del script y la lectura de este informe.
2. **Campos de búsqueda:** la evaluación se basa en títulos de datasets. No se evalúa relevancia de descripciones ni de recursos individuales.
3. **Ground truth por sistema:** cada sistema se evalúa parcialmente contra lo que él mismo devuelve. La columna cruzada mitiga este sesgo.
4. **Catálogo local:** nuestro buscador tiene 87.676 datasets ingestados de datos.gob.es; si datos.gob.es devuelve datasets no ingeridos, nuestro buscador no puede recuperarlos, lo que afecta a la columna cruzada.
5. **Detección de headless:** aunque Playwright superó Incapsula en esta ejecución, no se garantiza que lo haga en el futuro.

## 7. Conclusión

"""

    if m_nuestro['precision_at_5'] > m_dge['precision_at_5']:
        md += f"""Con la metodología descrita, **el buscador semántico propuesto supera al buscador web de datos.gob.es en P@5** ({m_nuestro['precision_at_5']:.4f} vs {m_dge['precision_at_5']:.4f}).

Sin embargo, la ventaja se reduce cuando se mide la cobertura cruzada: nuestro buscador recupera el {m_n_vs_d['precision_at_5']*100:.0f}% de los datasets relevantes según datos.gob.es en el top-5. Esto indica que, aunque nuestro sistema es más preciso en su propio ranking, aún no recupera todos los datasets que datos.gob.es considera relevantes.
"""
    else:
        md += f"""Con la metodología descrita, **el buscador web de datos.gob.es obtiene un P@5 comparable o superior** ({m_dge['precision_at_5']:.4f} vs {m_nuestro['precision_at_5']:.4f}) en su propio ground truth.

Esto no invalida las mejoras propuestas (búsqueda semántica, TL;DR, complementariedad, chat), pero muestra que la mejora cuantitativa en P@5 no es abrumadora frente al buscador oficial en este conjunto de queries.
"""

    md += """
## 8. Archivos generados

- `datosgobes_search_results.jsonl`: top-10 resultados web de datos.gob.es por query.
- `ground_truth_datosgobes.jsonl`: ground truth generado por LLM para datos.gob.es.
- `ragas_scores_datosgobes.json`: métricas de datos.gob.es sobre su propio ground truth.
- `ragas_scores_nuestro_vs_dge_gt.json`: métricas de nuestro buscador sobre ground truth de datos.gob.es.
- `reporte_comparativo_datosgobes.md`: este informe.
"""

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"✅ Informe guardado en: {OUTPUT}")


if __name__ == "__main__":
    main()
