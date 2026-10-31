# User Persona: Analista de Datos

## Proyecto: Buscador Semántico de Datasets Públicos
**Fecha:** Junio 2026

---

## 📋 Datos demográficos

| Campo | Valor |
|-------|-------|
| **Nombre ficticio** | Carlos Ruiz |
| **Edad** | 29 años |
| **Ocupación** | Data Analyst |
| **Sector** | Consultora tecnológica |
| **Ubicación** | Barcelona, España |
| **Frecuencia** | Busca datos diariamente |

---

## 🎯 Objetivos

1. Encontrar rápidamente datos para informes y dashboards
2. Construir análisis comparativos entre territorios
3. Automatizar la obtención de datos periódicos
4. Validar la calidad y actualidad de las fuentes

---

## 😤 Frustraciones (Pains)

- "Los datasets están en formatos incompatibles con mi stack"
- "Necesito datos actualizados y no sé cuándo se refrescan"
- "El API de datos.gob.es es lenta y tiene límites"
- "Los metadatos no incluyen estructura de los datos"
- "Tengo que limpiar mucho antes de poder usar nada"

---

## 🎉 GANs (Gains deseados)

- API programática para ingestión automática
- Preview de datos (primeras filas, columnas)
- Información de formato, tamaño, frecuencia de actualización
- Alertas cuando se publiquen nuevos datasets relevantes
- Filtros avanzados: territorio, temporal, formato

---

## 📱 Comportamiento de búsqueda

| Aspecto | Detalle |
|---------|---------|
| **Dónde busca** | datos.gob.es, Kaggle, INE, APIs propias |
| **Cómo busca** | Consultas específicas con filtros |
| **Tiempo promedio** | 10-20 minutos (urgente) |
| **Criterios de éxito** | Datos descargados en CSV/JSON, listos para ETL |
| **Qué hace si falla** | Busca alternativas, genera datos sintéticos |

---

## 💬 Citas directas

> "Necesito saber el formato y la estructura ANTES de descargar. Perder tiempo con un XLS mal formateado me retrasa horas."

> "Mi jefe me pide datos actualizados cada mes. Necesito automatizar esto."

---

## 🔗 Relación con otros perfiles

- Soporta a investigadores con análisis técnicos
- Colabora con periodistas en historias basadas en datos
- Usa herramientas de BI (Tableau, PowerBI, etc.)

---

## 🎯 Casos de uso típicos

1. **Informe mensual:** Descargar últimos datos de paro y PIB automáticamente
2. **Dashboard territorial:** Comparar indicadores entre provincias
3. **Análisis sectorial:** Cruzar datos de múltiples fuentes para cliente

---

## 📊 Prioridad para el MVP

| Feature | Prioridad | Justificación |
|---------|-----------|---------------|
| Preview datos | 🔴 Crítica | Evita descargas inútiles |
| API REST | 🟡 Alta | Automatización |
| Filtros facetados | 🟡 Alta | Agiliza búsqueda |
| Alertas | 🟢 Media | Nice-to-have |
