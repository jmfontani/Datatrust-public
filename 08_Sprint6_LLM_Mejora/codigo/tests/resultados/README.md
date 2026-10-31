# Tests Comparativos Sprint 08

Este directorio contiene los resultados del test comparativo entre **Sprint 07 (baseline)** y **Sprint 08 (re-ranking con LLM)**.

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `RESUMEN_TEST_v07_vs_v08.md` | Análisis ejecutivo completo (actualizado) |
| `test_v07_vs_v08_20queries_2025-05-26.json` | Datos completos test principal (JSON) |
| `test_comparativo_20_queries.py` | Script del test principal (20 queries) |
| `test_complementario_timeout_results.json` | Datos test complementario (6 queries) |
| `test_complementario_timeout_queries.py` | Script test complementario |

## Tests Disponibles

### 1. Test Principal (20 queries)

```bash
python3 test_comparativo_20_queries.py \
  --v07-url http://localhost:8000 \
  --v08-url http://localhost:8000 \
  --output resultados_nuevo_test.json
```

**Tiempo estimado**: ~25-30 minutos

**Subset rápido** (5 queries):
```bash
python3 test_comparativo_20_queries.py --subset 5
```

### 2. Test Complementario (6 queries timeout)

Para verificar queries que tuvieron timeout en el test principal:

```bash
python3 test_complementario_timeout_queries.py \
  --output resultados_verificacion.json
```

**Tiempo estimado**: ~7-10 minutos

## Requisitos

- API v07 corriendo en `http://localhost:8000`
- API v08 (con LLM) corriendo en el mismo puerto
- Ollama disponible en `host.docker.internal:11434`
- Python 3.11+ con `requests`

## Métricas Clave

- **Overlap**: % de resultados presentes en ambas versiones
- **Mejora ranking**: Cambio promedio de posición (positivo = mejoró)
- **Items reordenados**: Cuántos items cambiaron de posición
- **Tiempo v08**: Latencia promedio del re-ranking

## Resultados Principales (Actualizados)

Ver `RESUMEN_TEST_v07_vs_v08.md` para el análisis completo.

### Resumen Corregido (Post-Test Complementario)

| Métrica | Valor Original | Valor Corregido |
|---------|----------------|-----------------|
| Overlap | 88% | **89%** |
| Items reordenados | 80 | **102** |
| Mejora ranking | -0.03 | **-0.04** |
| Tiempo v08 | ~85s | **~80s** |

### Por Categoría (Datos Completos)

| Categoría | Mejora | Items Reordenados |
|-----------|--------|-------------------|
| Sinonimia | **+0.26** ⭐ | 26 |
| Conceptual | **+0.31** | 21 |
| Territorial | **-0.33** | 15 |
| Temporal | -0.08 | 18 |
| Facetada | -0.44 | 5 |
| Metadatos | -0.39 | 17 |

### Conclusiones

1. **Funciona técnicamente**: 102 items reordenados con éxito
2. **Timeouts fueron puntuales**: Verificación complementaria exitosa
3. **Sin mejora global**: -0.04 posiciones (neutral)
4. **Destacado**: Sinonimia y Conceptuales muestran mejora positiva

---

**Generado**: 2025-05-26  
**Última actualización**: 2025-05-26 (test complementario completado)
