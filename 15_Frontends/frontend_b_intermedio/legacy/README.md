# Legacy — Interfaces y componentes archivados

Esta carpeta contiene versiones antiguas de frontends y componentes que ya no se usan como punto de entrada principal, pero se conservan como parte del **relato de evolución del proyecto** y de las **lecciones aprendidas**.

> ⚠️ **No son la interfaz activa.** La interfaz principal se ejecuta con `streamlit run app.py` en `frontend_b_intermedio/`, que carga el modo público o avanzado según el parámetro `?mode=`.

---

## Archivos archivados

| Archivo | Origen | Propósito original | Por qué se archiva |
|---------|--------|--------------------|--------------------|
| `app_original.py` | Sprint 5, `frontend_b_intermedio/app.py` | Primera interfaz técnica con controles de pesos semántico/léxico, sidebar de configuración y panel de estado de API. | Se reemplaza por `advanced/app.py`, que incluye también las mejoras de Sprint 6, 7 y 8 (re-ranking, explicaciones, query preprocessor, TL;DR, chat, complementarios). |
| `app_router.py` | Sprint 6 | Router que cargaba `app_public.py`/`app.py` según `mode` o `APP_MODE`. | El enrutamiento se simplifica: ahora `app.py` en la raíz decide directamente qué modo cargar, eliminando una capa innecesaria. |
| `components_v2.py` | Sprint 5 | Componentes visuales de la interfaz técnica original. | Obsoleto tras la refactorización del modo avanzado. |
| `app_query_enhanced.py` | Sprint 6, `frontend_c_avanzado/` | Demo del Query Preprocessor (#3, #4, #12): validación, interpretación y expansión de queries. | Se integra como pestaña dentro del modo avanzado en `advanced/app.py`. |
| `app_v09_demo.py` | Sprint 6, `frontend_c_avanzado/` | Demo de re-ranking LLM y explicaciones de relevancia (#1, #2). | Se integra como pestaña dentro del modo avanzado. |
| `app_v13_query_suggestions.py` | Sprint 6, `frontend_c_avanzado/` | Demo de sugerencias de queries (#13). | Se integra como pestaña dentro del modo avanzado. |
| `launch_query_enhanced.sh` | Sprint 6 | Script de lanzamiento del Query Preprocessor. | El modo avanzado se lanza con un único comando `streamlit run app.py`. |
| `assets/` | Sprint 6 | Logos y recursos gráficos de las demos. | Se conservan para reutilizar en el modo avanzado si es necesario. |

---

## Lecciones aprendidas

1. **Menos puntos de entrada es mejor.** Tener tres frontends separados (A, B, C) con puertos distintos generaba confusión y procesos huérfanos. La unificación en una sola app con `?mode=advanced` simplifica el despliegue.

2. **Separar lo rápido de lo experimental.** Los usuarios finales necesitan una interfaz limpia y rápida. Las capacidades de demostración (re-ranking, explicaciones LLM, debug) deben estar disponibles pero no entorpecer el flujo principal.

3. **Preservar el historial.** Borrar las demos del Sprint 6 habría dificultado explicar la evolución y las decisiones tomadas. Archivarlas permite mantener el relato del TFM.

---

## Cómo consultarlos

Si necesitas recuperar alguna funcionalidad, estos archivos son legibles y ejecutables individualmente con:

```bash
cd ~/datos/PFM/Datatrust/15_Frontends/frontend_b_intermedio/legacy
streamlit run app_query_enhanced.py --server.port 8502
```

> Nota: pueden requerir ajustes de puerto o URL si el backend o la estructura de endpoints han cambiado.
