# Resumen Ejecutivo: Alternativas de Modelo de Negocio

**Fecha**: 2026-06-23  
**Propósito**: Documento de trabajo para la reunión con el tutor de EOI. Presenta las 3 alternativas de modelo de negocio de forma comparativa, para decidir cuál se desarrolla en profundidad.  
**Contexto**: Proyecto académico/independiente basado en datos abiertos de `datos.gob.es`. Los autores no pertenecen a red.es ni han recibido encargo formal. El código es propiedad de los autores.

---

## Alternativas de modelo de negocio

| Dimensión | **A. Proyecto interno en red.es** | **B. Licencia a terceros** | **C. SaaS/API multi-cliente** |
|---|---|---|---|
| **Qué es** | La solución se integra en `datos.gob.es` como mejora del buscador oficial. | Empresas licencian el producto para cumplir requisitos técnicos en concursos públicos de portales de datos. | Servicio cloud que contratan otras administraciones para indexar y buscar sus propios catálogos DCAT. |
| **Cliente** | red.es / ciudadanía usuaria del portal | Consultoras e integradores de sistemas | CC.AA., ayuntamientos, universidades, portales sectoriales |
| **Ingresos directos** | **Nulos** para los autores | Medios (licencias + soporte) | Altos (suscripciones + API) |
| **Valor medible** | KPIs de UX y ahorro de costes para red.es | Número de licencias e integraciones | Clientes recurrentes, MRR, volumen de consultas |
| **Horizonte** | Corto plazo (0-12 meses) | Medio plazo (6-18 meses) | Largo plazo (12-36 meses) |
| **Viabilidad técnica** | Alta | Media-alta | Media |
| **Viabilidad comercial** | Alta (cliente interno / caso de uso real) | Media (ciclos largos sector público) | Media-baja a corto, alta a largo |
| **Riesgo legal/PI** | Bajo | Bajo | Bajo |
| **Complejidad** | Baja | Media | Alta |
| **Alineación con TFM** | Muy alta (demostración real) | Alta (producto replicable) | Media (producto cloud) |

---

## KPIs propuestos por alternativa

### Alternativa A: Proyecto interno

| KPI | Baseline | Objetivo |
|---|---|---|
| Tiempo hasta dataset relevante | 15-60 min | < 2 min |
| Tasa de éxito de búsqueda | — | > 70% |
| Satisfacción de usuario | — | > 4/5 |
| Reducción de tickets de soporte | Baseline T0 | -20% |
| Reutilización de datasets | Baseline T0 | +15% |
| Cobertura semántica del catálogo | 0% | > 90% |

### Alternativa B: Licencia a terceros

| KPI | Objetivo año 1 | Objetivo año 2 |
|---|---|---|
| Licencias vendidas | 3-5 | 8-15 |
| Ingresos por licencias | 30.000-75.000 € | 80.000-150.000 € |
| Proyectos de implantación | 2-4 | 5-10 |
| Margen operativo | 0-20% | 20-40% |

### Alternativa C: SaaS/API

| KPI | Objetivo año 1 | Objetivo año 3 |
|---|---|---|
| Clientes activos | 5-10 | 20-50 |
| Ingresos recurrentes (MRR) | 4.000-20.000 € | 25.000-70.000 € |
| Datasets indexados totales | 200.000 | 1.000.000 |
| Consultas mensuales | 50.000 | 500.000 |

---

## Estimación de ingresos y costes (plan anual, EUR)

| Año | Alternativa dominante | Ingresos estimados | Costes estimados | Resultado estimado |
|---|---:|---:|---:|---:|
| 1 | A (interno) | 0 | 60.000-140.000 | -60.000 a -140.000 |
| 2 | A + B | 55.000-150.000 | 80.000-180.000 | -25.000 a -30.000 |
| 3 | B + C | 150.000-400.000 | 140.000-300.000 | -20.000 a +100.000 |
| 4 | C (escala) | 300.000-800.000 | 200.000-500.000 | +100.000 a +300.000 |

> Las cifras son **hipótesis de planificación**. El año 1 se justifica por valor institucional, no por ingresos directos.

---

## Recomendación preliminar para discutir con el tutor

**Modelo híbrido escalonado**:

1. **Fase 1 — Alternativa A (proyecto interno)**: integrar el buscador en `datos.gob.es`, validar KPIs de UX y ahorro de costes, acumular credibilidad y métricas.
2. **Fase 2 — Alternativa B (licencias)**: una vez probado el producto, ofrecerlo a integradores que compitan en concursos públicos de portales de datos.
3. **Fase 3 — Alternativa C (SaaS)**: si la Fase 1 y 2 generan tracción, productizar la solución como servicio multi-cliente.

**Por qué este orden**:
- Minimiza riesgo comercial y técnico al empezar con un caso de uso real.
- Permite medir impacto real antes de invertir en productización o comercialización.
- Conserva la opción de monetización (B/C) sin depender de ella para justificar el TFM.

---

## Preguntas para resolver con el tutor

1. **¿Cuál de las 3 alternativas prefiere que desarrollemos en profundidad para el TFM?**
2. **¿Se valora más la viabilidad técnica/inmediata (A) o el potencial de ingresos (B/C)?**
3. **¿El TFM debe defender un único modelo de negocio o puede presentar un híbrido escalonado?**
4. **¿Es necesario incluir canvas visuales tipo Business Model Canvas tradicional (9 bloques) o basta con esta comparativa estructurada?**
5. **¿Qué tan detalladas deben ser las estimaciones financieras?** (cifras anuales, flujo de caja, punto de equilibrio...)

---

## Documentación relacionada

- `docs/BUSINESS_MODEL_CANVAS.md` — Business Model Canvas completo por escenario, con estimaciones detalladas y plan de validación.
- `docs/NARRATIVA_TFM.md` — Sección "Viabilidad y Modelo de Negocio" integrada en la narrativa del TFM.
- `02_Idear_Prototipar/entregables/DMC/digital_maturity_canvas.md` — Canvas técnico previo (Digital Maturity Canvas).

---

*Documento de trabajo para la reunión con el tutor. Las cifras son estimaciones orientativas sujetas a validación.*