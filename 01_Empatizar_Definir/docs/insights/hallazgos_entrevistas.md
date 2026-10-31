# Hallazgos de Entrevistas - Usuarios de Datos Abiertos

## Proyecto: Buscador Semántico de Datasets Públicos
**Fecha:** Mayo-Junio 2026
**Participantes:** 5 (Analista, Investigadora, Periodista, Funcionario, Estudiante)

---

## 🔍 Hallazgo 1: Los títulos son insuficientes

**Evidencia:**
- 4/5 usuarios reportan que los títulos actuales no reflejan el contenido real
- Frustración recurrente: "El título dice 'Estadísticas municipales' pero no sé qué contiene"
- Los usuarios pierden tiempo descargando archivos que luego resultan irrelevantes

**Implicación:** El buscador debe indexar y mostrar descripciones completas, no solo títulos.

---

## 🔍 Hallazgo 2: Los usuarios buscan por intención, no por keywords técnicos

**Evidencia:**
- Investigadora: *"No sé qué keywords usar, busco conceptos temáticos como 'migración' o 'desigualdad'"*
- Estudiante: *"No conozco la terminología oficial, uso palabras del lenguaje natural"*
- Funcionario: *"Busco por temas que conozco, no por nombres de datasets"*

**Implicación:** La búsqueda semántica (embeddings) resuelve exactamente este problema.

---

## 🔍 Hallazgo 3: El preview/estructura de datos es fundamental

**Evidencia:**
- Analista: *"Descargo un XLS de 500MB y no sé si sirve hasta abrirlo"*
- Todos los usuarios reportan necesidad de saber formato, tamaño, estructura antes de descargar
- 3/5 reportan descubrir datasets "demasiado tarde" (después de haberlos buscado activamente)

**Implicación:** Cada resultado debe mostrar: formato, tamaño, fecha, descripción, y preferiblemente preview.

---

## 🔍 Hallazgo 4: Contexto temporal importa

**Evidencia:**
- Periodista: *"Necesito saber si los datos son de 2023 o de 2015"*
- Investigadora: *"¿Es la última versión? ¿Se actualiza anualmente?"*
- Analista automatiza informes mensuales y necesita saber cuándo se publican nuevos datos

**Implicación:** Incluir fechas de publicación, modificación y frecuencia de actualización en metadatos.

---

## 🔍 Hallazgo 5: Velocidad vs profundidad varía por perfil

**Evidencia:**
- Periodista: 15-30 min máximo, urgencia periodística
- Investigadora: 30-60 min, necesita validar calidad
- Analista: 10-20 min (urgente) vs 1h (proyecto)
- Funcionario: 20-40 min, informes planificados
- Estudiante: 45-90 min, exploración académica

**Implicación:** Interfaz adaptable: resultados rápidos por defecto, opción de profundizar.

---

## 🔍 Hallazgo 6: El chatbot NO es prioridad

**Evidencia sorprendente:**
- 4/5 usuarios prefieren lista de resultados sobre chat conversacional
- Solo la investigadora muestra interés moderado en chatbot
- Principal preocupación: velocidad y control sobre la búsqueda

**Implicación:** El MVP debe ser una interfaz de lista tradicional, no un chatbot. La búsqueda semántica funciona "por detrás" sin necesidad de conversación.

---

## 🔍 Hallazgo 7: Descubrimiento es tan importante como búsqueda

**Evidencia:**
- Todos los participantes reportan encontrar datasets relevantes "demasiado tarde"
- Investigadora: *"Seguro que existe un dataset perfecto pero no sé cómo buscarlo"*
- Funcionario repite búsquedas manuales periódicamente porque no tiene lista de datasets relevantes

**Implicación:** Incluir recomendaciones de datasets relacionados y permitir guardar búsquedas/favoritos.

---

## 📊 Priorización de features basada en entrevistas

| Feature | Prioridad | Justificación |
|---------|-----------|---------------|
| Búsqueda semántica por intención | 🔴 P0 | Dolor principal de todos los perfiles |
| Preview de datos y metadatos | 🔴 P0 | Fundamental para evitar descargas inútiles |
| Filtros facetados (territorio, tema, formato) | 🟡 P1 | Agiliza la búsqueda una vez entendida la intención |
| Contexto de actualización/frecuencia | 🟡 P1 | Necesario para validar relevancia temporal |
| Recomendación de datasets relacionados | 🟢 P2 | Descubrimiento, no crítico para MVP |
| API REST para automatización | 🟢 P2 | Solo relevante para analistas (1/5 perfiles) |
| Chatbot conversacional | ⚪ P3 | 4/5 prefieren lista tradicional |

---

*Documento generado a partir de entrevistas simuladas - Mayo 2026*
