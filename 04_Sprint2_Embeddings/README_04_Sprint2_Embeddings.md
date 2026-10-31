# Fase 04: Sprint 2 — Embeddings e Indexación

## Proyecto: Buscador Semántico de Datasets Públicos
**Estado:** ✅ COMPLETADO
**Última actualización:** 2026-05-22

---

## 🎯 Objetivo

Generar embeddings vectoriales para todos los datasets limpios (87.677) y crear los índices de búsqueda necesarios para recuperación eficiente.

---

## ✅ Completado

### 1. Embeddings para 87.677 datasets
| Parámetro | Valor |
|-----------|-------|
| **Modelo** | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| **Dimensiones** | 384D |
| **Shape** | (87.677, 384) |
| **Normalización** | L2 ✅ |
| **Tamaño** | ~129 MB |
| **Tiempo** | 19 min 22 seg |
| **Ubicación** | `04_Sprint2_Embeddings/datos/processed/embeddings.npy` |

### 2. Índices de búsqueda creados
| Índice | Tamaño | Descripción |
|--------|--------|-------------|
| `id_position_map.json` | 9.2 MB | 87.677 IDs → posición en embeddings |
| `index_tema.json` | 13 MB | 42 temas → 123.496 referencias |
| `index_territorio.json` | 8.7 MB | 37 territorios → 87.677 referencias |
| `index_publisher.json` | 8.7 MB | 182 publishers → 87.677 referencias |
| `bm25_index.pkl` | 58 MB | Índice léxico BM25 |
| `index_meta.json` | 529 B | Metadatos |

### 3. Scripts creados
- `build_indices.py` — Construye todos los índices (6.9 segundos)
- `search_hybrid.py` — Motor de búsqueda híbrida (semántica + léxica + filtros facetados)

---

## 📁 Estructura de archivos

```
04_Sprint2_Embeddings/
├── README_04_Sprint2_Embeddings.md       # ← este documento
├── codigo/
│   └── indexacion/
│       ├── build_indices.py                # Crea índices inversos
│       └── search_hybrid.py                # Búsqueda híbrida
├── datos/
│   ├── processed/
│   │   ├── embeddings.npy                  # Embeddings (129 MB)
│   │   └── embeddings_meta.json            # Metadatos
│   └── indices/
│       ├── id_position_map.json            # Mapa ID → posición
│       ├── index_tema.json                 # Índice tema → IDs
│       ├── index_territorio.json           # Índice territorio → IDs
│       ├── index_publisher.json            # Índice publisher → IDs
│       ├── index_formato.json              # Índice formato → IDs (vacío)
│       ├── bm25_index.pkl                  # Índice BM25
│       └── index_meta.json                 # Metadatos de índices
└── docs/
    └── arquitectura_indices.md             # Documentación de índices
```

---

## 🔜 Pendiente para fases siguientes

### Fase 05: Búsqueda + UI
- [x] Exponer búsqueda híbrida como endpoint REST (FastAPI)
- [x] Implementar paginación y facetas
- [x] Visualizar resultados con filtros activos (Streamlit)
- [x] Mostrar scores descompuestos (semántico + léxico)

### Fase 06: Evaluación
- [x] Evaluar calidad de embeddings con queries de prueba (41 tests)
- [x] Ajustar pesos semántico/lexical en búsqueda híbrida
- [x] Comparar recall@K vs búsqueda solo semántica

### Fase 07: Integración (PostgreSQL + Docker)
- [ ] Schema con pgvector
- [ ] Migración de datos a PostgreSQL
- [ ] Dockerización completa

### Fase 08: Documentación
- [ ] Redacción de memoria
- [ ] Anexos técnicos

---

## Notas

- Los **datos limpios** (datasets_clean.jsonl) permanecen en `03_Sprint1_Ingesta/datos/processed/` porque son el output de esa fase
- Los **embeddings** e **índices** están en `04_Sprint2_Embeddings/` como corresponde
- El índice de formatos está vacío porque `format_labels` no está en los datasets limpios. Se puede regenerar desde los datos crudos si hace falta.
- El mapa ID → posición es crítico para alinear embeddings con metadatos
