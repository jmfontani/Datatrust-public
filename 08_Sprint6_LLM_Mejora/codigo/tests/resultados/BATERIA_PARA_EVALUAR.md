# Batería de Pruebas - Explicaciones LLM
## Para Evaluación Humana

**Fecha:** 2026-05-30  
**Casos:** 6 explicaciones de 2 queries diferentes  
**Modelo:** deepseek-v4-flash:cloud

---

## 📝 Instrucciones

Para cada explicación, asigna una puntuación del **1 al 5**:

| Puntuación | Significado |
|------------|-------------|
| ⭐ (1) | **Muy mala** - Explicación incorrecta o irrelevante |
| ⭐⭐ (2) | **Mala** - Poco relevante, genérica o confusa |
| ⭐⭐⭐ (3) | **Aceptable** - Correcta pero genérica |
| ⭐⭐⭐⭐ (4) | **Buena** - Específica y útil |
| ⭐⭐⭐⭐⭐ (5) | **Excelente** - Muy específica y valiosa |

**Criterios a considerar:**
- ¿La explicación justifica bien por qué el dataset es relevante?
- ¿Es específica o usa frases genéricas?
- ¿Menciona datos concretos del dataset?
- ¿Sería útil para un usuario entender el resultado?

---

## 📊 Casos de Prueba

### CASO S1: Sinonimia
**Query:** `paro juvenil desempleo jóvenes`

> Query con sinónimos (paro/desempleo, juvenil/jóvenes). El LLM debe entender que "paro" = "desempleo" y "juvenil" = "jóvenes".

---

#### Resultado 1

| Campo | Valor |
|-------|-------|
| **Dataset** | Población parada registrada de 16 a 24 años de edad. Media anual. Barrios de Canarias. 2020 |
| **Publisher** | ISTAC - Gobierno de Canarias |
| **Score LLM** | 9.5/10 |
| **Explicación** | "Datos más recientes (2020) y mayor granularidad (barrios) para el grupo de edad exacto (16-24)." |

**Tu evaluación:**
- Puntuación: ___ /5
- Comentario: ___________________________

---

#### Resultado 2

| Campo | Valor |
|-------|-------|
| **Dataset** | Población parada registrada de 16 a 24 años de edad. Media anual. Secciones de Canarias. 2020 |
| **Publisher** | ISTAC - Gobierno de Canarias |
| **Score LLM** | 9.0/10 |
| **Explicación** | "Datos 2020 con granularidad secciones, muy detallados y actuales." |

**Tu evaluación:**
- Puntuación: ___ /5
- Comentario: ___________________________

---

#### Resultado 3

| Campo | Valor |
|-------|-------|
| **Dataset** | Población parada registrada de 16 a 24 años de edad. Media anual. Distritos de Canarias. 2020 |
| **Publisher** | ISTAC - Gobierno de Canarias |
| **Score LLM** | 8.5/10 |
| **Explicación** | "Datos 2020 a nivel distritos, menos granular que barrios/secciones pero actual." |

**Tu evaluación:**
- Puntuación: ___ /5
- Comentario: ___________________________

---

### CASO C1: Conceptual
**Query:** `vulnerabilidad económica juventud`

> Concepto abstracto que requiere interpretación. El LLM debe identificar datasets que midan vulnerabilidad económica en jóvenes (NEET, desempleo, etc.).

---

#### Resultado 4

| Campo | Valor |
|-------|-------|
| **Dataset** | Proporción de jóvenes entre 15 y 24 años que no cursan estudios, no están empleados...
| **Publisher** | INE - Instituto Nacional de Estadística |
| **Score LLM** | 9.5/10 |
| **Explicación** | "Mide directamente la proporción de jóvenes que no estudian, no trabajan ni reciben formación (tasa NEET), indicador clave de vulnerabilidad económica juvenil. Datos nacionales y actuales." |

**Tu evaluación:**
- Puntuación: ___ /5
- Comentario: ___________________________

---

#### Resultado 5

| Campo | Valor |
|-------|-------|
| **Dataset** | Juventud y economía |
| **Publisher** | Ministerio de Transportes y Movilidad Sostenible |
| **Score LLM** | 8.5/10 |
| **Explicación** | "Temática directamente sobre juventud y economía, aunque más general. Cubre aspectos económicos y demográficos a nivel nacional." |

**Tu evaluación:**
- Puntuación: ___ /5
- Comentario: ___________________________

---

#### Resultado 6

| Campo | Valor |
|-------|-------|
| **Dataset** | Asesoramiento a jóvenes |
| **Publisher** | Comunidad de Madrid |
| **Score LLM** | 7.5/10 |
| **Explicación** | "Iniciativa Garantía Juvenil, centrada en facilitar el acceso al empleo de jóvenes, relevante para la vulnerabilidad económica. Datos de la Comunidad de Madrid." |

**Tu evaluación:**
- Puntuación: ___ /5
- Comentario: ___________________________

---

## 📋 RESUMEN PARA ENVIAR

**Copia y pega tu evaluación en este formato:**

```
CASO S1 - Resultado 1: __/5
CASO S1 - Resultado 2: __/5
CASO S1 - Resultado 3: __/5
CASO C1 - Resultado 4: __/5
CASO C1 - Resultado 5: __/5
CASO C1 - Resultado 6: __/5

COMENTARIOS:
- Caso S1: ___________________________
- Caso C1: ___________________________

OBSERVACIONES GENERALES:
_________________________________
```

O simplemente dime las puntuaciones separadas por comas:
**Ejemplo:** "5, 4, 3, 5, 4, 3"

---

## 💡 ¿Qué evaluar en cada caso?

### Caso S1 (Sinonimia)
- ¿Reconoce que "paro" = "desempleo"?
- ¿Identifica correctamente el grupo de edad 16-24 como "juvenil"?
- ¿Son las explicaciones específicas o usan frases genéricas?

### Caso C1 (Conceptual)
- ¿Identifica correctamente el indicador NEET como medida de vulnerabilidad?
- ¿La explicación del resultado #4 es específica y precisa?
- ¿Las explicaciones son útiles para entender por qué es relevante?

---

## 📁 Archivos Disponibles

- **CSV completo:** `bateria_mini_2026-05-30_205714_para_evaluar.csv`
- **Este documento:** `BATERIA_PARA_EVALUAR.md`

**Para evaluar con Excel:** Abre el CSV y completa las columnas vacías `puntuacion_1_5` y `comentario`.

---

*Generado automáticamente el 2026-05-30*
