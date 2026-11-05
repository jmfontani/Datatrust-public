# Batería de preguntas y respuestas para la defensa · DataTrust

**TFM Máster IA y Ciencia de Datos (EOI) · Grupo 2 · Proyecto in company sobre datos.gob.es**
Documento de trabajo para el coloquio. Fuentes: repo `datos/PFM/Datatrust` (docs por fase, entregables por sprint, `docs/DECISIONES.md`, `09_Sprint7_RAGAS/`) y la guía de evaluación de EOI (*Claves del proyecto*).

---

## 0 · Cómo se usa este documento

**Formato de la defensa (guía EOI):** 15 min de exposición (incluida la demo del POC) + **15 min de coloquio**. Todos los miembros del equipo deben intervenir. Peso: Memoria 50 % · POC 15 % · Presentación 35 % (sobre el 45 % que vale el grupo).

**Tres reglas de oro para el coloquio**

1. **Una cifra por respuesta, con su instrumento.** Nunca sueltes un número sin decir con qué se midió y cuándo («nDCG@10 0,58 con ground truth v6, 214 consultas, 14 de octubre»).
2. **Separa lo medido de lo estimado.** «Medido», «proyectado» y «objetivo» no son sinónimos. Si es objetivo de KPI, dilo.
3. **Declara la limitación antes de que la encuentren.** Cada respuesta sobre resultados lleva su «pero»: cobertura de juicio, tamaño de muestra, latencia.

**Lo que NO se debe decir nunca** (está documentado como inválido): P@5 = 1,000, nDCG = 1,518 ni «recall 0,00» del informe de junio. Ver pregunta 38.

---

## Bloque 1 · Problema, usuarios y propuesta de valor

**1. ¿Qué problema resuelve DataTrust, en una frase?**
El catálogo nacional tiene **94.461 datasets** y se busca con un motor léxico: quien busca «ayudas para jóvenes que dejan de estudiar» no escribe «población activa registrada de 16 a 24 años». DataTrust añade una capa semántica (embeddings) y una capa LLM sobre los mismos metadatos, para pasar de *encontrar por palabras* a *encontrar por intención*.
*Fuente:* `docs/ANALISIS_COMPETENCIA_EUROPA.md`, `docs/BUSINESS_MODEL_CANVAS_RESUMEN.md`.

**2. ¿Eso no lo hace ya datos.gob.es?**
No. Comparamos con **data.europa.eu** (buscador léxico/estructurado), **Italia (SIMBA)**, el más avanzado en IA+semántica, **Suiza** (semántica institucional RDF/DCAT), **Francia** (apuesta por agentes MCP sin rediseñar el buscador) y **Reino Unido** (prepara el terreno normativo, sin despliegue). España está alineada con el estándar europeo pero **no ha desplegado búsqueda semántica** en su portal.
*Fuente:* `docs/ANALISIS_COMPETENCIA_EUROPA.md` (§1-§5).

**3. ¿Y vuestro diferenciador frente a OpenDataSoft o Huwise?**
Ellos validan que hay mercado comercial de búsqueda semántica, pero son plataformas cerradas y genéricas. Nuestro diferencial es doble: **especialización en datos abiertos públicos** (metadatos DCAT-AP, EUROVOC, territorios españoles) y **portabilidad**: el diseño sirve para cualquier catálogo DCAT, no solo datos.gob.es.

**4. ¿Cómo validasteis que el problema existía?**
Fase de Empatizar-Definir: **5 entrevistas semiestructuradas (20-30 min)**, tres *user personas* (analista de datos, investigador, periodista), *journey map* del proceso de búsqueda y **benchmark de consultas** contra el portal actual.
*Fuente:* `01_Empatizar_Definir/entregables/` (personas, entrevistas, journey).

**5. ¿Los usuarios son reales?**
Las personas son ficticias, construidas sobre 5 entrevistas reales. **No hicimos estudio cuantitativo ni test con usuarios finales sobre el prototipo**: es una limitación declarada, y el primer trabajo futuro.

**6. ¿Cuál es el valor medible?**
Los KPI que nos fijamos (objetivos, no mediciones): tiempo hasta el dataset relevante de **15-60 min → < 2 min**, tasa de éxito de búsqueda **> 70 %**, satisfacción **> 4/5**, cobertura semántica del catálogo **> 90 %**. Lo único medido con instrumento es la calidad del ranking (bloque 6).
*Fuente:* `docs/BUSINESS_MODEL_CANVAS_RESUMEN.md` (KPIs alternativa A).

---

## Bloque 2 · Metodología y alcance

**7. ¿Qué metodología habéis seguido?**
La del máster: Design Thinking (Empatizar → Definir → Idear → Prototipar) en **7 sprints con entregables cerrados** (Kickoff, Empatizar, Idear, Ingesta, Embeddings, Búsqueda/UI, Integración, LLM, Evaluación), con Digital Maturity Canvas, definición de MVP y registro de ideas descartadas.
*Fuente:* `00_Kickoff` … `09_Sprint7_RAGAS`; `02_Idear_Prototipar/entregables/DMC/`.

**8. ¿Qué es el MVP y qué quedó fuera?**
MVP = ingesta + embeddings + búsqueda híbrida + UI + API + capa LLM opcional. Quedaron fuera: **normalización conceptual de consultas** (caso #8, archivado tras medir **0 % de mejora**), 5 casos de uso LLM pendientes (#6, #7, #9, #11, parte del #15), multidioma y multi-catálogo.

**9. ¿Por qué archivar el caso #8 si sonaba bien?**
Porque se midió y no mejoró: 0 % de mejora en la batería de pruebas. Se conserva el post-mortem (`EXPERIMENTO_NORMALIZACION_CONCEPTUAL.md`) y la rama `experiment/conceptual-normalization`. **Archivar con evidencia es un resultado, no un fracaso.**

**10. ¿Qué haríais distinto si empezarais hoy?**
Dos cosas, y conviene decirlas antes de que las pregunten: (a) **construir el instrumento de evaluación el día 1** — la primera medición fue inválida y hubo que rehacerla; (b) **fijar el contrato de datos** (campos obligatorios, deduplicación, territorios) antes de indexar, porque el 64,6 % de fichas no traían territorio.

**11. ¿Cómo repartisteis el trabajo?**
*(Preparar respuesta de equipo, no improvisar: quién lideró ingesta, motor, LLM, evaluación, negocio, y cómo se revisaba el trabajo cruzado.)*

---

## Bloque 3 · Datos e ingesta

**12. ¿De dónde salen los datos y cuántos hay?**
De la API **CKAN + DCAT-AP** de datos.gob.es: **134.150 registros descargados** en 135 lotes JSONL, **87.677 únicos** tras deduplicar (46.473 duplicados, **34,7 %**), y hoy la base tiene **94.461** fichas tras las ingestas posteriores.
*Fuente:* `docs/ARQUITECTURA.md`, BD `buscador.datasets` (verificado en vivo).

**13. ¿Cómo deduplicáis y qué riesgo tiene?**
Huella **MD5** sobre campos clave. El riesgo, que declaramos: dos registros con el mismo título y fuente distinta pueden colapsar en uno y **perder un dataset real**; el contrapeso es que el catálogo federado repite mucho (un mismo dataset publicado por ayuntamiento y por comunidad).

**14. ¿Qué calidad tienen los metadatos de origen?**
Basta para buscar, mala para filtrar: **64,6 % sin territorio** (inferimos 56.674 desde el publisher y el título), **175 publishers**, **29 temas** (EUROVOC mapeado), **45 formatos** y descripciones muy desiguales. El análisis está en `docs/ANALISIS_METADATOS.md` y justifica por qué el LLM aporta en esta capa.

**15. ¿Guardáis los datos o solo los metadatos?**
Ambos: metadatos (obligatorio) y **contenido de ficheros** para la respuesta *data-aware*. Estado: `dataset_files` con **57.269 filas (56.170 con texto extraído)**; **31.149 datasets descargados (~48 GB)**; **6.825 inaccesibles** (enlaces roscos, formatos opacos, bloqueos); cobertura ≈ **60 %** del catálogo. El chat solo puede responder con datos de la parte descargada.

**16. ¿Se actualiza solo cuando cambia el catálogo?**
Hoy la reingesta es una ejecución controlada (hay *endpoint*/proceso de ingesta), **no un cron de refresco diario**: es una de las brechas hacia producción. La deduplicación y el versionado permiten reejecutar sin duplicar.

**17. ¿Problemas legales o de RGPD?**
Trabajamos con **metadatos públicos** y textos de ficheros ya publicados; no hay datos personales almacenados ni perfilado de usuarios (los logs de consulta son anónimos). Respetamos la licencia de cada dataset y **no redistribuimos los datos**, solo enlazamos y resumimos. Es un punto a reforzar antes de un uso comercial, no un bloqueo para el TFM.

---

## Bloque 4 · Embeddings y motor de búsqueda

**18. ¿Por qué embeddings y no solo BM25?**
Porque el lenguaje del ciudadano no coincide con el del catálogo. Con **léxico puro** el nDCG@10 se queda en **0,3269**, frente a **0,5575** del motor con vectores en la misma tanda pareada (G5). Las siglas, códigos y nombres propios siguen necesitando el léxico: de ahí el híbrido.
*Fuente:* `docs/DECISIONES.md` §G5.

**19. ¿Por qué empezasteis con MiniLM y migrasteis a BGE-M3?**
MiniLM multilingüe (384D) fue la elección de arranque: **18 min 24 s en CPU** para 87.677 fichas (~79 docs/s), 129-135 MB. Se quedó corto de techo semántico, y BGE-M3 (1024D) dio una mejora **pareada de +0,1326** de nDCG@10 con IC95 [+0,0929 · +0,1741], que no cruza cero.

**20. ¿Qué costó la migración?**
Re-vectorizar y construir índice **HNSW de 717 MB**. Hoy el **100 % del catálogo tiene vector BGE (94.461 de 94.461)**; el `embedding_text` persistido cubre **87.661 (92,8 %)**, porque los 6.800 restantes se vectorizaron sin guardar ese texto (los vectores son reales y distintos, verificado sobre la BD). Mantuvimos **reversibilidad**: tag `docker-api:pre-bge-20260930` y `EXPERIMENTO_MOTOR=minilm`.

**21. ¿Por qué pesos 0,7 / 0,3 y no 100 % semántico?**
Porque las medias favorecían ligeramente a 1,0/0,0, pero **el intervalo de confianza cruzaba cero**: no hay evidencia de que ganar sea real, y el léxico es lo que salva códigos y nombres propios. Decisión documentada con los tres escenarios medidos.
*Fuente:* `docs/DECISIONES.md` §G5 (tabla de pesos).

**22. ¿Cómo se combinan los dos rankings?**
Normalización **min-max** de cada score, ponderación y suma; después filtros facetados (territorio, tema, formato, publisher). El motor expone `semantic_weight` y `lexical_weight`, así que la ponderación es auditable desde la API.

**23. ¿Aguanta esto 10× más datos?**
El índice sí: la búsqueda vectorial HNSW tarda **~4,5 ms** y pgvector escala a millones de vectores con particionado. El cuello de botella es el **LLM del router** (~9 s en consulta completa) y el coste por token, no la base de datos.

**24. ¿Funciona en otros idiomas?**
BGE-M3 es multilingüe y la arquitectura es agnóstica, pero **no hemos evaluado** con ground truth en inglés o catalán: sería una afirmación sin respaldo. Queda como trabajo futuro.

---

## Bloque 5 · Capa LLM: qué hace, qué no y cuánto cuesta

**25. ¿Dónde usáis un LLM exactamente?**
Identificamos **15 casos de uso**; **9 están implementados y estables**: re-ranking y explicación de relevancia (#1, #2), interpretación y expansión de la consulta con validación (#3, #4, #12), búsqueda de datasets complementarios (#5), chat sobre el dataset (#10), sugerencia de consultas (#13) y respuesta *data-aware* (#14/#15). Uno se archivó con evidencia y cinco siguen pendientes.
*Fuente:* `08_Sprint6_LLM_Mejora/docs/INDICE_CASOS_USO_LLM.md`.

**26. ¿El re-ranking del LLM mejora los resultados?**
Honestamente: **acierta el top-1 pero no compensa en el resto**. En 4 iteraciones de prompt, el LLM pone el dataset correcto en posición 1 siempre, pero **sobrevalora las posiciones 2-3 (~70 % de error)** y añade **60-80 s de latencia** por consulta para una mejora de ranking marginal (−0,04). Conclusión operativa: **mostrar explicación LLM solo en el TOP-1**, no reordenar la lista entera, y así está implementado.

**27. Entonces, ¿por qué hay un LLM en la ruta de búsqueda?**
Es un **router**: clasifica la intención, decide si aplicar preproceso o búsqueda directa y evita malgastar llamadas. Es lo que explica los **~9 s** de la consulta completa (embedding ~2,5 s + router + léxico). Se puede desactivar y volver a los ~0,5 s del motor puro: es una decisión de producto, no una dependencia.

**28. ¿Qué son los perfiles/TL;DR y cuántos hay?**
Un enriquecimiento por LLM de cada ficha: **TL;DR de 2-3 frases** + perfil estructurado (variables clave, cobertura temporal, nivel geográfico, frecuencia). Estado: **5.039 fichas (5,3 % del catálogo)**, 0 nulos.

**29. ¿Cuánto costaría completarlo?**
Lo medimos: **555 tokens de entrada y 162 de salida por ficha** (dos llamadas), con descripción truncada a 500 caracteres. Para las **89.422 fichas pendientes**: **16,14 $ off-peak** (≈18 $ con reintentos) con deepseek-v4.1-flash; 7,82 $ con gpt-oss:20b; 32,27 $ en horario pico. Entre **4 y 9 horas** con 8 workers.
*Fuente:* medición propia del 31-oct-2026 (10 llamadas reales) + tarifas vigentes de ollama.com/pricing.

**30. ¿Dependencia de un proveedor cloud?**
Sí, y es un riesgo declarado: usamos **Ollama Cloud** con nombres `:cloud` y tenemos modelos locales para tareas concretas (OCR con `minicpm-v4.5:8b`). Mitigaciones: política de **off-peak (−50 %)**, modelo barato por defecto y la arquitectura permite sustituir el proveedor cambiando el cliente LLM, no el motor.

**31. ¿Cómo evitáis alucinaciones?**
El LLM **no genera datos**: resume y explica metadatos ya recuperados y, en modo *data-aware*, ficheros ya descargados. Cada respuesta se apoya en el `dataset_id` recuperado por el motor; si no hay ficha descargada, el sistema lo dice en vez de inventar. No es una garantía formal, es diseño de *grounding*.

---

## Bloque 6 · Evaluación y resultados (el bloque que más se pregunta)

**32. ¿Cómo evaluáis la calidad de la búsqueda?**
Con un instrumento propio inspirado en **RAGAS**: la métrica principal es **nDCG@10** con ganancia graduada, apoyada en **P@5, P@10 y MRR**, más la **cobertura del juicio** (qué parte del top-10 está etiquetada). La relevancia la decide un **juez LLM** (deepseek-v4.1-flash, temperatura 0) con escala **0/1/2** (0 no responde · 1 tema correcto pero otro alcance · 0→2 responde), etiquetando **por `dataset_id`**, no por coincidencia de palabras en el título.
*Fuente:* `docs/DECISIONES.md` §G1-G2; `docs/FASE-I-CIERRE-INSTRUMENTO.md`.

**33. ¿Cuál es la cifra oficial del proyecto?**
Snapshot de producción con **GT v6, cobertura 100 %** (14-oct-2026):
• **214 consultas:** nDCG@10 **0,5774** IC95 [0,5311 · 0,6237] · P@5 0,4318 · P@10 0,4000 · MRR 0,5942
• **47 consultas humanas:** nDCG@10 **0,7116** IC95 [0,6311 · 0,7921] · P@5 0,6511 · P@10 0,5851 · MRR 0,8039
Composición: las **47** son las consultas originales redactadas por personas; las **214** son ese núcleo ampliado a 216 consultas generadas por LLM **ancladas en 40 títulos reales del catálogo** por categoría (12 categorías × 18, dificultad fácil/media/difícil en la proporción del GT original), de las que se miden 214 tras depurar. La ampliación se hizo para bajar la mejora mínima detectable de 0,106 a ~0,050. **Se publican las dos cifras**, siempre diciendo cuál es cuál.

**34. ¿Por qué en vuestros documentos aparecen 0,4249, 0,5575, 0,6716, 0,5774 y 0,7116?**
Porque hubo **tres saltos**, y cada cifra pertenece a un instrumento distinto:
• **0,4249** → MiniLM con GT v5, cobertura 92,6 % (línea base de la Fase H, 30-sep)
• **0,5575** → BGE-M3 con GT v5, misma cobertura (lo publicado en la Fase H)
• **0,5774 / 0,7116** → BGE-M3 con **GT v6**, cobertura 100 % (**KPI publicado**)
• **0,6716** → nuestro buscador medido contra el ground truth derivado de **datos.gob.es** (47 consultas, 2-oct); es una comparación cruzada, no el KPI
El salto v5→v6 **no es mejora del motor**: es cerrar el instrumento (158 pares sin etiquetar que penalizaban al motor). Mismo motor, mismo snapshot.

**35. ¿Cómo sabemos que la mejora MiniLM→BGE-M3 no es casualidad?**
Con **contraste pareado sobre las mismas consultas** y recalculado con GT v6: **nDCG@10 +0,1526 IC95 [+0,1113 · +0,1938]** y **P@5 +0,0860 [+0,0477 · +0,1243]**; ningún intervalo cruza cero. Además, en el desglose de la Fase H la mejora aparecía en 94 consultas, empeoraba en 37 y empataba en 83, y el top-10 cambia en las 214, como se espera entre motores distintos. Y publicamos la **mejora mínima detectable** (0,0463 en las 214; 0,0805 en las 47) para que se vea qué tamaño de efecto es distinguible con esta muestra.

**36. ¿Un juez LLM no está sesgado? ¿Y si el juez es el mismo modelo que usa el sistema?**
Es el flanco débil y lo declaramos:
• Mitigación de reproducibilidad: prompt canónico único, **temperatura 0**, y **doble ciego** sobre el 10 % de los pares → **0,800 exacto y 1,000 con ±1** (en la Fase B, 0,847 de acuerdo).
• Mitigación de cobertura: se juzgaron los **158 pares que faltaban** hasta cobertura **100 %**, con 0 fallos.
• Riesgo que **no** está eliminado: el juez es de la misma familia que el modelo del sistema (posible autopreferencia). No es una validación humana, y por eso el KPI se formula como **mejora pareada con IC**, no como nota absoluta.

**37. ¿Y la comparación con datos.gob.es?**
Es una medición **propia** sobre el portal real (Playwright + Firefox headless, pausa de 2 s entre consultas, 47-48 consultas): **P@5 0,622 · nDCG@10 0,667** frente a nuestro **P@5 0,6511 · nDCG@10 0,7116** en las humanas. Dos matices obligatorios: (a) **no es un dato publicado por Red.es**, es nuestra medición; (b) **hoy no es recalculable con el juez**, porque el SERP de datos.gob.es no expone el identificador de dataset, así que la comparación se apoya en títulos.

**38. ¿Y las cifras del informe de junio (P@5 = 1,000, nDCG = 1,518)?**
**No son válidas y no se citan.** Aquel arnés generaba un ground truth idealizado y decidía relevancia por **coincidencia de subcadena en el título**, con un recall que podía pasar de 1,0. Se midió contra 470 juicios reales (precisión 0,697 · recall 0,929) y se **retiró en septiembre**. El objetivo antiguo del Sprint 2 (P@5 ≥ 0,700 · nDCG ≥ 0,750) queda como **referencia histórica** del arnés retirado, no como KPI: los dos instrumentos no son comparables.

**39. ¿Habéis probado con usuarios finales?**
No, y es la carencia más justa que se nos puede señalar: tenemos **5 entrevistas**, tres personas y un journey map, pero **ningún test de usabilidad ni medición de satisfacción** con usuarios reales. Está en el plan de trabajo futuro con una métrica concreta (tiempo hasta el dataset relevante, objetivo < 2 min).

**40. ¿La evaluación mide el sistema completo o solo el motor?**
Solo el **ranking de retrieval** con el motor puro (sin LLM en el ranking), que es lo que se puede medir de forma reproducible con el juez. Las capacidades LLM (explicaciones, chat, complementarios) se han validado con **protocolos propios y pruebas funcionales**, no con este instrumento: no mezclamos ambas cosas en la misma tabla.

---

## Bloque 7 · Arquitectura, despliegue y operación

**41. Dibujad la arquitectura en 30 segundos.**
**PostgreSQL + pgvector** (un solo almacén: metadatos, full-text y vectores) → **API FastAPI** (búsqueda híbrida, facetas, endpoints LLM) → **frontend Streamlit** (MVP, versión pública y demo LLM) → **Ollama** como proveedor de modelos. Tres contenedores en ejecución (postgres, api, frontend) detrás de un proxy nginx, servido en `datatrust.ejemplo.com`.
*Fuente:* `docs/AUDITORIA_BACKENDS_FRONTENDS.md`, `docs/diagrama_datatrust.mmd`.

**42. ¿Por qué pgvector y no Elasticsearch o FAISS?**
Porque el proyecto es pequeño y la **simplicidad operativa** manda: una sola base de datos para metadatos, filtros y vectores, transacciones coherentes y sin sincronizar dos sistemas. FAISS sería más rápido en búsqueda pura, pero añade un índice que hay que mantener aparte; Elasticsearch añade un cluster entero. Con **HNSW a ~4,5 ms**, el índice **no es el cuello de botella**: lo es el LLM.

**43. ¿Es reproducible?**
Sí, y hubo que ganárselo: encontramos y corregimos un **bug de determinismo** (el ranking dependía de `top_k` y no se guardaban los rankings), lo que invalidaba las comparaciones. Desde entonces se guardan **snapshots completos** y las métricas se recalculan desde ellos (`157_metricas_snapshot.py`) importando la fórmula canónica, **sin volver a martillar la API**.

**44. ¿Qué seguridad tiene el servicio?**
Realista: está **en red local tras un proxy**, sin autenticación en el frontend y sin autenticación en la API. No hay datos personales en juego, pero **publicarlo en abierto exigiría autenticación, rate-limiting y registro de uso**. Antes de un piloto real, eso es lo primero.

**45. ¿Y la operación diaria? Coste y actualización.**
Servidor propio (CPU + iGPU) con 3 contenedores; el coste variable es la API del LLM, gobernado por la política **off-peak (−50 %)** y por el uso del modelo barato. La **reingesta no está automatizada** con un cron: hoy es una ejecución controlada. Es la brecha operativa más clara hacia producción.

**46. ¿Cuánto tarda una consulta y de qué depende?**
**~9 s** en la consulta completa con router LLM (embedding ~2,5 s + router + léxico); **~0,5 s** con el motor híbrido puro; **60-80 s** si se activa el re-ranking completo del LLM. La latencia es, por tanto, **una decisión de producto**: se puede ofrecer modo rápido y modo explicado.

---

## Bloque 8 · Modelo de negocio, competencia y sostenibilidad

**47. ¿Cuál es el modelo de negocio?**
Tres alternativas evaluadas con KPIs y economía: **A) proyecto interno en red.es** (sin ingresos para los autores, viabilidad alta, horizonte 0-12 meses), **B) licencia a consultoras e integradores** (30.000-75.000 € el primer año, 3-5 licencias), **C) SaaS/API multi-cliente** (MRR 4.000-20.000 € año 1, 25.000-70.000 € a tres años). Recomendación: **A como caso de uso real y B como producto replicable**; C es la más ambiciosa y la de menor viabilidad a corto.
*Fuente:* `docs/BUSINESS_MODEL_CANVAS_RESUMEN.md`.

**48. ¿Tenéis relación con red.es?**
**No hay encargo formal.** Es un proyecto académico sobre datos públicos; el código es propiedad de los autores. Decirlo claro es mejor que insinuar una colaboración que no existe: el valor del TFM es demostrar que **se puede** hacer sobre el catálogo real.

**49. ¿Por qué alguien pagaría por esto habiendo OpenDataSoft?**
Porque el problema no es solo buscar, es **buscar en un catálogo concreto con metadatos concretos** (DCAT-AP, EUROVOC, 17 CCAA + Ceuta y Melilla, 175 publishers). Las plataformas comerciales son genéricas y cerradas; aquí el activo es la **especialización y la portabilidad** a cualquier catálogo DCAT.

**50. ¿Qué pasa cuando acabe el TFM?**
Riesgo real de quedar huérfano. Mitigación propuesta: dejarlo **operativo y documentado** (compose, scripts de reingesta, manual de operación), con la opción A como puerta natural de continuidad dentro de red.es y un plan de costes tan bajo (~18 $ por el enriquecimiento completo del catálogo) que no exige presupuesto.

**51. ¿Cuál es el coste real de operación?**
Servidor propio (hardware ya existente, sin coste cloud), almacenamiento ~48 GB de ficheros descargados y coste variable LLM **por uso**: el batch completo de perfiles ~18 $; una consulta con router, céntimos o menos. Es un sistema que se sostiene con muy poco dinero, y esa es una de sus fortalezas.

---

## Bloque 9 · Limitaciones, riesgos y preguntas trampa

**52. ¿Qué es lo más débil del proyecto?**
Sin adornos: (1) **la validación no es humana**, la hace un juez LLM; (2) **no hay test con usuarios finales**; (3) el **enriquecimiento LLM cubre el 5,3 %** de las fichas; (4) de las **6.800 fichas** que tienen vector BGE, **no guardamos el `embedding_text`** (92,8 % persistido), lo que limita auditar cómo se construyó ese vector; (5) **latencia de 9 s** con el router activo; (6) **reingesta no automatizada**. Todo está documentado; ninguna de estas cosas se descubre en el coloquio.

**53. ¿Cuánto falta para producción real?**
Cuatro cosas concretas: **persistir el `embedding_text` de las 6.800** fichas que se vectorizaron sin él, cerrar los perfiles del catálogo (89.422 pendientes), automatizar la reingesta (cron + validación de cambios) y añadir autenticación con rate-limiting. Nada de eso es investigación: es ingeniería con tareas identificadas.

**54. ¿Si cambia el precio del LLM o el proveedor cierra la API?**
El motor **no depende del LLM** para funcionar (la búsqueda híbrida va sola). El LLM es una capa opcional con un cliente aislado, y el sistema admite modelos locales. La política de off-peak y el modelo barato por defecto ya están aplicados.

**55. ¿Sesgo de la muestra de evaluación?**
Dos sesgos reconocidos: el **pool del juez** se construyó con la unión del top-20 de tres sistemas, así que un dataset relevante que ninguno recuperó **nunca se juzgó** (y no penaliza); y las **47 consultas humanas** son pocas, lo que se compensa con las 214 y con la mejora mínima detectable publicada.

**56. ¿Qué pasa con los 6.825 datasets inaccesibles?**
Se declaran: enlaces roscos, formatos opacos o portales que bloquean. Significa que el chat *data-aware* **no puede responder** sobre esa parte del catálogo; el buscador sí, porque trabaja con metadatos.

**57. ¿Cómo sabemos que no estáis maquillando números?**
Porque cada cifra de este documento lleva **fecha, instrumento y cobertura**, y el repo conserva los snapshots y los scripts que las recalculan. Si el tribunal quiere, la demo recalcula el KPI desde el snapshot en vivo.

**58. ¿Y si os preguntan por la parte de negocio y no es vuestro fuerte?**
Reconducir con datos: el canvas tiene KPIs, escenarios de ingresos y tres alternativas comparadas; lo que no hay es validación comercial con clientes reales, y así se dice.

---

## Bloque 10 · Futuro y cierre

**59. ¿Tres líneas de trabajo futuro?**
(1) **Cerrar el corpus**: persistir el texto de las 6.800 fichas, completar perfiles (89.422) y automatizar la reingesta. (2) **Validar con personas**: test de usabilidad con 10-15 usuarios y la métrica de tiempo hasta el dataset relevante. (3) **Producto**: autenticación, modo rápido/explicado, y portabilidad a un segundo catálogo DCAT para demostrar la alternativa B.

**60. Si solo pudiéramos mejorar una cosa del sistema, ¿cuál?**
La **latencia y la confianza del usuario**, en ese orden: el motor ya recupera bien (nDCG@10 0,7116 en las consultas humanas), pero 9 s de espera y una explicación que a veces sobrevalora resultados devalúan un ranking que es bueno. **Modo rápido por defecto y explicación solo del top-1** es la mejora con mejor relación coste/beneficio, y ya está medida.

---

## Anexo A · Ficha de cifras oficiales (llevar impresa)

| Dato | Valor | Fecha / instrumento |
|---|---|---|
| Datasets descargados / únicos | 134.150 / 87.677 | Ingesta CKAN+DCAT-AP (dedup 34,7 %) |
| Fichas en base de datos | 94.461 | BD `buscador`, verificado en vivo |
| Ficheros indexados | 57.269 filas (56.170 con texto) | `dataset_files` |
| Descargas de contenido | 31.149 datasets · ~48 GB · 6.825 inaccesibles | Informe de descarga |
| Embeddings producción | BGE-M3 1024D · HNSW 717 MB · **94.461/94.461 vectores (100 %)** · `embedding_text` persistido 87.661 (92,8 %) | BD, 2-nov |
| **KPI principal (214 consultas)** | **nDCG@10 0,5774** IC95 [0,5311 · 0,6237] · P@5 0,4318 · MRR 0,5942 · cobertura 100 % | GT v6, 14-oct |
| **KPI (47 consultas humanas)** | **nDCG@10 0,7116** IC95 [0,6311 · 0,7921] · P@5 0,6511 · MRR 0,8039 | GT v6, 14-oct |
| Mejora MiniLM→BGE-M3 | nDCG +0,1526 [+0,1113 · +0,1938] · P@5 +0,0860 [+0,0477 · +0,1243] | Contraste pareado, GT v6 |
| Juicios del juez | 10.653 etiquetas · escala 0/1/2 · temp. 0 · doble ciego 10 % (0,800 exacto) | GT v6 |
| Comparación datos.gob.es | P@5 0,622 · nDCG@10 0,667 (medición propia) | Playwright, 47-48 consultas |
| Latencia | ~9 s con router · ~0,5 s híbrido puro · 60-80 s re-ranking completo | Producción |
| Perfiles LLM | 5.039 fichas (5,3 %) | BD, 31-oct |
| Coste de completar perfiles | 555 in / 162 out por ficha → 16,14 $ off-peak (89.422 fichas) | Medición 31-oct, tarifas vigentes |

**Regla:** si una cifra no está en esta tabla, no se cita en la defensa sin comprobarla antes.

## Anexo B · Tabla de evolución del instrumento (para la pregunta 34)

| Etapa | Motor | Ground truth | Cobertura | nDCG@10 |
|---|---|---|---|---|
| Línea base G1 | MiniLM 384D | GT inicial | 57 % del pool | 0,5324 |
| Fase F/G/H | MiniLM 384D | GT v5 | 92,6 % | 0,4249 |
| Fase H (publicado) | BGE-M3 1024D | GT v5 | 92,6 % | 0,5575 |
| **Fase I (KPI actual)** | **BGE-M3 1024D** | **GT v6** | **100 %** | **0,5774 (214) · 0,7116 (47)** |
| Comparación cruzada | BGE-M3 1024D | GT datos.gob.es | 85,5 % | 0,6716 (47) |

## Anexo C · Plantilla de respuesta en 30 segundos

1. **Cifra** («nDCG@10 0,58 sobre 214 consultas»).
2. **Instrumento y fecha** («juez LLM con ground truth v6, cobertura 100 %, 14 de octubre»).
3. **Matiz honesto** («en las 47 consultas humanas sube a 0,71; la validación no es humana»).
4. **Siguiente paso** («el trabajo pendiente es test de usabilidad y automatizar la reingesta»).

## Anexo D · Preguntas que hay que preparar en equipo (no se responden solas)

• Reparto real de trabajo y horas por persona, y qué hizo cada uno en la demo.
• Qué parte del código es original y qué es librería (todo el stack es OSS: pgvector, FastAPI, Streamlit, BGE-M3, Ollama).
• Por qué no se pidió colaboración formal a red.es y qué se haría para conseguirla.
• Coste de oportunidad: qué se dejó de hacer para llegar a este alcance.
• Qué pasaría si el tribunal pidiera reejecutar la evaluación allí mismo (respuesta: `157_metricas_snapshot.py` desde el snapshot, sin tocar la API).
