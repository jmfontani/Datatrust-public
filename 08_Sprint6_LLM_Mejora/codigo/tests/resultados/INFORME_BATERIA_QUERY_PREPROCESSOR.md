# Informe de Batería de Pruebas - Query Preprocessor

**Fecha:** 2026-06-01  
**Objetivo:** Comparar efectividad de búsqueda NORMAL vs MEJORADA con expansión semántica

---

## 📊 Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| **Casos probados** | 8 |
| **Expansiones exitosas** | 1/8 (12.5%) |
| **Ganancia total en resultados** | +0 (1.0x) |
| **Nuevos datasets únicos** | 7 |
| **Overhead promedio** | Variable (1ms - 65s) |

**Veredicto:** ⚠️ **La expansión semántica solo funciona intermitentemente**. Solo el primer caso (T1) logró expansión exitosa.

---

## 🔍 Resultados por Caso

### ✅ Caso T1: "paro en 2022" - ÉXITO

| Aspecto | Valor |
|---------|-------|
| Query expandida | "paro 2022 desempleo desempleados tasa de paro EPA INE SEPE empleo contratos afiliaciones..." |
| Términos añadidos | 12 términos |
| Nuevos resultados | +7 datasets |
| Overhead | 7ms (muy bajo) |

**Análisis:** ✅ Expansión perfecta. Añade sinónimos (paro↔desempleo), fuentes (EPA, INE, SEPE), y conceptos relacionados.

---

### ❌ Casos C1-G1-A1-S1-D1-I1-E1: FALLIDOS

| Caso | Query Original | Query Expandida | Términos Añadidos | Resultado |
|------|---------------|-----------------|-------------------|-----------|
| C1 | "vulnerabilidad económica" | "vulnerabilidad económica" | [] | ❌ Sin cambios |
| G1 | "turismo Barcelona" | "turismo Barcelona" | [] | ❌ Sin cambios |
| A1 | "banco España" | "banco España" | [] | ❌ Sin cambios |
| S1 | "EPA jóvenes" | "EPA jóvenes" | [] | ❌ Sin cambios |
| D1 | "población mayor 65 años" | "población mayor 65 años" | [] | ❌ Sin cambios |
| I1 | "PIB per cápita" | "PIB per cápita" | [] | ❌ Sin cambios |
| E1 | "tasa abandono escolar" | "tasa abandono escolar" | [] | ❌ Sin cambios |

**Patrón identificado:** Solo el primer caso tras reinicio del pre-procesador logra expansión. Los subsiguientes fallan.

---

## 🚨 Problemas Detectados

### 1. **Expansión Intermitente (Crítico)**

```
Caso T1: ✅ Expansión exitosa
Caso C1-G1-A1-S1-D1-I1-E1: ❌ Sin expansión (query_expandida = query)
```

**Hipótesis:**
- Posible problema de cache
- Timeout en llamadas LLM subsiguientes
- Prompt que no funciona consistentemente
- Rate limiting de Ollama

### 2. **Overhead de Tiempo Variable (Crítico)**

| Caso | Tiempo Mejorada | Problema |
|------|-----------------|----------|
| T1 | 58ms | ✅ Normal |
| C1 | 29,706ms (30s) | ❌ Timeout/retardo |
| G1 | 65,358ms (65s) | ❌ Timeout/retardo |
| A1 | 19,572ms (20s) | ❌ Timeout/retardo |

**Hipótesis:** Las llamadas al LLM para expansión están tardando demasiado o fallando.

### 3. **Temas Detectados vs Expansión**

Aunque la interpretación estructural (#3) **sí funciona** y detecta temas:
- C1: "vulnerabilidad económica, pobreza, exclusión social"
- G1: "turismo, viajes, visitantes"
- A1: "banca, finanzas, Banco de España"

La expansión (#4) **no añade términos** a pesar de tener temas detectados.

---

## 📈 Métricas Agregadas

```
Total resultados (normal):     307
Total resultados (mejorada):   307
Ganancia total:                +0 (1.0x)
Nuevos datasets únicos:        7
Overhead promedio:             Variable (1ms - 65s)
```

---

## 🎯 Conclusiones

### Lo que SÍ funciona ✅

1. **Validación (#12):** Detecta queries inválidas y ambigüedades correctamente
2. **Interpretación estructural (#3):** Extrae temas, territorio, conceptos implícitos
3. **Cache persistente:** Reduce tiempo para queries repetidas
4. **Expansión (cuando funciona):** Añade términos relevantes y mejora recall (+7 nuevos datasets en T1)

### Lo que NO funciona ❌

1. **Expansión inconsistente:** Solo ~12% de éxito en la batería
2. **Timeouts frecuentes:** 20-65 segundos de espera
3. **Sin fallback:** Cuando expansión falla, no hay alternativa

---

## 💡 Recomendaciones

### Opción A: Desactivar Expansión (Conservador)
```python
# Usar solo validación + interpretación estructural
# La búsqueda se hace con query original
# Beneficio: Temas detectados para UI, sin riesgo de fallo
```

### Opción B: Fallback Automático (Recomendado)
```python
# Intentar expansión con timeout corto (5s)
# Si falla/tarda, usar expansión léxica simple (sinónimos de diccionario)
# Si también falla, usar query original
```

### Opción C: Procesar Offline (Ambicioso)
```python
# Pre-computar expansiones para queries comunes
# Guardar en base de datos
# Servir desde cache siempre que sea posible
```

---

## 🔧 Acciones Inmediatas Sugeridas

1. **Aumentar timeout** de expansión de 60s a 120s (ya está hecho)
2. **Implementar fallback** a expansión léxica simple si LLM falla
3. **Cachear expansiones exitosas** permanentemente
4. **Revisar prompt** de expansión para mayor consistencia

---

## 📁 Archivos Generados

- `bateria_query_preprocessor_2026-06-01_201439.csv` - Resultados completos

---

**Estado del caso de uso #3+#4+#12:** ⚠️ **Parcialmente funcional** - Requiere ajustes antes de producción.
