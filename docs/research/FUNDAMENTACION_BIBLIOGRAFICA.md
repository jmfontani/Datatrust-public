# Fundamentación Bibliográfica del Buscador Semántico

**Fecha:** 2026-06-19
**Propósito:** Sustentar en literatura científica las decisiones de diseño y los casos de uso LLM previstos para el proyecto. Las referencias provienen de `docs/research/semantic_search_llms.bib` (36 papers de arXiv); los PDFs en `docs/research/pdfs/`.

> Esta fundamentación se construye de forma prospectiva: se identifican las técnicas que respaldan la arquitectura y los casos de uso propuestos, de modo que el TFM tenga base académica antes de su implementación. El objetivo es dar soporte bibliográfico a la defensa del TFM.

> ⚠️ **Aviso sobre las claves de cita:** las claves tipo `Sun2023_230409542` son identificadores internos derivados de `semantic_search_llms.bib`. En varios casos el `.bib` registró **autorías incorrectas** (p. ej. la clave `Peng2026_260111863` corresponde en realidad a Yousuf et al., 2026; `Mariri2024_241020381` a Zhang et al., 2024; `Jeong2024_240913385` a Verma, 2024; `Yeligar2025_2601.03258` a George, 2025). Las autorías correctas, verificadas contra los PDFs, están en la sección **Referencias (APA)** de [`docs/NARRATIVA_TFM.md`](../NARRATIVA_TFM.md). Usar siempre esa lista para citas formales.

---

## 1. Papers ancla por caso de uso / decisión arquitectológica

Leyenda: **●●●** fundamento directo (citar siempre) · **●●** soporte fuerte · **●** contextual/familia técnica.

### #1 + #2 Re-ranking inteligente + Explicaciones de relevancia

| Ref | Nivel | Cómo sustenta la propuesta |
|-----|------|-----------------------------|
| `Sun2023_230409542` (RankGPT, *Is ChatGPT Good at Search?*) | ●●● | Fundacional del re-ranking con LLM. Demuestra que LLMs correctamente instruados igualan o superan métodos supervisados en IR. Sustenta usar un LLM para reordenar el top-N. |
| `Liu2023_230617563` (Pairwise Ranking Prompting) | ●● | Estrategia *pairwise* de re-ranking con LLM, alternativa a la listwise; contextualiza el diseño del prompt. |
| `Pradeep2023_230915088` (RankVicuna) | ●● | Re-ranking *listwise* zero-shot con modelos **open-source**; avala el uso previsto de modelos accesibles vía Ollama. |
| `Nogueira2020_200306713` (Document Ranking with Seq2Seq) | ● | Antecedente histórico del re-ranking neuronal. |

### #3 + #4 + #12 Interpretación + Expansión + Validación

| Ref | Nivel | Cómo sustenta |
|-----|------|----------------|
| `Wang2023_230307678` (Query2doc) | ●●● | Expansión de query con LLM que mejora **tanto BM25 como denso**. Justifica el fallback léxico previsto (la expansión beneficia también la rama léxica). |
| `Gao2022_221210496` (HyDE) | ●● | Generación de documentos hipotéticos para expansión densa zero-shot. |
| `Ma2023_230514283` (Query Rewriting for RAG) | ●● | Reescritura estructurada de queries para RAG (sustenta #3). |
| `Ning2024_241013765` (Knowledge-Aware Query Expansion) | ●● | Expansión con conocimiento relacional (conecta con #5 complementariedad). |
| `Ning2024_241023841` (Beyond Content Relevance) | ●●● | Evalúa atributos documentales (Formato, Idioma, Fuente) más allá de la relevancia de contenido — coincide con los filtros facetados y la validación de metadatos propuestos (#12). |
| `Peng2026_260111863` (Metadata for Better RAG) | ●●● | *Metadata-aware query reformulation*; sustenta extraer territorio/formato de la query como metadatos (#3). |
| `Rejas2026_260311008`, `Kumar2026_260111238`, `Yang2025_250401448` (familia PRF con LLM) | ● | Pseudo-relevance feedback asistido por LLM; familia técnica de la expansión. |

### Arquitectura: pipeline de dos etapas (expansión → híbrida → rerank)

| Ref | Nivel | Cómo sustenta |
|-----|------|----------------|
| `Yeligar2025_260103258` (Two-Stage Retrieval: FlashRank + Query Expansion) | ●●● | Describe casi exactamente la arquitectura propuesta: expansión de query para recall + reranker de utilidad marginal. |
| `Zhang2025_250604760` (Exp4Fuse) | ●● | Fusión de rankings (query original + expandida) — sustenta la combinación de scores en la búsqueda híbrida. |

### Arquitectura: búsqueda híbrida (semántica pgvector + léxica tsvector/BM25)

| Ref | Nivel | Cómo sustenta |
|-----|------|----------------|
| `Gildea2024_240407220` (Blended RAG) | ●●● | Defiende combinar retrievers semántico + léxico para mejorar la precisión de RAG. Justifica la híbrida. |
| `Mariri2024_241020381` (Dense-Sparse Hybrid Vectors + Graph ANN) | ●●● | Recuperación densa-sparse con ANN basado en grafos = el diseño previsto de HNSW de pgvector + tsvector. |
| `Lin2025_250210639` (Selective Dense Retrieval Guided by Sparse Lexical) | ●● | Recuperación densa guiada por léxica (patrón: léxica filtra/candidatea, semántica ordena). |
| `Formal2021_210705720` (SPLADE) | ● | Antecedente del sparse learned; contexto de la rama léxica. |
| `Formal2024_240811119` (Mistral-SPLADE) | ● | Sparse learned mejorado con LLM. |

### Arquitectura: modelo de embeddings (MiniLM multilingüe 384D)

| Ref | Nivel | Cómo sustenta |
|-----|------|----------------|
| `Wang2022_221203533` (E5, weakly-supervised contrastive) | ● | Contexto de la familia de embeddings contrastivos a la que pertenece MiniLM; justifica la elección de un modelo multilingüe pre-entrenado con supervisión contrastiva. |

### #5 Datasets complementarios / perfiles

| Ref | Nivel | Cómo sustenta |
|-----|------|----------------|
| `Peng2026_260111863` (Metadata for Better RAG) | ●●● | Base para perfiles con metadatos (variables_key, nivel geográfico, cobertura temporal). |
| `Li2025_250710897` (LLMATCH, schema matching con LLM) | ●● | Emparejamiento de esquemas con LLM — fundamento de la compatibilidad de uniones entre datasets. |

### #14 TL;DR / resumen automático (compresión contextual)

| Ref | Nivel | Cómo sustenta |
|-----|------|----------------|
| `Jeong2024_240913385` (Contextual Compression in RAG, survey) | ●●● | Fundamento directo del TL;DR previsto como compresión contextual de los metadatos del dataset. |
| `Peng2026_260111863` (Metadata for Better RAG) | ●● | Perfiles basados en metadatos (información sobre la que comprimir). |

### #10 Chat sobre datasets

| Ref | Nivel | Cómo sustenta |
|-----|------|----------------|
| `Jeong2024_240913385` (Contextual Compression survey) | ● | Compresión del contexto del dataset para responder preguntas sobre él. |

### #15 Respuesta data-aware con escalada (metadata → dato) + enrutado por tamaño

Caso añadido el 2026-06-26 (ver [`08_Sprint6_LLM_Mejora/docs/INDICE_CASOS_USO_LLM.md`](../../08_Sprint6_LLM_Mejora/docs/INDICE_CASOS_USO_LLM.md) y [`03_Sprint1_Ingesta/codigo/descarga_datos/informe_descarga.md`](../../03_Sprint1_Ingesta/codigo/descarga_datos/informe_descarga.md)). Combina dos sub-problemas: (a) decidir cuándo pasar de metadatos al dato real y (b) responder sobre el dato tabular. El componente (b) es **text-to-SQL / table-QA**, un campo distinto al de la búsqueda semántica que domina este `.bib`.

**Papers ya en `semantic_search_llms.bib` (verificados):**

| Ref | Nivel | Cómo sustenta |
|-----|------|----------------|
| `Jeong2024_240913385` (Contextual Compression in RAG, survey) | ●●● | Fundamento del nivel 1→2: comprimir el contexto del dataset (perfil + muestra) en vez de pasar el fichero entero. Sustenta el enrutado por tamaño (dar el fichero entero solo cuando cabe). |
| `Peng2026_260111863` (Metadata for Better RAG) | ●● | Perfiles basados en metadatos (esquema, variables, cobertura) como la información sobre la que opera el nivel 2. |
| `Ning2024_241023841` (Beyond Content Relevance) | ●● | Evalúa atributos documentales (formato, fuente, idioma) más allá de la relevancia de contenido — conecta con la decisión de suficiencia de metadatos y los filtros facetados. |

**Papers NUEVOS para #15 (text-to-SQL / table-QA) — incorporados al `.bib` y verificados contra los PDFs el 2026-06-26** (PDFs en `pdfs/<arxiv>.pdf`):

| Ref (arXiv) | Nivel | Cómo sustenta |
|-----|------|----------------|
| `Pourreza2023_230411015` (DIN-SQL, NeurIPS 2023) | ●●● | Fundamento directo del nivel 2: text-to-SQL descompuesto en sub-tareas (schema linking → clasificación de complejidad → generación → self-correction) con few-shot prompting. Sustenta "el LLM propone la consulta, el código la ejecuta". |
| `Li2024_240216347` (CodeS) | ●● | Text-to-SQL con modelos open-source: **schema filter** + **value retriever** + prompt con tipos/valores representativos/claves. Espejo de nuestro "schema + perfil + muestra" y del uso de modelos accesibles vía Ollama. |
| `Herzig2020_200402349` (TAPAS, ACL 2020) | ● | Antecedente fundacional del table-QA (QA sobre tabular con agregación). Contexto histórico de "estadísticos sobre el dato". |
| `Lu2024_240205121` (LLM for Table Processing, survey) | ●● | Survey que taxonomiza table QA / NL2SQL / data analysis con LLMs — marco de referencia del componente tabular de #15. |
| `Wu2024_240809174` (TableBench) | ● | Benchmark de table-QA con subcategorías *numerical reasoning* y *data analysis* — alineado con preguntas tipo "dame los estadísticos principales". Útil para evaluar #15. |

> **Nota de proceso (resuelta 2026-06-26):** estos 5 papers se añadieron a `semantic_search_llms.bib` (claves verificadas, autorías confirmadas contra los PDFs — p.ej. DIN-SQL en arXiv v3 lista a Rafiei primero, pero la versión publicada en NeurIPS es Pourreza primero, que es la canónica usada). Los PDFs están en `docs/research/pdfs/`. Listos para citar formalmente en `NARRATIVA_TFM.md`.

---

## 2. Trabajo futuro: papers que sustentan casos pendientes

| Caso futuro | Ref | Cómo apoya la implementación prevista |
|-------------|-----|--------------------------------------|
| #9 Perfilado técnico automático | `Li2024_240517533` (PAE), `Peng2024_240408886` (EIVEN) | Extracción de atributos/valores con LLM; análogos a la futura extracción de variables_key y perfil técnico. |
| #6 Evaluación de compatibilidad | `Li2025_250710897` (LLMATCH) | Schema matching con LLM para verificar campos comunes y claves de unión. |

---

## 3. Papers excluidos por baja relevancia

Se revisaron y se descartan de la fundamentación (no sustentan decisiones del proyecto, aunque están en el `.bib`):

| Ref | Razón de exclusión |
|-----|--------------------|
| `Khattab2020_200412832` (ColBERT), `Santhanam2021_211201488` (ColBERTv2), `Zhan2021_210407186` (COIL) | *Late interaction* / coincidencia léxica contextual; enfoques no adoptados (alternativas consideradas). |
| `Yang2025_250518105` (ManuSearch) | Búsqueda profunda multi-agente; enfoque distinto al del proyecto. |
| `Wang2023_240100368` (Improving Embeddings), `Ning2024_240320327` (Gecko), `Su2022_221209741` (Instructor), `Ning2025_250521439` (Instruction-Following Retrieval) | Sobre entrenamiento/destilación de embeddings; usamos un modelo off-the-shelf (MiniLM). |
| `Myung2026_260301417` (ReFeed) | Reescritura guiada por feedback de estilo; fuera del alcance actual. |
| `Yehuda2025_250405181` | IR generativo; marginal para las explicaciones de relevancia. |
| `Ning2024_241104602`, `Rejas2024_240614848`, `Ning2025_250513757`, `Rejas2025_250410509` | Variantes de re-ranking listwise; ya cubierto por RankGPT/RankVicuna como referente principal. |

---

## 4. Referencias BibTeX utilizadas (subconjunto activo)

```bibtex
@article{Sun2023_230409542,      ... Is ChatGPT Good at Search? (RankGPT) ...}
@article{Liu2023_230617563,     ... Pairwise Ranking Prompting ...}
@article{Pradeep2023_230915088, ... RankVicuna ...}
@article{Nogueira2020_200306713,... Document Ranking Seq2Seq ...}
@article{Wang2023_230307678,     ... Query2doc ...}
@article{Gao2022_221210496,      ... HyDE ...}
@article{Ma2023_230514283,       ... Query Rewriting for RAG ...}
@article{Ning2024_241013765,     ... Knowledge-Aware Query Expansion ...}
@article{Ning2024_241023841,     ... Beyond Content Relevance ...}
@article{Peng2026_260111863,     ... Metadata for Better RAG ...}
@article{Rejas2026_260311008,    ... PRF with LLMs (systematic study) ...}
@article{Kumar2026_260111238,    ... LLM-Assisted PRF ...}
@article{Yang2025_250401448,     ... LLM-VPRF ...}
@article{Yeligar2025_260103258,  ... Two-Stage Retrieval (FlashRank) ...}
@article{Zhang2025_250604760,   ... Exp4Fuse ...}
@article{Gildea2024_240407220,   ... Blended RAG ...}
@article{Mariri2024_241020381,   ... Dense-Sparse Hybrid + Graph ANN ...}
@article{Lin2025_250210639,      ... Selective Dense Retrieval Guided by Sparse ...}
@article{Formal2021_210705720,  ... SPLADE ...}
@article{Formal2024_240811119,  ... Mistral-SPLADE ...}
@article{Wang2022_221203533,     ... E5 (weakly-supervised contrastive) ...}
@article{Li2025_250710897,       ... LLMATCH (schema matching) ...}
@article{Jeong2024_240913385,    ... Contextual Compression in RAG (survey) ...}
@article{Li2024_240517533,       ... PAE (attribute extraction) ...}
@article{Peng2024_240408886,     ... EIVEN (attribute value extraction) ...}
@article{Pourreza2023_230411015, ... DIN-SQL (text-to-SQL) ...}
@article{Li2024_240216347,       ... CodeS (open-source text-to-SQL) ...}
@article{Herzig2020_200402349,   ... TAPAS (table parsing) ...}
@article{Lu2024_240205121,       ... LLM for Table Processing (survey) ...}
@article{Wu2024_240809174,       ... TableBench (table QA benchmark) ...}
```

Las entradas completas están en `docs/research/semantic_search_llms.bib`.

---

## 5. Documentos relacionados

- `docs/NARRATIVA_TFM.md`: sección "🔬 Estado del arte y fundamentación" con los 9 papers ancla (●●●).
- `docs/research/semantic_search_llms.bib`: archivo BibTeX con todas las referencias consultadas.
- `docs/FORMULACION_PROYECTO.md`: formulación del proyecto y casos de uso previstos.
- `README.md`: índice general del repositorio.