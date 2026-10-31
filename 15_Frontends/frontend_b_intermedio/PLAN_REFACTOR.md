# Plan: Refactor de Frontends del Buscador Semántico

## Objetivo

Tener dos interfaces claras sobre el mismo puerto (`8501`):

1. **Versión ligera / pública** (`?mode=public` o por defecto): rápida, visual, sin controles técnicos. TL;DR, complementarios y chat deben ser opcionales y no intrusivos.
2. **Versión avanzada / demostrador** (`?mode=advanced`): laboratorio con todas las capacidades probadas (pesos ajustables, debug, LLM re-ranking, Query Preprocessor, sugerencias, TL;DR/complementarios/chat, diagnósticos).

Todo lo viejo se archiva en `legacy/` para conservar el relato de evolución y lecciones aprendidas.

---

## Estructura propuesta

```
15_Frontends/frontend_b_intermedio/
├── app.py                              # Entrypoint unificado (detecta mode)
├── public/
│   ├── __init__.py
│   ├── app.py                          # Versión ligera actual (refactorizada)
│   └── components.py                   # Componentes visuales de la ligera
├── advanced/
│   ├── __init__.py
│   ├── app.py                          # Versión avanzada/demostrador
│   └── components.py                   # Componentes exclusivos del modo avanzado
├── common/
│   ├── __init__.py
│   ├── utils.py                        # Utilidades compartidas (ex utils_v2.py)
│   └── components.py                   # Componentes compartidos (tarjetas base, etc.)
├── legacy/
│   ├── README.md                       # Índice y justificación de archivos archivados
│   ├── app_router.py
│   ├── app_original.py                 # app.py antiguo del Sprint 5
│   ├── components_v2.py
│   ├── app_query_enhanced.py           # Demo Query Preprocessor
│   ├── app_v09_demo.py                 # Demo LLM re-ranking
│   └── app_v13_query_suggestions.py    # Demo sugerencias
└── README.md                           # Documentación actualizada
```

---

## Tareas detalladas

### 1. Archivar lo viejo

Mover a `legacy/` sin borrar:
- `app_router.py`
- `app.py` original del Sprint 5 → `app_original.py`
- `components_v2.py`
- `frontend_c_avanzado/app_query_enhanced.py`
- `frontend_c_avanzado/app_v09_demo.py`
- `frontend_c_avanzado/app_v13_query_suggestions.py`

Crear `legacy/README.md` que explique:
- Qué contiene cada archivo.
- Por qué se archiva (duplicidad, obsolescencia, integración en modo avanzado).
- Lección aprendida.

### 2. Extraer utilidades comunes

- Renombrar `utils_v2.py` → `common/utils.py`.
- Asegurar que `API_URL` sigue leyendo la variable de entorno.
- Mantener timeouts: GET 30s, POST 60s.
- Añadir funciones que ahora están dispersas (health, search, facetas, TL;DR, complementarios, chat, query preprocessor, suggestions, rerank).

### 3. Extraer componentes compartidos

Crear `common/components.py` con:
- `render_dataset_card()`: tarjeta base de resultado reutilizable en ambos modos.
- `render_tldr_box()`, `render_complementary_box()`, `render_chat_box()`: widgets Sprint 8.
- Estilos CSS compartidos.

### 4. Refactorizar versión ligera

`public/app.py` partirá de `app_public.py` actual:
- Eliminar lógica de delegación a `mode=advanced`.
- Usar componentes de `common/`.
- Mantener: header, barra de búsqueda, filtros chips, búsquedas populares, tarjetas con TL;DR inline, expanders para complementarios/chat.
- Mejorar contraste y feedback visual de carga (spinner + cajas de color).
- Asegurar que el chat y complementarios no interfieren en el flujo habitual.

### 5. Crear versión avanzada

`advanced/app.py` será un demostrador técnico:
- Sidebar con controles de pesos semántico/léxico, min_score, require_lexical.
- Panel de diagnóstico de API (health, modelos, conteos).
- Búsqueda híbrida con opción de explicaciones por dataset.
- Pestañas/menú para demostrar:
  - **Búsqueda estándar**
  - **Re-ranking LLM** (`/llm/search/rerank` o `/v09/enhance`)
  - **Explicaciones LLM** (`/llm/explain` o `/v09/explain`)
  - **Query Preprocessor** (`/query/enhanced/analyze`, `/validate`, `/expand`)
  - **Query Suggestions** (`/query/suggest`)
  - **Perfiles Sprint 8** (TL;DR, complementarios, chat sobre datasets)
- Incluir tarjetas de resultados con todos los metadatos y scores.
- Modo debug opcional.

### 6. Entrypoint unificado

`app.py` en la raíz de `frontend_b_intermedio`:
- Lee `st.query_params.get("mode", "public")`.
- Si `mode=advanced` → importa y ejecuta `advanced.app.main()`.
- Por defecto → importa y ejecuta `public.app.main()`.
- Configura `st.set_page_config` según el modo.
- Asegurar que los enlaces internos entre modos funcionan con `target="_self"` y el host real.

### 7. Actualizar documentación

- `frontend_b_intermedio/README.md`:
  - Cómo arrancar cada modo.
  - Diferencias entre modos.
  - Estructura de carpetas.
- `frontend_b_intermedio/README_VERSIONS.md`:
  - Actualizar con la nueva arquitectura.
- `15_Frontends/README.md`:
  - Ajustar tabla de frontends: solo A y B (C archivado dentro de B-avanzado).
- `legacy/README.md`:
  - Justificación del archivo y lecciones aprendidas.

### 8. Ajustes Docker

- El `Dockerfile.frontend` debe ejecutar `streamlit run app.py` desde `frontend_b_intermedio`.
- No depende de `APP_MODE` ni de `app_router.py`.
- Mantener variable `API_URL` configurable.

### 9. Verificación

- Arrancar API en `8001`.
- Probar modo ligero en `http://localhost:8501/`:
  - Búsqueda, filtros, TL;DR, complementarios, chat.
- Probar modo avanzado en `http://localhost:8501/?mode=advanced`:
  - Controles de pesos, re-ranking, explicaciones, query preprocessor, sugerencias, Sprint 8.
- Comprobar que el cambio de modo mediante enlace funciona.
- Ejecutar tests existentes de frontend si los hay.

---

## Criterios de éxito

- Solo hay un punto de entrada: `frontend_b_intermedio/app.py`.
- `?mode=advanced` carga la versión avanzada; sin parámetro carga la ligera.
- La ligera responde en <1s para búsquedas sin LLM.
- La avanzada demuestra todas las capacidades del backend sin depender de puertos adicionales.
- Los archivos antiguos están en `legacy/` con README que documenta su historia.
- La documentación refleja la nueva arquitectura.

---

## Notas de implementación

- **No se borra código**, solo se mueve.
- Se reutilizan `utils_v2.py` y `components_public.py` como base.
- El modo avanzado puede importar componentes del modo público para no duplicar tarjetas.
- Se mantiene compatibilidad con la API actual (`main_v2_final_v07.py` en `8001`).
- Se actualiza `.gitignore` si es necesario para ignorar checkpoints o logs de frontend.
