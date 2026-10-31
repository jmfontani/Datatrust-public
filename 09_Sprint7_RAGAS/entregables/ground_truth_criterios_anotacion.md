# Ground Truth - Criterios de Anotación y Relevancia

> **Versión:** v2.0  
> **Fecha:** 2026-06-04  
> **Autor:** TFM - Buscador Semántico de Open Data  
> **Propósito:** Documentar los criterios usados para determinar relevancia de cada query

---

## 📋 Introducción

Este documento describe los **criterios de anotación** utilizados para construir el ground truth de evaluación del buscador semántico. Su propósito es garantizar:

1. **Reproducibilidad** — Otro investigador puede replicar la evaluación
2. **Consistencia** — Criterios uniformes entre las 48 queries
3. **Transparencia** — Justificación clara de qué se considera "relevante"

---

## 🎯 Definición de Relevancia

Un dataset se considera **relevante** para una query si cumple **TODOS** estos criterios:

### Criterio 1: Pertinencia Temática

El dataset debe tratar sobre el **tema principal** de la query.

| Query | Tema Principal | Ejemplo Relevante | Ejemplo NO Relevante |
|-------|---------------|-------------------|---------------------|
| "paro juvenil" | Desempleo en jóvenes | "Tasa de desempleo menores de 25 años" | "Población ocupada por sectores" |
| "IPC inflación" | Índice de Precios de Consumo | "IPC mensual nacional" | "Índice de producción industrial" |
| "brecha salarial género" | Diferencia salarial hombres/mujeres | "Brecha salarial por sector" | "Salario mínimo interprofesional" |

### Criterio 2: Granularidad Adecuada

El dataset debe tener el **nivel de detalle** esperado por la query.

| Query | Granularidad Esperada | Relevante | NO Relevante |
|-------|----------------------|-----------|--------------|
| "paro registrado por comunidades" | Por CCAA | "Paro por comunidades autónomas" | "Paro nacional agregado" |
| "densidad municipios pequeños" | Municipal | "Densidad por municipio" | "Densidad por provincia" |
| "PIB por comunidades" | Por CCAA | "PIB autonómico" | "PIB nacional" |

### Criterio 3: Actualidad

El dataset debe contener datos **recientes** (últimos 2-3 años) salvo que la query especifique lo contrario.

| Query | Actualidad Esperada | Relevante | NO Relevante |
|-------|--------------------|-----------|--------------|
| "censo población 2024" | 2023-2024 | "Cifras de población 2024" | "Censo 2011" |
| "IPC inflación mensual" | Últimos 12 meses | "IPC enero 2026" | "IPC 2015-2018" |
| "envejecimiento poblacional" | Serie histórica larga | "Proyecciones 2020-2050" | "Datos puntuales 1990" |

### Criterio 4: Fuente Oficial

El dataset debe provenir de una **fuente oficial** reconocida.

| Fuente | ¿Oficial? | Ejemplo |
|--------|-----------|---------|
| INE | ✅ | "Instituto Nacional de Estadística" |
| SEPE | ✅ | "Servicio Público de Empleo Estatal" |
| MITECO | ✅ | "Ministerio para la Transición Ecológica" |
| ONG | ❌ | "Informes de organizaciones no gubernamentales" |
| Empresa privada | ❌ | "Estudios de mercado privados" |

---

## 📊 Criterios Específicos por Categoría

### Empleo

| Concepto | Criterio de Relevancia |
|----------|----------------------|
| "paro" / "desempleo" | Debe medir desempleo (no empleo) |
| "juvenil" | Debe especificar rango de edad (16-29 años) |
| "contratos" | Debe diferenciar temporal vs indefinido |
| "brecha salarial" | Debe comparar hombres vs mujeres |
| "formación ocupacional" | Debe ser para desempleados (no continua) |

**Ejemplo de bordes:**
- "Población ocupada" → ❌ No es paro
- "Contratos menores" → ❌ No cuenta para temporales/indefinidos
- "Salario medio por sector" → ❌ No es brecha de género

### Demografía

| Concepto | Criterio de Relevancia |
|----------|----------------------|
| "censo" / "población" | Debe ser recuento oficial de habitantes |
| "pirámide poblacional" | Debe tener desglose por edad y sexo |
| "envejecimiento" | Debe medir población 65+ años o índice de envejecimiento |
| "migración" | Debe ser movimientos poblacionales (no turismo) |
| "densidad" | Debe ser hab/km² a nivel municipal |

**Ejemplo de bordes:**
- "Padrón continuo" → ✅ Es censo
- "Población por provincias" → ❌ No sirve para pirámide (necesita edad/sexo)
- "Índice de juventud" → ❌ No es envejecimiento (es lo opuesto)

### Economía

| Concepto | Criterio de Relevancia |
|----------|----------------------|
| "AROPE" / "vulnerabilidad" | Debe ser indicador de riesgo de pobreza |
| "renta media" | Debe ser por hogar (no individual) |
| "IPC" | Debe ser índice de precios (no inflación subyacente) |
| "PIB" | Debe ser Producto Interior Bruto (no PNB) |
| "deuda pública" | Debe ser deuda autonómica (no estatal) |

**Ejemplo de bordes:**
- "Tasa de pobreza" → ✅ Es AROPE
- "Renta per cápita" → ❌ No es por hogar
- "IPCA" → ✅ Es IPC armonizado (válido)
- "Déficit público" → ❌ No es deuda

### Transporte

| Concepto | Criterio de Relevancia |
|----------|----------------------|
| "tráfico" | Debe ser intensidad de circulación (IMD) |
| "pasajeros aeropuerto" | Debe ser tráfico aéreo de personas |
| "transporte público" | Debe ser urbano (metro, autobús, cercanías) |
| "accidentes" | Debe ser mortalidad vial |
| "vehículos eléctricos" | Debe ser matriculaciones (no puntos de recarga) |

**Ejemplo de bordes:**
- "Velocidad media" → ❌ No es IMD
- "Mercancías aeropuerto" → ❌ No es pasajeros
- "Bicicletas públicas" → ❌ No es transporte público motorizado
- "Heridos en accidente" → ❌ No es mortalidad

### Medio Ambiente

| Concepto | Criterio de Relevancia |
|----------|----------------------|
| "calidad del aire" | Debe medir contaminantes (NO2, PM2.5, PM10) |
| "residuos" | Debe ser urbanos (no industriales) |
| "emisiones GEI" | Debe ser inventario nacional de gases |
| "agua embalses" | Debe ser capacidad/estado de embalses |
| "renovables" | Debe ser producción energética |

**Ejemplo de bordes:**
- "Índice de calidad" → ✅ Es calidad del aire
- "Recogida selectiva" → ✅ Es residuos urbanos
- "Emisiones CO2 industriales" → ❌ No es inventario GEI nacional
- "Consumo agua urbano" → ❌ No es estado de embalses

### Cultura

| Concepto | Criterio de Relevancia |
|----------|----------------------|
| "bibliotecas" | Debe ser equipamiento (no préstamos) |
| "museos" | Debe ser visitantes/afluencia |
| "cine" | Debe ser taquilla/espectadores |
| "festivales" | Debe ser música en verano |
| "UNESCO" | Debe ser Patrimonio Mundial (no otros programas) |

**Ejemplo de bordes:**
- "Catálogo bibliográfico" → ❌ No es número de bibliotecas
- "Exposiciones temporales" → ❌ No es visitantes de museos
- "Producción cinematográfica" → ❌ No es taquilla
- "Fiestas populares" → ❌ No son festivales de música

### Deporte

| Concepto | Criterio de Relevancia |
|----------|----------------------|
| "licencias federadas" | Debe ser por deporte/sexo/edad/CCAA |
| "instalaciones" | Debe ser equipamiento deportivo municipal |
| "hábitos deportivos" | Debe ser encuesta de práctica deportiva |
| "subvenciones deporte base" | Debe ser para jóvenes (no élite) |
| "eventos internacionales" | Debe ser competiciones en España |

**Ejemplo de bordes:**
- "Clubes registrados" → ❌ No son licencias
- "Piscinas municipales" → ✅ Son instalaciones
| "Resultados deportivos" → ❌ No son hábitos
| "Ayudas a federaciones" → ❌ No es deporte base

### Sanidad

| Concepto | Criterio de Relevancia |
|----------|----------------------|
| "camas hospital" | Debe incluir UCI específicamente |
| "médicos primaria" | Debe ser ratio médicos/pacientes |
| "espera quirúrgica" | Debe ser tiempo en días |
| "gasto farmacéutico" | Debe ser público (SNS) |
| "esperanza de vida" | Debe ser al nacer, por sexo |

**Ejemplo de bordes:**
| "Camas totales" → ❌ No especifica UCI
| "Médicos especialistas" → ❌ No es atención primaria
| "Lista de espera consultas" → ❌ No es quirúrgica
| "Gasto privado farmacia" → ❌ No es público

### Educación

| Concepto | Criterio de Relevancia |
|----------|----------------------|
| "universidad matrícula" | Debe ser estudiantes por grado |
| "abandono escolar" | Debe ser 18-24 años sin secundaria completada |
| "nota corte" | Debe ser acceso a grados universitarios |
| "becas MEC" | Debe ser programa del Ministerio |
| "FP plazas" | Debe ser oferta formativa por familia |

**Ejemplo de bordes:**
| "Egresados universitarios" → ❌ No es matrícula
| "Fracaso escolar primaria" → ❌ No es abandono 18-24
| "Nota media bachillerato" → ❌ No es nota de corte
| "Becas Erasmus" → ❌ No es MEC

### Ambiguas

Para queries ambiguas, se aplica criterio de **priorización por contexto**:

| Query | Interpretación Prioritaria | Interpretación Secundaria |
|-------|---------------------------|--------------------------|
| "paro" | Desempleo (SEPE) | Parada de transporte (❌ excluir) |
| "banco" | Entidad financiera | Asiento/mobiliario (❌ excluir) |
| "planta" | Instalación industrial | Vegetal/botánica (❌ excluir) |

**Regla:** Si la query tiene múltiples interpretaciones, priorizar la más común en contexto de datos abiertos y excluir las demás.

---

## 🔍 Proceso de Anotación

### Paso 1: Búsqueda Inicial

Para cada query:
1. Ejecutar búsqueda en el buscador semántico
2. Obtener top-20 resultados
3. Guardar títulos completos

### Paso 2: Evaluación Individual

Para cada resultado:
1. Leer título completo
2. Aplicar criterios de la categoría correspondiente
3. Marcar como relevante / no relevante / dudoso

### Paso 3: Revisión de Dudosos

Para resultados marcados como "dudoso":
1. Revisar descripción del dataset (si disponible)
2. Consultar fuente original
3. Decisión final: relevante o no relevante

### Paso 4: Validación Cruzada

1. Segundo annotador revisa 20% de queries
2. Calcular acuerdo inter-annotador (Cohen's kappa)
3. Resolver discrepancias por consenso

---

## 📈 Métricas de Calidad del Ground Truth

| Métrica | Valor | Interpretación |
|---------|-------|----------------|
| Queries totales | 48 | Cobertura de categorías |
| Queries por categoría | 5 (promedio) | Balanceado |
| Datasets relevantes por query | 3 (mínimo) | Suficientes para evaluación |
| Acuerdo inter-annotador | 0.85 (estimado) | Alto acuerdo |
| Queries ambiguas | 3 | Casos borde documentados |

---

## 📝 Ejemplos de Casos Difíciles

### Caso 1: "paro juvenil" vs "empleo juvenil"

**Query:** "paro juvenil"  
**Resultado:** "Tasa de empleo juvenil 16-29 años"

**Decisión:** ❌ NO relevante  
**Justificación:** Empleo ≠ paro. El usuario busca desempleo, no ocupación.

### Caso 2: "IPC" vs "IPCA"

**Query:** "IPC inflación mensual"  
**Resultado:** "IPCA armonizado mensual"

**Decisión:** ✅ Relevante  
**Justificación:** IPCA es IPC armonizado europeo, válido como medida de inflación.

### Caso 3: "brecha salarial" vs "salario medio"

**Query:** "brecha salarial género"  
**Resultado:** "Salario medio de hombres por sector"

**Decisión:** ❌ NO relevante  
**Justificación:** Falta comparación con mujeres. Brecha requiere diferencia entre sexos.

### Caso 4: "museos visitantes" vs "museos exposiciones"

**Query:** "museos visitantes"  
**Resultado:** "Exposiciones temporales en museos 2023"

**Decisión:** ❌ NO relevante  
**Justificación:** Exposiciones ≠ visitantes. El usuario busca afluencia, no oferta cultural.

### Caso 5: "paro" (ambigua)

**Query:** "paro"  
**Resultado:** "Paradas de autobús de Madrid"

**Decisión:** ❌ NO relevante  
**Justificación:** En contexto de datos abiertos, "paro" prioritariamente significa desempleo.

---

## 🔗 Referencias

- **Archivo JSONL original:** `ground_truth_actualizado.jsonl`
- **Tabla completa:** `ground_truth_v2_tabla.md`
- **CSV para análisis:** `ground_truth_v2.csv`
- **Resultados RAGAS:** `ragas_scores_basic_final.json`

---

*Documento de criterios de anotación - TFM Buscador Semántico de Open Data*
