# Benchmark de Queries - Buscador Semántico de Datasets

## Proyecto: Buscador Semántico de Datasets Públicos
**Fecha:** Junio 2026
**Objetivo:** Crear queries de referencia para evaluar el sistema

---

## 📊 Categorías de queries

### 1. Queries directas (fáciles)

| ID | Query | Categoría | Dificultad | Dataset esperado |
|----|-------|-----------|------------|------------------|
| Q001 | "población por municipio" | Demografía | Fácil | Censo INE |
| Q002 | "calidad del aire Madrid" | Medio ambiente | Fácil | Estaciones contaminación |
| Q003 | "paro por provincia" | Economía | Fácil | EPA, paro registado |
| Q004 | "hospitales públicos España" | Salud | Fácil | Catálogo centros sanitarios |
| Q005 | "precio vivienda 2024" | Vivienda | Fácil | Índice precio vivienda |

### 2. Queries por intención/contexto (medias)

| ID | Query | Categoría | Dificultad | Dataset esperado |
|----|-------|-----------|------------|------------------|
| Q010 | "¿Por qué se están vaciando los pueblos?" | Despoblación | Medio | Censo, movimiento natural, migraciones |
| Q011 | "datos para estudiar el impacto del turismo" | Turismo | Medio | Turistas por CCAA, alojamientos, precios |
| Q012 | "información sobre desigualdad educativa" | Educación | Medio | Tasa escolarización, repetición, abandono |
| Q013 | "datasets sobre cambio climático en España" | Clima | Medio | Temperaturas, emisiones CO2, energía |
| Q014 | "datos de movilidad urbana" | Transporte | Medio | Transporte público, tráfico, bicicletas |

### 3. Queries complejas/desafiantes (difíciles)

| ID | Query | Categoría | Dificultad | Dataset esperado |
|----|-------|-----------|------------|------------------|
| Q020 | "relación entre renta y esperanza de vida" | Salud/Social | Difícil | Renta por hogar, mortalidad, esperanza de vida |
| Q021 | "impacto de las renovables en el empleo rural" | Energía/Empleo | Difícil | Instalaciones renovables, empleo, paro |
| Q022 | "patrones de consumo y obesidad infantil" | Salud/Consumo | Difícil | Encuesta hogar, prevalencia obesidad |
| Q023 | "eficiencia del gasto sanitario por CCAA" | Salud/Economía | Difícil | Gasto sanitario, indicadores salud, población |
| Q024 | "vulnerabilidad al cambio climático por región" | Clima/Social | Difícil | Variables climáticas, socioeconómicas |

### 4. Queries en lenguaje natural (para chatbot)

| ID | Query | Categoría | Dificultad |
|----|-------|-----------|------------|
| Q030 | "Necesito datos para mi tesis sobre despoblación" | Despoblación | Medio |
| Q031 | "¿Qué datasets hay sobre contaminación acústica?" | Medio ambiente | Fácil |
| Q032 | "Busco información de tráfico en Barcelona" | Transporte | Fácil |
| Q033 | "Datos de mortalidad por causas en España" | Salud | Medio |
| Q034 | "Información sobre ayudas al alquiler" | Vivienda/Social | Medio |

---

## 📈 Métricas de evaluación

Para cada query registraremos:

| Métrica | Descripción | Cómo medir |
|---------|-------------|------------|
| **Tíempo de búsqueda** | Minutos hasta encontrar dataset relevante | Cronómetro |
| **Resultados relevantes** | Nº de datasets útiles en top 5 | Juicio humano |
| **Precisión@5** | % de relevantes en top 5 | Relevante/Sí |
| **Esperado vs encontrado** | ¿Se encontró el dataset objetivo? | Sí/No/Parcial |
| **Frustración** | Nivel de dificultad percibida | 1-5 |

---

## 🔄 Proceso de recolección

1. **Cada miembro del equipo ejecuta 10-15 queries** en datos.gob.es
2. **Registrar:** tiempo, resultados, frustración
3. **Sintetizar:** tabla consolidada con todos los resultados
4. **Definir baseline:** métricas actuales del portal

---

## ✅ Estado

- [ ] Queries validadas con equipo
- [ ] Búsquedas manuales ejecutadas
- [ ] Métricas baseline recopiladas
- [ ] Resultados sintetizados
