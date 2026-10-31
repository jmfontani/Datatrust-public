# Fase I · cierre del instrumento de evaluación (14-oct-2026)

**Motivo.** El snapshot de producción (motor BGE-M3, 30-sep) recupera fichas que el pool de las
fases B/C nunca vio, así que su top-10 tenía **158 pares (consulta, ficha) sin etiquetar**, 54 de
ellos en el top-5. El instrumento los trata como no interpretables y **penaliza** al motor: una ficha
sin juicio ocupa un puesto y no suma. Con la cobertura al 100 % la métrica pasa a ser citable sin
asteriscos.

## Qué se hizo

`156_juzgar_pendientes_top10.py` juzga esos 158 pares con el **prompt canónico de la Fase B**
(`109_juzgar_pool.py`, copiado verbatim), `deepseek-v4.1-flash`, temperatura 0, lotes de ≤10 fichas y
una llamada por consulta (6 en vuelo). Los metadatos se toman de los pools cuando la ficha ya se había
juzgado antes, y para las 119 restantes de la misma consulta a `datasets` que usa
`108_construir_pool.py`.

| Control | Resultado |
|---|---|
| Pares juzgados | **158** en 44 consultas · **0 fallos** · 120 s |
| `gt_etiquetas_v5.json` | **INTACTO** — sha256 `05ad416cf6ba52c9…` idéntico antes y después, registrado en el `meta` de v6 |
| Reparto de los nuevos | {0: 90, 1: 42, **2: 26**} |
| Doble ciego (15 pares, 10 %) | **0,800 exacto · 1,000 con ±1** (la Fase B dio 0,847) |

## Cifras canónicas (snapshot de producción, GT v6, cobertura 100 %)

| | 214 consultas | 47 humanas |
|---|---|---|
| P@5 | **0,4318** | **0,6511** |
| P@10 | **0,4000** | **0,5851** |
| nDCG@10 | **0,5774** IC95 [0,5311 · 0,6237] | **0,7116** IC95 [0,6311 · 0,7921] |
| MRR | **0,5942** | **0,8039** |
| Cobertura top-10 | **100 %** | **100 %** |

**El Δ v5→v6 no es una mejora del motor, es el cierre del instrumento** (mismo motor, mismo snapshot):
sobre las 214, +0,0093 en P@5 [+0,0001 · +0,0186] y +0,0198 en nDCG [+0,0075 · +0,0322]; sobre las 47,
+0,0085 (cruza cero) y +0,0400 en nDCG [+0,0046 · +0,0754].

**Toda comparación de motores publicada con v5 debe recalcularse con v6 antes de citarla**, y sale
gratis porque los snapshots ANTES/DESPUÉS son completos: MiniLM→BGE-M3 pasa de +0,1326 (nDCG) y +0,0766
(P@5) a **+0,1526 [+0,1113 · +0,1938] y +0,0860 [+0,0477 · +0,1243]**. Que el valor con v5 reproduzca
exactamente lo publicado en la Fase H es el control de que el arnés es el mismo.

## Medir sin martillar la API

`157_metricas_snapshot.py` recalcula P@5, P@10, nDCG@10, MRR y cobertura desde los rankings completos
guardados (`fase_h_SNAPSHOT_DESPUES.json`) con el ground truth que se le pase, importando
`utils/gt_metrics.py` —nunca reimplementando la fórmula— y reportando el intervalo de confianza y la
mejora mínima detectable.

```bash
cd 09_Sprint7_RAGAS/codigo
python3 157_metricas_snapshot.py --gt gt_etiquetas_v5.json    # control previo: 0,4224 / 0,5575
python3 157_metricas_snapshot.py --gt gt_etiquetas_v6.json    # KPI publicado
python3 156_juzgar_pendientes_top10.py --dry-run               # plan; no ejecuta llamadas
```

## Decisión sobre el KPI

El objetivo de precisión del Sprint 2 (P@5 ≥ 0,700 · nDCG@10 ≥ 0,750) procede de un arnés que decidía
la relevancia por coincidencia de patrones en el título, retirado en septiembre tras medirlo contra 470
juicios reales (precisión 0,697 · recall 0,929). **Los dos instrumentos no son comparables**: el KPI se
reformula en las unidades del juez como mejora pareada con intervalo de confianza, y las cifras de
0,700/0,750 se conservan como referencia histórica del arnés retirado. La comparación con datos.gob.es
(P@5 0,622 · nDCG@10 0,667) es una medición propia sobre el portal real, no un dato publicado por
Red.es, y hoy no es recalculable con el juez porque su SERP no expone el identificador de dataset.

## Vuelta atrás

Borrar `gt_etiquetas_v6.json`, `juicio_pendientes.json`, `fase_h_METRICAS_v6.json` y
`_checkpoint_pendientes.json`. `gt_etiquetas_v5.json` no se ha modificado en ningún momento.
