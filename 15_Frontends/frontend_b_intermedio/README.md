# Frontend B — Intermedio (Producto Principal)

**Estado:** 🟢 Operativo (2026-06-16)  
**Origen:** `07_Sprint5_Integracion/codigo/frontend_v2/`  
**Producto principal del proyecto** — es el que se enseña en la defensa.

---

## 📚 Documentación completa

- [`DOCUMENTACION_SPRINT10.md`](DOCUMENTACION_SPRINT10.md): Journey maps, flujos, guión de defensa, checklist.
- [`README_VERSIONS.md`](README_VERSIONS.md): Diferencias entre modo público y modo avanzado.
- [`legacy/README.md`](legacy/README.md): Archivos antiguos archivados y lecciones aprendidas.

---

## ✅ Estado actual

El frontend se ha refactorizado en una **arquitectura unificada** con dos modos:

- **Modo público**: interfaz rápida y visual para usuarios finales.
- **Modo avanzado**: demostrador técnico con controles y capacidades LLM.

Ambos modos se sirven desde un único punto de entrada (`app.py`) en el puerto `8501`.

---

## 📂 Contenido

```
frontend_b_intermedio/
├── app.py                       # Entrypoint unificado (detecta ?mode=)
├── public/
│   ├── app.py                   # Modo público (interfaz principal)
│   └── components.py            # Componentes del modo público
├── advanced/
│   ├── app.py                   # Modo avanzado (demostrador técnico)
│   └── __init__.py
├── common/
│   ├── utils.py                 # Utilidades compartidas (llamadas API, facetas)
│   └── __init__.py
├── legacy/                      # Archivos antiguos archivados
│   ├── README.md
│   ├── app_original.py
│   ├── app_router.py
│   ├── components_v2.py
│   ├── app_query_enhanced.py
│   ├── app_v09_demo.py
│   ├── app_v13_query_suggestions.py
│   └── assets/
├── README.md                    # este archivo
├── README_V2_ORIGEN.md          # Documentación original del V2
└── README_VERSIONS.md           # Modo público vs avanzado
```

---

## 🚀 Cómo arrancar

```bash
# Pre-requisito: API corriendo en http://localhost:8001
cd 15_Frontends/frontend_b_intermedio

# Entrypoint unificado
streamlit run app.py --server.port 8501

# Modo público (por defecto)
# http://localhost:8501

# Modo avanzado
# http://localhost:8501/?mode=advanced
```

La URL de la API se configura con la variable de entorno `API_URL` (por defecto `http://localhost:8001`):

```bash
API_URL=http://mi-servidor:8001 streamlit run app.py --server.port 8501
```

---

## 🎯 Rol en la defensa

- **Defensa principal (15 min):** usar el modo público (`http://localhost:8501`).
- **Coloquio:** si el tribunal pregunta por la versión técnica o las capacidades LLM, mostrar `?mode=advanced`.
- **Evolución del proyecto:** explicar que los frontends antiguos y demos están archivados en `legacy/` como lecciones aprendidas.

---

## 🔍 Personalización (opcional)

- Colores y estilos del modo público: `public/components.py` (`THEME_COLORS`).
- Pesos por defecto de la búsqueda pública: `public/app.py`, función `execute_search()`.
- Controles técnicos del modo avanzado: `advanced/app.py`.
- Utilidades compartidas: `common/utils.py`.
