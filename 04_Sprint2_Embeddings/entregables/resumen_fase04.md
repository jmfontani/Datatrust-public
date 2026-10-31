# Entregables Fase 04 – Sprint 2: Embeddings e Indexación

## Resumen Ejecutivo

Se han generado embeddings semánticos para los 87.677 datasets limpios y construido 6 índices auxiliares para búsqueda híbrida.

## Artefactos generados

### Datos
| Archivo | Tamaño | Descripción |
|---------|--------|-------------|
| `datos/processed/embeddings.npy` | ~135 MB | Matriz de embeddings 87.677×384 float32 |
| `datos/processed/embeddings_meta.json` | 369 B | Metadatos del modelo y parámetros |
| `datos/indices/index_tema.json` | Variable | Índice invertido por tema |
| `datos/indices/index_territorio.json` | Variable | Índice invertido por territorio |
| `datos/indices/index_formato.json` | Variable | Índice invertido por formato |
| `datos/indices/index_publisher.json` | Variable | Índice invertido por publisher |
| `datos/indices/id_position_map.json` | Variable | Mapa ID dataset → posición en embeddings |
| `datos/indices/bm25_index.pkl` | Variable | Índice BM25 para ranking textual |
| `datos/indices/index_meta.json` | ~1 KB | Metadatos de los índices construidos |

### Código
| Script | Ubicación | Descripción |
|--------|-----------|-------------|
| `build_indices.py` | `codigo/indexacion/` | Construcción de índices invertidos y BM25 |
| `search_hybrid.py` | `codigo/indexacion/` | Motor de búsqueda híbrida (semántica + filtros + BM25) |

### Documentación
| Documento | Ubicación |
|-----------|-----------|
| Comparativa de modelos evaluados | `docs/modelos_evaluados/comparativa.md` |
| README de la fase | `README_04_Sprint2_Embeddings.md` |

## Validación

- [x] Embeddings: 87.677 registros × 384 dimensiones
- [x] Normalización L2 verificada
- [x] Índices invertidos: 4 filtros (tema, territorio, formato, publisher)
- [x] BM25 index construido sobre corpus completo
- [x] Mapa ID→posición consistente con embeddings.npy

## Estado: ✅ COMPLETADA

*Generado: 2026-05-22*
