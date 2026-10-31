# Fase 04 – Sprint 2: Embeddings e Indexación

## Objetivo
Generar representaciones vectoriales (embeddings) de los datasets limpios y construir índices auxiliares para búsqueda híbrida (semántica + filtrada).

---

## Estado del arte – Modelos evaluados

| Modelo | Dim | Idioma | Pros | Contras | Decisión |
|--------|-----|--------|------|---------|----------|
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | Multi (incl. ES) | Rápido, buen balance calidad/tamaño | Menor precisión que modelos grandes | ✅ **Elegido** |
| all-MiniLM-L6-v2 | 384 | EN | Muy rápido | Solo inglés, datasets son español | ❌ |
| distiluse-base-multilingual-cased-v2 | 512 | Multi | Buen rendimiento | Más lento, mayor tamaño | ❌ |
| Instructor-xl | 768 | Multi | Alta calidad con instrucciones | Muy lento para inferencia masiva | ❌ |

**Criterios de selección:**
1. Soporte de español (obligatorio, datos de datos.gob.es)
2. Tamaño de modelo razonable para CPU (servidor sin GPU)
3. Dimensiones ≤ 512 (compromiso calidad vs. almacenamiento)
4. Normalización L2 para búsqueda por similitud coseno directa

**Resultado:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384D, normalizado L2)

---

## Proceso de generación

1. **Input:** `03_Sprint1_Ingesta/datos/processed/datasets_clean.jsonl` (87.677 datasets)
2. **Texto a vectorizar:** `title + " — " + description` (truncado a 512 tokens)
3. **Batch size:** 32 en CPU
4. **Tiempo estimado:** ~22 minutos (67 docs/s en CPU)
5. **Output:**
   - `datos/processed/embeddings.npy` – matriz 87.677 × 384 float32 (135 MB)
   - `datos/processed/embeddings_meta.json` – metadatos del modelo

---

## Índices construidos

| Índice | Tipo | Descripción | Archivo |
|--------|------|-------------|---------|
| Tema | Invertido | theme → [dataset_ids] | `index_tema.json` |
| Territorio | Invertido | territory → [dataset_ids] | `index_territorio.json` |
| Formato | Invertido | format → [dataset_ids] | `index_formato.json` |
| Publisher | Invertido | publisher → [dataset_ids] | `index_publisher.json` |
| ID→Posición | Map | dataset_id → índice en embeddings.npy | `id_position_map.json` |
| BM25 | Pickle | Índice BM25 sobre títulos+descripciones | `bm25_index.pkl` |
| Meta | JSON | Resumen de índices construidos | `index_meta.json` |

---

## Métricas de la fase

| Métrica | Valor |
|---------|-------|
| Datasets vectorizados | 87.677 |
| Dimensiones por vector | 384 |
| Espacio en disco (embeddings) | ~135 MB |
| Tiempo de generación | ~22 min CPU |
| Índices auxiliares | 6 |

---

## Notas técnicas

- Los embeddings están **normalizados L2**, por lo que producto escalar = similitud coseno.
- La búsqueda híbrida combina: similitud semántica (embeddings) + filtrado por índices invertidos + ranking BM25.
- El índice BM25 requiere `rank_bm25` y se serializa con pickle.

---

## Próximos pasos (Fase 05)

- Evaluar calidad de búsqueda con queries reales
- Ajustar pesos de componentes híbridos (semántico vs. BM25 vs. filtros)
- Preparar dataset de evaluación con relevancia anotada

---

*Generado: 2026-05-22*
