# Casos de Uso LLM - Indice del Sprint 6

## Resumen

El proyecto define **14 casos de uso de LLM** para mejorar la busqueda semantica:

| Estado | Cantidad | Casos |
|--------|----------|-------|
| Implementados y estables | 8/14 | #1, #2, #3, #4, #5, #12, #13, #14 |
| Archivados (via muerta) | 1/14 | #8 |
| Pendientes | 5/14 | #6, #7, #9, #10, #11 |

## Implementados

### #1 + #2: Re-ranking inteligente + explicaciones
- Toma Top-N resultados del motor hibrido y los reordena con LLM.
- Genera explicaciones de relevancia por dataset.
- Archivos: `llm_reranker.py`, `routes_llm_v2.py`.
- Latencia: ~60-80s por query (cloud).
- Conclusion: LLM acierta siempre en posicion 1, sobrevalora posiciones 2-3.

### #3 + #4 + #12: Interpretacion + expansion + validacion de queries
- Pipeline de preprocesamiento.
- Valida queries, extrae estructura y expande con sinonimos.
- Fallback lexico implementado (resuelve 88% de fallos de expansion).
- Archivos: `query_preprocessor.py`, `lexical_expander.py`, `routes_query_enhanced.py`.
- Latencia: ~10-30s por query.

### #5: Deteccion de datasets complementarios
- Identifica datasets combinables analiticamente.
- Archivos: `routes_complementary.py`, `batch_generate_profiles.py`.
- Endpoint: `POST /complementary/find`.
- Latencia: ~8-15s.

### #13: Sugerencias de queries relacionadas
- Propone busquedas alternativas (lexico + LLM background).
- Archivo: `query_suggester.py`.
- Latencia: <5ms (lexico) + ~3-5s (LLM background).
- 20 tests unitarios passing.

### #14: Resumen automatico de datasets (TL;DR)
- Genera resumen de 2-3 frases por dataset.
- Archivo: `batch_generate_profiles.py`, `routes_complementary.py`.
- Endpoint: `GET /complementary/{id}/tldr`.
- Batch offline + <100ms runtime.

## Archivado

### #8: Normalizacion semantica de conceptos
- Estado: via muerta tras 0% de mejora.
- Causa: mismatch terminologico entre diccionario coloquial y lenguaje administrativo de los datasets.
- Rama: `experiment/conceptual-normalization`.

## Pendientes

| # | Caso | Descripcion |
|---|------|-------------|
| #6 | Evaluacion de compatibilidad | Analiza si dos datasets pueden unirse tecnicamente |
| #7 | Generacion de planes de analisis | Crea propuestas de analisis combinatorio |
| #9 | Perfilado tecnico automatico | Describe campos, formatos y calidad del dataset |
| #10 | Respuestas a preguntas sobre datasets | Chat sobre un dataset especifico |
| #11 | Sintesis de multiples datasets | Resume varios datasets como grupo coherente |

## Archivos relevantes

```
08_Sprint6_LLM_Mejora/
├── docs/
│   ├── INDICE_CASOS_USO_LLM.md          (este resumen)
│   ├── CASO_13_QUERY_SUGGESTIONS.md
│   ├── INFORME_FINAL_4_ITERACIONES.md     (#1 + #2)
│   └── EVALUACION_QWEN_2026-06-01.md
├── codigo/
│   ├── motor/
│   │   ├── llm_client.py                # Cliente generico LLM
│   │   ├── llm_reranker.py              # #1 + #2
│   │   ├── query_preprocessor.py        # #3 + #4 + #12
│   │   ├── lexical_expander.py          # Fallback #4
│   │   └── query_suggester.py           # #13
│   ├── api/
│   │   ├── routes_llm_v2.py             # #1 + #2
│   │   ├── routes_query_enhanced.py     # #3 #4 #12 #13
│   │   ├── routes_complementary.py      # #5 + #14
│   │   └── main_v2_final_v07.py         # API principal
│   └── tests/
│       ├── test_query_preprocessing.py
│       ├── test_query_suggester.py      # 20 tests
│       └── test_sprint8_paquete_a.py
└── README_08_Sprint6_LLM_Mejora.md
```
