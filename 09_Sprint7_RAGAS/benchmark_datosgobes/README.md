# Sub-Sprint: Benchmark contra datos.gob.es ✅ COMPLETADO

**Sprint padre**: `09_Sprint7_RAGAS`  
**Fecha de creación**: 2026-06-18  
**Fecha de cierre**: 2026-06-18  
**Estado**: ✅ COMPLETADO  
**Objetivo**: Evaluar el buscador oficial `datos.gob.es` con la misma metodología usada en el proyecto, para obtener una comparativa cuantitativa directa.

---

## 📁 Estructura

```
benchmark_datosgobes/            # Punto de entrada documental del sub-sprint
└── README.md                    # Este archivo

09_Sprint7_RAGAS/                # Código y entregables del benchmark
├── codigo/
│   ├── probe_datosgobes_web.py              # Piloto Playwright
│   ├── search_datosgobes_web.py             # Extracción batch web
│   ├── generar_ground_truth_datosgobes.py   # Ground truth via LLM
│   ├── eval_datosgobes_core.py              # Métricas de datos.gob.es
│   ├── eval_nuestro_vs_dge_gt.py            # Evaluación cruzada
│   └── generar_reporte_comparativo_datosgobes.py  # Informe Markdown
└── entregables/
    ├── datosgobes_search_results.jsonl
    ├── ground_truth_datosgobes.jsonl
    ├── ragas_scores_datosgobes.json
    ├── ragas_scores_nuestro_vs_dge_gt.json
    └── reporte_comparativo_datosgobes.md
```

---

## 🎯 Métricas finales

| Métrica | Nuestro buscador (GT propio) | datos.gob.es (GT propio) | Nuestro vs GT datos.gob.es |
|---------|------------------------------|----------------------------|----------------------------|
| **P@5** | **0.7021** | **0.6219** | **0.4625** |
| P@10 | 0.6468 | 0.6073 | 0.4042 |
| NDCG@10 | 0.7917 | 0.6674 | 0.5358 |
| Recall | 1.9656 | 0.7477 | 0.9446 |

---

## ⚠️ Limitaciones conocidas

1. **Extracción web con Playwright**: se usó un navegador headless para obtener resultados reales de `https://datos.gob.es/es/catalogo`. Incapsula podría bloquear futuras ejecuciones.
2. **Búsqueda por título**: la evaluación se basa en títulos de datasets, no en descripciones.
3. **Ground truth por sistema**: cada sistema se evalúa parcialmente contra lo que él mismo devuelve. La columna cruzada mitiga este sesgo.
4. **Catálogo local**: nuestro buscador tiene 87.676 datasets ingestados; si datos.gob.es devuelve datasets no ingeridos, nuestro buscador no puede recuperarlos.
5. **Tasa de peticiones controlada**: se respetó una pausa de 2 segundos entre llamadas para no saturar el servidor público.

---

## 🔗 Fuentes

- Web de búsqueda: `https://datos.gob.es/es/catalogo?q=...`
- Endpoint SPARQL (no usado en evaluación final): `https://datos.gob.es/virtuoso/sparql`
- Documentación API: https://datos.gob.es/es/apidata
