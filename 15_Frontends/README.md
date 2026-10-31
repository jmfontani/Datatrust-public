# Buscador Semántico — Frontends

**Carpeta centralizada de frontends del proyecto**  
**Fecha de creación:** 2026-06-03  
**Última refactorización:** 2026-06-16  
**Origen:** refactor desde `05_Sprint3_Busqueda_UI/codigo/frontend/`, `07_Sprint5_Integracion/codigo/frontend_v2/` y `08_Sprint6_LLM_Mejora/codigo/frontend/`

---

## 🎯 Propósito

Esta carpeta aísla los frontends del proyecto como productos independientes sobre el mismo backend (API FastAPI). Actualmente hay un **producto principal unificado** con dos modos, más un frontend histórico básico.

| Nivel | Carpeta | Producto | Perfil objetivo | Última revisión |
|-------|---------|----------|-----------------|-----------------|
| **A (básico)** | [`frontend_a_basico/`](frontend_a_basico/) | Streamlit MVP histórico (Sprint 3) | Referencia de evolución | 2026-06-03 |
| **B (intermedio)** | [`frontend_b_intermedio/`](frontend_b_intermedio/) | **Producto principal** con modo público + modo avanzado (`?mode=advanced`) | Usuarios finales + demos técnicas en defensa | 2026-06-16 |

> El antiguo frontend C (`frontend_c_avanzado/`) se ha archivado dentro de `frontend_b_intermedio/legacy/` como parte del relato de evolución y lecciones aprendidas.

---

## 📐 Reglas de la estructura

1. **Todos los frontends se sostienen sobre la misma API** (`http://localhost:8001`).
2. **El producto principal (B) tiene un único punto de entrada** (`app.py`) que carga el modo público o avanzado según `?mode=`.
3. **Los archivos antiguos no se borran**: se archivan en `legacy/` para conservar el relato de los sprints.
4. **Los diagnósticos y scripts de análisis NO se mueven aquí**: permanecen en sus sprints de origen.

---

## 🧱 Historia de los frontends

| Versión | Origen | Destino actual | Notas |
|---------|--------|----------------|-------|
| Frontend Streamlit inicial (Sprint 3) | `05_Sprint3_Busqueda_UI/codigo/frontend/` | **A** | Primera versión funcional, con controles de pesos. |
| Frontend V2 personalizable (Sprint 5) | `07_Sprint5_Integracion/codigo/frontend_v2/app.py` | **B → `legacy/app_original.py`** | Base del modo avanzado actual. |
| Frontend público / amigable (Sprint 5) | `07_Sprint5_Integracion/codigo/frontend_v2/app_public.py` | **B → `public/app.py`** | Interfaz principal del producto. |
| Demo V09 LLM (Sprint 6) | `08_Sprint6_LLM_Mejora/codigo/frontend/app_v09_demo.py` | **B → `legacy/app_v09_demo.py`** | Re-ranking y explicaciones LLM. |
| Demo Query Preprocessor (Sprint 6) | `08_Sprint6_LLM_Mejora/codigo/frontend/app_query_enhanced.py` | **B → `legacy/app_query_enhanced.py`** | Casos de uso LLM #3, #4, #12. |
| Demo Query Suggestions (Sprint 6) | `frontend_c_avanzado/app_v13_query_suggestions.py` | **B → `legacy/app_v13_query_suggestions.py`** | Caso de uso LLM #13. |

---

## 🚀 Cómo arrancar

```bash
# 1. Backend (siempre primero)
cd 08_Sprint6_LLM_Mejora/codigo/api
uvicorn main_v2_final_v07:app --host 0.0.0.0 --port 8001

# 2. Producto principal (modo público por defecto)
cd 15_Frontends/frontend_b_intermedio
streamlit run app.py --server.port 8501

# Modo público:  http://localhost:8501
# Modo avanzado: http://localhost:8501/?mode=advanced

# 3. Frontend A histórico (opcional)
cd 15_Frontends/frontend_a_basico
streamlit run app.py --server.port 8502
```

---

## 📂 Contenido de esta carpeta

```
15_Frontends/
├── README.md                       ← este archivo
├── MAPA_DECISION.md                ← criterios históricos para elegir A/B/C
├── frontend_a_basico/              ← MVP histórico (Sprint 3)
│   ├── app.py
│   ├── components.py
│   ├── utils.py
│   ├── facetas.json
│   ├── __init__.py
│   └── README.md
└── frontend_b_intermedio/          ← producto principal (refactorizado 2026-06-16)
    ├── app.py                      # entrypoint unificado
    ├── public/                     # modo público
    │   ├── app.py
    │   └── components.py
    ├── advanced/                   # modo avanzado/demostrador
    │   ├── app.py
    │   └── __init__.py
    ├── common/                     # utilidades compartidas
    │   ├── utils.py
    │   └── __init__.py
    ├── legacy/                     # archivos históricos archivados
    │   ├── README.md
    │   ├── app_original.py
    │   ├── app_router.py
    │   ├── components_v2.py
    │   ├── app_query_enhanced.py
    │   ├── app_v09_demo.py
    │   ├── app_v13_query_suggestions.py
    │   └── assets/
    ├── README.md
    ├── README_V2_ORIGEN.md
    └── README_VERSIONS.md
```

---

## 🔮 Trabajo futuro

- Completar documentación del modo avanzado con capturas y casos de uso.
- Evaluar la experiencia de usuario de ambos modos en la defensa.
- Considerar la extracción del modo avanzado como aplicación independiente si crece en funcionalidades.

---

*Esta carpeta es resultado del refactor aprobado el 2026-06-03 y de la refactorización de frontends del 2026-06-16.*
