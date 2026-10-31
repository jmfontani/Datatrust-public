# Informe: Tres Iteraciones de Prompts LLM

**Fecha:** 2026-05-31  
**Evaluador:** Usuario  
**Modelo:** deepseek-v4-flash:cloud  
**Iteraciones:** 3 versiones de prompt

---

## 📊 Comparativa de las 3 Baterías

### Iteración 1: Prompt ORIGINAL

| Caso | Score Humano | Score LLM | Estado |
|------|--------------|-----------|--------|
| S1-R1 | 4/5 | 9.5 | ✅ Buena |
| S1-R2 | 3/5 | 9.0 | ⚠️ Genérica |
| S1-R3 | 3/5 | 8.5 | ⚠️ Genérica |
| C1-R1 | 5/5 | 9.5 | ⭐ Excelente |
| C1-R2 | 2/5 | 8.5 | ❌ Sobreestimado |
| C1-R3 | 3/5 | 7.5 | ⚠️ Aceptable |

**Media humana:** 3.33/5  
**Patrón:** Explicaciones breves, genéricas, scores inflados

---

### Iteración 2: Prompt MEJORADO (ejemplos buenos/malos)

| Caso | Score Humano | Score LLM | Estado |
|------|--------------|-----------|--------|
| C1-R1 | 5/5 | 10.0 | ⭐ Excelente |
| C1-R2 | 3/5 | 9.0 | ⚠️ Persiste genérico |
| C1-R3 | 3/5 | 8.0 | ⚠️ Aceptable |
| T1-R1 | 5/5 | 10.0 | ⭐ Excelente |
| T1-R2 | 2/5 | 8.0 | ❌ Sobreestimado |
| T1-R3 | 1/5 | 6.0 | ❌ Detecta problema pero score alto |

**Media humana:** 3.17/5  
**Avance:** Detecta incoherencias (dice "sin conexión"), pero scores aún altos

---

### Iteración 3: Prompt CON REGLAS DE PUNTUACIÓN EXPLÍCITAS

| Caso | Score Humano | Score LLM | Estado |
|------|--------------|-----------|--------|
| S1-R1 | **5/5** | 10.0 | ⭐ "Mejorado respecto a baterías anteriores" |
| S1-R2 | **3/5** | 9.5 | ⚠️ "Demasiado escueto" |
| S1-R3 | **3/5** | 9.0 | ⚠️ "Demasiado escueto" |
| C1-R1 | **5/5** | 9.5 | ⭐ Excelente |
| C1-R2 | **2/5** | 9.0 | ❌ "Sobreestimado" |
| C1-R3 | **3/5** | 7.5 | ⚠️ Aceptable |
| T1-R1 | **5/5** | 10.0 | ⭐ "Muy bueno" |
| T1-R2 | **2/5** | 7.0 | ❌ "Demasiado permisivo" |
| T1-R3 | **1/5** | 6.0 | ❌ "Geográficamente distante" |

**Media humana:** 3.22/5  
**Patrón consistente:** Acierta en posición 1, sobrevalora 2 y 3

---

## 🎯 Hallazgos Clave

### 1. Patrón Sistemático Confirmado

> **"El modelo acierta en posición 1 pero sobrevalora posiciones 2 y 3 con justificaciones débiles o circulares."**

| Iteración | Posición 1 | Posición 2 | Posición 3 |
|-----------|------------|------------|------------|
| 1 | 4-5/5 ✅ | 2-3/5 ❌ | 2-3/5 ❌ |
| 2 | 5/5 ✅ | 2-3/5 ❌ | 1-3/5 ❌ |
| 3 | 5/5 ✅ | 2-3/5 ❌ | 1-3/5 ❌ |

**Conclusión:** El LLM siempre acierta el TOP 1 pero falla en discriminar 2-3.

---

### 2. Problema de Consistencia de Idioma

**Nuevo hallazgo en Iteración 3:**

| Query | Explicación | Idioma |
|-------|-------------|--------|
| "vulnerabilidad económica juventud" (español) | "Directly measures youth economic vulnerability..." | **INGLÉS** ❌ |

> **"Las explicaciones están en inglés siendo la query en español — inconsistencia notable."**

**Impacto:** El prompt no especificó idioma de salida, y los ejemplos en inglés ("Directly measures...") condicionaron al modelo.

---

### 3. Avances por Iteración

| Aspecto | v1 | v2 | v3 | Mejora? |
|---------|----|----|----|---------|
| **Especificidad** | 2.5/5 | 3.5/5 | 3.5/5 | ✅ v2→v3 estable |
| **Detección problemas** | ❌ No | ✅ Sí | ✅ Sí | ✅ v1→v2 |
| **Penalización scores** | 8.5 para malos | 6.0 para malos | 6.0-7.0 para malos | ⚠️ Limitada |
| **Idioma consistente** | ✅ Español | ✅ Español | ❌ Inglés | ❌ Regresión v3 |

---

### 4. Caso Territorial T1: El Peor Escenario

El caso T1 expone claramente la tendencia del modelo:

| Dataset | Relevancia Real | Score LLM v3 | Tu Evaluación |
|---------|-----------------|--------------|---------------|
| Hoteles Tenerife | ✅ Canarias | 10.0 | 5/5 ✅ |
| Menorca (Baleares) | ❌ No Canarias | 7.0 | 2/5 ❌ |
| Cantabria | ❌ No Canarias, lejano | 6.0 | 1/5 ❌ |

**Problema:** El LLM usa "similar contexto insular" (T1-R8) y "geográficamente distante" (T1-R9) pero aún puntu 6-7.

---

## 💡 Veredicto Final

### ¿Funcionan las iteraciones?

**Sí, pero con límites.** Cada iteración mejoró algo, pero ninguna logró:
- ✅ Que el LLM penalice correctamente datasets lejanos
- ✅ Que discrimine entre posición 2 y 3
- ✅ Mantener consistencia de idioma (v3)

### Prompt Óptimo Recomendado

Híbrido de v2 + v3, con corrección de idioma:

```python
prompt = f"""Reordena datasets según relevancia para: "{query}"

Responde SOLO con JSON:
- relevance_score: 0-10 (sé CRÍTICO)
- explanation: justificación ESPECÍFICA en ESPAÑOL

REGLAS DE PUNTUACIÓN:
- 9-10: Dataset PERFECTO (ubicación exacta, tema exacto)
- 7-8: Relación INDIRECTA válida
- 5-6: Conexión DÉBIL (forzada)
- 3-4: Relación casi inexistente
- 0-2: No relacionado

IMPORTANTE:
- Responde SIEMPRE en ESPAÑOL
- Si hay diferencia de ubicación: score 6 o menos
- Si dices "similar", "aunque", "pero": score 7 o menos
- Si dices "distante", "diferente región": score 4 o menos
"""
```

---

## 📁 Archivos Generados

```
resultados/
├── bateria_mini_2026-05-30_205714_para_evaluar.csv   # v1 Original
├── bateria_mini_2026-05-30_212544_para_evaluar.csv   # v2 Mejorado
├── bateria_mini_2026-05-31_203914_para_evaluar.csv   # v3 Reglas puntuación
├── INFORME_EVALUACION_EXPLICACIONES.md               # v1
├── INFORME_COMPARATIVA_EVALUACIONES.md               # v1 vs v2
└── INFORME_3_ITERACIONES.md                          # Este documento
```

---

**Evaluaciones completadas:** 3 baterías  
**Prompt final recomendado:** v3 con corrección de idioma  
**Próximo paso sugerido:** Cuarta iteración corrigiendo idioma y reforzando penalización de scores

---

*Nota: El patrón "acierta en 1, falla en 2-3" parece ser una limitación fundamental del modelo más que del prompt.*
