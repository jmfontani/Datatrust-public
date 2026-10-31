# Informe Comparativo: Buscador Semántico vs datos.gob.es

**Fecha:** 2026-06-18 17:27
**Queries evaluadas:** 47 (mismo conjunto para ambos sistemas)

## 1. Resumen de métricas

| Métrica | Nuestro buscador (GT propio) | datos.gob.es (GT propio) | Nuestro buscador vs GT datos.gob.es |
|---------|------------------------------|----------------------------|--------------------------------------|
| **P@5** | **0.7021** | **0.6219** | **0.4625** |
| **P@10** | 0.6468 | 0.6073 | 0.4042 |
| **NDCG@10** | 0.7917 | 0.6674 | 0.5358 |
| **Recall** | 1.9656 | 0.7477 | 0.9446 |

### Interpretación

- **Columna 1 (nuestro GT propio):** evalúa nuestro buscador con ground truth generado a partir de sus propios resultados (método del proyecto).
- **Columna 2 (datos.gob.es GT propio):** evalúa datos.gob.es con ground truth generado a partir de sus propios resultados web. Es la comparación más justa sistema-a-sistema.
- **Columna 3 (nuestro vs GT datos.gob.es):** mide cuántos datasets relevantes para datos.gob.es también encuentra nuestro buscador. Es una medida de **cobertura cruzada**.

## 2. Comparación directa

### 2.1 ¿Mejora nuestro buscador a datos.gob.es?

Sobre **ground truth propio de cada sistema**:

- **P@5 nuestro buscador:** 0.7021
- **P@5 datos.gob.es:** 0.6219
- **Diferencia:** +0.0802

Con esta métrica, nuestro buscador **supera** a datos.gob.es en P@5.

### 2.2 Cobertura cruzada

Cuando el ground truth es el de **datos.gob.es**, nuestro buscador obtiene P@5=0.4625. Esto significa que, de los datasets que datos.gob.es considera relevantes, nuestro buscador recupera aproximadamente el **46%** en el top-5.

## 3. Robustez: queries con 0 resultados

| Sistema | Queries con 0 resultados |
|---------|--------------------------|
| datos.gob.es web | 12 / 48 |
| Nuestro buscador vs GT datos.gob.es | 17 / 48 |

Nota: en datos.gob.es, las queries con 0 resultados son literalmente ausencia de datasets en su catálogo para esos términos. En nuestro buscador, "0 resultados" significa que no encontramos datasets que datos.gob.es considerara relevantes.

## 4. Análisis por categoría (datos.gob.es)

| Categoría | Queries | P@5 < 0.6 |
|-----------|---------|-----------|
| unknown | 48 | 16 |

## 5. Metodología

### 5.1 Recuperación de resultados de datos.gob.es
- Se usó **Playwright + Firefox headless** para navegar por la web real de `https://datos.gob.es/es/catalogo?q=...`.
- Se extrajeron los títulos del selector `.dge-list__title.dataset-heading`.
- Se respetó una pausa de 2 segundos entre queries para no saturar el servidor.

### 5.2 Ground truth
- Para cada query, se tomaron los top-10 resultados reales de cada sistema.
- Se pasaron a un LLM (`deepseek-v4-flash:cloud`) para clasificar relevancia y extraer `patrones_palabras_clave`.
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

Con la metodología descrita, **el buscador semántico propuesto supera al buscador web de datos.gob.es en P@5** (0.7021 vs 0.6219).

Sin embargo, la ventaja se reduce cuando se mide la cobertura cruzada: nuestro buscador recupera el 46% de los datasets relevantes según datos.gob.es en el top-5. Esto indica que, aunque nuestro sistema es más preciso en su propio ranking, aún no recupera todos los datasets que datos.gob.es considera relevantes.

## 8. Archivos generados

- `datosgobes_search_results.jsonl`: top-10 resultados web de datos.gob.es por query.
- `ground_truth_datosgobes.jsonl`: ground truth generado por LLM para datos.gob.es.
- `ragas_scores_datosgobes.json`: métricas de datos.gob.es sobre su propio ground truth.
- `ragas_scores_nuestro_vs_dge_gt.json`: métricas de nuestro buscador sobre ground truth de datos.gob.es.
- `reporte_comparativo_datosgobes.md`: este informe.
