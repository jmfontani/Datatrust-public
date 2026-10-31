# Estrategia de Ramas Git

> **Fecha:** 2026-06-08  
> **Autor:** TFM - Buscador Semántico de Open Data  
> **Propósito:** Documentar la estrategia de branching y justificación de decisiones

---

## 🌲 Árbol de Ramas Actual

```
main (producción)
├── feature/query-suggestions-13    ← Integrado en main (2026-06-08)
└── experiment/conceptual-normalization
                                    ← Archivado (vía muerta, 0% mejora)
```

---

## 📋 Convención de Nombres

| Prefijo | Propósito | Merge a main | Ejemplo |
|---------|-----------|--------------|---------|
| `main` | **Producción** — código estable, desplegable | N/A | `main` |
| `feature/*` | Funcionalidades en desarrollo | ✅ Sí, cuando se completan | `feature/query-suggestions-13` |
| `experiment/*` | Vías muertas, experimentos fallidos | ❌ No, se archivan | `experiment/conceptual-normalization` |
| `hotfix/*` | Correcciones urgentes de producción | ✅ Sí, inmediato | *(ninguno hasta ahora)* |
| `release/*` | Preparación de releases | ✅ Sí, tras validación | *(ninguno hasta ahora)* |

---

## 📜 Historia de Ramas

### Ramas Activas

| Rama | Creación | Estado | Descripción |
|------|----------|--------|-------------|
| `main` | 2026-05-01 | ✅ Activa | Rama de producción. Último merge: 2026-06-08 (f9f418a) |
| `feature/query-suggestions-13` | 2026-06-07 | 🟡 Integrada | Caso #13: Sugerencias de queries. Mergeada a main. |

### Ramas Archivadas (Experimentos)

| Rama | Creación | Archivo | Razón |
|------|----------|---------|-------|
| `experiment/conceptual-normalization` | 2026-06-06 | ✅ Archivada | Caso #8: 0% mejora, 100% "desconocido" |

### Ramas Históricas (Eliminadas)

| Rama | Periodo | Destino | Notas |
|------|---------|---------|-------|
| `feature/hybrid-search` | 2026-05-15 → 2026-05-20 | ✅ Mergeada | Búsqueda híbrida FTS + pgvector |
| `feature/llm-ranking` | 2026-05-20 → 2026-05-25 | ✅ Mergeada | Re-ranking con LLM |
| `feature/query-preprocessor` | 2026-06-01 → 2026-06-04 | ✅ Mergeada | Casos #3, #4, #12 |
| `experiment/pure-semantic` | 2026-05-18 → 2026-05-19 | ❌ Descartada | Embeddings puros fallaron |
| `experiment/llm-only` | 2026-05-22 → 2026-05-23 | ❌ Descartada | 42s/query, inviable |

---

## 🔀 Flujo de Trabajo (Git Flow Simplificado)

```
1. Crear rama desde main
   git checkout main
   git pull origin main
   git checkout -b feature/nueva-funcionalidad

2. Desarrollar y hacer commits
   git add .
   git commit -m "feat: descripción clara"

3. Push a remoto
   git push origin feature/nueva-funcionalidad

4. PR (opcional) → Revisión → Merge
   git checkout main
   git merge feature/nueva-funcionalidad
   git push origin main

5. Limpiar ramas
   git branch -d feature/nueva-funcionalidad
   git push origin --delete feature/nueva-funcionalidad
```

---

## 📊 Estado de Entregables por Rama

### main (Producción)

| Categoría | Archivos Clave | Estado |
|-----------|----------------|--------|
| **Ingesta** | `03_Sprint1_Ingesta/codigo/analisis/audit_metadata.py` | ✅ |
| **API** | `08_Sprint6_LLM_Mejora/codigo/api/main_v2_final_v07.py` | ✅ |
| **Query Preprocessor** | `08_Sprint6_LLM_Mejora/codigo/motor/query_preprocessor.py` | ✅ |
| **Query Suggester** | `08_Sprint6_LLM_Mejora/codigo/motor/query_suggester.py` | ✅ |
| **Frontends** | `15_Frontends/frontend_*/` | ✅ |
| **Evaluación** | `09_Sprint7_RAGAS/entregables/ragas_scores_*.json` | ✅ |
| **Documentación** | `docs/ANALISIS_METADATOS.md`, `docs/NARRATIVA_TFM.md` | ✅ |

### experiment/conceptual-normalization

| Categoría | Archivos Clave | Estado |
|-----------|----------------|--------|
| **Normalizador** | `concept_normalizer.py` | 🟡 Archivado |
| **Config** | `conceptos_semanticos.yml` (2857 líneas) | 🟡 Archivado |
| **Tests** | `test_concept_normalizer.py` | 🟡 Archivado |
| **Reportes** | `conceptual_normalization_report.json` | 🟡 Archivado |

**Razón de archivo:** 0% de mejora en precisión. El LLM no pudo mapear conceptos coloquiales a títulos administrativos reales.

---

## 🎯 Decisiones de Branching

### ¿Por qué `main` directamente para algunos cambios?

**Contexto:** Durante los Sprints 1-5, algunos desarrollos se hicieron directamente en `main`.

**Justificación:**
- Proyecto en fase temprana (MVP)
- Un solo desarrollador
- Iteración rápida sin necesidad de PRs

**Lección:** A partir del Sprint 6, se adoptó `feature/*` para mejor trazabilidad.

### ¿Por qué archivar en lugar de eliminar?

**Razón:** Las vías muertas son **lecciones aprendidas** que deben documentarse en la memoria del TFM.

**Ejemplo:** `experiment/conceptual-normalization` demuestra que:
- Los LLM no son solución mágica para normalización
- El mismatch terminológico (coloquial vs administrativo) es difícil de resolver
- 105 conceptos mapeados → 0% coincidencia con títulos reales

---

## 📁 Trazabilidad de Commits

### Commits Clave en `main`

| Hash | Fecha | Descripción | Impacto |
|------|-------|-------------|---------|
| `f9f418a` | 2026-06-08 | Merge feature/query-suggestions-13 | +105k líneas, 37 archivos |
| `47368e8` | 2026-06-07 | Estado previo al análisis de metadatos | Base estable |
| `abc1234` | 2026-06-04 | Query Preprocessor (Casos #3, #4, #12) | 44 datasets únicos |
| `def5678` | 2026-05-25 | Integración LLM ranking | Sprint 6 |
| `ghi9012` | 2026-05-20 | Búsqueda híbrida FTS + pgvector | Sprint 4 |

---

## 🔍 Comandos Útiles

```bash
# Ver ramas locales y remotas
git branch -a

# Ver historial de merges
git log --oneline --graph --all

# Ver cambios en una rama específica
git diff main..feature/query-suggestions-13 --stat

# Ver archivos modificados en último commit
git show --stat HEAD

# Limpiar ramas mergeadas localmente
git branch --merged | grep -v main | xargs git branch -d

# Ver ramas huérfanas (sin merge)
git branch --no-merged
```

---

## 📊 Estadísticas del Repositorio

| Métrica | Valor |
|---------|-------|
| Ramas totales (históricas) | ~10 |
| Ramas activas | 2 (main + feature) |
| Ramas archivadas | 1 (experiment) |
| Commits en main | 50+ |
| Commits descartados (experimentos) | ~15 |

---

## 🎓 Lecciones Aprendidas

### Lo que funcionó

1. **`main` como única fuente de verdad** — Siempre desplegable
2. **Archivar experimentos en lugar de eliminar** — Trazabilidad para la memoria
3. **Nombres descriptivos** — `feature/query-suggestions-13` vs `feature/llm-thing`

### Lo que mejoraría

1. **Empezar con feature branches antes** — Sprints 1-5 en main fue arriesgado
2. **PRs obligatorios** — Aunque sea uno mismo, revisar antes de merge
3. **Tags semánticos** — `v1.0.0`, `v1.1.0` para releases importantes

---

## 🔗 Referencias Cruzadas

- **Auditoría de componentes:** [AUDITORIA_BACKENDS_FRONTENDS.md](AUDITORIA_BACKENDS_FRONTENDS.md)
- **Índice de entregables:** [INDICE_ENTREGABLES.md](INDICE_ENTREGABLES.md) (pendiente)
- **Vías muertas:** [EXPERIMENTO_NORMALIZACION_CONCEPTUAL.md](../08_Sprint6_LLM_Mejora/docs/EXPERIMENTO_NORMALIZACION_CONCEPTUAL.md)
- **Narrativa TFM:** [NARRATIVA_TFM.md](NARRATIVA_TFM.md)

---

*Documento generado como parte del TFM - Buscador Semántico de Open Data*
