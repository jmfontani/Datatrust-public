# 📊 Evaluación de Normalización Conceptual - Experimental

**Fecha**: 2026-06-06T09:36:21.050573
**Queries evaluadas**: 10
**API**: http://localhost:8000

---

## 📈 Resumen Comparativo

### Precision@5

| Modo | P@5 | vs Básico |
|------|-----|-----------|
| **Básico** | 0.5200 | - |
| **Anotado** | 0.5200 | +0.0000 |
| **Ajustado** | 0.5200 | +0.0000 |

### Precision@10

| Modo | P@10 | vs Básico |
|------|------|-----------|
| **Básico** | 0.5300 | - |
| **Anotado** | 0.5300 | +0.0000 |
| **Ajustado** | 0.5300 | +0.0000 |

### NDCG@10

| Modo | NDCG@10 | vs Básico |
|------|---------|-----------|
| **Básico** | 0.5343 | - |
| **Anotado** | 0.5343 | +0.0000 |
| **Ajustado** | 0.5343 | +0.0000 |

### Tiempo Medio por Query

| Modo | Tiempo (ms) | Overhead |
|------|-------------|----------|
| **Básico** | 62.5ms | - |
| **Anotado** | 33.4ms | +-29.1ms |
| **Ajustado** | 33.7ms | +-28.8ms |

---

## 📊 Distribución de Clasificaciones Conceptuales

### Modo Anotado
| Clasificación | Count |
|---------------|-------|
| Equivalente | 0 |
| Relacionado | 0 |
| Complementario | 0 |
| No equivalente | 0 |
| Desconocido | 100 |

### Modo Ajustado
| Clasificación | Count |
|---------------|-------|
| Equivalente | 0 |
| Relacionado | 0 |
| Complementario | 0 |
| No equivalente | 0 |
| Desconocido | 100 |

---

## 🎯 Criterios de Éxito

| Criterio | Target | Resultado | Estado |
|----------|--------|-----------|--------|
| Mejora P@5 | +5-10% | +0.0% | ⚠️ |
| Mejora NDCG@10 | Apreciable | +0.0% | ⚠️ |
| Overhead latencia | <20ms | +-28.8ms | ✅ |

---

## 📝 Conclusiones

⚠️ La normalización conceptual NO muestra mejora significativa.

✅ El overhead de latencia es aceptable (<20ms).

### Recomendación

**NO INCORPORAR** la normalización conceptual en su estado actual. Se recomienda:
- Ampliar el diccionario de conceptos
- Ajustar los multiplicadores de score
- Refinar las reglas de clasificación

---

*Reporte generado automáticamente por `eval_conceptual_normalization.py` - Experimental*
