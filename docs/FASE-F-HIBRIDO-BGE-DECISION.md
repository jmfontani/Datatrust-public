# FASE F — El híbrido con BGE-M3: resultado y decisión de despliegue

Fecha: 2026-09-29
Estado: **cerrada**. Veredicto: **BGE-M3 mejora también el sistema híbrido real.**

---

## 1. El resultado que decide

La Fase E midió el motor semántico **aislado**. El buscador de producción es
**híbrido** (0,7 semántico + 0,3 léxico), así que la pregunta de despliegue era
otra: ¿mejora BGE-M3 *dentro* del buscador real? Medido con las 214 consultas,
mismo GT v5, misma máquina, misma sesión, replicando el pipeline completo de la
API (expansión de sinónimos, stop words, detección de territorio y ambigüedad,
`min_score` 0,15, normalización léxica `raw/(raw+0,2)`):

| motor | nDCG@10 | IC95 | P@5 | MRR | cobertura |
|---|---|---|---|---|---|
| MiniLM (actual) | 0,4249 | [0,3772 · 0,4727] | 0,3458 | 0,4932 | 100 % |
| **BGE-M3** | **0,5621** | [0,5163 · 0,6079] | **0,4290** | **0,6020** | 93 % |

**Comparación pareada: +0,1372 [+0,0963 · +0,1781]**, mejora mínima detectable
0,0409 → **decidido**. Gana en 112 consultas, empata en 48, pierde en 54.

---

## 2. El sesgo va EN CONTRA del resultado (importante)

La cobertura de juicios de BGE en el híbrido es **93 %** (150 pares sin juzgar de
2.140), frente al **100 %** de MiniLM. Causa: el pool conjunto de la Fase E se
construyó con el top-20 de los dos motores **semánticos puros**, pero el híbrido
BGE además usa el canal **léxico**, que trae fichas que nunca se juzgaron.

El nDCG puntúa esas 150 fichas como 0. Es decir: **se penaliza a BGE por lo que
no se ha juzgado**, no por lo que hace mal. El +0,1372 es un **límite inferior**:
si alguna de esas 150 fuese relevante, la ventaja real sería mayor.

Conclusión: no invalida el resultado, lo hace conservador. Es la misma lección de
la Fase E, aplicada en dirección contraria.

---

## 3. Control de fidelidad del clon

La medición no se hizo tocando producción. Se levantó un **clon de la API**
(`main_v2_bge_experimento.py`) con el motor y la columna parametrizados por
variables de entorno, sirviendo en otro puerto.

**Control previo obligatorio:** el clon con la configuración de producción
(MiniLM + columna `embedding`) devolvió **rankings idénticos** al buscador real.
Sin ese control, cualquier diferencia podría ser del andamiaje y no del motor.

`/health` del clon reporta el motor y la columna efectivos, para poder verificar
qué está corriendo en vez de suponerlo.

---

## 4. Dos bugs silenciosos (que casi falsean el resultado)

1. **El clon «con BGE» daba rankings idénticos a MiniLM.** No era similitud: el
   proceso anterior seguía ocupando el puerto, el nuevo no arrancó y se estaba
   midiendo el equivocado. Peor: `/health` reportaba MiniLM siempre, así que la
   comprobación de salud *confirmaba* el error. → `/health` honesto.
2. **Con BGE daba cero resultados.** La guarda
   `if not USE_REAL_EMBEDDINGS or not EMBEDDING_MODEL` abortaba antes de llegar a
   BGE (que no usa modelo local, va por ollama), y caía a un **fallback de vector
   aleatorio de 384 dims** que producía cero resultados sin error visible.
   → El modo BGE se enruta antes de la guarda, y la lección: *un fallback
   silencioso camufla el fallo; el error debe ser ruidoso*.

**Verificación sin esperar al servidor:** importar el módulo y llamar a
`get_embedding()` directamente. Devuelve 1024 dims → BGE real; 384 → sigue en el
fallback. Más rápido y más seguro que arrancar uvicorn y rezar.

---

## 5. Nota sobre las cifras y comparabilidad

- **0,4249 no es comparable con 0,4854.** El 0,4854 era MiniLM con GT v4; el
  0,4249 es MiniLM con **GT v5**, cuyo ideal por consulta es mayor porque el pool
  conjunto añadió juicios (muchos de nivel 2). La comparación válida es *en
  pareado y con el mismo GT*, y esa es la de la §1.
- P@5 y MRR de MiniLM **sí coinciden exactamente** entre v4 y v5 (0,3458 / 0,4932):
  son sensibles al ranking, no al tamaño del pool ideal. Buen control cruzado.
- `semantico vs lexico` deja de ser distinguible en BGE: con el canal léxico fijo,
  el híbrido BGE y el semántico puro BGE empatan (−0,0072, IC cruza cero). Con
  MiniLM el híbrido sí aportaba sobre el semántico puro (+0,0537). Interpretación:
  **BGE-M3 hace que el canal léxico sea prescindible** — el peso 0,3 deja de
  aportar porque el semántico ya recupera lo que el léxico aportaba.

---

## 6. Qué queda por decidir (no decidido aquí)

1. **La adopción no está hecha.** BGE-M3 vive en la columna paralela
   `embedding_bge`; producción sigue con MiniLM y `embedding` intacta.
2. **Coste operativo del despliegue:** BGE-M3 son 1024 dims frente a 384 (2,7×
   más vector), 560M parámetros frente a 118M, y en CPU/GPU-ROCm tarda ~4,75 h el
   catálogo completo. Requiere: nueva imagen con sentence-transformers + BGE-M3,
   decidir si se sirve por ollama o embebido, y regenerar el `Dockerfile.api`
   (el pin actual fija MiniLM).
3. **Rejuzgar el residual de 150 pares** para cerrar la cobertura al 100 % y
   obtener el número exacto en lugar del límite inferior.
4. **¿Peso léxico distinto?** Con BGE el 0,3 de léxico no aporta (ver §5). Probar
   1,0/0,0 en producción sería igual de bueno y más simple, pero eso es una
   decisión de producto aparte.

---

## 7. Artefactos

**Scripts** (`09_Sprint7_RAGAS/codigo/`):
- `api_bge/main_v2_bge_experimento.py` — clon de la API parametrizado
- `gestionar_clon.sh` — arranque/parada verificada del clon
- `146_hibrido_pareado.py` — **la medición de esta fase** (pareada + cobertura)
- `132_evaluar_216.py` — modificado: `--api` para apuntar al clon

**Entregables** (`09_Sprint7_RAGAS/entregables/`):
- `fase_f_HIBRIDO_PAREADO.json` — **resultado definitivo** (+0,1372)
- `fase_f_HIBRIDO_MINILM.json` · `fase_f_HIBRIDO_BGE.json` — medias por sistema

**Columnas** (producción intacta): `embedding` (384, MiniLM) · `embedding_bge`
(1024, BGE-M3) · `embedding_minilm_aprox` (384, control de texto).
