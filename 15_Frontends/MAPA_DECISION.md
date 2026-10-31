# Mapa de Decisión: ¿Qué Frontend Usar?

**Documento de apoyo**  
**Fecha:** 2026-06-03

---

## 🎯 Resumen en una frase

- **Si quieres enseñar el producto al tribunal → usa B** (`app_public.py`).
- **Si quieres enseñar la tecnología al tribunal → usa A** (`app.py`).
- **Si quieres demostrar el valor del LLM → usa C** (`app_v09_demo.py`).
- **Si quieres evaluar la calidad → consulta RAGAS** (ver `metodologia/05_VALOR_RAGAS.md`).

---

## 📊 Tabla comparativa de los 3 niveles

| Dimensión | A (básico) | B (intermedio) | C (avanzado) |
|-----------|-----------|----------------|--------------|
| **Origen** | Sprint 3 (MVP) | Sprint 5 (producto) | Sprint 6 (LLM) |
| **Funcionalidad** | Búsqueda + pesos + facetas | Búsqueda + vista pública + `?mode=advanced` | Re-ranking LLM + explicaciones + Query Preprocessor |
| **Complejidad** | Baja | Media | Alta |
| **Latencia típica** | ~50-100 ms | ~50-100 ms | ~3-5 s (LLM local) o 60-80 s (LLM cloud) |
| **Requiere GPU/CPU** | No | No | Sí (modelo local) o API key (cloud) |
| **Requiere Ollama** | No | No | **Sí** |
| **Adecuado para defensa** | Demo técnica (5 min) | **Defensa principal (15 min)** | Demo avanzada (opcional, 5 min) |
| **Riesgo de fallo en directo** | Bajo | Bajo | **Medio** (depende de LLM) |
| **Usuarios objetivo** | Equipo | Usuarios finales | Evaluadores técnicos |
| **Estado de los tests** | Sintaxis OK | ⚠️ Imports rotos (preexistente) | Sintaxis OK, paths arreglados |
| **Documentación** | README.md (del Sprint 3) | Pendiente (Sprint 10) | Pendiente |

---

## 🧭 Criterios de decisión

### Elige **A (básico)** si…

- Estás haciendo una **demo técnica rápida** (< 5 min) donde el foco es el motor, no la UX.
- No quieres riesgos: la API funciona, no hay LLM, no hay nada que pueda romperse.
- Estás explicando el **funcionamiento interno** (pesos semántico vs léxico, filtros, facetas).

### Elige **B (intermedio)** si…

- Es la **defensa principal** ante el tribunal.
- Quieres enseñar el **producto terminado** que un usuario real usaría.
- Necesitas la **vista pública** (limpia, sin jerga técnica) y, opcionalmente, el `?mode=advanced` para enseñar el control fino.

### Elige **C (avanzado)** si…

- Estás respondiendo a la pregunta **"¿el LLM aporta valor?"** con un demo.
- Quieres mostrar la **diferencia visible** entre búsqueda pura y búsqueda con re-ranking.
- Estás cómodo con que pueda fallar (depende de Ollama, latencia alta).

---

## 🚦 Plan de defensa recomendado

1. **Apertura (2 min):** Frontend B — vista pública, hacer una query que se vea bien (ej: "despoblación") para captar la atención.
2. **Profundización (5 min):** Frontend A — abrir controles de pesos, filtros facetados, mostrar el motor.
3. **Pico técnico (3 min):** Frontend C — comparar mismo query sin LLM y con LLM, mostrar la diferencia en el ranking.
4. **Cierre (5 min):** Volver a B, contestar preguntas, mostrar la vista pública de nuevo.

**Plan B (si algo falla):** Vídeo pregrabado de 3 min con los 3 niveles + frontend B en vivo para preguntas.

---

## ❓ Decisiones pendientes

- [ ] **¿Se reescribe `utils_v2.py` y `components_v2.py` para arreglar frontend B?** (esfuerzo: 2-3 h). Sin esto, `app.py` de B no funciona y `app_public.py` también está roto por el mismo import.
- [ ] **¿Se mantienen 3 apps Streamlit separadas o se fusionan en una sola con `?mode=basic|advanced|llm`?** (decisión de sprint 10).
- [ ] **¿Se hace plan B con vídeo de demo grabado?** (decisión sprint 9).

---

*Documento vivo. Actualizar conforme se ejecuten los sprints 9-10 y se incorporen decisiones del equipo.*
