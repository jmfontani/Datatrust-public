# Ground Truth - Ground Truth Completo para Evaluación RAGAS

> **Versión:** v2.0  
> **Fecha:** 2026-06-04  
> **Total queries:** 48  
> **Categorías:** 8 (empleo, demografía, economía, transporte, medio ambiente, cultura, deporte, sanidad, educación, ambiguas)

---

## 📊 Resumen por Categoría

| Categoría | Queries | % | Dificultad Media |
|-----------|---------|---|------------------|
| Empleo | 5 | 10.4% | Media |
| Demografía | 5 | 10.4% | Media |
| Economía | 5 | 10.4% | Media |
| Transporte | 5 | 10.4% | Fácil-Media |
| Medio Ambiente | 5 | 10.4% | Fácil-Media |
| Cultura | 5 | 10.4% | Fácil-Difícil |
| Deporte | 5 | 10.4% | Media |
| Sanidad | 5 | 10.4% | Media |
| Educación | 5 | 10.4% | Fácil-Media |
| Ambiguas | 3 | 6.2% | Difícil |

---

## 📋 Tabla Completa de Queries

| # | ID | Query | Categoría | Dificultad | Datasets Esperados | Mínimo Relevantes |
|---|----|-------|-----------|------------|-------------------|-------------------|
| 1 | empleo_001 | empleo juvenil | empleo | fácil | INE.*empleo.*joven, SEPE.*juvenil | 3 |
| 2 | empleo_002 | paro registrado por comunidades | empleo | media | SEPE.*paro.*registrado | 3 |
| 3 | empleo_003 | contratos temporales vs indefinidos | empleo | media | SEPE.*contratos.*temporal | 3 |
| 4 | empleo_004 | brecha salarial género | empleo | difícil | INE.*brecha.*salarial | 3 |
| 5 | empleo_005 | formación profesional ocupacional | empleo | media | SEPE.*formación.*ocupacional | 3 |
| 6 | demo_001 | censo población 2024 | demografía | fácil | INE.*censo.*población | 3 |
| 7 | demo_002 | pirámide poblacional Andalucía | demografía | media | INE.*pirámide.*Andalucía | 3 |
| 8 | demo_003 | envejecimiento poblacional España | demografía | media | INE.*envejecimiento | 3 |
| 9 | demo_004 | migración extranjera | demografía | media | INE.*extranjería | 3 |
| 10 | demo_005 | densidad poblacional municipios pequeños | demografía | difícil | INE.*municipios.*población | 3 |
| 11 | econ_001 | vulnerabilidad económica | economía | difícil | INE.*AROPE | 3 |
| 12 | econ_002 | renta media por hogar | economía | media | INE.*encuesta.*ingresos | 3 |
| 13 | econ_003 | IPC inflación mensual | economía | fácil | INE.*IPC | 3 |
| 14 | econ_004 | PIB por comunidades autónomas | economía | media | INE.*PIB.*CCA | 3 |
| 15 | econ_005 | deuda pública autonómica | economía | media | Banco.*España.*deuda.*CCA | 3 |
| 16 | trans_001 | tráfico carreteras estatal | transporte | fácil | MITMA.*tráfico.*carreteras | 3 |
| 17 | trans_002 | pasajeros aeropuerto | transporte | fácil | AENA.*pasajeros.*aeropuerto | 3 |
| 18 | trans_003 | transporte público urbano | transporte | media | INE.*transporte.*urbano | 3 |
| 19 | trans_004 | accidentes tráfico mortalidad | transporte | media | DGT.*accidentes.*víctimas | 3 |
| 20 | trans_005 | vehículos eléctricos matriculación | transporte | media | GANVAM.*vehículos.*eléctricos | 3 |
| 21 | medio_001 | calidad del aire ciudades | medio ambiente | fácil | MITECO.*calidad.*aire | 3 |
| 22 | medio_002 | residuos urbanos reciclaje | medio ambiente | media | INE.*residuos.*urbanos | 3 |
| 23 | medio_003 | emisiones gases efecto invernadero | medio ambiente | media | MITECO.*emisiones.*GEI | 3 |
| 24 | medio_004 | consumo agua embalses | medio ambiente | media | embalses.*capacidad.*estado | 3 |
| 25 | medio_005 | energías renovables producción | medio ambiente | media | REE.*renovables.*producción | 3 |
| 26 | cult_001 | bibliotecas públicas | cultura | fácil | INE.*bibliotecas.*públicas | 3 |
| 27 | cult_002 | museos visitantes | cultura | fácil | INE.*museos.*visitantes | 3 |
| 28 | cult_003 | cines taquilla películas | cultura | media | ICAA.*cine.*taquilla | 3 |
| 29 | cult_004 | festivales música verano | cultura | media | festivales.*música.*verano | 3 |
| 30 | cult_005 | patrimonio mundial UNESCO España | cultura | difícil | UNESCO.*patrimonio.*mundial | 3 |
| 31 | dep_001 | licencias deportivas federadas | deporte | fácil | CSD.*licencias.*federadas | 3 |
| 32 | dep_002 | instalaciones deportivas municipales | deporte | media | INE.*instalaciones.*deportivas | 3 |
| 33 | dep_003 | hábitos deportivos españoles | deporte | media | CSD.*hábitos.*deportivos | 3 |
| 34 | dep_004 | subvenciones deporte base | deporte | difícil | CSD.*subvenciones.*deporte.*base | 3 |
| 35 | dep_005 | eventos deportivos internacionales España | deporte | media | evento.*deportivo.*internacional | 3 |
| 36 | san_001 | camas hospitalarias UCI | sanidad | media | INE.*camas.*hospital | 3 |
| 37 | san_002 | médicos atención primaria ratio | sanidad | media | INE.*médicos.*primaria | 3 |
| 38 | san_003 | espera quirúrgica lista | sanidad | media | lista.*espera.*quirúrgica | 3 |
| 39 | san_004 | gasto farmacéutico público | sanidad | difícil | farmacia.*gasto.*público | 3 |
| 40 | san_005 | esperanza de vida hombres mujeres | sanidad | fácil | INE.*esperanza.*vida | 3 |
| 41 | edu_001 | universidades estudiantes matrícula | educación | fácil | INE.*universidades.*estudiantes | 3 |
| 42 | edu_002 | abandono escolar temprano | educación | media | INE.*abandono.*escolar | 3 |
| 43 | edu_003 | nota corte universidad grados | educación | media | universidad.*nota.*corte | 3 |
| 44 | edu_004 | becas MEC estudiantes beneficiarios | educación | media | MEC.*becas.*estudiantes | 3 |
| 45 | edu_005 | FP formación profesional plazas | educación | media | FP.*formación.*profesional.*plazas | 3 |
| 46 | amb_001 | paro | ambigua | difícil | SEPE.*paro.*desempleo | 3 |
| 47 | amb_002 | banco | ambigua | difícil | Banco.*España | 3 |
| 48 | amb_003 | planta | ambigua | difícil | planta.*energética.*industrial | 3 |

---

## 🔍 Criterios de Relevancia Detallados

### Empleo (empleo_001 - empleo_005)

| ID | Criterios "Debe Contener" | Criterios "No Debe Contener" |
|----|---------------------------|------------------------------|
| empleo_001 | tasa de paro juvenil, 16-29 años, comunidades autónomas | pensiones, formación profesional reglada |
| empleo_002 | comunidades autónomas, paro registrado, datos mensuales/trimestrales | paro encuestado (EPA), datos exclusivamente anuales |
| empleo_003 | contratos temporales, indefinidos, sector económico, reforma laboral 2022 | paro registrado, salarios, prestaciones por desempleo |
| empleo_004 | comparativa salarial por sexo, desglose por sector, metodología de cálculo | datos agregados sin desglose por sexo |
| empleo_005 | desempleados, certificados de profesionalidad, participantes en formación | formación universitaria, becas de estudio |

### Demografía (demo_001 - demo_005)

| ID | Criterios "Debe Contener" | Criterios "No Debe Contener" |
|----|---------------------------|------------------------------|
| demo_001 | población total, desglose por sexo, desglose por edad, ámbito municipal | datos de viviendas, datos económicos |
| demo_002 | Andalucía, edad, sexo, población, grupos de edad | empleo, educación, renta |
| demo_003 | población mayor de 65 años, serie histórica o proyecciones, índice de envejecimiento | datos económicos no relacionados, inmigración |
| demo_004 | extranjeros, población, nacionalidad, comunidad autónoma, flujos migratorios | turismo, visados, asilo, refugiados |
| demo_005 | densidad de población, municipios pequeños, evolución temporal | grandes ciudades, datos de empleo |

### Economía (econ_001 - econ_005)

| ID | Criterios "Debe Contener" | Criterios "No Debe Contener" |
|----|---------------------------|------------------------------|
| econ_001 | AROPE, riesgo de pobreza, exclusión social, desglose territorial | inflación, PIB per cápita, criminalidad |
| econ_002 | renta media, renta mediana, hogar, comunidad autónoma, datos recientes | renta per cápita individual, salario por hora |
| econ_003 | IPC, mensual, Índice de Precios de Consumo, variación interanual | desempleo, salario mínimo, PIB |
| econ_004 | PIB por comunidad autónoma, PIB per cápita, serie histórica | PIB nacional sin desglose, datos mundiales |
| econ_005 | deuda, comunidad autónoma, trimestral, PIB, euros | deuda municipal, deuda de empresas públicas |

### Transporte (trans_001 - trans_005)

| ID | Criterios "Debe Contener" | Criterios "No Debe Contener" |
|----|---------------------------|------------------------------|
| trans_001 | Intensidad Media Diaria, carreteras estatales, tipo de vehículo | velocidad, accidentes, peatones |
| trans_002 | pasajeros, aeropuerto, mensual, anual, comparativa interanual | mercancías, vuelos de carga |
| trans_003 | viajeros, metro, autobús, cercanías, ciudades españolas | bicicleta, vehículo privado |
| trans_004 | número de fallecidos, tipo de vía, evolución anual | heridos leves, accidentes sin víctimas |
| trans_005 | matriculaciones, vehículos eléctricos, BEV, PHEV, cuota de mercado | coches de combustión, datos de producción |

### Medio Ambiente (medio_001 - medio_005)

| ID | Criterios "Debe Contener" | Criterios "No Debe Contener" |
|----|---------------------------|------------------------------|
| medio_001 | NO2, PM2.5, PM10, datos horarios/diarios, ciudades españolas | previsión meteorológica, emisiones industriales |
| medio_002 | tasa de reciclaje, kg por habitante, comunidad autónoma | residuos industriales, peligrosos |
| medio_003 | Inventario Nacional GEI, sectores, tendencia temporal, objetivos UE | contaminantes locales, calidad del aire |
| medio_004 | porcentaje de capacidad, cuenca hidrográfica, datos semanales | datos de calidad del aire, temperatura |
| medio_005 | producción, eólica, solar, hidráulica, mix energético | consumo fósil, energía nuclear, precios |

### Cultura (cult_001 - cult_005)

| ID | Criterios "Debe Contener" | Criterios "No Debe Contener" |
|----|---------------------------|------------------------------|
| cult_001 | número de bibliotecas, fondos bibliográficos, usuarios activos | museos, teatros, préstamos específicos |
| cult_002 | visitantes, museos, afluencia, post-COVID, estatales/autonómicos | bibliotecas, teatros, monumentos |
| cult_003 | recaudación, espectadores, comunidades autónomas, películas españolas | alquiler, streaming, televisión |
| cult_004 | festivales, verano, música, subvenciones, listado | invierno, deportes, cine |
| cult_005 | UNESCO, Patrimonio Mundial, España, lista de sitios, tipo | gastronomía, playas, hoteles, fiestas |

### Deporte (dep_001 - dep_005)

| ID | Criterios "Debe Contener" | Criterios "No Debe Contener" |
|----|---------------------------|------------------------------|
| dep_001 | licencias federadas, deporte, sexo, edad, comunidad autónoma | actividades no federadas, presupuesto |
| dep_002 | instalaciones deportivas, municipales, piscinas, pistas, titularidad | eventos deportivos, competiciones |
| dep_003 | porcentaje población practica deporte, frecuencia, deportes más practicados | economía, turismo, instalaciones |
| dep_004 | subvenciones, deporte base, juvenil, convocatorias, importe | deporte profesional, élite, infraestructuras |
| dep_005 | eventos deportivos internacionales, España, listado, impacto económico | eventos nacionales |

### Sanidad (san_001 - san_005)

| ID | Criterios "Debe Contener" | Criterios "No Debe Contener" |
|----|---------------------------|------------------------------|
| san_001 | camas, UCI, hospital, comunidad autónoma | funerarias, consultas externas |
| san_002 | ratio médicos/pacientes, atención primaria, comunidad autónoma | hospitales, especialistas, enfermería |
| san_003 | tiempo medio de espera, tipo de intervención, hospital/CCAA | urgencias, consultas, citas previas |
| san_004 | gasto farmacéutico público, SNS, medicamentos, evolución | gasto privado, veterinarios |
| san_005 | esperanza de vida al nacer, hombres, mujeres, comunidad autónoma | adultos mayores, enfermedades específicas |

### Educación (edu_001 - edu_005)

| ID | Criterios "Debe Contener" | Criterios "No Debe Contener" |
|----|---------------------------|------------------------------|
| edu_001 | número estudiantes matriculados, universidad, grado, curso académico | profesorado, presupuestos, becas |
| edu_002 | tasa abandono escolar temprano, 18-24 años, CCAA, comparativa UE | rendimiento primaria, absentismo, universidad |
| edu_003 | notas de corte, universidad, grados, último curso | bachillerato, FP, máster, doctorado |
| edu_004 | becarios, importe medio, beca matrícula/residencia | becas investigación, internacionales |
| edu_005 | plazas FP, familias profesionales, CCAA, FP Básica/Media/Superior | universidad, máster, empleo |

### Ambiguas (amb_001 - amb_003)

| ID | Criterios "Debe Contener" | Criterios "No Debe Contener" |
|----|---------------------------|------------------------------|
| amb_001 | paro registrado, desempleo, SEPE, INE, desempleados | parada de autobús, transporte, metro |
| amb_002 | Banco de España, entidad financiera, sector bancario, crédito | parque, asiento, banco de madera |
| amb_003 | centrales eléctricas, plantas de tratamiento, instalaciones industriales | jardín, vegetales, flores, ornamentales |

---

## 📈 Métricas Esperadas por Query

| Query ID | P@5 Esperada | P@10 Esperada | MRR Esperado | Justificación |
|----------|--------------|---------------|--------------|---------------|
| empleo_001 | 0.60 | 0.50 | 0.70 | Query directa, terminología clara |
| empleo_002 | 0.50 | 0.40 | 0.60 | Múltiples fuentes (SEPE, CCAA) |
| empleo_003 | 0.40 | 0.35 | 0.50 | Requiere comparación temporal |
| empleo_004 | 0.30 | 0.25 | 0.40 | Terminología técnica (brecha) |
| empleo_005 | 0.40 | 0.35 | 0.50 | FPO es término específico |
| demo_001 | 0.70 | 0.60 | 0.80 | Query muy directa (censo) |
| demo_002 | 0.40 | 0.35 | 0.50 | Requiere datos por edad/sexo |
| demo_003 | 0.35 | 0.30 | 0.45 | Concepto abstracto (envejecimiento) |
| demo_004 | 0.45 | 0.40 | 0.55 | Múltiples fuentes posibles |
| demo_005 | 0.25 | 0.20 | 0.35 | Query compleja (municipios pequeños) |
| econ_001 | 0.20 | 0.15 | 0.30 | Término técnico (AROPE) |
| econ_002 | 0.40 | 0.35 | 0.50 | Concepto claro (renta) |
| econ_003 | 0.80 | 0.70 | 0.90 | Query muy específica (IPC) |
| econ_004 | 0.50 | 0.45 | 0.60 | PIB es término estándar |
| econ_005 | 0.35 | 0.30 | 0.45 | Deuda autonómica específica |
| trans_001 | 0.60 | 0.50 | 0.70 | IMD es término técnico conocido |
| trans_002 | 0.65 | 0.55 | 0.75 | AENA es fuente única |
| trans_003 | 0.40 | 0.35 | 0.50 | Múltiples modos de transporte |
| trans_004 | 0.45 | 0.40 | 0.55 | DGT es fuente principal |
| trans_005 | 0.35 | 0.30 | 0.45 | Términos técnicos (BEV, PHEV) |
| medio_001 | 0.55 | 0.50 | 0.65 | NO2, PM son términos estándar |
| medio_002 | 0.45 | 0.40 | 0.55 | Reciclaje es concepto claro |
| medio_003 | 0.40 | 0.35 | 0.50 | GEI es término técnico |
| medio_004 | 0.40 | 0.35 | 0.50 | Embalses es concepto específico |
| medio_005 | 0.45 | 0.40 | 0.55 | Renovables es término común |
| cult_001 | 0.60 | 0.55 | 0.70 | Bibliotecas es concepto claro |
| cult_002 | 0.65 | 0.60 | 0.75 | Museos es término directo |
| cult_003 | 0.40 | 0.35 | 0.50 | Taquilla es término específico |
| cult_004 | 0.35 | 0.30 | 0.45 | Festivales es amplio |
| cult_005 | 0.30 | 0.25 | 0.40 | UNESCO es específico pero nicho |
| dep_001 | 0.55 | 0.50 | 0.65 | Licencias federadas es claro |
| dep_002 | 0.45 | 0.40 | 0.55 | Instalaciones es concepto amplio |
| dep_003 | 0.40 | 0.35 | 0.50 | Hábitos requiere encuestas |
| dep_004 | 0.30 | 0.25 | 0.40 | Subvenciones es disperso |
| dep_005 | 0.40 | 0.35 | 0.50 | Eventos internacionales es claro |
| san_001 | 0.45 | 0.40 | 0.55 | UCI es término específico |
| san_002 | 0.40 | 0.35 | 0.50 | Ratio es concepto técnico |
| san_003 | 0.35 | 0.30 | 0.45 | Lista de espera es específico |
| san_004 | 0.30 | 0.25 | 0.40 | Gasto farmacéutico es técnico |
| san_005 | 0.60 | 0.55 | 0.70 | Esperanza de vida es estándar |
| edu_001 | 0.65 | 0.60 | 0.75 | Matrícula universitaria es claro |
| edu_002 | 0.35 | 0.30 | 0.45 | Abandono escolar es técnico |
| edu_003 | 0.50 | 0.45 | 0.60 | Nota corte es término común |
| edu_004 | 0.40 | 0.35 | 0.50 | Becas MEC es específico |
| edu_005 | 0.45 | 0.40 | 0.55 | FP es término conocido |
| amb_001 | 0.20 | 0.15 | 0.30 | Ambigua (paro vs parada) |
| amb_002 | 0.15 | 0.10 | 0.25 | Ambigua (banco financiero vs asiento) |
| amb_003 | 0.20 | 0.15 | 0.30 | Ambigua (planta industrial vs vegetal) |

---

## 📝 Notas de Versión

### v2.0 (2026-06-04)

**Cambios realizados:**
- Actualizados patrones de títulos reales desde resultados de búsqueda
- Añadidos criterios de evaluación explícitos ("debe_contener", "no_debe_contener")
- Revisados mínimos de datasets relevantes (todos = 3)
- Añadidas 3 queries ambiguas (amb_001, amb_002, amb_003)

### v1.0 (2026-05-20)

**Versión inicial:**
- 45 queries originales
- Categorías: empleo, demografía, economía, transporte, medio ambiente, cultura, deporte, sanidad, educación

---

## 🔗 Referencias

- **Archivo original:** `ground_truth_actualizado.jsonl`
- **Script de actualización:** `actualizar_ground_truth.py`
- **Resultados RAGAS:** `ragas_scores_basic_final.json`, `ragas_scores_llm_final.json`

---

*Documento generado para anexos de memoria TFM - Buscador Semántico de Open Data*
