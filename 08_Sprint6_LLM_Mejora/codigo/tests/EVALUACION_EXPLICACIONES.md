# Evaluación de Explicaciones LLM

Sistema de evaluación de la calidad de las explicaciones generadas por el LLM en el proceso de re-ranking.

## ¿Por qué evaluar las explicaciones?

El re-ranking con LLM genera dos outputs:
1. **Resultados reordenados** (ya evaluados en tests v07 vs v08)
2. **Explicaciones de relevancia** (sin evaluar hasta ahora)

Aunque el re-ranking tiene problemas de latencia, las explicaciones podrían tener valor independiente si son:
- ✅ **Correctas**: Justifican adecuadamente la relevancia
- ✅ **Útiles**: Ayudan al usuario a entender los resultados
- ✅ **Precisas**: Los datos mencionados son reales

## Requisitos Previos

Antes de ejecutar cualquier script, activa el entorno virtual:

```bash
source ~/datos/PFM/Datatrust/venv/bin/activate
```

**Nota**: Los scripts requieren dependencias instaladas en el entorno virtual (requests, urllib3, etc.)

---

## Sistema de Evaluación Implementado

### 1. Evaluación Humana Interactiva

**Script**: `evaluar_explicaciones_llm.py`

**Ejecución:**
```bash
source ~/datos/PFM/Datatrust/venv/bin/activate
cd ~/datos/PFM/Datatrust/08_Sprint6_LLM_Mejora/codigo/tests
python3 evaluar_explicaciones_llm.py
```

Presenta casos reales al evaluador humano para puntuación manual.

#### Dimensiones evaluadas (1-5 puntos):

| Dimensión | Descripción |
|-----------|-------------|
| **Relevancia** | ¿Justifica correctamente por qué es relevante? |
| **Precisión** | ¿Los datos/facts mencionados son correctos? |
| **Utilidad** | ¿Ayuda al usuario a entender el resultado? |
| **Coherencia** | ¿Tiene sentido y está bien escrita? |
| **Justificación Score** | ¿El score corresponde con la explicación? |

#### Uso:

```bash
# 1. Activar entorno virtual (obligatorio)
source ~/datos/PFM/Datatrust/venv/bin/activate

# 2. Ir al directorio y ejecutar
cd ~/datos/PFM/Datatrust/08_Sprint6_LLM_Mejora/codigo/tests
python3 evaluar_explicaciones_llm.py
```

#### Flujo:

1. Introducir nombre del evaluador
2. Para cada caso:
   - Se muestra query + dataset + explicación del LLM
   - El evaluador puntúa las 5 dimensiones (1-5)
   - Opcional: comentario adicional
3. Al finalizar se guardan resultados en JSON y CSV
4. Se muestra resumen con métricas agregadas

#### Salida generada:

```
resultados/
├── evaluacion_explicaciones_2025-05-30_143022.json  (datos completos)
└── evaluacion_explicaciones_2025-05-30_143022.csv   (resumen tabular)
```

---

### 2. Evaluación Automática (Heurística)

**Script**: `evaluacion_automatica_explicaciones.py`

Analiza explicaciones mediante reglas sin intervención humana.

#### Dimensiones automáticas:

| Dimensión | Heurística |
|-----------|------------|
| **Longitud** | 60-150 caracteres = óptimo |
| **Relevancia** | Overlap de keywords con query/dataset |
| **Especificidad** | Detección de frases genéricas |
| **Legibilidad** | Longitud promedio de palabras |
| **Diversidad** | Ratio palabras únicas / total |

#### Frases genéricas detectadas:

- "dataset relevante"
- "contiene información"
- "proporciona datos"
- "relacionado con"
- "sobre el tema"
- "información sobre"
- "datos de"

#### Uso:

```bash
# Activar entorno virtual primero
source ~/datos/PFM/Datatrust/venv/bin/activate

# Ejecutar evaluación
python3 evaluacion_automatica_explicaciones.py
```

#### Ejemplo de resultado:

```
📝 CASO 1:
   Query: paro juvenil desempleo jóvenes
   Explicación: Directamente relacionado con empleo juvenil...
   
   Scores:
     longitud       : 4.0/5.0 - Larga (150-300 caracteres)
     relevancia     : 5.0/5.0 - Excelente overlap (52%)
     especificidad  : 2.0/5.0 - Muy genérica (3 frases genéricas)
     legibilidad    : 5.0/5.0 - Muy legible (5.6 caracteres)
     diversidad     : 5.0/5.0 - Alta diversidad léxica (86%)
   
   🎯 GLOBAL: 4.20/5.0 - Buena
```

---

## Hallazgos del Análisis Automático (Ejemplo)

Basado en 5 casos de prueba:

### Métricas Agregadas

| Dimensión | Score Medio |
|-----------|-------------|
| **Longitud** | 4.60/5.0 ✅ |
| **Relevancia** | 4.60/5.0 ✅ |
| **Especificidad** | 3.40/5.0 ⚠️ |
| **Legibilidad** | 5.00/5.0 ✅ |
| **Diversidad** | 5.00/5.0 ✅ |
| **GLOBAL** | **4.52/5.0** ✅ |

### Problema Identificado: **Falta de Especificidad**

Las explicaciones tienden a usar frases genéricas como:
- "proporciona información sobre..."
- "dataset relevante que contiene..."
- "puede relacionarse con..."

### Recomendación

**Ajustar el prompt del LLM** para:
1. Evitar frases genéricas
2. Exigir mención de datos concretos del dataset
3. Forzar conexión explícita con términos de la query

**Ejemplo de prompt mejorado**:

```
Explica por qué este dataset es relevante para la query.
REGLAS:
- NO uses frases genéricas como "proporciona información"
- MENCIONA datos específicos del dataset (título, descripción)
- CONECTA explícitamente con la query del usuario
- MÁXIMO 100 caracteres
- Sé específico y conciso

Ejemplo BUENO: "Dataset específico sobre paro registrado de 16-24 años en Canarias, directamente sobre juventud laboral"
Ejemplo MALO: "Proporciona información relevante sobre el tema"
```

---

## Frontend Streamlit

Para ejecutar el frontend gráfico:

```bash
# 1. Activar entorno virtual
source ~/datos/PFM/Datatrust/venv/bin/activate

# 2. Ejecutar Streamlit
cd ~/datos/PFM/Datatrust/08_Sprint6_LLM_Mejora/codigo/frontend
streamlit run app_v09_demo.py --server.port 8502
```

Luego abre: http://localhost:8502

---

## Demo Interactivo en Consola

Para ejecutar el demo interactivo:

```bash
# 1. Activar entorno virtual
source ~/datos/PFM/Datatrust/venv/bin/activate

# 2. Ejecutar demo
cd ~/datos/PFM/Datatrust/08_Sprint6_LLM_Mejora/codigo/tests
python3 demo_interactivo_explicaciones.py
```

---

## Métricas Sugeridas para Dashboard

```python
# Métricas de calidad de explicaciones
{
    "explicaciones_evaluadas": 50,
    "score_medio": 4.2,
    "tasa_genéricas": 0.25,  # % con frases genéricas
    "tasa_relevantes": 0.85,  # % con relevancia > 4
    "por_categoria": {
        "sinonimia": 4.5,
        "conceptual": 4.1,
        "territorial": 3.8
    }
}
```

---

## Próximos Pasos

1. **Ejecutar evaluación humana** con al menos 20 casos
2. **Comparar** resultados humanos vs automáticos
3. **Ajustar prompt** del LLM según recomendaciones
4. **Iterar**: Nueva evaluación → Mejora prompt → Nueva evaluación
5. **Decisión**: ¿Las explicaciones justifican el coste del LLM?

---

## Archivos Relacionados

- `evaluar_explicaciones_llm.py` - Evaluación humana interactiva
- `evaluacion_automatica_explicaciones.py` - Evaluación automática
- `resultados/evaluacion_explicaciones_*.json` - Resultados guardados
- `resultados/evaluacion_explicaciones_*.csv` - Resumen CSV
- `llm_reranker.py` - Generador de explicaciones (línea 207)
- `app_v09_demo.py` - Frontend con explicaciones

---

**Nota**: Aunque el re-ranking tiene problemas de latencia, las explicaciones podrían desacoplarse y mostrarse bajo demanda (click del usuario) sin afectar el tiempo de respuesta inicial.
