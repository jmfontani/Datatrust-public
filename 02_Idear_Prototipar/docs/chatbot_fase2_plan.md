# Chatbot como Modo Alternativo - Plan para Fase 2

## Proyecto: Buscador Semántico de Datasets Públicos
**Estado:** PLANTEADO (pendiente de validación MVP)
**Fase objetivo:** Fase 2 (post-MVP)
**Condición de activación:** La búsqueda por lista debe demostrar valor en la evaluación del MVP (Sprint 5)

---

## 🎯 Propósito

Incorporar un **chatbot como modo alternativo de navegación** (no principal) para usuarios que prefieren explorar datos conversacionalmente, una vez validada la búsqueda basada en listas como opción principal.

---

## 📋 Contexto de la decisión

### Fase 01 (Empatizar/Definir)
Las entrevistas revelaron que **4 de 5 usuarios prefieren lista tradicional** sobre chatbot para el problema principal: *"encontrar datasets relevantes rápidamente"*.

**Razones principales:**
- Velocidad: ver todos los resultados de golpe sin turnos de conversación
- Control: filtrar, ordenar y navegar libremente
- Trazabilidad: acceso directo a fuentes verificables

### Fase 02 (Idear/Prototipar)
**Decisión:** El chatbot se descarta para el MVP pero se **replante explícitamente para Fase 2** como modo alternativo, no como reemplazo de la lista.

---

## 🤖 Funcionalidades previstas del chatbot (Fase 2)

### 1. Navegación conversacional por datasets
Permitir al usuario refinar la búsqueda mediante preguntas de seguimiento:
- *"¿Y qué datos hay de 2023?"*
- *"Muéstrame solo los de Castilla y León"*
- *"¿Hay alguno con datos mensuales en lugar de anuales?"*
- *"Dame el que tenga más cobertura territorial"*

### 2. Explicaciones de relevancia conversacionales
En lugar de mostrar un score numérico, el chatbot puede explicar:
- *"Te recomiendo el Censo del INE porque incluye población por municipio con series temporales desde 1996, lo cual permite analizar tendencias de despoblación a largo plazo."*

### 3. Descubrimiento de conexiones
Identificar relaciones entre datasets que no son evidentes en la vista de lista:
- *"Si estás estudiando despoblación, también te puede interesar el dataset de 'Movimiento natural de población' porque muestra el saldo migratorio que explica el vaciamiento de pueblos."*

### 4. Asistencia en la formulación de queries
Ayudar al usuario a expresar mejor su necesidad:
- Usuario: *"Quiero datos sobre pueblos vacíos"*
- Chatbot: *"¿Te refieres a despoblación demográfica, viviendas desocupadas, o ambos? También puedo buscarte datasets sobre envejecimiento poblacional si te interesa."*

---

## 🏗️ Arquitectura técnica propuesta (preliminar)

```
Usuario
  ↓ (mensaje en lenguaje natural)
Modo Chatbot (Fase 2)
  ↓
Análisis de intención + Contexto (gestión de estado conversacional)
  ↓
Búsqueda semántica en los mismos embeddings del sistema principal
  ↓
Formulación de respuesta conversacional (con trazabilidad a fuentes)
  ↓
Respuesta con resumen + links verificables a datos.gob.es
```

**Requisitos técnicos adicionales:**
- Gestión de contexto conversacional (memoria de turnos previos)
- Generación de texto explicativo (posiblemente LLM controlado)
- Validación de que la respuesta no alucine datos (enlaces siempre verificables)

---

## ✅ Condiciones de activación

El chatbot se implementará en Fase 2 **solo si** se cumplen las siguientes condiciones tras la evaluación del MVP (Sprint 5):

| Condición | Umbral | Métrica |
|-----------|--------|---------|
| La búsqueda por lista demuestra valor | Precisión@5 ≥ 70% | Métrica objetiva |
| Usuarios solicitan modo conversacional | ≥ 2 usuarios en feedback | Feedback cualitativo |
| El equipo tiene capacidad técnica | ≥ 40h disponibles | Estimación de esfuerzo |
| No hay riesgos bloqueantes | Sin dependencias críticas | Evaluación técnica |

---

## 📊 Comparativa: Lista vs Chatbot

| Aspecto | Lista de resultados (MVP) | Chatbot (Fase 2) |
|---------|---------------------------|------------------|
| **Velocidad** | ⚡ Rápida (<2s) | 🐢 Lenta (turnos) |
| **Control** | 🎛️ Alto (filtros, orden) | 🎮 Bajo (sigue flujo) |
| **Trazabilidad** | ✅ Directa (links) | ⚠️ Requiere validación |
| **Descubrimiento** | 📋 Limitado (lista estática) | 🔮 Potencial (preguntas de seguimiento) |
| **Explicaciones** | 💡 Breves (por qué relevante) | 📖 Detalladas (contexto conversacional) |
| **Navegación** | 🔍 Directa | 🧭 Exploratoria |

**Conclusión:** Son complementarios, no excluyentes. La lista cubre el 80% de casos rápidamente; el chatbot añade valor para exploración profunda.

---

## 🔗 Documentación relacionada

- [ideas_rechazadas.md](../docs/ideas_descartadas/ideas_rechazadas.md) — Idea 1: evolución del chatbot de "descartado" a "replanteada para Fase 2"
- [wireframe_busqueda_principal.md](../entregables/wireframes/wireframe_busqueda_principal.md) — Diseño de la interfaz principal (lista)
- [prototipo_streamlit.md](../entregables/prototipos/prototipo_streamlit.md) — Especificación del MVP sin chatbot

---

## 📝 Notas

- Este documento se creó en respuesta a la solicitud del usuario (2026-05-22) de dejar constancia de que el chatbot se plantea para Fase 2 como modo alternativo de navegación.
- La decisión final de implementar el chatbot dependerá de los resultados de la evaluación del MVP (Sprint 5) y del feedback de usuarios reales.

---

*Documento vivo: Se actualizará tras la evaluación del MVP (Sprint 5)*
