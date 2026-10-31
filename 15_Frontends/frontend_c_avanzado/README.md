# Frontend C — Avanzado (Demos con LLM)

**Estado:** 🟢 Movido el 2026-06-03, paths arreglados, sintaxis OK  
**Origen:** `08_Sprint6_LLM_Mejora/codigo/frontend/`  
**Producto opcional para la defensa** — demuestra el valor del LLM, no es obligatorio.

---

## 📂 Contenido

```
frontend_c_avanzado/
├── app_v09_demo.py            # Demo endpoints /llm/enhance y /llm/explain
├── app_query_enhanced.py      # Demo Query Preprocessor (casos LLM #3, #4, #12)
├── launch_query_enhanced.sh   # Script de arranque
└── assets/
    ├── logo_buscador_semantico.png
    └── logo_buscador_semantico.svg
```

## 🔧 Dependencias

- **API específica:** `main_v2_final_v07.py` con `router_v09` cargado (endpoints `/llm/enhance`, `/llm/explain`).
- **Ollama corriendo** localmente con `qwen2.5:7b` (recomendado, ya validado) o modelo cloud.
- **Query Preprocessor:** módulo en `08_Sprint6_LLM_Mejora/codigo/motor/query_preprocessor.py` (path ya arreglado).

## 🚀 Cómo arrancar

```bash
# Pre-requisitos:
# 1. API v07 corriendo en http://localhost:8000
# 2. Ollama con qwen2.5:7b disponible (ollama serve)

cd 15_Frontends/frontend_c_avanzado

# Demo V09 — re-ranking + explicaciones
streamlit run app_v09_demo.py --server.port 8502

# Query Preprocessor — validación + expansión
streamlit run app_query_enhanced.py --server.port 8503
```

## 🎯 Rol en la defensa

- **Pico técnico (3 min):** comparar mismo query con y sin LLM, mostrar la diferencia en el ranking.
- **Coloquio:** responder "¿el LLM aporta valor?" con un demo en lugar de palabras.
- **Plan B:** tener un vídeo de 3 min grabado por si Ollama falla en directo.

## ⚠️ Riesgos

- **Latencia alta:** ~3-5 s con modelo local, ~60-80 s con cloud. **El demo debe estar precalculado** o aceptar la espera ante el tribunal.
- **Dependencia de Ollama:** si Ollama no arranca, el demo falla. **Tener siempre un plan B con vídeo.**
- **Posible alucinación:** las explicaciones LLM a veces inventan conexiones. **No usar ejemplos no validados.**

## 🔗 Referencias cruzadas

- [`metodologia/05_VALOR_RAGAS.md`](../../metodologia/05_VALOR_RAGAS.md) — análisis del valor del LLM
- [`metodologia/06_DISENO_RAGAS.md`](../../metodologia/06_DISENO_RAGAS.md) — diseño de evaluación RAGAS
- `08_Sprint6_LLM_Mejora/docs/EVALUACION_QWEN_2026-06-01.md` — evaluación previa del LLM
