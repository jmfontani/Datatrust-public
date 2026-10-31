# Informe Final: Cuatro Iteraciones de Prompts LLM

**Fecha:** 2026-05-31  
**Evaluador:** Usuario  
**Modelo:** deepseek-v4-flash:cloud  
**Iteraciones:** 4 versiones de prompt evaluadas

---

## 📊 Comparativa de las 4 Baterías

### Métricas Agregadas

| Iteración | Prompt | Media Humana | Media LLM | Tendencia |
|-----------|--------|--------------|-----------|-----------|
| **v1** | Original | 3.33/5 | 8.75/10 | Scores inflados |
| **v2** | Ejemplos buenos/malos | 3.17/5 | 8.50/10 | Detecta incoherencias |
| **v3** | Reglas de puntuación | 3.22/5 | 8.17/10 | Mejora especificidad |
| **v4** | **Idioma español** | **3.22/5** | **7.94/10** | **Mejor calibración** |

**Conclusión global**: Las iteraciones mejoran el sistema, pero la media humana se estabiliza en ~3.2/5.

---

## 🎯 Patrón Sistemático Confirmado (4/4 baterías)

> **"Posición 1 siempre bien evaluada, posiciones 2-3 consistentemente sobreestimadas por el LLM."**

| Iteración | Posición 1 | Posición 2 | Posición 3 |
|-----------|------------|------------|------------|
| v1 | 4-5/5 ✅ | 2-3/5 ❌ | 2-3/5 ❌ |
| v2 | 5/5 ✅ | 2-3/5 ❌ | 1-3/5 ❌ |
| v3 | 5/5 ✅ | 2-3/5 ❌ | 1-3/5 ❌ |
| **v4** | **5/5 ✅** | **2/5 ❌** | **1-3/5 ❌** |

**Este es un problema fundamental del modelo**, no del prompt.

---

## 📈 Evolución por Aspectos

### 1. Calibración de Scores (Mejorado ✅)

| Caso Problemático | v1 Score | v2 Score | v3 Score | **v4 Score** |
|-------------------|----------|----------|----------|--------------|
| T1-R9 (Murcia) | N/A | N/A | 6.0 | **4.0** ✅ |
| T1-R8 (Menorca) | N/A | 8.0 | 7.0 | **6.0** ✅ |

**Hallazgo v4**: "Mejora notable en discriminación de scores" - Evaluador

### 2. Consistencia de Idioma (Corregido ✅)

| Iteración | C1 Explicaciones | Estado |
|-----------|------------------|--------|
| v1 | Español | ✅ |
| v2 | Español | ✅ |
| v3 | **Inglés** | ❌ **Regresión** |
| **v4** | **Español** | ✅ **Corregido** |

> "Vuelta al español, mejora de consistencia" - Evaluador v4

### 3. Especificidad (Mejorado parcialmente ⚠️)

| Caso | Evolución | Estado v4 |
|------|-----------|-----------|
| **S1-R1** | "Datos más recientes..." → "Dataset más reciente..." → "Dataset más reciente..." | ✅ Sólido (5/5) |
| **S1-R2** | "Datos 2020 con granularidad..." → "Misma temática y año..." → "2020 y granularidad secciones..." | ⚠️ "Espejo del título" (3/5) |
| **S1-R3** | Similar a R2 | ⚠️ Sin valor añadido (3/5) |

> "R2/R3 siguen siendo explicaciones-espejo del título, sin valor añadido" - Evaluador v4

---

## ❌ Problemas Persistentes (4/4 baterías)

### Problema 1: C1-R5 (Juventud y economía / Ministerio de Transportes)

| Versión | Score LLM | Score Humano | Explicación | Problema |
|---------|-----------|--------------|-------------|----------|
| v2 | 9.0 | 2/5 | "Temática explícita..." | Publisher incoherente |
| v3 | 9.0 | 2/5 | "Explicitly combines..." | En inglés |
| **v4** | **9.0** | **2/5** | **"Título y tema... aunque descripción genérica"** | **¡Se autocontradice!** |

> "R5 se autocontradice ('genérica' con 9/10)" - Evaluador v4

**El LLM reconoce que es genérica pero aún así da 9/10.**

### Problema 2: S1-R2/R3 (Redundancia)

| Versión | Explicación R2 | Explicación R3 | Problema |
|---------|----------------|----------------|----------|
| v1 | "Datos 2020 con granularidad secciones..." | "Datos 2020 a nivel distritos..." | Intercambiables |
| v2 | "Misma temática y año..." | "Misma temática y año..." | Redundantes |
| v4 | "2020 y granularidad secciones..." | "2020 y granularidad distritos..." | **Espejo del título** |

### Problema 3: T1 (Recupera datasets incorrectos)

> "Si el modelo sabe que R8/R9 no son Canarias, no debería recuperarlos en top-3" - Evaluador v4

**Hallazgo crítico**: El LLM **detecta** que Menorca y Murcia no son Canarias, pero aún así los incluye en el top-3.

| Resultado | Score v4 | ¿Qué dice? | ¿Por qué está en top-3? |
|-----------|----------|------------|-------------------------|
| T1-R8 (Menorca) | 6.0 | "aunque no es Canarias" | ❌ No debería estar |
| T1-R9 (Murcia) | 4.0 | "pero no Canarias" | ❌ No debería estar |

**Conclusión**: El motor híbrido (PostgreSQL) los recupera, y el LLM no los filtra suficientemente.

---

## ✅ Avances por Iteración

### v1 → v2: Detección de problemas
- ✅ Empieza a decir "sin conexión", "diferente región"

### v2 → v3: Especificidad
- ✅ Menciona indicadores concretos (NEET)
- ⚠️ Pero introduce problema de idioma

### v3 → v4: Calibración + Idioma
- ✅ Vuelve al español
- ✅ Scores más realistas (6.0 y 4.0 para datasets incorrectos)
- ✅ Menos redundancia en explicaciones

---

## 🎯 Veredicto Final

### ¿Vale la pena seguir iterando?

**No.** Se han probado 4 versiones y se ha alcanzado un **techo de rendimiento**:

| Métrica | Techo observado |
|---------|-----------------|
| Media humana | ~3.2/5 (no mejora más) |
| Acierto Posición 1 | 100% (5/5) ✅ |
| Fallo Posición 2 | ~70% (2-3/5) ❌ |
| Fallo Posición 3 | ~70% (1-3/5) ❌ |

### Prompt Recomendado: v4

El prompt v4 es el **óptimo actual**:
- ✅ Idioma español consistente
- ✅ Mejor calibración de scores
- ✅ Detecta y penaliza incoherencias (6.0, 4.0)
- ✅ Explicaciones más específicas

### Limitaciones Inherentes al Modelo

1. **No puede mejorar S1-R2/R3**: Son datasets casi idénticos, cualquier explicación será similar
2. **No filtra C1-R5**: Aunque detecta que es genérico, no lo penaliza suficiente
3. **Incluye datasets incorrectos**: El motor híbrido los recupera, el LLM no los excluye

---

## 💡 Recomendaciones de Implementación

### Para el Frontend

**Opción A: Mostrar solo Posición 1 con explicación**
```python
# Solo mostrar el top-1 del LLM
if result.new_rank == 1:
    show_explanation(result.explanation)
    show_score(result.llm_relevance_score)
```

**Opción B: Mostrar todos pero con advertencias**
```python
# Posición 1: sin advertencia
# Posición 2-3: con advertencia "Posiblemente menos relevante"
```

**Opción C: Descartar re-ranking, usar explicaciones bajo demanda**
- Búsqueda normal (rápida)
- Botón "¿Por qué este resultado?" → Genera explicación LLM solo para ese dataset

### Para la Arquitectura

**Problema identificado**: El motor híbrido recupera datasets incorrectos (Menorca, Murcia para "Canarias").

**Solución**: Añadir filtro post-búsqueda, pre-LLM:
```python
if query_contains_location("Canarias"):
    results = filter(results, territory_contains("Canarias"))
```

---

## 📁 Archivos Finales

```
resultados/
├── INFORME_FINAL_4_ITERACIONES.md                    ← Este documento
├── bateria_mini_2026-05-30_205714_para_evaluar.csv   # v1 Original
├── bateria_mini_2026-05-30_212544_para_evaluar.csv   # v2 Ejemplos
├── bateria_mini_2026-05-31_203914_para_evaluar.csv   # v3 Reglas
└── bateria_mini_2026-05-31_205027_para_evaluar.csv   # v4 Español
```

---

## 🏁 Conclusión

**Tres iteraciones de prompts han llevado al sistema a su óptimo.**

El prompt v4 (actual) es **suficientemente bueno** para:
- ✅ Generar explicaciones útiles en español
- ✅ Detectar incoherencias y penalizarlas
- ✅ Justificar el re-ranking con argumentos específicos

Pero **no puede superar**:
- ❌ La redundancia inherente a datasets similares
- ❌ La inclusión de datasets geográficamente incorrectos
- ❌ La sobreestimación sistemática de posiciones 2-3

**Recomendación**: Usar el prompt v4 en producción, pero:
1. Mostrar solo el TOP-1 con explicación, o
2. Añadir filtro geográfico pre-LLM, o
3. Considerar alternativas (#3 interpretación, #4 expansión) para futuro

---

**Iteraciones completadas:** 4  
**Prompt final recomendado:** v4 (español, reglas de puntuación explícitas)  
**Próxima evaluación:** No requiere más iteraciones de prompt
