# Pinning de dependencias y determinismo del embedding

**Fecha:** 24-sep-2026
**Estado:** **APLICADO Y VERIFICADO** (24-sep-2026) · `requirements.txt` + `Dockerfile.api` + revisión del modelo
**Motivo:** los embeddings del catálogo no se pueden reproducir; dos contenedores con el mismo código dan métricas distintas (P@5 0,6298 vs 0,6383)

---

## 1. El problema, en una frase

El `Dockerfile.api` instalaba **13 paquetes sin ninguna versión fijada**, así que
cada `docker compose build` produce un entorno potencialmente distinto. Y el
modelo de embeddings se carga **por nombre, sin versión ni revisión**, en 5
sitios del código.

---

## 2. Estado de partida (verificado)

`Dockerfile.api`, bloque de instalación:

```dockerfile
RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] psycopg2-binary pgvector python-dotenv \
    sentence-transformers numpy pyyaml requests scikit-learn scipy ollama
```

Trece paquetes, **cero versiones fijadas**.

### 2.1 El coste oculto: CUDA en un contenedor sin GPU

`sentence-transformers` arrastra `torch`. Al no fijar build, pip resuelve la
variante CUDA:

| componente | tamaño |
|---|---|
| `/usr/local/lib/python3.11/site-packages/nvidia` | **3,2 GB** |
| `…/torch` | 1,2 GB |
| `…/triton` | 897 MB |
| **imagen completa** | **10,1 GB** |

Y en el contenedor `buscador_api`, `torch.cuda.is_available()` devuelve
**`False`**. Es decir: **más de la mitad de la imagen son librerías CUDA que
nunca se ejecutan** en el cálculo de embeddings.

No se cambia a build CPU en este paso porque eso obliga a revalidar los
embeddings. Queda como optimización separada.

---

## 3. El fichero creado

`07_Sprint5_Integracion/codigo/docker/requirements.txt`

Contiene las **77 versiones exactas** del entorno que está ahora en
funcionamiento, organizadas en cuatro bloques:

| bloque | n | papel |
|---|---|---|
| dependencias directas | 12 | lo que pide la aplicación |
| **núcleo del embedding** | 11 | **determinan el vector** |
| transitivas | 35 | reproducibilidad de la resolución |
| CUDA | 19 | arrastradas por torch |

El bloque que importa es el segundo, porque fija a propósito paquetes que
*nadie pide directamente* pero que **deciden qué vector sale**:

```
torch==2.14.0
transformers==5.17.0
tokenizers==0.23.2
huggingface_hub==1.32.0
safetensors==0.8.0
regex==2026.9.10
```

Si alguno de estos sube de versión, **los 94.461 embeddings del catálogo quedan
invalidados** y hay que recalcularlos.

### 3.1 Verificación

`scripts/86_verificar_requirements.py` compara el fichero con el entorno
instalado, en los dos sentidos (que no falte ninguno, que no sobre ninguno, que
ninguna versión difiera). Resultado:

```
### entorno: 77 paquetes | requirements.txt: 77 ###
RESULTADO: COINCIDE EXACTAMENTE.
  77 paquetes, todas las versiones identicas al entorno.
```

La primera pasada **falló** y detectó dos errores propios: un `nvidia-cusparse`
escrito como `12.6.3.5` cuando el entorno tiene `12.6.3.3`, y el sufijo
`uvicorn[standard]` que falseaba la comparación. Ambos corregidos y reverificados.

### 3.2 Índice de paquetes

`torch==2.14.0` debe instalarse desde el índice de PyTorch, no desde PyPI. El
wheel instalado tiene tag `cp311-cp311-manylinux_2_28_x86_64`:

```
pip install --index-url https://download.pytorch.org/whl/cu130 -r requirements.txt
```

---

## 4. Segundo problema: el modelo se carga sin fijar

Cinco puntos del código cargan el modelo **por nombre, con nombre corto y sin
revisión**:

```python
# 08_Sprint6_LLM_Mejora/codigo/api/main_v2_final_v07.py:359   <-- API en uso
EMBEDDING_MODEL = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 08_Sprint6_LLM_Mejora/codigo/api/routes_llm_v2.py:101
# 05_Sprint3_Busqueda_UI/codigo/motor/search_engine.py:44
# 03_Sprint1_Ingesta/codigo/limpieza/generate_embeddings_pg.py:61
# 04_Sprint2_Embeddings/codigo/indexacion/search_hybrid.py
```

Dos defectos:

1. **Nombre corto.** `'paraphrase-multilingual-MiniLM-L12-v2'` no es un
   identificador de HuggingFace; el repo real es
   `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. El nombre
   corto lo resuelve la heurística de `sentence-transformers`, que puede
   cambiar entre versiones de la librería.
2. **Sin revisión.** Es un puntero móvil: la rama `main` del repo. Si el autor
   publica un cambio, un build nuevo descarga **pesos distintos** con el mismo
   nombre.

### 4.1 Revisión a fijar (leída del modelo cacheado)

```
e8f8c211226b894fcb81acc59f3b34ba3efd5f42
```

Corrección propuesta, en los 5 puntos:

```python
MODEL_NAME  = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)
```

Debe ser **la misma constante** en todos los scripts. Hoy hay 15 ficheros con
`SentenceTransformer(`, varios en carpetas `historial/` y `_backup` que no
deberían entrar en la imagen.

---

## 5. Tercer problema: el texto vectorizado no está versionado

`generate_embeddings_pg.py` (línea ~71) y `ingest_incremental.py` (línea 247)
construyen el texto **de formas distintas**:

```python
# generate_embeddings_pg.py
COALESCE(title,'') || ' ' || COALESCE(description,'') || ' ' ||
COALESCE(array_to_string(keywords,' '),'') || ' ' ||
COALESCE(theme_label,'') || ' ' || COALESCE(territory_label,'')

# ingest_incremental.py
f"{title}. {description}. {keywords} {theme_label} {territory_label}"
```

Con puntos y comas en uno, sin ellos en el otro. **Los embeddings del catálogo
no son todos del mismo generador**, y no hay constancia de cuál produjo cada uno.

Propuesta: extraer la construcción a **una función única** en un módulo común,
usada por todos los generadores, y guardar en la tabla un campo
`embedding_source_hash` con el hash del texto vectorizado. Así se puede
comprobar por SQL qué fichas están desincronizadas, sin recalcular nada.

---

## 6. Lo que NO queda resuelto con esto

Fijar versiones **no arregla los embeddings ya guardados**. Sigue pendiente:

- Recalcular los 94.461 embeddings con el entorno fijado, para dejar el catálogo
  en un estado consistente.
- Añadir una prueba de regresión que rehaga 20 embeddings y exija coseno
  ≥ 0,9999 contra lo guardado, de forma que un build roto no pase inadvertido.

Nota honesta: **no se ha podido demostrar cuál de las librerías causó el
desajuste**, porque no hay copia del entorno anterior para comparar. Lo que está
demostrado es que *con el entorno actual los vectores guardados no se reproducen
desde los datos de la BD* (probadas 13 plantillas de texto y 9 combinaciones de
campos, ninguna llega a coseno 1,0), y que el `Dockerfile` **no garantiza que
mañana sea el mismo entorno**.

---

## 7. Cambios a aplicar (pendientes de revisión)

### 7.1 `Dockerfile.api`

```dockerfile
# ANTES
RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] psycopg2-binary pgvector python-dotenv \
    sentence-transformers numpy pyyaml requests scikit-learn scipy ollama

# DESPUÉS
COPY 07_Sprint5_Integracion/codigo/docker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cu130 \
    -r requirements.txt
```

### 7.2 Código

- Fijar `revision=e8f8c211226b894fcb81acc59f3b34ba3efd5f42` en las 5 cargas del
  modelo que entran en la imagen.
- Unificar la construcción del texto vectorizado en un módulo común.
- Excluir `historial/` y `*_backup*` del `COPY` de la imagen.

### 7.3 Orden recomendado

1. Aplicar el pinning (este fichero + `Dockerfile`).
2. Reconstruir la imagen y verificar que las 77 versiones se mantienen.
3. Fijar la revisión del modelo y **recalcular los 94.461 embeddings**.
4. Crear la prueba de regresión.

Sin el paso 3, seguir midiendo P@5 es medir sobre vectores cuyo origen no se
puede determinar.

---

## Anexo · cómo se generó `requirements.txt`

```bash
docker exec buscador_api pip freeze > entornos.txt   # 77 paquetes
# clasificados por función: directas / núcleo embedding / transitivas / CUDA
# verificados con scripts/86_verificar_requirements.py (comparación bidireccional)
```

El entorno de referencia es el contenedor `buscador_api`, imagen
`docker-api:latest` con ID `sha256:c09eb2fa61db…`, construida el **23-sep-2026
a las 11:04**. Es el entorno que produce las métricas que hay que defender, así
que es el que se fija.


---

## 8. Resultado de la aplicación (24-sep-2026)

### 8.1 Cambios aplicados

| fichero | cambio |
|---|---|
| `07_Sprint5_Integracion/codigo/docker/requirements.txt` | **nuevo** · 77 versiones fijadas |
| `07_Sprint5_Integracion/codigo/docker/Dockerfile.api` | instala desde `requirements.txt` |
| `main_v2_final_v07.py` · `routes_llm.py` · `routes_llm_v2.py` · `routes_v10.py` · `routes_llm_v2_backup.py` | `revision=MODEL_REVISION` |
| `generate_embeddings.py` · `generate_embeddings_pg.py` · `search_hybrid.py` · `search_engine.py` · `search_semantic.py` | idem |
| `routes_v10.py` | además, el modelo deja de recargarse en cada petición |

**10 ficheros** actualizados, 9 puntos de carga con revisión fijada. Las 4
cargas de `07_Sprint5_Integracion/codigo/api/historial/` se dejan como están:
no entran en la imagen.

### 8.2 Verificaciones

| comprobación | resultado |
|---|---|
| `requirements.txt` vs entorno instalado | **77/77 idénticas** |
| `pip freeze` tras reconstruir la imagen | **idéntico** al anterior |
| el modelo se carga con la revisión | `…@e8f8c211` en el log de arranque |
| coseno(nombre corto, nombre+revisión) | **0,9999999404** → mismo vector |
| health de la API | `200` |
| caso A (*patrimonio mundial UNESCO España*) | puesto **1** con 0,7440 |

El cambio es **neutro en comportamiento**: no altera ningún vector, solo elimina
la dependencia del puntero móvil `main`. La imagen anterior quedó etiquetada como
`docker-api:pre-pinning-2026-09-24` por si hay que volver atrás.

---

## 9. Diagnóstico del desajuste de embeddings (corregido)

Al aplicar el pinning se creó `scripts/88_regresion_embeddings.py` para tener una
referencia. El resultado **obligó a revisar el diagnóstico anterior**.

### 9.1 Nuevo dato que cambia la explicación

La prueba de regresión sobre las **100 últimas fichas** da:

```
coseno medio    : 1.00000
coseno minimo   : 1.00000
reproduccion exacta (>0,9999): 100/100
```

**Reproducen exactamente.** Eso descarta que el catálogo esté «generado con otro
modelo» de forma global.

### 9.2 La correlación real

> ⚠️ **RETIRADO 2026-09-28.** Esta «correlación» era un **artefacto de comparar
> contra el texto equivocado**: con textos largos el truncamiento a 128 tokens
> igualaba el prefijo de los dos textos (y por eso «reproducía»); con textos cortos
> entraba todo y la diferencia se veía. Con el texto correcto
> (`embedding_text` de la limpieza), **las fichas cortas reproducen a 0,9997**.
> Ver `docs/FASE-D-HALLAZGO-EMBEDDINGS.md` §2-3.

Muestreo sistemático de 300 fichas repartidas por todo el catálogo:

| condición | n | coseno medio | exactos |
|---|---|---|---|
| título+descripción **cabe** en 128 tokens | 264 | 0,92175 | 14/264 |
| título+descripción **no cabe** | 50 | **0,99408** | **43/50** |

Es decir: **cuando el texto se trunca, el vector se reproduce** (porque el
sufijo no llega a entrar y da igual cuál sea); cuando el texto es corto y entra
**entero**, no coincide.

Esto invierte la interpretación inicial: no es que «los textos largos
reproduzcan porque no se ven afectados», sino que **el sufijo del texto
vectorizado no es el que se reconstruye**.

### 9.3 Hipótesis probadas y descartadas

| hipótesis | prueba | resultado |
|---|---|---|
| modelo distinto | 9/60 y 100/100 exactos | **descartada** |
| dos épocas cronológicas | dispersión por todo el rango | **descartada** |
| el arreglo de `territory_label` | texto con valores de `raw_metadata` | **descartada** |
| un campo que falta (7 campos × 128 combinaciones) | fuerza bruta | **ninguna reproduce** |
| el sufijo es `tags`/`url`/`license`/`content_text`… | uno a uno | **ninguno mejora** |

Sobre 30 fichas cortas que fallan:

| variante | coseno medio |
|---|---|
| texto actual | 0,97569 |
| texto con valores de `raw_metadata` | 0,94237 |
| solo título + descripción | 0,90960 |

El texto actual es el que más se acerca (0,9757) pero **no llega a 1,0**, y
todos **coinciden en `created_at` = 2026-05-24 y `updated_at` = 2026-09-23**.

### 9.4 Lo que queda establecido

1. **El modelo es el mismo.** Cien fichas reproducen exactamente.
2. **El truncamiento a 128 tokens está confirmado** y explica por qué las fichas
   largas son insensibles al sufijo.
3. **En las fichas cortas hay un desajuste no identificado** entre el texto que
   se reconstruye y el que se vectorizó. No es el modelo, no es un campo que
   falte, no es el arreglo de metadatos.
4. Las fichas afectadas **concentran `updated_at` en 2026-09-23**, el día del
   arreglo de metadatos de producción.

### 9.5 Consecuencia práctica

⚠️ **CORREGIDO 2026-09-28 — ver `docs/FASE-D-HALLAZGO-EMBEDDINGS.md`.**

La causa raíz **sí se identificó** y este apartado queda superado:

- Los vectores se generaron desde el campo **`embedding_text`** de la limpieza
  (`clean_datasets.py:468-477`), **no** con la concatenación del script de
  embeddings. Con el texto correcto las fichas cortas reproducen a **0,9997**.
- El «desajuste de las fichas cortas» era un **artefacto de comparar contra el
  texto equivocado** (§9.2 queda retirada): con textos largos el truncamiento a 128
  tokens igualaba el prefijo de ambos textos y parecía «reproducir».
- **No hace falta recalcular para arreglarlo**: el 92,8 % del catálogo ya reproduce.
  Reconstruir el texto desde la BD da 0,923, así que recalcular con esa aproximación
  **degradaría** los 87.661 vectores buenos.

Lo que sí procede:

1. **Añadir una columna `embedding_text`** y poblarla en la ingesta: hoy el texto
   vectorizado **no se guarda**, y por eso no es reproducible al 100 %. Es la
   corrección estructural.
2. Corregido el texto que vectoriza `generate_embeddings_pg.py` (usaba `theme_label`,
   que contiene el **URI** en el 95 % de las fichas) y un bug de guardado que
   impedía escribir el vector (`malformed vector literal`).
3. Integrar `88_regresion_embeddings.py` como comprobación tras cada build.
