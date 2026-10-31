# Resumen: precios off-peak Ollama Cloud y política de uso LLM

**Fecha**: 2026-09-06 · **Documento completo**: [`../wiki-buscador-okf/decisions/politica-uso-llm-offpeak.md`](../wiki-buscador-okf/decisions/politica-uso-llm-offpeak.md)

## Qué ha cambiado

Ollama Cloud aplica un **50% de descuento en DeepSeek-V4** fuera de horas pico:

- **Off-peak**: antes de 12:00 UTC o después de 18:00 UTC en laborables, y **todo el fin de semana**.
- **Peak**: de 12:00 a 18:00 UTC, L-V. En hora española (CEST): **14:00–20:00 L-V**.
- ⚠️ En invierno (CET) la ventana peak pasa a 13:00–19:00 — revisar con el cambio de hora.

| Modelo | Input peak | Input off-peak | Output peak | Output off-peak |
|---|---:|---:|---:|---:|
| deepseek-v4-flash | $0.44 | **$0.22** | $1.32 | **$0.66** |
| deepseek-v4-pro | $1.32 | **$0.66** | $3.96 | **$1.98** |

## Política aplicada al PFM

| Caso de uso | Modelo | Franja |
|---|---|---|
| Interactivos (re-ranking, expansión, chat, TL;DR individual) | `deepseek-v4-flash:cloud` | siempre |
| **Batches diferibles** (perfiles 87k, descripciones, RAGAS, ground truth) | `deepseek-v4-flash:cloud` | **off-peak** |
| Análisis complejo no interactivo | `deepseek-v4-pro:cloud` | **off-peak** |

## Coste del batch de enriquecimiento (87.676 datasets, ~2k in / ~0.5k out)

| Escenario | USD | EUR |
|---|---:|---:|
| flash off-peak | $68 | **~62 €** |
| flash peak | $135 | ~124 € |
| pro off-peak | $203 | ~186 € |
| pro peak | $405 | ~373 € |

**Recomendación**: ejecutar el batch de enriquecimiento un **fin de semana** en
tramos (límite de 5h por ventana; ~27-37 h totales) con
`deepseek-v4-flash:cloud` — ~62 €, la mitad que en horario pico.