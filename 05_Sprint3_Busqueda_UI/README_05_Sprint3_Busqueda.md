# Fase 05 - Sprint 3: Motor de Búsqueda

## 📋 Resumen

Implementación del motor de búsqueda híbrida (semántica + léxica) con API REST y frontend.

## 🎯 Objetivos

- Motor de búsqueda con combinación ponderada semántica/léxica
- API REST para consultas
- Frontend interactivo (Streamlit)
- Filtros facetados por territorio, temática, formato

## 📁 Estructura

```
05_Sprint3_Busqueda_UI/
├── codigo/
│   ├── api/
│   │   ├── main.py              # API FastAPI
│   │   └── launch_dev.sh        # Script lanzamiento
│   ├── frontend/
│   │   ├── app.py               # Aplicación Streamlit
│   │   ├── components.py        # Componentes UI
│   │   ├── utils.py             # Utilidades
│   │   ├── analisis_indices.py  # Análisis de índices
│   │   ├── diagnostico.py       # Diagnóstico general
│   │   ├── diagnostico_busqueda.py # Diagnóstico de búsqueda
│   │   └── facetas.json         # Configuración facetas
│   ├── motor/
│   │   └── search_engine.py     # Motor híbrido
│   └── tests/
│       └── test_search.py       # Tests unitarios motor
├── docs/
│   ├── GUIA_EJECUCION.md        # Guía ejecución
│   ├── algoritmo/
│   │   └── ranking.md           # Documentación ranking
│   └── arquitectura/
│       └── ALMACENAMIENTO.md    # Arquitectura PoC + roadmap PostgreSQL
└── entregables/
    └── resumen_fase05.md        # Resumen fase
```

## 🚀 Ejecución

```bash
# API
./codigo/api/launch_dev.sh

# Frontend
streamlit run codigo/frontend/app.py

# Tests unitarios motor
cd codigo/tests && python test_search.py
```

## 📊 Tests

Los tests de evaluación de calidad están en **Fase 06 - Sprint 4 Evaluación**.

## 🗄️ Arquitectura de Almacenamiento

La fase 05 implementa un **PoC con almacenamiento en memoria** (NumPy + Python) por simplicidad y velocidad de desarrollo.

**Documentación completa:** [`docs/arquitectura/ALMACENAMIENTO.md`](docs/arquitectura/ALMACENAMIENTO.md)

### Resumen de decisiones

| Aspecto | Decisión | Justificación |
|---------|----------|---------------|
| **Almacenamiento** | NumPy en memoria | Simplicidad, velocidad de iteración |
| **Persistencia** | Archivos `.npy` + `.jsonl` | Suficiente para 87K datasets |
| **Escalabilidad** | Limitada a RAM | Aceptable para el alcance del TFM |
| **Producción** | PostgreSQL + pgvector | Roadmap definido en documento |

### Roadmap PostgreSQL

- **Fase 1** (post-entrega): Schema + migración de datos
- **Fase 2** (post-entrega): Motor adaptado a SQL
- **Fase 3** (post-entrega): Dockerización completa

**Timeline estimado:** 1-1.5 semanas de trabajo post-entrega.

## 🔗 Relación con otras fases

- **Fase 04**: Recibe índices de embeddings
- **Fase 06**: Recibe tests de evaluación de calidad
- **Fase 09**: UI de lista de resultados sirve como base para modo conversacional (chatbot futuro)
