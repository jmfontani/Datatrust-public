# Fase 06 - Sprint 4: Evaluación y Métricas

## 📋 Resumen

Evaluación sistemática de la calidad del buscador semántico mediante baterías de tests.

## 🎯 Objetivos

- Evaluar calidad de resultados de búsqueda
- Medir precisión y recall del motor
- Identificar debilidades y áreas de mejora
- Documentar métricas de rendimiento

## 📁 Estructura

```
07_Sprint5_Evaluacion/
├── codigo/
│   └── benchmark/
│       ├── test_bateria.py              # Batería 12 tests
│       └── test_bateria_extendida.py  # Batería 40+ tests
├── datos/
│   └── queries_benchmark/
│       └── test_queries.json          # Queries de test
├── docs/
│   └── metricas/
│       └── ANALISIS_BATERIA_EXTENDIDA.md  # Análisis resultados
└── entregables/
    ├── test_report.json               # Reporte batería básica
    └── test_report_extendido.json     # Reporte batería extendida
```

## 🚀 Ejecución

```bash
# Requisitos: API corriendo en localhost:8000

# Batería básica (12 tests)
cd codigo/benchmark && python test_bateria.py

# Batería extendida (40+ tests)
cd codigo/benchmark && python test_bateria_extendida.py
```

## 📊 Métricas Evaluadas

- **Precisión**: % tests que cumplen criterios
- **Relevancia**: Términos esperados en resultados
- **Territorialidad**: Resultados con información geográfica
- **Rendimiento**: Tiempo de respuesta
- **Cobertura**: Diversidad de dominios

## 🔗 Relación con otras fases

- **Fase 05**: Evalúa el motor de búsqueda implementado
- **Fase 07**: Resultados alimentan mejoras de integración
