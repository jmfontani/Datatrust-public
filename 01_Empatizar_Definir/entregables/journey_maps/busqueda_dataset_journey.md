# Journey Map: Búsqueda de Datasets

## Proyecto: Buscador Semántico de Datasets Públicos
**Fecha:** Junio 2026
**Usuario:** Investigador/Analista/Periodista (genérico)

---

## 📍 Escenario: María necesita datos sobre despoblación rural para su investigación

### Paso 1: Identificación de necesidad

| Aspecto | Detalle |
|---------|---------|
| **Acción** | María decide buscar datos para su tesis sobre despoblación |
| **Pensamiento** | "Necesito datos comparables entre provincias españolas últimos 10 años" |
| **Emoción** | 😊 Motivada, expectante |
| **Dolor** | No sabe por dónde empezar |

---

### Paso 2: Decisión de portal

| Aspecto | Detalle |
|---------|---------|
| **Acción** | Entra a datos.gob.es |
| **Pensamiento** | "Aquí debería haber datos oficiales del INE o Ministerio" |
| **Emoción** | 😐 Neutral, cautelosa |
| **Dolor** | Recordar URL, navegar estructura del portal |

**Oportunidad:** Acceso directo desde Google/buscadores

---

### Paso 3: Formulación de búsqueda

| Aspecto | Detalle |
|---------|---------|
| **Acción** | Escribe "despoblación" en el buscador |
| **Pensamiento** | "¿Funcionará con esta palabra? ¿Será demasiado amplia?" |
| **Emoción** | 😐 Incertidumbre |
| **Dolor** | No sabe si usar "despoblación", "población", "demografía", "migración" |

**Oportunidad:** Sugerencias semánticas, sinónimos, búsqueda por intención

---

### Paso 4: Evaluación de resultados

| Aspecto | Detalle |
|---------|---------|
| **Acción** | Recibe 150 resultados con "despoblación" en el título |
| **Pensamiento** | "Son demasiados, muchos no son relevantes. ¿Cómo filtro?" |
| **Emoción** | 😤 Frustrada |
| **Dolor** | Resultados por palabra clave sin contexto, sin priorización |

**Oportunidad:** Ranking por relevancia, filtros facetados, preview

---

### Paso 5: Exploración individual

| Aspecto | Detalle |
|---------|---------|
| **Acción** | Abre dataset "Padrón municipal de habitantes" |
| **Pensamiento** | "¿Tendrá datos por municipio? ¿Está actualizado?" |
| **Emoción** | 😐 Escepticismo |
| **Dolor** | Metadatos incompletos, no sabe si es útil sin descargar |

**Oportunidad:** Preview de datos, metadatos estructurados, calidad visual

---

### Paso 6: Descarga y validación

| Aspecto | Detalle |
|---------|---------|
| **Acción** | Descarga CSV de 500MB, abre, descubre que no tiene lo que busca |
| **Pensamiento** | "Perdí 20 minutos. Esto no era lo que necesitaba." |
| **Emoción** | 😠 Frustrada, tiempo perdido |
| **Dolor** | Dataset incorrecto, formato no usable, datos desactualizados |

**Oportunidad:** Preview previo, sugerencias de datasets relacionados

---

### Paso 7: Iteración (o abandono)

| Aspecto | Detalle |
|---------|---------|
| **Acción** | Prueba con otra búsqueda: "población municipal 2014-2024" |
| **Pensamiento** | "A ver si ahora tengo más suerte..." |
| **Emoción** | 😤 Persistencia pero con frustración creciente |
| **Dolor** | Ciclo de prueba-error, sin garantías de éxito |

**Oportunidad:** Búsqueda conversacional, refinamiento progresivo

---

## 📊 Resumen de puntos de dolor

| Fase | Dolor principal | Severidad | Oportunidad de mejora |
|------|-----------------|-----------|----------------------|
| 3. Formulación | No sabe qué términos usar | 🔴 Alta | Búsqueda semántica |
| 4. Evaluación | Demasiados resultados sin contexto | 🔴 Alta | Ranking + filtros |
| 5. Exploración | Metadatos insuficientes | 🟡 Media | Preview estructurado |
| 6. Descarga | Dataset incorrecto, tiempo perdido | 🔴 Alta | Preview + sugerencias |

---

## 💡 Momentos de verdad (Make-or-break)

1. **Moment 1:** Si la búsqueda no entiende la intención → abandona
2. **Moment 2:** Si no puede verificar calidad sin descargar → abandona
3. **Moment 3:** Si el primer dataset no es relevante → abandona o reintenta

**Meta del proyecto:** Que ninguno de estos momentos resulte en abandono.

---

## 🎯 Métricas de éxito del journey mejorado

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Tiempo hasta dataset relevante | 30-60 min | < 5 min |
| Tasa de abandono en búsqueda | ~40% | < 10% |
| Satisfacción con resultados | 2-3/5 | 4-5/5 |
| Datasets descubiertos (vs buscados) | 1:1 | 1:3 |
