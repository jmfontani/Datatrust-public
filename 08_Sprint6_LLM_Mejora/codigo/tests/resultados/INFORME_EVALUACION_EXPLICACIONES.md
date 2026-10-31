# Informe de Evaluación de Explicaciones LLM

**Fecha:** 2026-05-30  
**Evaluador:** Usuario  
**Modelo:** deepseek-v4-flash:cloud  
**Casos evaluados:** 6 explicaciones (2 queries × 3 resultados)

---

## 📊 Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| **Puntuación media** | 3.33/5.0 |
| **Mejor explicación** | C1-R4: 5/5 (Vulnerabilidad económica NEET) |
| **Peor explicación** | C1-R5: 2/5 (Juventud y economía - Ministerio de Transportes) |
| **Score LLM vs Humano** | Correlación débil |

### Veredicto General
> **El modelo es significativamente mejor recuperando datasets relevantes que generando explicaciones útiles.**

Las explicaciones tienden a ser:
- ✅ **Técnicamente correctas** (no contienen errores factuales graves)
- ⚠️ **Genéricas y redundantes** (especialmente en queries con múltiples resultados similares)
- ❌ **Poco discriminativas** (no penalizan claramente resultados de baja calidad)

---

## 📈 Resultados Detallados

### Caso S1: Sinonimia (paro juvenil desempleo jóvenes)

| Resultado | Dataset | Score LLM | Score Humano | Diferencia |
|-----------|---------|-----------|--------------|------------|
| **S1-R1** | Paro registrado 16-24 años (Barrios) | 9.5/10 | **4/5** ✅ | -0.5 |
| **S1-R2** | Paro registrado 16-24 años (Secciones) | 9.0/10 | **3/5** ⚠️ | -3.0 |
| **S1-R3** | Paro registrado 16-24 años (Distritos) | 8.5/10 | **3/5** ⚠️ | -2.7 |
| **Media** | | 9.0/10 | **3.3/5** | -5.7 |

#### Análisis del Evaluador:
> "Recuperación correcta, explicaciones demasiado breves y redundantes entre sí. Solo R1 añade valor real."

#### Problemas identificados:

1. **Redundancia**: Las 3 explicaciones son casi **intercambiables**
   - Todas mencionan: "Datos 2020", "granularidad [nivel]"
   - No justifican por qué un nivel de granularidad es mejor que otro
   - El usuario no aprende nada nuevo entre resultados

2. **Brevedad excesiva**: Frases telegráficas sin contexto
   - Ejemplo: "Datos 2020 con granularidad secciones, muy detallados y actuales"
   - ¿Por qué "detallados" es relevante para "paro juvenil"?
   - Falta conexión explícita query → dataset

3. **Score LLM inflado**: 8.5-9.5/10 para explicaciones que el evaluador considera mediocres (3/5)

---

### Caso C1: Conceptual (vulnerabilidad económica juventud)

| Resultado | Dataset | Score LLM | Score Humano | Diferencia |
|-----------|---------|-----------|--------------|------------|
| **C1-R4** | Tasa NEET (INE) | 9.5/10 | **5/5** ⭐ | +0.5 |
| **C1-R5** | Juventud y economía | 8.5/10 | **2/5** ❌ | -4.8 |
| **C1-R6** | Garantía Juvenil | 7.5/10 | **3/5** ⚠️ | -2.0 |
| **Media** | | 8.5/10 | **3.3/5** | -4.4 |

#### Análisis del Evaluador:
> "R4 es sobresaliente. R5 tiene score LLM inflado — el publisher no es coherente y la explicación es vacía. R6 tiene conexión razonable pero indirecta."

#### Hallazgos clave:

1. **R4 (5/5) - Excelente**: 
   - ✅ Identifica correctamente el indicador NEET
   - ✅ Explica el vínculo con "vulnerabilidad económica"
   - ✅ Menciona datos "nacionales y actuales"
   - **Conclusión**: Cuando el dataset encaja perfectamente, el LLM brilla

2. **R5 (2/5) - Deficiente**:
   - ❌ **Publisher incorrecto**: Ministerio de Transportes para "Juventud y economía"
   - ❌ Explicación vacía: "Temática directamente sobre juventud y economía, aunque más general"
   - ❌ **Score LLM 8.5/10**: El modelo no penaliza la incoherencia del publisher
   - **Conclusión**: El LLM no verifica metadatos antes de puntuar

3. **R6 (3/5) - Aceptable**:
   - ⚠️ Conexión indirecta pero razonable
   - ⚠️ Garantía Juvenil → vulnerabilidad económica (vía empleo)
   - **Conclusión**: Justificación forzada pero no incorrecta

---

## 🔍 Análisis Comparativo: Score LLM vs Humano

### Correlación por Caso

```
Score LLM:  ████████████████████ 9.0/10 (S1)
Humano:     ████████ 3.3/5 (S1)
            
Score LLM:  ████████████████████ 8.5/10 (C1)  
Humano:     ████████ 3.3/5 (C1)
```

**Hallazgo**: El LLM **sobrestima sistemáticamente** la calidad de sus explicaciones.

- Diferencia promedio: **-4.5 puntos** (escala 0-10)
- El modelo no tiene autocrítica sobre la utilidad de sus explicaciones

### Matriz de Discrepancias

| Dataset | Score LLM | Score Humano | Tipo de Error |
|---------|-----------|--------------|---------------|
| S1-R2 | 9.0 | 3.0 | Sobreestimación grave |
| S1-R3 | 8.5 | 3.0 | Sobreestimación grave |
| C1-R5 | 8.5 | 2.0 | **Sobreestimación crítica** |

**C1-R5 es el caso más preocupante**: El LLM da 8.5/10 a una explicación que el evaluador considera deficiente (2/5), sin detectar que el publisher es completamente incoherente.

---

## 💡 Hallazgos Clave

### 1. El LLM es mejor "recuperador" que "explicador"

| Aspecto | Calidad |
|---------|---------|
| **Recuperación de datasets** | ✅ Excelente (datasets relevantes encontrados) |
| **Re-ranking** | ⚠️ Aceptable (reordena pero no siempre mejora) |
| **Explicaciones** | ⚠️ Regular (genéricas, redundantes) |
| **Validación de metadatos** | ❌ Débil (no detecta publishers incoherentes) |

### 2. Problemas estructurales en las explicaciones

#### Problema A: Frases genéricas
Ejemplos encontrados:
- "Temática directamente sobre [tema]" → C1-R5
- "Datos [año] con granularidad [nivel]" → S1-R1/R2/R3
- "Relevante para [query]" → Genérico

#### Problema B: Justificaciones circulares
- "Juventud y economía... sobre juventud y economía" → C1-R5
- No aporta información nueva respecto al título

#### Problema C: Falta de discriminación
- Todos los resultados de S1 tienen scores 8.5-9.5
- No penaliza el hecho de que el publisher sea incorrecto (C1-R5)

### 3. Caso de Éxito: C1-R4

La única explicación 5/5 comparte características:
- ✅ Menciona indicador específico (NEET)
- ✅ Explica el vínculo con el concepto de la query
- ✅ Aporta información no obvia del dataset
- ✅ Estructura: Dato concreto → Vínculo → Valor añadido

---

## 🎯 Recomendaciones

### Para Mejorar el Prompt del LLM

**Problema**: Explicaciones genéricas y circulares

**Solución**: Añadir ejemplos de "buenas" y "malas" explicaciones en el prompt:

```python
prompt = """Explica por qué este dataset es relevante para la query.

REGLAS:
1. NO repitas el título del dataset
2. MENCIONA un dato específico que justifique la relevancia
3. EXPLICA el vínculo con la query (no solo digas que existe)
4. MÁXIMO 100 caracteres
5. PENALIZA datasets con metadatos incoherentes

Ejemplo BUENO (C1-R4):
"Indicador NEET mide jóvenes vulnerables económicamente. Datos nacionales actualizados."

Ejemplo MALO (C1-R5):
"Temática directamente sobre juventud y economía" ❌ Repite título, no aporta valor

Responde SOLO con la explicación, sin comillas.
"""
```

### Para el Re-ranking

1. **Añadir validación de metadatos** antes de puntuar
   - Detectar publishers incoherentes
   - Penalizar datasets con temas desviados

2. **Forzar diversidad en explicaciones**
   - Si hay 3 resultados similares, evitar que las 3 explicaciones sean variantes de "datos 2020, granularidad X"

3. **Ajustar scores del LLM**
   - El rango actual (7.5-9.5) es demasiado estrecho
   - Debería haber más variabilidad (4.0-9.5)

### Para el Frontend

Mostrar **advertencias** cuando:
- Publisher parece incoherente con el tema
- Explicación es muy genérica (< 30 caracteres sin datos específicos)
- Score del LLM es muy alto (>9.0) pero la explicación breve

---

## 📋 Conclusiones Finales

### ¿Vale la pena usar explicaciones del LLM?

| Aspecto | Veredicto |
|---------|-----------|
| **Para usuarios expertos** | ❌ No aporta valor suficiente (explicaciones obvias) |
| **Para usuarios novatos** | ⚠️ Moderado (ayuda a entender relevancia básica) |
| **Para detección de errores** | ❌ No detecta incoherencias (C1-R5) |
| **Para justificar re-ranking** | ⚠️ Aceptable (da contexto aunque sea genérico) |

### Decisión Recomendada

**Opción A: Mejorar antes de usar**
- Iterar en el prompt con los ejemplos de éxito/fracaso identificados
- Añadir validación de metadatos al sistema de explicaciones
- Volver a evaluar con batería similar

**Opción B: Usar con advertencias**
- Mostrar explicaciones como "contexto adicional"
- Añadir indicadores de confianza (ej: "⚠️ Explicación genérica")
- No mostrar score numérico del LLM al usuario

**Opción C: Descartar re-ranking con LLM**
- Las explicaciones no justifican el coste de latencia (~40s)
- El re-ranking tampoco mejora significativamente la calidad
- Pivotar a alternativas (#3 interpretación, #4 expansión semántica)

---

## 📁 Archivos Relacionados

- `bateria_mini_2026-05-30_205714_para_evaluar.csv` - Datos brutos
- `BATERIA_PARA_EVALUAR.md` - Formato de evaluación
- `bateria_pruebas_mini.py` - Script para generar batería
- `evaluacion_automatica_explicaciones.py` - Evaluación heurística

---

**Evaluación realizada el:** 2026-05-30  
**Próxima acción recomendada:** Iterar en el prompt del LLM usando los casos de éxito (C1-R4) como ejemplo positivo.
