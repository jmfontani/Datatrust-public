# Descarga de datasets tabulares

Descarga selectiva del contenido real de los datasets de datos.gob.es para
alimentar el caso de uso #15 (respuesta data-aware con escalada bajo
demanda). Solo se descargan **ficheros tabulares** (CSV > JSON > XLSX > XLS > TXT)
y, por dataset, **una sola distribución** (la más sencilla de procesar).

## Cifras del corpus (medido)

- 87.676 datasets únicos (dedup por `identifier`).
- 37.974 (43%) tienen al menos una distribución tabular → 37.974 descargas.
- ~15–40 GB estimados; cap por fichero 100 MB (descarta la cola patológica).
- 139 hosts distintos; `access_url` al 100%, `download_url` al 0%.

## Pipeline

```
raw/*.jsonl ──▶ build_manifest.py ──▶ manifest.csv (37.974 pending)
                                          │
                                          ▼
                                 download_datasets.py ──▶ ~/datos/{csv,json,xlsx,xls,txt}/
                                          │
                                          ├──▶ inaccesibles.csv   (no descargables + reason)
                                          ├──▶ download_progress.jsonl (1 línea por item)
                                          └──▶ manifest.csv (status actualizado)
```

## Uso

### 1. Manifiesto

```bash
cd 03_Sprint1_Ingesta/codigo/descarga_datos
venv/bin/python build_manifest.py           # usa ../datos/raw por defecto
```

### 2. Muestra de validación (recomendado antes del masivo)

```bash
venv/bin/python download_datasets.py --shuffle --limit 300 \
  --progress download_progress.jsonl.sample --inaccesibles inaccesibles_sample.csv
```

Revisar `muestra_300.log`: tasa de HTML/fallos, tamaño real vs `byte_size`,
hosts problemáticos. Ajustar `--per-host` / `--workers` si hace falta.

### 3. Descarga completa (reanudable)

```bash
venv/bin/python download_datasets.py
# si corta, relanzar el mismo comando retoma solo los status=pending
```

### 4. Reintentar inaccesibles transitorios

Los `reason` transitorios (TIMEOUT, HTTP_5XX, HTTP_429, CONN_ERROR) se
reintentan en otra ventana horaria:

```bash
venv/bin/python download_datasets.py --retry-inaccessible
```

Los permanentes (HTTP_404/403, HTML_LANDING, BADFORMAT, OVERSIZE) no se
reintentan: se atienden por nivel 1 (respuesta solo con metadatos).

## Flags

| Flag | Default | Descripción |
|---|---|---|
| `--manifest` | `manifest.csv` | Manifiesto de entrada/salida |
| `--dest` | `~/datos` | Raíz de destino |
| `--workers` | 24 | Hilos concurrentes globales |
| `--per-host` | 3 | Concurrencia máxima por host (educación vial) |
| `--cap-mb` | 100 | Cap por fichero en MB |
| `--limit N` | 0 (todos) | Procesar solo N items |
| `--shuffle` | off | Aleatoriza pending (semilla 42) para muestreo representativo |
| `--only-host X` | — | Procesar solo un host |
| `--retry-inaccessible` | off | Reabre los de `inaccesibles.csv` para reintento |
| `--dry-run` | off | Solo lista items sin descargar |

## Razones de inaccesibilidad (`reason`)

| Reason | Tipo | Reintentable |
|---|---|---|
| `HTML_LANDING` | la URL es una página HTML, no un fichero | no (permanente) |
| `HTTP_4XX` | 404/403/401… | no |
| `HTTP_5XX` | 500/502/503… | sí |
| `HTTP_429` | rate limit | sí |
| `TIMEOUT` | connect/read timeout | sí |
| `CONN_ERROR` | DNS/refused/SSL | sí |
| `REDIRECT_LOOP` | demasiadas redirecciones | sí |
| `BADFORMAT` | magic bytes no casan con el formato | no |
| `OVERSIZE` | supera cap en disco | no |
| `OTHER` | cualquier otra | depende |

## Entregables

- `manifest.csv` — estado de los 37.974 (`done` / `inaccesible` / `pending`).
- `inaccesibles.csv` — datasets no descargables con `reason`, `access_url`, `identifier`.
- `download_progress.jsonl` — una línea JSON por item procesado.
- `informe_descarga.md` — resumen final (generado tras la descarga masiva).

## Notas

- `byte_size` es auto-reportado (33% de cobertura); el tamaño real se
  confirma en la muestra y en el informe final.
- exFAT no admite `:` en nombres; los `identifier` (algunos son URIs) se
  sanean con `safe_name()` (solo `[A-Za-z0-9._-]`, recorte + hash si >150).
- El descargador respeta `Retry-After` en 429 y backoff exponencial en 5xx.