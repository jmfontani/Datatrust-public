# Evaluación de Explicaciones - Qwen2.5:7b vs DeepSeek

## 📅 Fecha: 01/06/2026
## 👤 Evaluador: Usuario (análisis manual)

---

## 📊 Resumen de Puntuaciones

### Modelo: Qwen2.5:7b (Local)

| Caso | Resultado | Score LLM | Puntuación Usuario | Diff |
|------|-----------|-----------|-------------------|------|
| **S1** | R1 | 9.0 | **4/5** | - |
| **S1** | R2 | 7.0 | **3/5** | - |
| **S1** | R3 | 6.5 | **3/5** | - |
| **C1** | R4 | 9.0 | **5/5** ⭐ | - |
| **C1** | R5 | 6.5 | **2/5** ⚠️ | - |
| **C1** | R6 | 5.0 | **3/5** | - |

### Promedios
- **Promedio puntuaciones usuario:** 3.33/5
- **Promedio scores LLM:** 7.17/10
- **Correlación:** Score LLM ~2x puntuación usuario

---

## 📝 Comentarios Detallados por Caso

### Caso S1 - Sinonimia ("paro juvenil desempleo jóvenes")

**Veredicto general:** ✅ Recuperación correcta, ⚠️ Explicaciones débiles

| Pos | Puntuación | Observación |
|-----|------------|-------------|
| R1 | 4/5 | Añade valor real, aunque breve |
| R2 | 3/5 | Genérica, redundante con R1 |
| R3 | 3/5 | Genérica, casi intercambiable con R2 |

**Problema identificado:** Las 3 explicaciones son **casi intercambiables** - no diferencian por qué R1 es mejor que R2 o R3. El LLM repite la misma estructura: "proporciona información sobre..." sin añadir valor analítico.

**Ejemplo de redundancia:**
- R1: "proporciona información sobre la población parada..."
- R2: "ofrece información sobre la población parada..."
- R3: "también proporciona información sobre la población parada..."

---

### Caso C1 - Conceptual ("vulnerabilidad económica juventud")

**Veredicto general:** ⭐ R4 sobresaliente, ⚠️ R5 falla, R6 aceptable

| Pos | Score LLM | Puntuación | Análisis |
|-----|-----------|------------|----------|
| R4 | 9.0 | **5/5** ⭐ | Explicación perfecta: "proporciona información directamente relacionada con la vulnerabilidad económica de la juventud en el País Vasco" |
| R5 | 6.5 | **2/5** ⚠️ | **Score inflado** - El publisher (Eustat/País Vasco) no es coherente con la descripción (datos de España entera). Explicación vacía: "no se centra específicamente en la juventud ni en el País Vasco" |
| R6 | 5.0 | **3/5** | Conexión razonable pero indirecta. Justificación aceptable. |

**Problema crítico identificado:** El LLM asigna **6.5/10 a R5** cuando la explicación misma dice que NO cumple los criterios. Esto confirma el patrón de **sobrevaloración de posiciones 2-3**.

---

## 🔍 Observaciones Generales del Evaluador

> "El modelo es **mejor recuperando** (datasets acertados) que **explicando** (justificaciones genéricas o circulares). 
> 
> Para S1 las 3 explicaciones son casi intercambiables. 
> 
> Para C1 hay buena discriminación en R4 pero falla en penalizar R5."

---

## 📈 Comparativa con DeepSeek (basado en evaluaciones previas)

| Aspecto | DeepSeek-v4-flash | Qwen2.5:7b |
|---------|-------------------|------------|
| **Velocidad** | ~2s/query | ~50s/query ❌ |
| **Recuperación** | ✅ Buena | ✅ Buena (similar) |
| **Calidad explicaciones** | 3.2/5 (promedio iteraciones) | 3.33/5 |
| **Especificidad** | Alta (menciona años, territorios) | Media (frases genéricas) |
| **Calibración scores** | Tendencia a sobrevalorar 2-3 | Similar - R5 inflado |
| **Redundancia** | Media | ⚠️ **Alta** (S1) |

---

## 🎯 Conclusiones

### Fortalezas de Qwen2.5:7b
1. ✅ **R4 (C1) sobresaliente** - Mejor explicación que cualquiera de DeepSeek
2. ✅ Recuperación de datasets tan buena como DeepSeek
3. ✅ Respeta formato JSON correctamente
4. ✅ Idioma español perfecto

### Debilidades de Qwen2.5:7b
1. ❌ **15-25x más lento** (impracticable para producción)
2. ⚠️ **Explicaciones redundantes** - mismo patrón repetido
3. ⚠️ **Score inflado en R5** - no penaliza debilidades reales
4. ⚠️ **Genérico** - falta especificidad (años, datos concretos)

### Veredicto Final
**DeepSeek-v4-flash:cloud sigue siendo mejor opción** por:
- Velocidad: 2s vs 50s
- Calidad similar (3.2 vs 3.33)
- Especificidad mejor en DeepSeek

**Qwen2.5:7b viable solo para:** desarrollo offline, casos sin internet, o análisis profundo sin prisa.

---

## 💡 Recomendaciones para Mejorar Prompts

1. **Forzar variedad:** Añadir instrucción "Cada explicación debe ser ÚNICA y no intercambiable"
2. **Concreción:** Exigir "menciona año, territorio o dato específico que justifique el score"
3. **Autocrítica:** "Si el dataset tiene debilidades, menciónalas explícitamente"
4. **Diferenciación:** "Explica por qué este dataset es mejor/peor que los otros"

---

## 📁 Archivos Relacionados

- Resultados Qwen: `bateria_qwen_directo_2026-06-01_182545_para_evaluar.csv`
- Resultados DeepSeek: `bateria_mini_2026-05-31_205027_para_evaluar.csv`
- Este documento: `EVALUACION_QWEN_2026-06-01.md`
