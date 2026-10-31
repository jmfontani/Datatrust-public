# Índice de Casos de Uso LLM - Buscador Semántico

**Fase 08: Sprint 6 - Mejoras con LLM**  
**Última actualización:** 2026-06-26

---

## 📊 Resumen General

| Estado | Cantidad | Casos |
|--------|----------|-------|
| ✅ **Implementados y Estables** | 9/15 | #1, #2, #3, #4, #5, #10, #12, #13, #14 |
| ⚰️ **Archivados (Vía Muerta)** | 1/15 | #8 (ver experiment branch) |
| ⏸️ **Pendientes** | 5/15 | #6, #7, #9, #11, **#15** |

**Notas:**
- Caso #4 tiene **fallback léxico implementado** (resuelve 88% de fallos de expansión)
- Caso #8 fue **explorado en rama separada** y archivado tras evaluar 0% de mejora
- **Caso #15 añadido (2026-06-26):** respuesta data-aware con escalada y enrutado por tamaño. Sus dependencias (dato en local) ya están cubiertas: 52.887 ficheros descargados en `~/datos` (60,3% del catálogo). Ver [`03_Sprint1_Ingesta/codigo/descarga_datos/informe_descarga.md`](../../../03_Sprint1_Ingesta/codigo/descarga_datos/informe_descarga.md).

---

## 🔗 Referencias a Propuestas Originales

| Documento | Ubicación |
|-----------|-----------|
| **Propuestas Originales (14)** | `docs/PROPUESTAS_LLM_ORIGEN.md` |
| **Experimento Archivado (#8)** | [`experiment/conceptual-normalization`](https://github.com/jmfontani/BuscadorDatosAbiertos/tree/experiment/conceptual-normalization) |
| **Post-Mortem #8** | `EXPERIMENTO_NORMALIZACION_CONCEPTUAL.md` |

---

## ✅ CASOS IMPLEMENTADOS

---

### #1 + #2: Re-ranking Inteligente + Explicaciones de Relevancia

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Toma Top N resultados del motor híbrido y los reordena usando LLM según relevancia analítica. Genera explicaciones de por qué cada dataset es relevante. |
| **Estado** | ✅ **COMPLETADO** - Prompt v4 (definitivo) |
| **Archivos** | `motor/llm_reranker.py`, `motor/llm_client.py`, `api/routes_llm_v2.py` |
| **Latencia** | ~60-80s por query (cloud) |
| **Tests** | 4 iteraciones de prompts evaluadas, 4 baterías completadas |

**Conclusiones:**
- ✅ **El LLM acierta siempre en posición 1** (100% → 5/5)
- ❌ **Sobrevalora consistentemente posiciones 2-3** (~70% error)
- ⚠️ Problema es **limitación del modelo**, no del prompt
- ⚠️ Alta latencia (~80s) vs mejora marginal (-0.04 ranking improvement)
- 📋 **Recomendación:** Mostrar solo TOP-1 con explicación; posiciones 2-3 sin explicación LLM

**Documentación:**
- `INFORME_FINAL_4_ITERACIONES.md` - Comparativa completa
- `EVALUACION_QWEN_2026-06-01.md` - Comparativa Qwen vs DeepSeek

**📚 Fundamento bibliográfico:** `Sun2023_230409542` (RankGPT, ●●●), `Pradeep2023_230915088` (RankVicuna, ●●), `Liu2023_230617563` (Pairwise Prompting, ●●), `Nogueira2020_200306713` (●). Ver [`docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`](../../../docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md).

---

### #3 + #4 + #12: Interpretación + Expansión + Validación

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Pipeline de pre-procesamiento: valida queries, extrae estructura (tema, territorio, año), expande con sinónimos y términos relacionados. |
| **Estado** | ✅ **IMPLEMENTADO** - Funcional con ajustes pendientes |
| **Archivos** | `motor/query_preprocessor.py`, `api/routes_query_enhanced.py` |
| **Latencia** | ~10-30s por query (3 llamadas LLM) |
| **Tests** | Tests básicos ejecutados, funcionando en casos estándar |

**Conclusiones:**
- ✅ **Validación (#12) funciona bien** - Detecta queries inválidas, ambigüedades, typos
- ✅ **Interpretación (#3) extracción correcta** - Temas, territorio, años, conceptos implícitos
- ✅ **Expansión (#4) CON FALLBACK LÉXICO** - Antes fallaba 88%, ahora 100% con fallback
- ✅ **Fallback léxico implementado** - Expansión basada en diccionario, <1ms, offline
- ⚠️ **Latencia acumulada** - 3 llamadas × ~5s = ~15s (aceptable vs 80s del re-ranking)
- 📋 **Recomendación:** Cachear resultados, expandir diccionario de sinónimos

**Actualización 2026-06-01 - Fallback Léxico:**
- Problema identificado: Expansión LLM fallaba 88% de las veces
- Solución implementada: Fallback a expansión léxica con diccionario de ~100 términos
- Resultado: 100% tasa de éxito, expansión siempre disponible
- Velocidad: <1ms (vs 3,000-65,000ms del LLM)
- Archivo: `motor/lexical_expander.py`

**Ejemplo de funcionamiento:**
```
Input: "paro juvenil Canarias 2023"
Validación: ✅ Económica (confianza 0.95)
Estructura: {temas: ["paro", "desempleo"], territorio: "Canarias", años: [2023]}
Expansión: "paro desempleo EPA jóvenes 16-24 años Canarias..."
Filtros: {theme: "Empleo", territory: "Canarias"}
```

**📚 Fundamento bibliográfico:** `Wang2023_230307678` (Query2doc, ●●●), `Peng2026_260111863` (Metadata for RAG, ●●●), `Ma2023_230514283` (Query Rewriting, ●●), `Gao2022_221210496` (HyDE, ●●), `Ning2024_241013765` (Knowledge-Aware Expansion, ●●), `Ning2024_241023841` (Beyond Content Relevance, ●●●). Ver [`docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`](../../../docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md).

---

## ⏸️ CASOS PENDIENTES (por prioridad)

---

### #5: Detección de Datasets Complementarios

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Identifica datasets que podrían combinarse analíticamente (ej: población + PIB para renta per cápita) |
| **Estado** | ✅ **IMPLEMENTADO** - Sprint 8 (Paquete A) |
| **Archivos** | `api/routes_complementary.py`, `batch_generate_profiles.py` |
| **Endpoint** | `POST /complementary/find` |
| **Valor estimado** | ⭐⭐⭐⭐⭐ Alto |
| **Latencia** | ~8-15s (LLM bajo demanda) |

**Resultados:**
- Endpoint funcional con explicaciones de complementariedad
- Tests: 100% de complementarios con explicación completa
- Detección basada en tema + geografía + análisis LLM
- Muestra representativa 2K generada y validada (2026-06-13)
- Precálculo offline: 931 datasets, 88% con complementarios
- Evaluación LLM-as-judge (50 datasets): calidad general 2.90/5, 48.5% aceptables

**Ejemplo:**
- Dataset: "Mapas estratégicos de Ruido"
- Complementario: "Valores Límite de Ruido"
- Razón: "Permite evaluar cumplimiento normativo de niveles de ruido"

**Documentación:**
- `docs/README_Sprint8_Paquete_A.md`

**📚 Fundamento bibliográfico:** `Peng2026_260111863` (Metadata for RAG, ●●●), `Li2025_250710897` (LLMATCH schema matching, ●●). Ver [`docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`](../../../docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md).

---

### #13: Sugerencias de Queries Relacionadas

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Propone búsquedas alternativas basadas en el contexto actual |
| **Estado** | ✅ **IMPLEMENTADO** - Híbrido asíncrono (léxico + LLM background) |
| **Latencia** | <5ms (léxico) + ~3-5s (LLM background) |
| **Archivos** | `motor/query_suggester.py`, `api/routes_query_enhanced.py` |
| **Tests** | 20 tests unitarios passing |

**Conclusiones:**
- ✅ **Enfoque híbrido** — Usuario ve sugerencias inmediatas, LLM enriquece después
- ✅ **Diversidad de categorías** — sinonimo, temporal, territorial, tecnica, especificacion
- ✅ **API con polling** — `/enhanced/query/suggest` + `/{cache_key}/result`
- ✅ **Cache 5 min** — Resultados LLM cacheados para ahorrar tokens

**Documentación:**
- `docs/CASO_13_QUERY_SUGGESTIONS.md` — Documentación completa

**📚 Fundamento bibliográfico:** `Ma2023_230514283` (Query Rewriting, ●●), `Rejas2026_260311008` (PRF with LLMs, ●). Ver [`docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`](../../../docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md).

**Ejemplo de funcionamiento:**
```
Input: "paro juvenil Canarias"

Sugerencias (5 léxicas <5ms):
  1. [sinonimo] desempleo juvenil Canarias
  2. [territorial] paro juvenil España
  3. [temporal] paro últimos 5 años

Sugerencias (+5 LLM ~3s):
  4. [tecnica] EPA jóvenes Canarias
  5. [especificacion] paro por municipio
```

---

### #8: Normalización Semántica de Conceptos ⚰️ ARCHIVADO

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Unifica términos diferentes que significan lo mismo ("paro" ↔ "desempleo", "población" ↔ "habitantes") |
| **Estado** | ⚰️ **ARCHIVADO** - Vía muerta (0% mejora) |
| **Rama** | `experiment/conceptual-normalization` |
| **Fecha archivo** | 2026-06-06 |

**Resultado del Experimento:**
- Diccionario creado: 105 conceptos, 521 triggers, 11 dominios
- Queries evaluadas: 10
- Resultados clasificados: 100
- **Clasificaciones útiles: 0 (100% "desconocido")**

**Causa Raíz:** Mismatch terminológico — los títulos reales de datasets usan lenguaje administrativo técnico que no coincide con el diccionario coloquial.

| Nuestro Diccionario | Títulos Reales en BD |
|---------------------|---------------------|
| "paro juvenil" | "Paro registrado: 2005-2023. Evolución" |
| "desempleo" | "Tasa de desempleo de personas 16-74 años" |
| "vivienda" | "Tablas estadísticas de Edificación y Vivienda" |

**Documentación:**
- [`experiment/conceptual-normalization`](https://github.com/jmfontani/BuscadorDatosAbiertos/tree/experiment/conceptual-normalization) — Rama archivada
- `EXPERIMENTO_NORMALIZACION_CONCEPTUAL.md` — Post-mortem completo
- [`PROPUESTAS_LLM_ORIGEN.md`](PROPUESTAS_LLM_ORIGEN.md) — Propuesta original (#10)

**Lección:** Los diccionarios manuales de conceptos no son sostenibles para datos abiertos. La búsqueda semántica con embeddings y expansión simple de sinónimos funciona mejor.

---

### #10: Respuestas a Preguntas sobre Datasets

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Chat sobre dataset específico: "¿Incluye datos de 2023?", "¿Qué campos tiene?" |
| **Estado** | ✅ **IMPLEMENTADO** - Sprint 8 (Paquete A) |
| **Archivos** | `motor/dataset_chat_engine.py`, `api/routes_dataset_chat.py`, `tests/test_dataset_chat.py` |
| **Endpoint** | `POST /dataset/chat` |
| **Valor estimado** | ⭐⭐⭐⭐ Medio-Alto |
| **Latencia real** | ~600-2.500 ms |

**Resultados:**
- Endpoint funcional basado en metadatos (título, descripción, TL;DR, variables, cobertura temporal, geografía)
- Tests: endpoint responde, evita inventar información, devuelve 404 para datasets inexistentes
- Integrado en frontend como expander "Preguntar sobre este dataset" dentro de cada tarjeta de resultado
- No requiere historial de conversación; cada pregunta es independiente

**Ejemplo:**
- Pregunta: *"¿Qué datos contiene?"*
- Respuesta: *"Clasificación jerárquica de unidades territoriales de Canarias con fecha de referencia 01/01/2024."*

**Documentación:**
- `docs/README_Sprint8_Paquete_A.md`

**📚 Fundamento bibliográfico:** `Jeong2024_240913385` (Contextual Compression in RAG, ●). Ver [`docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`](../../../docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md).

---

### #14: Resumen Automático de Datasets (TL;DR)

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Genera TL;DR de metadatos para scan rápido |
| **Estado** | ✅ **IMPLEMENTADO** - Sprint 8 (Paquete A) |
| **Archivos** | `batch_generate_profiles.py`, `api/routes_complementary.py` |
| **Endpoint** | `GET /complementary/{dataset_id}/tldr` |
| **Valor estimado** | ⭐⭐⭐ Medio |
| **Latencia** | Batch offline + <100ms runtime |

**Resultados:**
- 2.000 perfiles generados con TL;DR (muestra representativa validada)
- Calidad: 90-100% de TL;DR aceptables en muestra
- Integrado en tarjetas de resultados del frontend
- Endpoint soporta IDs con slashes vía query parameter
- Evaluación de impacto (20 queries): P@5 mejora de 0.50 a 0.59 (+18.0%), sin empeorar ninguna query

**Ejemplo:**
- Dataset: "Mapas estratégicos de Ruido"
- TL;DR: "Mapas estratégicos de ruido de la tercera fase de la Directiva 2002/49/CE..."

**Documentación:**
- `docs/README_Sprint8_Paquete_A.md`

**📚 Fundamento bibliográfico:** `Jeong2024_240913385` (Contextual Compression in RAG, survey, ●●●), `Peng2026_260111863` (Metadata for RAG, ●●). Ver [`docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`](../../../docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md).

---

### #7: Generación de Planes de Análisis

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Crea propuestas de análisis: "Combina X con Y para ver Z" |
| **Estado** | ⏸️ **PENDIENTE** |
| **Valor estimado** | ⭐⭐⭐ Medio |
| **Latencia estimada** | Alta (~10-15s) |
| **Dependencias** | Requiere #5 (datasets complementarios) |

**Notas de implementación:**
- Generar sugerencias analíticas basadas en datasets del usuario
- Ejemplo: "Con el dataset de población y el de PIB, podrías calcular renta per cápita"
- Mostrar en sección "Análisis sugeridos"

---

### #6: Evaluación de Compatibilidad

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Analiza técnicamente si dos datasets pueden unirse (campos comunes, granularidad compatible) |
| **Estado** | ⏸️ **PENDIENTE** |
| **Valor estimado** | ⭐⭐⭐ Medio |
| **Latencia estimada** | Alta (~10s) |
| **Dependencias** | Requiere inspección de esquemas de datos |

**Notas de implementación:**
- Comparar campos disponibles en cada dataset
- Verificar granularidad temporal y geográfica
- Sugerir claves de unión posibles

**📚 Fundamento bibliográfico (trabajo futuro):** `Li2025_250710897` (LLMATCH, schema matching con LLM). Ver [`docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`](../../../docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md).

---

### #9: Perfilado Técnico Automático

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Genera descripción técnica del contenido del dataset (campos, formatos, calidad) |
| **Estado** | ⏸️ **PENDIENTE** |
| **Valor estimado** | ⭐⭐⭐ Medio |
| **Latencia estimada** | Alta (~10s) o batch |
| **Dependencias** | Requiere acceso a datos reales o metadatos técnicos detallados |

**Notas de implementación:**
- Proceso batch preferible
- Analizar distribución de valores, campos nulos, etc.
- Generar reporte técnico automático

**📚 Fundamento bibliográfico (trabajo futuro):** `Li2024_240517533` (PAE), `Peng2024_24040886` (EIVEN) — extracción de atributos/valores con LLM. Ver [`docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`](../../../docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md).

---

### #11: Síntesis de Múltiples Datasets

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Resume información de varios datasets relacionados como grupo coherente |
| **Estado** | ⏸️ **PENDIENTE** |
| **Valor estimado** | ⭐⭐ Bajo-Medio |
| **Latencia estimada** | Alta (~15s+) |
| **Dependencias** | Requiere entender relaciones entre datasets |

**Notas de implementación:**
- Usar cuando el usuario selecciona múltiples datasets
- Generar vista unificada de metadatos
- Combinar descripciones de forma coherente

---

### #15: Respuesta Data-Aware con Escalada (Metadata → Dato)

| Aspecto | Detalle |
|---------|---------|
| **Descripción** | Tras la búsqueda híbrida (fase 1, P@5=0,702), el usuario selecciona uno o varios datasets y formula una pregunta. El sistema responde en una **escalera de dos niveles**: nivel 1 desde metadatos (#10/#14), nivel 2 desde el **dato real** si los metadatos son insuficientes. |
| **Estado** | ⏸️ **PENDIENTE (diseñado, dependencias cubiertas)** |
| **Valor estimado** | ⭐⭐⭐⭐⭐ Alto — promueve el "RAG sobre contenido" de trabajo futuro a diseño actual; diferencia real frente al buscador de datos.gob.es. |
| **Latencia estimada** | Nivel 1: ~1-2 s (como #10 actual). Nivel 2: decenas de s (con streaming + indicador). |
| **Disparador nivel 2** | **Botón explícito del usuario** "responder desde los datos" (recomendado: transparente, sin riesgo de coste). Evolución futura: tool-use automático del LLM que pide `fetch_data` cuando juzga los metadatos insuficientes (requiere calibración). |
| **Dependencias** | ✅ Dato en local: 52.887 ficheros en `~/datos/` (60,3% del catálogo). ✅ URLs resueltas. ⚠️ Falta indexación del contenido (dataset_id → fichero + esquema). |

**Arquitectura — regla rectora: "el código calcula, el LLM interpreta"**

```
fase 1: búsqueda híbrida + fallback léxico  →  listado rankeado (barato, rápido)
fase 2: usuario selecciona dataset(s) y pregunta
   nivel 1: responder desde metadatos      (#10 chat + #14 TL;DR actuales)
   nivel 2: si metadatos insuficientes → leer fichero local → procesar → responder citando filas
```

**Estrategia de enrutado por tamaño** (medido sobre los 53.033 ficheros descargados; mediana 14 KB, p90 811 KB, p95 3,2 MB):

| Tamaño del fichero | % catálogo | Preguntas descriptivas / esquema / exploración | Estadísticos (media, mediana, conteos) / agregaciones |
|---|---|---|---|
| **≤ 300 KB** | **83,6%** | **LLM ve el fichero entero** (cabe en contexto 128K: deepseek-v4-flash, glm-5.2). Responde "qué campos tiene, qué contiene, qué preguntas puedo hacerle, resume, quality issues". | **Código calcula** (`pandas.describe` / DuckDB) → LLM interpreta la tabla resultante. Exacto. |
| **≤ 1 MB** | 91,0% | LLM ve el fichero entero si se usa modelo de **1M tokens** (`qwen3-coder-next:cloud`). | Igual: código calcula, LLM interpreta. |
| **> 300 KB / > 1 MB** | 9-16,4% | Código extrae **schema + perfil + muestra** y se lo pasa al LLM. | **Text-to-SQL sobre DuckDB**: el LLM propone la consulta, el código la ejecuta, el LLM interpreta el resultado + **cita filas**. |

**Por qué los estadísticos siempre los calcula el código:** los LLM son poco fiables haciendo aritmética sobre muchas filas (alucinan cifras). Para media/mediana/conteos, `pandas.describe` / DuckDB es exacto y barato; el LLM solo interpreta. En cambio, para **descripción de campos, resumen, detección de quality issues y sugerencia de preguntas**, el LLM viendo el fichero entero (pequeño) es excelente y más simple que montar un agente.

**Bundle reutilizable (una lectura → varios casos):** una vez cargado el fichero, el mismo `perfil + esquema + muestra` alimenta #9 (perfilado técnico, gratis), #14 (TL;DR enriquecido con contenido real), #2 (explicación de relevancia fundamentada en el dato), #5/#6 (complementariedad/compatibilidad a nivel de claves reales).

**Carga robusta del dato:** `chardet` para encoding (latin1 habitual en datos.gob.es), `xlrd`/`openpyxl` para XLS/XLSX (ya en venv), `json` module para JSON anidado de CKAN. **XLSX/XLS/ODS son binarios**: convertir a texto (`pandas.to_csv`) antes de pasar al LLM. Mapeo dataset_id → fichero vía `manifest.csv` / `manifest_sniff.csv` (campo `out_path`).

**Lo que NO es (límites del alcance):**
- No procesa formatos no tabulares (geo, PDF, XML, HTML) → nivel 1 con metadatos.
- No descarga bajo demanda (el dato ya está en local; los ~34.789 datasets sin fichero se atienden en nivel 1).
- No reemplaza la búsqueda (P@5=0,702 sigue siendo el selector; #15 es la capa de respuesta, no de recall).
- Reemplaza el rerank data-aware *search-time* (descartado: con P@5=0,702 no merece la pena descargar para reordenar el top-N en cada búsqueda).

**📚 Fundamento bibliográfico:** ver [`docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`](../../../docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md) (sección #15).
- *Ya en `.bib`:* `Jeong2024_240913385` (Contextual Compression, ●●●), `Peng2026_260111863` (Metadata for Better RAG, ●●), `Ning2024_241023841` (Beyond Content Relevance, ●●).
- *Añadidos al `.bib` para #15 (text-to-SQL / table-QA, verificados contra PDF 2026-06-26):* `Pourreza2023_230411015` (DIN-SQL, ●●●), `Li2024_240216347` (CodeS, ●●), `Lu2024_240205121` (LLM for Table Processing survey, ●●), `Herzig2020_200402349` (TAPAS, ●), `Wu2024_240809174` (TableBench, ●).

---

## 📋 Tabla Comparativa de Pendientes

| # | Caso | Valor | Latencia | Complejidad | Requiere Datos | Prioridad |
|---|------|-------|----------|-------------|----------------|-----------|
| **15** | **Respuesta data-aware con escalada** | ⭐⭐⭐⭐⭐ | Media-Alta | Media-Alta | ✅ Sí (ya en local) | 🥇 Alta |
| 10 | Respuestas preguntas | ⭐⭐⭐⭐ | Media | Media | ✅ Sí | 🥈 Media |
| 7 | Planes de análisis | ⭐⭐⭐ | Alta | Alta | ✅ Sí | 🥉 Baja |
| 6 | Compatibilidad técnica | ⭐⭐⭐ | Alta | Alta | ✅ Sí | 🥉 Baja |
| 9 | Perfilado técnico | ⭐⭐⭐ | Alta | Alta | ✅ Sí | 🥉 Baja |
| 11 | Síntesis múltiples | ⭐⭐ | Alta | Alta | ✅ Sí | 📄 Futuro |

**Notas:**
- #5 y #14 implementados en Sprint 8 (Paquete A)
- #8 archivado (ver sección específica)
- #13 ya implementado
- **#15 = próximo paso natural**: sus dependencias (52.887 ficheros en `~/datos`) ya están cubiertas. El enrutado por tamaño (83,6% ≤300 KB → LLM-directo para descriptivas) simplifica la implementación frente a un text-to-SQL completo.

---

## 🎯 Decisiones de Arquitectura

### Combinaciones que funcionan bien juntas:

1. **#3 + #4 + #12** (Pre-procesamiento) → ✅ Ya implementado
2. **#5 + #7** (Complementarios → Planes análisis) → Secuencia lógica
3. **#10 + #14** (Chat + Resúmenes) → UI de análisis de dataset
4. **#15 + #9 + #14 + #2** (Respuesta data-aware + bundle) → #15 carga el dato una vez y el mismo perfil+esquema+muestra alimenta #9 (perfilado), #14 (TL;DR enriquecido), #2 (explicación con contenido real). Una lectura → varios casos.

### Casos independientes:

- **#8** (Normalización) → Proceso batch, sin dependencias
- **#13** (Sugerencias) → Usa estructura de #3, baja complejidad
- **#6** (Compatibilidad) → Análisis técnico puro
- **#15** (Respuesta data-aware) → Capa de respuesta sobre la búsqueda existente; no toca el recall. Reusa #10/#14 en nivel 1.

---

## 📁 Ubicación de Archivos

```
08_Sprint6_LLM_Mejora/
├── docs/
│   ├── INDICE_CASOS_USO_LLM.md          ← Este documento
│   ├── CASO_13_QUERY_SUGGESTIONS.md     ← #13 Implementado
│   ├── INFORME_FINAL_4_ITERACIONES.md   ← Análisis #1+#2
│   └── EVALUACION_QWEN_2026-06-01.md    ← Comparativa modelos
├── codigo/
│   ├── motor/
│   │   ├── llm_client.py                # Cliente genérico LLM
│   │   ├── llm_reranker.py              # #1 + #2 implementados
│   │   ├── query_preprocessor.py        # #3 + #4 + #12 implementados
│   │   ├── lexical_expander.py          # Fallback léxico (#4)
│   │   └── query_suggester.py           # #13 implementado
│   ├── api/
│   │   ├── routes_llm_v2.py             # Endpoints #1+#2
│   │   ├── routes_query_enhanced.py     # Endpoints #3+#4+#12+#13
│   │   ├── routes_complementary.py      # Endpoints #5 + #14
│   │   ├── routes_dataset_chat.py       # Endpoint #10
│   │   └── main_v2_final_v07.py         # API principal
│   └── tests/
│       ├── test_query_preprocessing.py  # Tests #3+#4+#12
│       ├── test_query_suggester.py      # Tests #13 (20 tests)
│       └── resultados/                    # Evaluaciones
│           ├── INFORME_FINAL_4_ITERACIONES.md
│           └── EVALUACION_QWEN_2026-06-01.md
└── README_08_Sprint6_LLM_Mejora.md       # Documentación general
```

---

## 💡 Recomendaciones para Continuar

1. **Estabilizar #3+#4+#12:** Ajustar prompt de expansión, aumentar timeouts, implementar cache persistente
2. **Implementar #5:** Alta prioridad, valor demostrable, depende de metadatos disponibles
3. **Implementar #10:** Respuestas a preguntas sobre datasets (RAG con metadatos)
4. **Evaluar #8:** Proceso batch de sinónimos, mejora recall sin latencia
5. **Diferir #6, #7, #9, #11:** Alta complejidad, requieren datos reales, latencia alta

---

## ✅ Estado Actual (2026-06-13)

**Implementados:** #1, #2, #3, #4, #5, #10, #12, #13, #14  
**Archivado:** #8 (vía muerta - normalización conceptual)  
**Pendientes:** #6, #7, #9, #11

---

**¿Qué caso de uso quieres revisar en detalle o implementar a continuación?**
