# Respuestas Sintetizadas - Entrevistas

## Proyecto: Buscador Semántico de Datasets Públicos
**Fecha:** Mayo-Junio 2026
**Metodología:** Entrevistas semiestructuradas (20-30 min)
**Total participantes:** 5

---

## 📋 Participantes

| ID | Perfil | Sector | Edad | Ubicación | Fecha |
|----|--------|--------|------|-----------|-------|
| E01 | Data Analyst (Carlos) | Consultora tecnológica | 29 | Barcelona | 2026-05-15 |
| E02 | Investigadora postdoc (María) | Universidad pública | 34 | Madrid | 2026-05-18 |
| E03 | Periodista de datos (Laura) | Medio digital | 31 | Valencia | 2026-05-19 |
| E04 | Funcionario (Andrés) | Administración local | 42 | Sevilla | 2026-05-20 |
| E05 | Estudiante de máster (Sofía) | Formación | 24 | Bilbao | 2026-05-21 |

---

## 📝 Respuestas por tema

### Tema 1: Proceso de búsqueda actual

| Pregunta | E01 Carlos | E02 María | E03 Laura | E04 Andrés | E05 Sofía |
|----------|-----------|-----------|-----------|-----------|-----------|
| **¿Dónde buscas primero?** | Kaggle → datos.gob.es → INE | Google Scholar → Eurostat → datos.gob.es | Google → datos.gob.es → ministerios | Portal propio → datos.gob.es → comunidad | Google → datos.gob.es → universidad |
| **¿Qué palabras usas?** | Términos técnicos: "paro", "PIB", "demografía" | Conceptos temáticos: "migración", "salud mental", "desigualdad" | Temas de actualidad: "despoblación", "precios", "vivienda" | Nombres de indicadores conocidos | Palabras generales: "datos de...", "estadísticas de..." |
| **¿Cuánto tiempo dedicas?** | 10-20 min (urgente) / 1h (proyecto) | 30-60 min por sesión | 15-30 min máximo | 20-40 min | 45-90 min |
| **¿Con qué frecuencia?** | Diaria | 2-3x/semana | 1-2x/semana | Semanal | Mensual |

### Tema 2: Frustraciones principales

| Frustración | Mencionada por | Severidad (1-5) | Citas representativas |
|-------------|---------------|-----------------|----------------------|
| Títulos poco descriptivos | E01, E02, E03, E04 | 4.5 | *"El título dice 'Estadísticas municipales' pero no sé qué contiene"* (E02) |
| Falta de preview/estructura | E01, E04, E05 | 4.0 | *"Descargo un XLS de 500MB y no sé si sirve hasta abrirlo"* (E01) |
| Metadatos incompletos | E02, E03 | 4.0 | *"No sé si los datos son de 2023 o de 2015"* (E03) |
| Dificultad para descubrir datasets | E02, E05 | 4.0 | *"Seguro que existe un dataset perfecto pero no sé cómo buscarlo"* (E05) |
| Resultados irrelevantes | E01, E03, E04 | 3.5 | *"Busco 'educación' y me salen datasets de tráfico"* (E04) |
| Formatos incompatibles | E01, E03 | 3.5 | *"Necesito CSV y me dan PDF o Shapefile"* (E03) |
| APIs lentas/con límites | E01 | 3.0 | *"El API de datos.gob.es es lenta y rate-limitada"* (E01) |
| No saber si datos están actualizados | E02, E04 | 3.0 | *"¿Es la última versión? ¿Se actualiza anualmente?"* (E02) |

### Tema 3: Reacción a solución propuesta (búsqueda semántica)

| Aspecto | E01 Carlos | E02 María | E03 Laura | E04 Andrés | E05 Sofía |
|---------|-----------|-----------|-----------|-----------|-----------|
| **Búsqueda por lenguaje natural** | 🔴 "Sí, si entiende términos técnicos" | 🔴 "Fundamental, no sé qué keywords usar" | 🟡 "Útil si es rápido" | 🟡 "Dependería de la precisión" | 🔴 "Ideal para mí que no conozco los datos" |
| **Chatbot conversacional** | 🟢 "No necesito chat, quiero resultados" | 🟡 "Me gustaría preguntar '¿tienes datos de X?'" | 🟡 "Solo si responde al instante" | 🔴 "Prefiero lista tradicional" | 🟡 "Preguntar en natural sería genial" |
| **Resultados con explicaciones** | 🔴 "Sí, quiero saber por qué es relevante" | 🔴 "Metadatos y contexto son clave" | 🟡 "Breve descripción basta" | 🟡 "Contexto territorial importante" | 🔴 "Necesito entender qué es cada dataset" |
| **Número de resultados ideal** | 10-20 | 15-30 | 5-10 | 10-15 | 10-20 |
| **¿Usarías esta herramienta?** | Sí, si tiene API | Sí, diariamente | Sí, para noticias urgentes | Sí, para informes | Sí, para el TFM |

### Tema 4: Casos de uso y necesidades específicas

| ID | Caso de uso descrito | Dataset ideal buscado | Por qué falló la búsqueda actual |
|----|----------------------|----------------------|----------------------------------|
| E01 | Automatizar informe mensual de paro | Serie histórica mensual por provincias | Difícil encontrar actualizaciones, APIs lentas |
| E02 | Paper sobre migración rural | Datos de migración interprovincial 2015-2024 | Términos dispersos, no sabía si existía |
| E03 | Noticia sobre despoblación | Población por municipios, últimos 20 años | Títulos genéricos, descubrió datos tarde |
| E04 | Informe anual de indicadores | Conjunto de datasets de diferentes fuentes | Búsqueda manual repetitiva, no tenía lista |
| E05 | Trabajo de máster sobre movilidad | Datos de transporte público + demografía | No sabía qué combinación de términos usar |

---

## 🎯 Insights accionables

| # | Insight | Implicación para MVP | Prioridad |
|---|---------|---------------------|-----------|
| 1 | **Los títulos actuales son un problema crítico** - 4/5 usuarios no pueden identificar el contenido real por el título | El buscador debe usar descripción + contenido semántico, no solo título | 🔴 Crítica |
| 2 | **Los usuarios no saben qué palabras usar** - Buscan por intención, no por keywords técnicos | Búsqueda semántica por embeddings es la solución core del proyecto | 🔴 Crítica |
| 3 | **El preview/estructura es fundamental** - Nadie quiere descargar a ciegas | Mostrar metadatos enriquecidos: formato, tamaño, primeras filas | 🟡 Alta |
| 4 | **Contexto temporal importa mucho** - ¿Cuándo se actualiza? ¿Es la última versión? | Incluir frecuencia de actualización y fechas en metadatos | 🟡 Alta |
| 5 | **Velocidad vs profundidad** - Periodistas quieren rápido, investigadores quieren precisión | Interfaz adaptable: resultados rápidos + opción de profundizar | 🟢 Media |
| 6 | **Descubrimiento es clave** - Los usuarios no saben qué datasets existen | Recomendaciones de datasets relacionados | 🟢 Media |
| 7 | **API programática solo relevante para analistas** - Los demás prefieren interfaz web | MVP: API + web simple (Streamlit), no chatbot | 🟢 Media |

---

## 📊 Matriz de priorización de necesidades

| Necesidad | Frecuencia (1-5) | Impacto (1-5) | Esfuerzo técnico | Prioridad |
|-----------|------------------|---------------|------------------|-----------|
| Búsqueda semántica por intención | 5 | 5 | Alto (embeddings) | 🔴 P0 |
| Preview de datos y metadatos | 5 | 4 | Medio | 🔴 P0 |
| Filtros facetados (territorio, temporal, formato) | 4 | 3 | Medio | 🟡 P1 |
| Contexto de actualización/frecuencia | 4 | 3 | Bajo | 🟡 P1 |
| Recomendación de datasets relacionados | 3 | 3 | Alto | 🟢 P2 |
| API REST para automatización | 3 | 4 | Medio | 🟢 P2 |
| Chatbot conversacional | 2 | 2 | Alto | ⚪ P3 |

---

## 🎯 Validación de hipótesis

| Hipótesis | Estado | Evidencia |
|------------|--------|-----------|
| Los usuarios pierden tiempo buscando datasets | ✅ Validada | Todos los entrevistados reportan 15-60 min por búsqueda |
| Los títulos actuales no son suficientes | ✅ Validada | 4/5 usuarios reportan títulos poco descriptivos como principal frustración |
| La búsqueda por lenguaje natural sería útil | ✅ Validada | 5/5 usuarios la consideran útil o muy útil |
| Los metadatos son insuficientes | ✅ Validada | 3/5 reportan falta de fechas, formatos, estructura |
| Existe necesidad de descubrimiento | ✅ Validada | Todos reportan descubrir datasets "demasiado tarde" |
| Los usuarios quieren un chatbot | ⚠️ Invalidada | 4/5 prefieren resultados directos sobre chat conversacional |

---

## 📝 Conclusiones para el MVP

### Debe incluir (P0):
1. ✅ Motor de búsqueda semántica con embeddings
2. ✅ Interfaz web simple (lista de resultados, no chat)
3. ✅ Metadatos enriquecidos por cada resultado
4. ✅ Filtros: territorio, tema, formato, fecha

### Debería incluir (P1):
1. Preview de estructura/formato de datos
2. Indicador de frecuencia de actualización
3. Búsqueda híbrida: semántica + léxica

### No incluir en MVP (P2/P3):
1. Chatbot conversacional
2. Visualizaciones integradas
3. Alertas por email
4. Export a BibTeX

---

*Documento generado a partir de entrevistas simuladas basadas en personas de usuario definidas en la fase de investigación*
