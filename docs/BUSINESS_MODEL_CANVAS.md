# Modelo de Negocio: Buscador Semántico de Datasets Públicos

**Fecha**: 2026-06-23  
**Contexto**: Este documento se redacta en la **fase previa a la implementación** del TFM. Las cifras, escenarios y propuestas son **hipótesis de planificación** y requieren validación posterior. El proyecto es una iniciativa **académica/independiente** desarrollada fuera del ámbito laboral de sus autores y se basa **exclusivamente en datos abiertos** del portal nacional `datos.gob.es` (gestionado por red.es). Los autores no pertenecen al departamento responsable del portal ni han recibido un encargo formal de red.es para realizar esta solución.

---

## 1. Contexto estratégico

### 1.1 Posicionamiento respecto a red.es y datos.gob.es

- `datos.gob.es` es el portal nacional de datos abiertos, gestionado por **red.es**.
- El proyecto del TFM es **independiente**: no depende de red.es, no requiere su autorización para explotar el código (desarrollado por los autores con datos abiertos) y no parte de un encargo interno.
- red.es aparece como **cliente potencial** y **caso de uso de referencia**, no como empleador o propietaria del proyecto.
- Las opciones de monetización incluyen:
  1. **Venta / propuesta a red.es**: ofrecer la solución como mejora del buscador oficial.
  2. **Licencia a terceros**: empresas que compiten en concursos públicos de portales de datos.
  3. **SaaS/API multi-cliente**: otras administraciones, universidades o portales sectoriales.
  4. **Modelo híbrido escalonado**: validar con red.es y/o otros clientes, luego escalar.

### 1.2 Restricciones y oportunidades

| Restricción | Oportunidad |
|-------------|-------------|
| Proyecto académico con scope limitado | El MVP sirve de carta de presentación para concursos o clientes |
| Los datos son abiertos y públicos | Baja barrera legal para ingesta, indexación y demostración |
| Sin contrato previo con red.es | Flexibilidad para ofrecer la solución a cualquier cliente |
| Sin presupuesto institucional propio | El coste del MVP puede mantenerse muy bajo con software libre y datos abiertos |
| Debe demostrar viabilidad económica (EOI) | Los escenarios B y C aportan ingresos directos y escalabilidad |

---

## 2. Escenarios de modelo de negocio propuestos

Se definen tres escenarios puros y uno recomendado. Todos se presentan como **planes**, no como realidades construidas.

---

## 3. Escenario A: Proyecto interno de mejora de datos.gob.es

**Hipótesis**: la solución se integra dentro del roadmap de `datos.gob.es` como mejora del buscador oficial. No genera ingresos directos para los autores, pero aporta valor institucional a red.es: mejor experiencia de usuario, menor tiempo de búsqueda, reducción de tickets de soporte, mayor reutilización de datos públicos y cumplimiento de objetivos de transparencia/datos abiertos.

### Business Model Canvas

| Bloque | Propuesta |
|--------|-----------|
| **Propuesta de valor** | Reducir el tiempo de búsqueda de datasets relevantes; mejorar la experiencia de usuario; aumentar la reutilización de datos abiertos mediante búsqueda semántica + LLM. |
| **Segmentos de clientes** | Ciudadanos, analistas de datos, periodistas, investigadores, desarrolladores y administraciones públicas que usan `datos.gob.es`. |
| **Canales** | Portal `datos.gob.es`, canales de comunicación de red.es, formación a usuarios, documentación técnica. |
| **Relación con clientes** | Soporte a través de la oficina técnica de datos.gob.es; comunidad de reutilizadores; encuestas de satisfacción. |
| **Ingresos** | No directos para los autores. El valor se materializa en ahorro de costes operativos y mejora del servicio público para red.es. |
| **Recursos clave** | Equipo de desarrollo, infraestructura de red.es, catálogo de datos.gob.es, modelos de embeddings open source, acceso a LLM, métricas de benchmark. |
| **Actividades clave** | Desarrollo del motor semántico, integración con el portal, evaluación continua, mantenimiento, comunicación de resultados, formación a usuarios. |
| **Socios clave** | red.es (responsable del portal), equipo de datos.gob.es, Ministerio de Transformación Digital, comunidad de reutilizadores. |
| **Estructura de costes** | Infraestructura cloud (alta disponibilidad), almacenamiento de vectores, coste de LLM (API o servidores propios), equipo de mantenimiento. |

### Estimación de costes e ingresos (plan anual, EUR)

| Concepto | Estimación baja | Estimación alta | Nota |
|----------|-----------------|-----------------|------|
| Infraestructura cloud (producción) | 15.000 | 40.000 | PostgreSQL + pgvector + servidores de aplicación |
| Coste LLM (uso interno) | 5.000 | 20.000 | Dependiendo de tráfico y modelo |
| Equipo de mantenimiento (FTE parcial) | 40.000 | 80.000 | Soporte, evolutivo y evaluación |
| **Coste total anual estimado** | **60.000** | **140.000** | |
| **Ingresos directos** | 0 | 0 | Proyecto interno para red.es |
| **Ahorro / valor generado** | 50.000 | 200.000 | Menos tickets, más reutilización, cumplimiento normativo |

### KPIs propuestos para medir el valor interno

| KPI | Baseline | Objetivo | Métrica | Frecuencia |
|-----|----------|----------|---------|------------|
| Tiempo medio hasta dataset relevante | 15-60 min | < 2 min | Segundos desde query a clic en resultado relevante | Mensual |
| Tasa de éxito de búsqueda | N/A | > 70% | % queries con clic en top-5 | Mensual |
| Satisfacción del usuario | N/A | > 4/5 | Encuesta post-búsqueda (1-5) | Trimestral |
| Reducción de tickets de soporte | Baseline T0 | -20% | Tickets relacionados con "no encuentro datos" | Semestral |
| Reutilización de datasets | Baseline T0 | +15% | Descargas / visitas de datasets desde el buscador | Trimestral |
| Cobertura semántica del catálogo | 0% | > 90% | % datasets indexados con embedding válido | Trimestral |

### Viabilidad

- **Riesgo técnico**: bajo (la solución se prueba sobre el catálogo real).
- **Riesgo organizativo**: medio (depende de la priorización dentro de red.es).
- **Riesgo económico**: bajo (el presupuesto ya existe en red.es; no requiere inversión externa).
- **Viabilidad general**: **alta**, aunque no aporta ingresos directos a los autores.

---

## 4. Escenario B: Licencia a terceros para concursos públicos

**Hipótesis**: la solución se comercializa como **producto reutilizable** que empresas privadas adquieren para cumplir requisitos técnicos en concursos públicos de portales de datos abiertos (convocados por red.es u otras administraciones). No se requiere autorización de red.es: el producto es propiedad de los autores y se basa en datos abiertos.

### Business Model Canvas

| Bloque | Propuesta |
|--------|-----------|
| **Propuesta de valor** | Producto probado con arquitectura documentada, métricas de evaluación (RAGAS) y benchmark contra datos.gob.es. Reduce el riesgo y el tiempo de desarrollo del licenciatario. |
| **Segmentos de clientes** | Consultoras tecnológicas, integradores de sistemas, empresas de software que se presentan a concursos de portales de datos abiertos. |
| **Canales** | Concursos públicos, alianzas con integradores, participación en eventos de datos abiertos, contactos profesionales del equipo. |
| **Relación con clientes** | Contratos de licencia, soporte técnico, formación, personalización bajo demanda. |
| **Ingresos** | Licencia de software (perpetua o anual), mantenimiento, soporte premium, implantación y formación. |
| **Recursos clave** | Código documentado, arquitectura replicable, know-how de evaluación, credibilidad del caso de uso con datos.gob.es. |
| **Actividades clave** | Adaptación a otros catálogos DCAT, documentación comercial, soporte, marketing B2B, gestión de licencias. |
| **Socios clave** | Consultoras integradoras, otras administraciones públicas, proveedores cloud. |
| **Estructura de costes** | Desarrollo de adaptadores a otros catálogos, documentación, comercialización, soporte, mantenimiento de la plataforma base. |

### Estimación de ingresos y costes (plan anual, EUR)

| Concepto | Estimación baja | Estimación alta | Nota |
|----------|-----------------|-----------------|------|
| Licencias anuales (3-10 clientes) | 30.000 | 150.000 | 3.000-15.000 EUR/licencia/año |
| Soporte e implantación | 20.000 | 80.000 | Proyectos de integración |
| Formación | 5.000 | 20.000 | Cursos y talleres |
| **Ingresos totales estimados** | **55.000** | **250.000** | |
| Equipo comercial/técnico | 40.000 | 100.000 | Adaptación y soporte |
| Documentación y certificación | 10.000 | 30.000 | Manuales, audits, compliance |
| Infraestructura propia | 10.000 | 25.000 | Demos, tests, preproducción |
| **Coste total anual estimado** | **60.000** | **155.000** | |
| **Resultado operativo estimado** | **-5.000** | **+95.000** | Depende fuertemente del número de licencias |

### Viabilidad

- **Riesgo técnico**: medio-bajo (el núcleo es replicable, pero cada catálogo tiene peculiaridades).
- **Riesgo comercial**: medio (ciclos largos de venta en sector público).
- **Riesgo legal/organizativo**: bajo (los autores desarrollan el código de forma independiente y usan datos abiertos).
- **Viabilidad general**: **media-alta**, con alto potencial si se generan oportunidades de concurso.

---

## 5. Escenario C: SaaS / API para múltiples administraciones

**Hipótesis**: la solución se productiza como **servicio en la nube** que cualquier administración, universidad o portal sectorial puede contratar para indexar y buscar semánticamente sobre su propio catálogo DCAT.

### Business Model Canvas

| Bloque | Propuesta |
|--------|-----------|
| **Propuesta de valor** | Buscador semántico como servicio: indexación, búsqueda híbrida, re-ranking con LLM, perfiles de datasets y chat, sin desarrollo propio. |
| **Segmentos de clientes** | Comunidades autónomas, ayuntamientos, universidades, portales sectoriales (salud, medio ambiente, transparencia), agencias europeas. |
| **Canales** | Web del producto, marketplace de soluciones públicas, eventos sectoriales, partners tecnológicos, marketing de contenidos. |
| **Relación con clientes** | Onboarding automatizado, documentación, soporte técnico por nivel de suscripción, comunidad de usuarios, roadmap compartido. |
| **Ingresos** | Suscripción mensual/anual por volumen de datasets y consultas; tier API; setup inicial; soporte premium. |
| **Recursos clave** | Plataforma multi-tenant, infraestructura escalable, modelos de embeddings optimizados, pipelines de ingesta, equipo de producto. |
| **Actividades clave** | Desarrollo del producto SaaS, onboarding de clientes, escalado de infraestructura, soporte, marketing, gobernanza de modelos. |
| **Socios clave** | Proveedores cloud, integradores locales, organismos europeos de datos abiertos. |
| **Estructura de costes** | Infraestructura multi-tenant (compute + almacenamiento + LLM), equipo de producto y soporte, marketing, seguridad y compliance. |

### Estimación de ingresos y costes (plan anual, EUR)

| Concepto | Estimación baja | Estimación alta | Nota |
|----------|-----------------|-----------------|------|
| Clientes SaaS (5-20) | 50.000 | 300.000 | 500-2.500 EUR/mes/cliente |
| API / consultas adicionales | 10.000 | 60.000 | Pay-per-use |
| Setup / personalización | 20.000 | 100.000 | Integraciones a medida |
| **Ingresos totales estimados** | **80.000** | **460.000** | |
| Infraestructura y LLM | 40.000 | 120.000 | Multi-tenant, alta disponibilidad |
| Equipo producto + soporte | 80.000 | 200.000 | Escencial para SaaS |
| Marketing y ventas | 20.000 | 80.000 | Captación de clientes |
| **Coste total anual estimado** | **140.000** | **400.000** | |
| **Resultado operativo estimado** | **-60.000** | **+60.000** | Rampa de crecimiento necesaria |

### Viabilidad

- **Riesgo técnico**: medio (requiere multi-tenancia, aislamiento de datos, escalado).
- **Riesgo comercial**: alto (competencia con soluciones genéricas como Elastic, Solr + AI).
- **Riesgo legal/organizativo**: bajo (código propiedad de los autores, datos abiertos).
- **Riesgo financiero**: alto (rampa de clientes y costes de infraestructura iniciales).
- **Viabilidad general**: **media-baja** a corto plazo, **alta** a medio/largo plazo si se alcanza escala.

---

## 6. Escenario recomendado: Híbrido escalonado

**Propuesta**: combinar los tres escenarios en una **hoja de ruta de viabilidad** que minimice el riesgo y maximice el valor:

| Fase | Escenario | Horizonte | Objetivo principal |
|------|-----------|-----------|--------------------|
| **Fase 1** | A: Proyecto interno red.es | Corto plazo (0-12 meses) | Integrar el buscador en datos.gob.es, validar métricas de UX y ahorro de costes, acumular credibilidad. |
| **Fase 2** | B: Licencia a terceros | Medio plazo (6-18 meses) | Reutilizar el código y el know-how en concursos públicos; generar primeros ingresos directos. |
| **Fase 3** | C: SaaS multi-cliente | Largo plazo (12-36 meses) | Productizar la solución y escalar a otras administraciones si la Fase 1 y 2 lo justifican. |

### Business Model Canvas híbrido recomendado

| Bloque | Propuesta |
|--------|-----------|
| **Propuesta de valor** | "Buscador semántico probado en el portal nacional de datos abiertos, disponible como mejora interna para red.es, licencia replicable o SaaS para otras administraciones." |
| **Segmentos de clientes** | (Fase 1) Usuarios de datos.gob.es; (Fase 2) integradores en concursos públicos; (Fase 3) administraciones y portales sectoriales. |
| **Canales** | Portal datos.gob.es, concursos públicos, web de producto, partners, eventos de datos abiertos. |
| **Relación con clientes** | Soporte institucional (Fase 1), contratos de licencia (Fase 2), suscripción y comunidad (Fase 3). |
| **Ingresos** | Fase 1: valor institucional (no ingresos directos); Fase 2: licencias + soporte; Fase 3: suscripción SaaS + API. |
| **Recursos clave** | Código modular, arquitectura documentada, métricas RAGAS, caso de uso con datos.gob.es, equipo técnico. |
| **Actividades clave** | Integración con datos.gob.es, documentación, comercialización B2B, productización SaaS, soporte continuo. |
| **Socios clave** | red.es (cliente referente potencial), integradores, otras administraciones, proveedores cloud, comunidad open source. |
| **Estructura de costes** | Fase 1 dominada por costes de infraestructura interna; Fases 2 y 3 añaden comercialización, soporte y escalado. |

### Proyección de ingresos acumulados (plan, EUR)

| Año | Fase dominante | Ingresos estimados | Costes estimados | Resultado estimado |
|-----|----------------|--------------------|------------------|--------------------|
| 1 | A (interno) | 0 | 60.000 - 140.000 | -60.000 a -140.000 |
| 2 | A + B (licencias) | 55.000 - 150.000 | 80.000 - 180.000 | -25.000 a -30.000 |
| 3 | B + C (SaaS rampa) | 150.000 - 400.000 | 140.000 - 300.000 | -20.000 a +100.000 |
| 4 | C (escala) | 300.000 - 800.000 | 200.000 - 500.000 | +100.000 a +300.000 |

> Año 1: el valor se mide con KPIs de UX y ahorro de costes para red.es, no con ingresos directos. Desde el año 2, los Escenarios B/C comienzan a generar retorno.

> Las cifras son **hipótesis de planificación**. Requieren validación con datos reales de adopción y contratación.

---

## 7. Comparativa de escenarios

| Dimensión | A: Interno red.es | B: Licencia | C: SaaS | Híbrido recomendado |
|-----------|-------------------|-------------|---------|---------------------|
| **Viabilidad a corto plazo** | Alta | Media | Baja | Alta |
| **Potencial de ingresos** | Nulo | Medio | Alto | Alto |
| **Riesgo legal/PI** | Bajo | Bajo | Bajo | Bajo |
| **Riesgo comercial** | Bajo (cliente interno) | Medio | Alto | Medio |
| **Complejidad técnica** | Baja | Media | Alta | Media (escala progresiva) |
| **Alineación con TFM académico** | Alta | Alta | Media | Alta |
| **Recomendación para el TFM** | MVP y validación | Segundo paso | Futuro | **Estrategia global** |

---

## 8. Plan de validación (mapa de experimentos)

Inspirado en el "Mapa de Experimentos" compartido por la tutora. Cada experimento valida una hipótesis del modelo de negocio.

| # | Hipótesis | Experimento | Métrica de validación | Propietario |
|---|-----------|-------------|----------------------|-------------|
| 1 | Los usuarios de datos.gob.es tienen dificultades para encontrar datasets | Encuesta / entrevistas a 10-15 usuarios | % que confirma problemas de búsqueda | Producto/UX |
| 2 | La búsqueda semántica mejora la precisión frente al buscador actual | Benchmark de 48 queries con métricas P@5, NDCG@10 | P@5 > 0.70 vs baseline datos.gob.es | ML/Datos |
| 3 | red.es prioriza la mejora del buscador | Entrevista con stakeholders de red.es | Compromiso de roadmap interno | Storytelling |
| 4 | Existe demanda de licencias en el mercado B2B | Contacto con 3-5 integradores de portales de datos | 2+ muestran interés | Storytelling |
| 5 | El coste de LLM es sostenible en producción | Medir latencia y coste por consulta en el MVP | < 2 s y coste predecible | Backend |
| 6 | El SaaS es técnicamente escalable | Prototipo multi-tenant con 2 catálogos | Funciona con aislamiento básico | Backend |

---

## 9. Supuestos críticos y próximos pasos

### Supuestos que deben validarse

1. **Adopción por red.es**: red.es integra la solución como mejora interna del portal y asigna recursos para mantenerla en producción (Escenario A).
2. **Propiedad intelectual**: los autores mantienen la titularidad del código del TFM y pueden explotar los Escenarios B y C de forma independiente.
3. **Coste del LLM**: el uso de modelos locales, cloud propio o API de terceros tiene un coste sostenible con el tráfico esperado.
4. **Calidad de los datos**: el catálogo de datos.gob.es tiene metadatos suficientes para que la búsqueda semántica sea útil, aunque se planifique un enriquecimiento posterior.
5. **Adopción B2B**: existen integradores u otras administraciones dispuestos a licenciar o suscribir una solución de este tipo.

### Próximos pasos recomendados

1. **Definir el acuerdo con red.es** para el Escenario A: alcance, KPIs de UX/ahorro de costes, responsable del mantenimiento y propiedad intelectual.
2. **Construir el MVP** orientado a validar la hipótesis de mejora de precisión (P@5) frente al buscador actual de datos.gob.es.
3. **Elaborar un plan de enriquecimiento de metadatos** (punto de dolor #3 del tutor), clave para la calidad del producto en cualquier escenario.
4. **Definir la estrategia de despliegue de LLM** (punto de dolor #2 del tutor) con comparativa local/cloud/híbrida y mención a smolagents.
5. **Evaluar opciones B y C** en paralelo: contactos con integradores y análisis de mercado SaaS para portales de datos abiertos.

---

## 10. Nota metodológica

Este documento **no describe una implementación realizada**. Es una **propuesta de modelo de negocio** elaborada en la fase de diseño del TFM, coherente con la metodología de EOI (Diseño, Generación y Evaluación de Modelos de Negocio). Los números son estimaciones orientativas y deben revisarse con datos reales en fases posteriores.

**Relacionado con**:
- [[metodologia-EOI-mapeo]] — Cumplimiento de la metodología EOI.
- `02_Idear_Prototipar/entregables/DMC/digital_maturity_canvas.md` — Canvas técnico previo (Digital Maturity Canvas).
- `docs/ESTRATEGIA_LLM_DEPLOY.md` (planificado) — Estrategia de despliegue de LLM (responde al punto de dolor #2 del tutor).
- `docs/PLAN_ENRIQUECIMIENTO_METADATOS.md` (planificado) — Plan de mejora de metadatos (responde al punto de dolor #3 del tutor).