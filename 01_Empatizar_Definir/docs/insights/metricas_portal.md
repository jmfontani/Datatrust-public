# Métricas del Portal - datos.gob.es

## Proyecto: Buscador Semántico de Datasets Públicos
**Fecha:** Junio 2026
**Objetivo:** Establecer métricas baseline del portal actual

---

## 📊 Métricas de búsqueda manual

### Método

Cada miembro del equipo ejecuta 10 búsquedas en datos.gob.es y registra:
- Query utilizada
- Tiempo hasta primer resultado relevante
- Número de resultados relevantes en top 5
- Dataset esperado vs encontrado
- Nivel de frustración (1-5)

### Resultados consolidados

| Métrica | Valor | N muestras |
|---------|-------|------------|
| **Tiempo promedio** | [Pendiente] min | 0 |
| **Tiempo mediano** | [Pendiente] min | 0 |
| **Precisión@5** | [Pendiente] % | 0 |
| **Tasa de éxito** | [Pendiente] % | 0 |
| **Frustración promedio** | [Pendiente] /5 | 0 |

---

## 🔍 Observaciones estructurales del portal

| Aspecto | Estado | Notas |
|---------|--------|-------|
| Buscador principal | Funcional | Palabras clave exactas |
| Filtros disponibles | [Pendiente] | Tema, organismo, formato... |
| Paginación | [Pendiente] | Resultados por página |
| Preview datos | ❌ No existe | Solo título + descripción |
| API CKAN | ✅ Disponible | JSON, limitado |
| Metadatos DCAT-AP | ✅ Estándar | Pero incompletos en muchos datasets |

---

## 📈 Estadísticas del catálogo

| Métrica | Valor | Fuente |
|---------|-------|--------|
| Datasets totales | 113.313+ | CKAN API (mayo 2026) |
| Organismos | [Pendiente] | |
| Temas principales | [Pendiente] | |
| Formato más común | [Pendiente] | |
| Cobertura temporal | [Pendiente] | |

---

## 🎯 Baseline para comparar

Estas métricas servirán para medir la mejora del buscador semántico vs el portal actual.

| Escenario | Métrica actual | Objetivo buscador |
|-----------|---------------|-------------------|
| Query directa (fácil) | [Pendiente] | < 2 min, 80% Prec@5 |
| Query por intención (media) | [Pendiente] | < 3 min, 60% Prec@5 |
| Query compleja (difícil) | [Pendiente] | < 5 min, 40% Prec@5 |

---

## ✅ Checklist de recolección

- [ ] 6 miembros × 10 queries = 60 búsquedas ejecutadas
- [ ] Datos registrados en CSV (benchmark_resultados.csv)
- [ ] Métricas calculadas y documentadas
- [ ] Insights extraídos para diseño

---

*Documento vivo: Actualizar tras ejecución del benchmark*
