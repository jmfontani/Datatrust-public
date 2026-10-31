# Propuestas LLM para el Buscador Semántico

**Fecha:** 2026-05-24  
**Origen:** Fonta  
**Estado:** Análisis pendiente (Fase 09: Sprint 7 — Chatbot / Asistente Inteligente)

---

## Nota previa importante

> Los usuarios en las entrevistas (Fase 01) dijeron que **prefieren una lista de resultados sobre un chatbot conversacional** (4/5).  
> **Esto no significa que no se pueda usar un LLM.** Las propuestas aquí NO son necesariamente un chatbot: muchas son **capas de inteligencia** que operan "por detrás" de la interfaz de lista.

---

## Las 14 propuestas

### 1. Interpretación estructurada de la consulta

El LLM convierte una petición en lenguaje natural en una especificación analítica estructurada.

**Ejemplo:**
- *Entrada:* "Quiero analizar la relación entre renta, paro juvenil y abandono escolar por municipio."
- *Salida:* JSON con variables, granularidad, periodo, filtros → alimenta el motor de búsqueda

**Ventaja:** La consulta semántica entiende intención, no solo palabras clave.

---

### 2. Re-ranking inteligente de resultados

1. El buscador actual devuelve top N por similitud + BM25
2. El LLM recibe los metadatos de esos N resultados
3. Reordena según criterios analíticos:
   - Relevancia real para el objetivo
   - Granularidad geográfica
   - Cobertura temporal
   - Actualidad
   - Formato
   - Posibilidad de cruce
   - Calidad de la descripción

**Salida:** Ranking explicado, no solo por similitud.

---

### 3. Detección de datasets complementarios

El LLM descompone el objetivo en necesidades de datos y busca datasets para cada bloque.

**Ejemplo:** "Vulnerabilidad energética municipal" → necesita:
- renta
- consumo energético
- antigüedad de viviendas
- clima
- población vulnerable
- ayudas sociales

**Salida:** Propuesta de combinaciones útiles.

---

### 4. Evaluación de compatibilidad entre datasets

El LLM razona si varios datasets se pueden cruzar:

- ¿Clave común? (código INE, municipio, fecha)
- ¿Misma granularidad?
- ¿Misma escala temporal?
- ¿Cobertura territorial compatible?
- ¿Licencia compatible?
- ¿Calidad de metadatos?

**Ejemplo:** "Los datasets A y B son combinables por código de municipio y datos anuales. Pero A llega hasta 2022 y B hasta 2024, así que el análisis conjunto debería limitarse a 2022."

---

### 5. Perfilado técnico de datasets

Inspeccionar los recursos reales enlazados (no solo metadatos):

- Columnas reales
- Tipos de datos
- Tamaño y número de filas
- Valores nulos
- Muestra de registros
- Periodo y granularidad detectada
- Claves candidatas de cruce

**Ventaja:** Información mucho más útil que título + descripción.

---

### 6. Estrategia adaptativa según tamaño del dataset

| Tamaño | Estrategia |
|--------|-----------|
| **Pequeño** | Descargar completo, perfilar, pasar muestra al LLM |
| **Mediano** | Descargar/perfilar, pasar resumen + esquema + muestra |
| **Grande** | No pasar al LLM; usar DuckDB/Polars/Spark, enviar solo perfil |
| **Muy grande** | Inspección parcial, cabeceras, primeras filas, muestreo |
| **API** | Consultar esquema, endpoints, primeras páginas y límites |

> **Regla:** El código calcula; el LLM interpreta.

---

### 7. Generación de planes de análisis

Una vez detectados los datasets adecuados, el LLM propone:

- Qué datasets usar
- Qué variables seleccionar
- Cómo limpiarlos
- Cómo cruzarlos
- Qué indicadores construir
- Qué gráficos generar
- Qué limitaciones declarar

**Ejemplo:** Plan completo para analizar despoblación municipal.

---

### 8. Análisis dentro de la herramienta

Opción más avanzada: ejecutar análisis directamente (pandas, Polars, DuckDB, Spark).

- Carga de datos
- Limpieza
- Joins
- Cálculo de indicadores
- Correlaciones
- Rankings
- Visualizaciones
- Notebooks o informes

> El LLM **explicaría** resultados y sugeriría siguientes pasos.

---

### 9. Explicación de resultados

El LLM justifica por qué recomienda o descarta datasets:

- **Recomendación:** "Este dataset contiene renta media por municipio, cobertura nacional, y puede cruzarse mediante código INE."
- **Descarte:** "Este dataset habla de empleo pero solo a nivel autonómico; el usuario necesita análisis municipal."

**Ventaja:** Transparencia del sistema.

---

### 10. Normalización semántica de conceptos

Distinguir conceptos próximos pero no equivalentes:

- "paro registrado" ≠ "tasa de desempleo" ≠ "demandantes de empleo" ≠ "afiliación" ≠ "contratos"

**Ventaja:** Evita cruces conceptualmente incorrectos.

---

### 11. Conversación guiada (interfaz opcional)

Cuando la consulta sea ambigua, el LLM hace preguntas de aclaración.

**Ejemplo:**
- *Usuario:* "Busco datos sobre vivienda."
- *Sistema:* "¿Precios de vivienda, alquiler, vivienda protegida, licencias urbanísticas, parque residencial o vulnerabilidad habitacional?"

**Nota:** Esto **puede** usarse en una interfaz de chat, pero también como "modalidad de refinamiento" en la lista de resultados.

---

### 12. Arquitectura propuesta (flujo completo)

```
Usuario
  ↓
LLM interpreta intención
  ↓
Buscador híbrido sobre 134k metadatos
  ↓
Top N datasets candidatos
  ↓
LLM re-rankea resultados
  ↓
Inspección técnica de datasets seleccionados
  ↓
LLM evalúa compatibilidad y propone combinaciones
  ↓
Opcional: motor analítico ejecuta análisis
  ↓
LLM explica resultados y genera plan/informe
```

---

### 13. Propuesta de valor resumida

**No es solo un buscador. Es un asistente de descubrimiento y composición de datasets abiertos:**

- Entiende el objetivo del usuario
- Busca datasets relevantes
- Identifica datasets complementarios
- Evalúa si son combinables
- Propone cómo analizarlos
- Opcionalmente ejecuta parte del análisis
- Explica las limitaciones

---

### 14. Funcionalidades prioritarias para el TFM

| Prioridad | Funcionalidad | Complejidad |
|-----------|--------------|-------------|
| 🔴 Alta | Interpretación estructurada de consultas con LLM | Media |
| 🔴 Alta | Re-ranking explicado de resultados | Media |
| 🟡 Media | Recomendación de datasets complementarios | Media |
| 🟡 Media | Evaluación de compatibilidad entre datasets | Alta |
| 🟡 Media | Generación de plan de análisis reproducible | Media |
| 🟢 Baja | Perfilado técnico básico de datasets | Alta |

**Dejar como mejora opcional:** Ejecución completa de análisis (introduce mucha complejidad adicional).

---

## Posibles posiciones en el roadmap actual

### Opción A: Fase 05 (Búsqueda + UI)
Integrar re-ranking y explicación de resultados en el motor actual.

### Opción B: Fase 09 (Chatbot / Asistente Inteligente)
Implementar como modo alternativo: lista de resultados tradicional + "asistente de análisis" para usuarios que quieran ir más allá.

### Opción C: Post-entrega TFM
Desarrollar como extensión completa del sistema.

---

## Notas para futuro análisis

- ¿Qué LLM usar? (OpenAI API, local con Ollama, Mistral, Llama...)
- ¿Coste por consulta? (importante si hay usuarios reales)
- ¿Latencia añadida? (LLM + búsqueda semántica puede ser lento)
- ¿Caché de interpretaciones? (para queries repetidas)
- ¿Privacidad de datos? (queries enviadas a API externa)

---

*Documento vivo. Se actualizará cuando se decida incorporar alguna de estas funcionalidades.*
