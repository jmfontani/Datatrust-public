# Fase H · Despliegue de BGE-M3 en producción

**Fecha:** 30-sep-2026
**Decisiones:** G5 (adoptar BGE-M3) — **APROBADA por el usuario** · Bug de
determinismo en producción — **APROBADO aplicarlo con medición antes/después**

---

## 1. Resultado de la medición antes/después (producción real)

Medido sobre el buscador **en servicio**, 214 consultas, GT v5, instrumento
canónico (`gt_metrics.evaluar`):

| métrica | ANTES (MiniLM) | DESPUÉS (BGE-M3) | contraste pareado |
|---|---|---|---|
| **nDCG@10** | 0,4249 [0,3772·0,4727] | **0,5575** [0,5113·0,6038] | **+0,1326 [+0,0929 · +0,1741]** |
| P@5 | 0,3458 | **0,4224** | — |
| P@10 | 0,2977 | **0,3879** | — |
| MRR | 0,4932 | **0,5895** | — |
| cobertura@10 | 100 % | 92,6 % | — |

**El contraste no cruza cero: la mejora es estadísticamente distinguible.**
Mejora en 94 consultas, empeora en 37, empata en 83. El top-10 cambia en
**214/214** consultas, que es lo esperado entre motores distintos.

**Las cifras de producción reproducen EXACTAMENTE las del clon experimental**
(Fase G: P@5 0,4224 · P@10 0,3879 · nDCG 0,5575). Dos implementaciones
independientes dando el mismo número es la validación más fuerte disponible de
que el despliegue no introdujo ninguna desviación.

La línea base ANTES reprodujo igualmente la cifra de Fase F (0,4249 · 0,3458 ·
0,4932), lo que valida el instrumento de medida.

**Cobertura:** baja de 100 % a 92,6 %. No es un defecto del motor: BGE recupera
fichas que el juicio no había cubierto. Penaliza la métrica, así que
**+0,1326 es un límite inferior**.

---

## 2. Cómo se despliega: por variable de entorno

El motor es seleccionable sin tocar código:

```
EXPERIMENTO_MOTOR   = "minilm" | "bge"      (defecto: minilm)
EXPERIMENTO_COLUMNA = columna de datasets   (defecto: embedding)
```

La vuelta atrás **no requiere rebuild** (10 GB, minutos): basta recrear el
contenedor con las variables en sus valores históricos. El defecto es MiniLM, así
que arrancar sin variables deja el sistema exactamente como estaba antes de esta
fase.

Vuelta atrás completa: imagen `docker-api:pre-bge-20260930` (ID `25381cec8c7b`),
etiquetada antes de tocar nada.

---

## 3. Superficie real del cambio (auditada, no supuesta)

La columna `embedding` se usaba en **más sitios** de los que el plan asumía:

| fichero | usa la columna | ¿montado? | acción |
|---|---|---|---|
| `main_v2_final_v07.py` (`/search`) | sí | **sí** | parametrizado |
| `routes_v10.py` (`/llm/search/fast`) | sí | **sí** | parametrizado + 3 bugs corregidos |
| `routes_llm_v2.py` | sí | no | sin tocar (código muerto) |
| `routes_llm_v2_backup.py` | sí | no | sin tocar (código muerto) |

**`routes_v10` es el hallazgo que importa.** Tiene su **propia copia** de
`get_embedding()` y su propia SQL contra `d.embedding`. Si se hubiera cambiado
solo el fichero principal, ese endpoint habría comparado un vector de 1024 dims
contra una columna de 384.

---

## 4. Índice HNSW: sin él el despliegue habría sido inviable

`embedding_bge` **no tenía índice**. Medido en la base real:

| | plan | latencia |
|---|---|---|
| sin índice | Parallel Seq Scan | **1.850 ms** |
| con HNSW | Index Scan | **4,5 ms** |

**411× de diferencia.** Creado `idx_datasets_embedding_bge_hnsw`
(HNSW, `vector_cosine_ops`, m=16, ef_construction=64, 717 MB). Sin esto el
buscador pasa de instantáneo a ~2 s por consulta: BGE habría ganado en calidad y
perdido en uso. Producción mantiene su HNSW en `embedding` (182 MB), intacto.

---

## 5. Un fallo evitado por diseño

Con BGE no existe modelo local: `EMBEDDING_MODEL` es `None` **por diseño**. La
guarda original era:

```python
if not USE_REAL_EMBEDDINGS or not EMBEDDING_MODEL:
    return [random.uniform(-0.1, 0.1) for _ in range(384)]
```

Con BGE eso es un vector **aleatorio de 384 dims** que no compara contra una
columna de 1024: cero resultados, sin error visible. Es el mismo fallo que ya
apareció dos veces en el clon (Fase F). En producción `_embed_bge` **propaga la
excepción** en vez de degradar en silencio: mejor un error visible que un ranking
inventado.

---

## 6. Bugs preexistentes encontrados en `routes_v10`

Al verificar el endpoint salieron **tres fallos encadenados** que ya estaban ahí
(uno de ellos sí lo introduje al parametrizar). Ninguno era visible, porque el
endpoint devolvía `[]` **sin log de error**:

1. **`sql = """` sin `f`** — al parametrizar la columna, el placeholder viajaba
   literal a PostgreSQL. *(introducido por el cambio, corregido)*
2. **`DB_HOST` con fallback a `localhost`** — el contenedor define
   `POSTGRES_HOST=postgres`; el router no encontraba la base. Corregido para
   aceptar ambas familias de variables. *(preexistente)*
3. **`WHERE score_final > 0.1`** — PostgreSQL no admite un alias del `SELECT` en
   el `WHERE`. Corregido repitiendo la expresión con sus parámetros en orden.
   *(preexistente)*

Verificado contra la base real tras corregir: la SQL devuelve resultados.

---

## 7. Verificación

`149_verificar_bge_produccion.py` — snapshots de rankings de las 214 consultas
(antes/después) y comparación. Guarda los rankings completos, así que cualquier
métrica a cualquier k se recalcula sin volver a consultar el buscador en
servicio.

Artefactos: `fase_h_SNAPSHOT_ANTES.json` · `fase_h_SNAPSHOT_DESPUES.json` ·
`fase_h_VERIFICACION.json`.

**Latencia de producción tras el despliegue: ~2,5 s por consulta**, dominada por
la llamada a ollama para vectorizar la consulta (BGE corre en la GPU del host).
El índice HNSW no es el cuello de botella. Es el coste de calidad a asumir.

---

## 8. Estado

- [x] Línea base ANTES reproducible contra Fase F
- [x] Código parametrizado + arreglo de determinismo (`sorted(expanded)`)
- [x] Índice HNSW en `embedding_bge` (411× más rápido)
- [x] Despliegue con BGE-M3 activo (`/health` lo confirma)
- [x] Medición DESPUÉS: **+0,1326 nDCG**, distinguible
- [x] 3 bugs preexistentes de `routes_v10` corregidos
- [ ] Pendiente: decidir si el canal léxico (peso 0,3) sigue aportando con BGE
      — en el clon medía −0,0072 (no distinguible): con BGE el híbrido podría
      simplificarse a semántico puro
- [ ] Pendiente: latencia. 2,5 s por consulta es notable para un buscador
      interactivo; estudiar caché de embeddings de consulta
