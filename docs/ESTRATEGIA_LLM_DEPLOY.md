# Estrategia de despliegue de LLM

**Fecha**: 2026-06-23  
**Contexto**: Respuesta al punto de dolor #2 del tutor de EOI: "Ejecuciones locales vs cloud para LLMs y tiempos de respuesta". Recomendación: https://smolagents.org/es/.

> Este documento se redacta en la **fase de diseño previa a la implementación**. Las decisiones son propuestas y están sujetas a validación con datos reales de producción.

---

## 1. Resumen ejecutivo

El proyecto **no usa LLMs locales tradicionales** (modelos descargados y ejecutados directamente en CPU/GPU del propio servidor de aplicaciones). El único componente local es el **modelo de embeddings**; los LLM generativos se sirven a través de **Ollama Cloud** (modelos con sufijo `:cloud`) accedidos desde un contenedor/puente Ollama local.

| Componente | Modelo / Tecnología | Dónde corre | Tipo de despliegue |
|---|---|---|---|
| **Embeddings** | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384D) | CPU local del servidor de aplicación | **Local**, sin llamadas externas |
| **LLM generativo** | `deepseek-v4-flash:cloud`, `deepseek-v4-pro:cloud`, `qwen3-coder-next:cloud`, `glm-5.2:cloud` | **Nube de Ollama** (acceso vía contenedor/puente local en puerto 11434) | **Cloud gestionado por Ollama** |

La distinción es importante: los modelos `:cloud` **no se ejecutan en nuestro hardware**. La inferencia corre en la infraestructura de Ollama Cloud; el contenedor local actúa como proxy/gateway. Esto ofrece simplicidad de despliegue, pero introduce dependencia de un proveedor externo y el tráfico de consultas sí sale de la red local.

---

## 2. Arquitectura actual de LLM en el proyecto

```
┌─────────────────────────────────────────────────────────────┐
│  Servidor de aplicación (FastAPI + Streamlit)                 │
│  ├── Embeddings: sentence-transformers en CPU local           │
│  └── LLM generativo: llamadas HTTP al puente Ollama local       │
│       URL: http://localhost:11434/api/chat                    │
│       Modelos: deepseek-v4-flash:cloud, qwen3-coder-next:cloud│
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP interno
┌────────────────────────────▼────────────────────────────────┐
│  Contenedor Ollama local (Docker) — puente/gateway           │
│  Reenvía las peticiones a Ollama Cloud (:cloud)               │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS externo
┌────────────────────────────▼────────────────────────────────┐
│  Ollama Cloud                                               │
│  Infraestructura gestionada por Ollama                        │
└─────────────────────────────────────────────────────────────┘
```

### Ventajas del despliegue actual

- **Simplicidad**: no hay que gestionar GPUs ni cuantizar modelos.
- **Acceso a modelos grandes** sin inversión en hardware propio.
- **Latencia razonable** para un servicio cloud gestionado (1-2 s por consulta corta).
- **Facilidad de iteración** en el entorno de desarrollo.

### Inconvenientes

- **Dependencia de Ollama Cloud**: caídas, cambios de precio o disponibilidad de modelos afectan al proyecto.
- **Privacidad limitada**: los prompts sí salen de la red local hacia la nube de Ollama.
- **Coste por uso**: puede ser por token, por tiempo o por suscripción (depende del plan de Ollama Cloud).
- **Menor control**: no se puede optimizar la infraestructura ni forzar una versión/cuantización específica.

---

## 3. Latencias observadas en el entorno de desarrollo

Mediciones reales sobre el endpoint `/dataset/chat` con el mismo dataset y pregunta (2026-06-22). Las latencias incluyen la ida y vuelta a Ollama Cloud:

| Modelo | Tipo | Latencia API (ms) | Calidad observada | Uso actual |
|---|---|---:|---|---|
| `qwen3-coder-next:cloud` | Ollama Cloud | ~700-1.100 | Correcta, concisa | Perfiles, evaluación RAGAS, juez complementariedad |
| `deepseek-v4-flash:cloud` | Ollama Cloud | ~1.100-1.500 | Correcta, mejor razonamiento | Re-ranking, expansión, TL;DR, chat #10 |
| `glm-5.2:cloud` | Ollama Cloud | ~6.000-6.600 | Equivalente a qwen, más lento | No usado tras benchmark |
| `deepseek-v4-pro:cloud` | Ollama Cloud | No medido en chat | Mayor capacidad, más lento | Perfiles complejos (batch) |

### Latencias por caso de uso (estimadas con Ollama Cloud)

| Caso de uso | Modelo | Latencia típica | Frecuencia | Nota |
|---|---|---:|---|---|
| Re-ranking top-N (#1) | `deepseek-v4-flash:cloud` | 1-3 s | Por consulta con LLM | Limitado a top-N pequeño |
| Expansión de query (#4) | `deepseek-v4-flash:cloud` | 1-5 s | Por consulta | Cacheable |
| Validación semántica (#12) | `deepseek-v4-flash:cloud` | 0.5-2 s | Por consulta | Fallback rápido disponible |
| Chat sobre dataset (#10) | `deepseek-v4-flash:cloud` | 1-2 s | Interactiva | Aceptable para chat |
| TL;DR / perfiles (#14) | `deepseek-v4-flash:cloud` | 1-3 s | Batch o bajo demanda | Precalculable offline |
| Complementariedad (#5) | `qwen3-coder-next:cloud` | 0.5-2 s | Por consulta | Modo rápido sin LLM por defecto |

---

## 4. Opciones de despliegue comparadas

| Opción | Descripción | Control | Privacidad | Latencia típica | Coste | Calidad | Mantenimiento |
|---|---|---|---|---|---|---|---|
| **A. Ollama Cloud (actual)** | Modelos `:cloud` accedidos vía puente Ollama local | Medio | Media-baja (prompts en nube de Ollama) | Media (1-2 s) | Por uso/suscripción Ollama | Media-alta | Bajo |
| **B. LLM local puro (CPU/GPU propia)** | Modelos tipo `qwen2.5:7b` descargados y ejecutados en servidor propio | Alto | Alta | Media-alta (según hardware) | Hardware + energía | Media (cuantización) | Alto |
| **C. API cloud gestionada** | OpenAI, Anthropic, Google, Azure, etc. | Bajo | Media-baja | Variable (red pública) | Por token, escalable | Alta | Bajo |
| **D. Híbrido recomendado** | Embeddings locales + Ollama Cloud para la mayoría; API cloud solo para casos de alta calidad | Medio | Media-baja para lo sensible; baja para lo optativo | Media | Mixto | Alta donde se requiere | Medio |

### Observaciones

- **El despliegue actual (Opción A) es cloud**: aunque haya un contenedor Ollama local, la inferencia de los modelos `:cloud` ocurre en la nube de Ollama.
- **La Opción B (local puro)** no se usa actualmente. Sería una alternativa para ganar privacidad total, a costa de hardware y calidad de cuantización.
- **La Opción C (API cloud)** resolvería dependencia de Ollama y probablemente mejoraría calidad, pero introduce coste por token y dependencia de otro proveedor.
- **La Opción D** es la más robusta para producción: usa Ollama Cloud para el grueso de las llamadas y API cloud gestionada solo donde la mejora de calidad justifique el coste.

---

## 5. Estrategia recomendada para producción

### Fase 1: Mantener Ollama Cloud para el MVP y validación

- Motivo: simplicidad, acceso a modelos grandes sin hardware propio, facilidad para iterar.
- Modelos: `deepseek-v4-flash:cloud` como modelo principal; `deepseek-v4-pro:cloud` para análisis complejos; `qwen3-coder-next:cloud` para evaluación/perfiles.
- Embeddings: seguir con `paraphrase-multilingual-MiniLM-L12-v2` en CPU local.

### Fase 2: Evaluar API cloud gestionada para casos críticos de calidad

- Casos candidatos:
  - Re-ranking con contexto muy complejo.
  - Generación de perfiles/TL;DR donde la calidad del lenguaje natural importa mucho.
  - Chat avanzado con razonamiento multi-paso.
- Proveedores a evaluar: OpenAI GPT-4o-mini/4o, Anthropic Claude 3.5 Sonnet/Haiku, Google Gemini Flash.
- Criterio de decisión: comparar calidad vs coste por consulta en un subconjunto representativo.

### Fase 3: Híbrido optimizado

- Embeddings: local (sin coste adicional).
- Búsqueda híbrida + validación rápida: Ollama Cloud.
- Re-ranking complejo y chat avanzado: API cloud gestionada (OpenAI/Anthropic/Google) si la mejora de P@5 o satisfacción del usuario lo justifica.
- Fallback automático a Ollama Cloud si la API cloud falla o es lenta.

---

## 6. smolagents como opción futura

El tutor recomienda explorar **https://smolagents.org/es/**. smolagents es un framework de Hugging Face para construir **agentes LLM con herramientas** (tool-calling), no un modelo de LLM ni un proveedor de inferencia.

### Dónde podría encajar en el proyecto

| Uso potencial | Descripción | Complejidad |
|---|---|---|
| **Agente de enriquecimiento de metadatos** | LLM que, dado un dataset, decida qué herramientas usar para completar descripción, tema, territorio, formato. | Media |
| **Agente de búsqueda multi-paso** | Refinar la query llamando a búsqueda semántica, léxica y facetas de forma iterativa. | Media-alta |
| **Agente de validación de resultados** | Evaluar si los resultados de una query son relevantes y, si no, reformular la búsqueda. | Media |

### Recomendación respecto a smolagents

- **No es sustituto directo** de Ollama Cloud ni de API cloud; es una capa de orquestación.
- Puede ejecutarse sobre **cualquier modelo compatible**, incluidos los `:cloud` de Ollama o APIs cloud gestionadas.
- Para el TFM actual, se propone como **trabajo futuro** una vez estabilizados los casos de uso básicos (#1-#14). No es prioridad en el MVP.
- Si se adopta, la recomendación sería usar smolagents sobre el modelo más rápido (`deepseek-v4-flash:cloud`) para minimizar latencia en los ciclos de tool-calling.

---

## 7. Costes estimados por opción de despliegue

| Opción | Coste año 1 estimado (EUR) | Notas |
|---|---|---|
| Ollama Cloud (uso moderado, ~500 consultas/día) | 3.000 - 8.000 | Depende del plan y volumen de Ollama Cloud. |
| LLM local puro con GPU | 5.000 - 15.000 | Hardware propio, electricidad, mantenimiento. |
| API cloud gestionada (uso moderado) | 3.000 - 10.000 | OpenAI/Anthropic/Google; por token, escalable. |
| Híbrido (Ollama Cloud + API cloud) | 4.000 - 12.000 | Balance entre coste y calidad. |

> Estimaciones para un entorno de demostración/MVP con cientos de consultas diarias. A escala de datos.gob.es los costes crecerían proporcionalmente.

---

## 8. Plan de decisión y próximos pasos

1. **Confirmar el despliegue actual como estrategia MVP**: Ollama Cloud con modelos `:cloud` y embeddings locales.
2. **Medir latencias reales en producción** para cada caso de uso, no solo en entorno de desarrollo.
3. **Establecer umbrales de latencia aceptables** por funcionalidad (p. ej. chat < 2 s, re-ranking < 3 s, TL;DR batch < 5 s).
4. **Evaluar API cloud gestionada** en un subconjunto de queries de alta dificultad, comparando calidad y coste.
5. **Evaluar smolagents** como prototipo de agente de enriquecimiento de metadatos, una vez cerrados los casos de uso core.

---

## 9. Relación con otros documentos

- `docs/BUSINESS_MODEL_CANVAS.md` — El modelo de negocio incluye el coste de LLM como partida clave.
- `docs/PLAN_ENRIQUECIMIENTO_METADATOS.md` (planificado) — smolagents podría aplicarse aquí.
- `docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md` — Fundamenta el uso de LLM para re-ranking y expansión.

---

*Documento de planificación. Las latencias y costes son estimaciones basadas en mediciones del entorno de desarrollo; deben validarse en producción.*