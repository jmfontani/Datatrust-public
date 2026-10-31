# Análisis de la Batería de Pruebas Extendida

**Fecha:** 2026-05-23  
**Tests ejecutados:** 41  
**Precisión global:** 73,2% (30 PASS / 11 FAIL / 0 ERROR)  
**API:** http://localhost:8000  
**Datasets cargados:** 87.677

---

## 1. Resumen Ejecutivo

La batería extendida evalúa el buscador semántico en **41 casos de prueba** distribuidos en **17 categorías temáticas**, incluyendo tests básicos, específicos por territorio, de umbrales de calidad y casos especiales (términos modernos, sensibles, inclusión).

### Resultados Clave

| Métrica | Valor |
|---------|-------|
| Tests totales | 41 |
| PASS | 30 (73,2%) |
| FAIL | 11 (26,8%) |
| ERROR | 0 (0%) |
| Categorías con 100% precisión | 11/17 |
| Categorías con problemas | 6/17 |

---

## 2. Metodología

### Estructura de la Batería

La batería está organizada en 12 bloques:

1. **TESTS_BASE** (12 tests): Tests originales mejorados
2. **TESTS_TRANSPORTE** (3 tests): Movilidad, infraestructuras ciclistas, transporte público
3. **TESTS_MEDIO_AMBIENTE** (3 tests): Cambio climático, residuos, espacios verdes
4. **TESTS_ECONOMIA** (3 tests): PIB, pensiones, subvenciones
5. **TESTS_CULTURA** (3 tests): Museos, bibliotecas, festivales
6. **TESTS_DEPORTE** (2 tests): Instalaciones, fútbol
7. **TESTS_INFRAESTRUCTURAS** (2 tests): Obras públicas, carreteras
8. **TESTS_AGRICULTURA** (2 tests): Cultivos, pesca
9. **TESTS_TECNOLOGIA** (2 tests): Banda ancha, I+D+i
10. **TESTS_ESPECIALES** (4 tests): COVID-19, género, discapacidad, inmigración
11. **TESTS_TERRITORIALES** (3 tests): Filtros por Andalucía, Madrid, Cataluña
12. **TESTS_UMBRALES** (2 tests): Comparativa de umbrales (0.10 vs 0.50)

### Criterios de Evaluación

Cada test verifica:
- **min_results**: Número mínimo de resultados esperados
- **must_contain_any**: Al menos un término relevante debe aparecer en cada resultado
- **must_not_contain**: Ningún término prohibido debe aparecer
- **territory_expected**: El territorio debe estar presente
- **territory_filter**: Filtro territorial opcional
- **min_score**: Umbral de calidad (default 0.20, variable en tests de umbrales)

---

## 3. Resultados por Categoría

### Categorías con 100% de Precisión (11/17)

| Categoría | Tests | PASS | Precisión |
|-----------|-------|------|-----------|
| DEMOGRAFIA | 2 | 2 | 100% |
| EDUCACION | 1 | 1 | 100% |
| ENERGIA | 1 | 1 | 100% |
| ESPECIAL | 4 | 4 | 100% |
| INFRAESTRUCTURAS | 2 | 2 | 100% |
| MEDIO_AMBIENTE | 5 | 5 | 100% |
| SANIDAD | 1 | 1 | 100% |
| SEGURIDAD | 1 | 1 | 100% |
| TURISMO | 1 | 1 | 100% |
| UMBRALES | 2 | 2 | 100% |
| VIVIENDA | 1 | 1 | 100% |

**Observación:** Las categorías con 100% incluyen dominios bien representados en el corpus de datos.gob.es (medio ambiente, sanidad, demografía) y casos especiales modernos que el motor maneja correctamente.

### Categorías con Problemas (6/17)

| Categoría | Tests | PASS | FAIL | Precisión |
|-----------|-------|------|------|-----------|
| TERRITORIAL | 3 | 0 | 3 | **0%** |
| EMPLEO | 1 | 0 | 1 | **0%** |
| CULTURA | 3 | 1 | 2 | 33,3% |
| DEPORTE | 2 | 1 | 1 | 50% |
| AGRICULTURA | 2 | 1 | 1 | 50% |
| TECNOLOGIA | 2 | 1 | 1 | 50% |
| ECONOMIA | 3 | 2 | 1 | 66,7% |
| TRANSPORTE | 4 | 3 | 1 | 75% |

---

## 4. Análisis Detallado de Fallos

### 4.1 Filtros Territoriales (3 FAIL - Prioridad ALTA)

**Problema:** Los filtros territoriales (`territorio` en el payload) devuelven **0 resultados** en todos los casos.

**Tests afectados:**
- "turismo" + filtro "Andalucía" → 0 resultados
- "padrón habitantes" + filtro "Madrid" → 0 resultados
- "playas costa" + filtro "Cataluña" → 0 resultados

**Diagnóstico:** El campo `territorio` en el payload de búsqueda no está siendo procesado correctamente por la API, o no hay datasets etiquetados con esos territorios específicos en el corpus.

**Impacto:** ALTO. Los filtros territoriales son una funcionalidad clave para la navegación por comunidades autónomas.

**Recomendación:** Verificar que el campo `territorio` en el payload sea procesado por `search_engine.py` y que los datasets tengan correctamente etiquetado el territorio.

---

### 4.2 Paro Juvenil (1 FAIL)

**Problema:** Resultado #6 "Proporción de jóvenes entre 15 y 24 años que no cursan estudios, no están empleados..." no contiene términos esperados.

**Análisis:** El resultado habla de "jóvenes" y "empleados" pero el contenido no contiene las palabras exactas del test (`paro`, `desempleo`, `juvenil`, `joven`, etc.). El motor detecta "jóvenes" pero el test busca "joven" (sin tilde).

**Recomendación:** Mejorar la normalización de acentos en el test o ampliar los sinónimos en el motor.

---

### 4.3 Movilidad Sostenible - Bicicleta (1 FAIL)

**Problema:** Resultados #1 y #2 son "Carriles Bici" pero el test no detecta "carril bici" ni "bicicleta".

**Análisis:** Los resultados contienen "Carriles Bici" que es la forma correcta, pero el test busca "bicicleta" o "carril bici" (en minúsculas y con espacio). Hay un problema de coincidencia de términos compuestos.

**Adicional:** Resultado #6 contiene "motor" (Red de bidegorris) como falso positivo.

**Recomendación:** Ampliar los sinónimos para incluir "bici" y normalizar la búsqueda de términos compuestos.

---

### 4.4 Pensiones (1 FAIL)

**Problema:** Resultados #7 y #8 son "Pensiones" y "Pensiones contributivas" pero no contienen términos esperados.

**Análisis:** Los resultados contienen "Pensiones" que debería coincidir con "pensión" (plural vs singular). El problema es la coincidencia de plural/singular.

**Recomendación:** El motor ya maneja plurales en `search_engine.py` (líneas 249-252), verificar que funcione correctamente.

---

### 4.5 Museos (1 FAIL)

**Problema:** Resultado #3 "Salas de exposiciones" no contiene términos esperados.

**Análisis:** "Salas de exposiciones" está relacionado con museos pero no contiene las palabras exactas del test. Es un caso de sinónimo implícito.

**Recomendación:** Añadir "sala" y "exposición" como sinónimos de museo.

---

### 4.6 Festivales (1 FAIL)

**Problema:** Resultado #7 "Centres musicals 2016 / Centros musicales 2016" no contiene términos esperados.

**Análisis:** El resultado contiene "musicales" pero el test busca "música" o "festival". Es un problema de coincidencia de términos relacionados.

**Recomendación:** Añadir "musical" como sinónimo de música/festival.

---

### 4.7 Instalaciones Deportivas (1 FAIL)

**Problema:** Todos los resultados son "Instalaciones deportivas" pero el test no detecta términos esperados.

**Análisis:** Los resultados contienen "deportivas" pero el test busca "deporte" o "deportivo". Es un problema de coincidencia de forma femenina/plural.

**Recomendación:** Verificar que la normalización de género/número funcione en el motor.

---

### 4.8 Agricultura (1 FAIL)

**Problema:** Resultados contienen "cultivos industriales" que aparece como falso positivo para "industrial".

**Análisis:** "Cultivos industriales" es un término agrícola válido (cultivos para industria), no debe penalizarse.

**Recomendación:** Ajustar `must_not_contain` para permitir "cultivos industriales" o mejorar el contexto de penalización.

---

### 4.9 Banda Ancha (1 FAIL)

**Problema:** Resultado #10 "Redes informáticas en los establecimientos de 10 o mas empleados" no contiene términos esperados.

**Análisis:** El resultado está relacionado con tecnología pero no contiene "banda ancha", "internet" o "conectividad". Es un falso positivo por proximidad semántica.

**Recomendación:** Revisar el umbral semántico para este tipo de consultas.

---

## 5. Fortalezas Identificadas

### 5.1 Dominios Bien Cubiertos

- **Medio ambiente** (5/5): Calidad del aire, cambio climático, residuos, espacios verdes, agua potable
- **Sanidad y salud** (1/1): Gasto sanitario
- **Demografía** (2/2): Despoblación, natalidad
- **Seguridad** (1/1): Delitos
- **Casos especiales** (4/4): COVID-19, género, discapacidad, inmigración

### 5.2 Rendimiento

- **Tiempo medio de respuesta:** ~105ms por consulta
- **Rango:** 52ms (umbral alto) a 151ms (COVID-19)
- **Todos los tests completados en:** ~4.5 segundos

### 5.3 Estabilidad

- **0 errores de API** en 41 tests
- **0 timeouts**
- Motor robusto bajo carga

---

## 6. Debilidades y Oportunidades de Mejora

### 6.1 Prioridad ALTA

| Problema | Impacto | Solución propuesta |
|----------|---------|-------------------|
| Filtros territoriales no funcionan | ALTO | Verificar procesamiento de `territorio` en payload |
| Coincidencia de plural/singular | MEDIO | Mejorar normalización en motor |
| Coincidencia de acentos | MEDIO | Normalizar NFD en búsqueda y test |

### 6.2 Prioridad MEDIA

| Problema | Impacto | Solución propuesta |
|----------|---------|-------------------|
| Sinónimos compuestos (carril bici) | MEDIO | Ampliar mapeo de sinónimos |
| Términos relacionados implícitos (museos/salas) | MEDIO | Añadir sinónimos de dominio |
| Contexto de términos prohibidos (cultivos industriales) | MEDIO | Mejorar detección de contexto |

### 6.3 Prioridad BAJA

| Problema | Impacto | Solución propuesta |
|----------|---------|-------------------|
| Umbral para términos técnicos (banda ancha) | BAJO | Ajustar pesos semánticos |
| Variaciones dialectales (centres/centros) | BAJO | Normalización lingüística |

---

## 7. Comparativa con Batería Original

| Métrica | Original (12 tests) | Extendida (41 tests) | Cambio |
|---------|---------------------|----------------------|--------|
| PASS | 10 (83,3%) | 30 (73,2%) | -10.1pp |
| FAIL | 2 (16,7%) | 11 (26,8%) | +10.1pp |
| ERROR | 0 (0%) | 0 (0%) | = |

La precisión disminuye al ampliar la batería porque:
1. Se incluyen más dominios especializados (cultura, deporte, tecnología)
2. Se detectan casos límite no cubiertos originalmente
3. Los filtros territoriales (3 FAIL) afectan significativamente

**Sin filtros territoriales:** 30/38 = **78,9%**  
**Con solo tests base + específicos:** 28/32 = **87,5%**

---

## 8. Recomendaciones para Mejorar la Precisión

### Inmediatas (antes de documentar)

1. **Arreglar filtros territoriales**: Es el problema más grave (3 FAIL, 0% precisión en esa categoría)
2. **Ampliar sinónimos** para: bicicleta/bici, musical/música, sala/exposición, deportiva/deporte
3. **Normalizar acentos** en el test para "jóvenes/jovenes"

### Corto plazo

4. **Revisar must_not_contain** para permitir contextos válidos (cultivos industriales)
5. **Mejorar detección de plural/singular** para términos en mayúsculas (Pensiones/pensión)
6. **Añadir tests de regresión** para evitar degradación

### Largo plazo

7. **Evaluación con usuarios reales** para identificar consultas frecuentes
8. **Expansión de sinónimos** basada en feedback
9. **Benchmark periódico** semanal o quincenal

---

## 9. Conclusiones

El buscador semántico demuestra un **rendimiento sólido del 73,2%** en una batería diversa de 41 tests, con **100% de estabilidad** (0 errores) y **tiempos de respuesta aceptables** (~105ms).

Las principales fortalezas son:
- ✅ Excelente cobertura en medio ambiente, sanidad, demografía
- ✅ Manejo correcto de términos modernos y sensibles (COVID-19, género, discapacidad)
- ✅ Motor estable y rápido

Las principales áreas de mejora son:
- 🔴 **Filtros territoriales** (funcionalidad rota)
- 🟡 **Normalización lingüística** (acentos, plurales, género)
- 🟡 **Expansión de sinónimos** para dominios culturales y deportivos

Con las correcciones propuestas, se estima que la precisión podría alcanzar **85-90%**.

---

## 10. Archivos Generados

- `test_bateria_extendida.py`: Script de la batería (40+ tests)
- `test_report_extendido.json`: Resultados detallados en JSON
- `ANALISIS_BATERIA_EXTENDIDA.md`: Este documento de análisis

---

*Documento generado automáticamente tras la ejecución de la batería extendida.*
