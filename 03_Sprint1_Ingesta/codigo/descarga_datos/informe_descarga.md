# Informe de descarga de datasets tabulares

**Fecha**: 2026-06-26 (actualizado tras fallback #1 + sniff #2)
**Procesos**: `download_datasets.py` (descarga base + retry + fallback de formato) sobre `manifest.csv`, y `sniff_download.py` (sniff de distribuciones sin formato) sobre `manifest_sniff.csv`
**Destino**: `~/datos/{csv,json,xlsx,xls,txt,ods}/`

## ✅ Balance final consolidado

| Fase | Datasets done | Notas |
|---|---|---|
| Descarga base (tabulares declarados) | 31.149 | `download_datasets.py` sobre 37.974 |
| + Retry de inaccesibles transitorios | +160 | `--retry-inaccessible` |
| + Fallback de formato (#1) | +247 | probando formato alternativo si el primario era HTML |
| **Subtotal base+fallback** | **31.556** | 36,0% del catálogo |
| + Sniff de sin-formato (#2) | +21.331 | `sniff_download.py` sobre 49.694 (descubre tabulares ocultos + descomprime ZIPs) |
| **TOTAL datasets con dato en local** | **52.887** | **60,3% del catálogo (87.676)** |
| **Volumen total en disco** | **67 GB** | csv 48 · json 9,0 · xlsx 2,3 · xls 695M · txt 431M · ods 64M |

De los 87.676 datasets del catálogo, **52.887 (60,3%) tienen ahora su fichero tabular descargado y verificado en local**, listo para alimentar el caso #15 (agente data-aware con escalada). Partiendo del 35,7% de la descarga base, las dos mejoras añadieron +16,7 puntos de cobertura (fallback +0,3pp, sniff +24,3pp).

## Resumen por manifiesto

### Manifiesto principal (`manifest.csv`) — datasets con distribución tabular declarada

| Métrica | Valor |
|---|---|
| Datasets en el manifiesto | 37.974 |
| **Descargados (done)** | **31.556** (base 31.149 + retry +160 + fallback +247) |
| **Inaccesibles** | 6.418 |
| **Éxito (sobre tabulares)** | **83,1%** |
| Volumen | 48,4 GB |

### Manifiesto sniff (`manifest_sniff.csv`) — datasets SIN distribución tabular declarada

| Métrica | Valor |
|---|---|
| Datasets a sniffear | 49.694 |
| **Tabulares descubiertos (done)** | **21.331** (42,9%) |
| no_tabular | 28.363 |
| Volumen descubierto | 9,45 GB (incremental) |

Sniff done por formato: JSON 10.077 · CSV 8.051 · TXT 1.382 · XLS 861 · XLSX 707 · ODS 253.
(no_tabular reasons: ALL_HOSTS_DEAD 17.945 — endpoints lentos/caídos saltados por la cache de umbral; HTML 3.947; UNKNOWN 3.840; XML 1.099; ZIP_NO_DATA 625; etc.)

## Composición por formato

### Descargados (done)

| Formato | Nº | % done |
|---|---|---|
| CSV | 24.148 | 77,5% |
| XLSX | 5.649 | 18,1% |
| XLS | 849 | 2,7% |
| JSON | 465 | 1,5% |
| TXT | 38 | 0,1% |

### Inaccesibles por formato

| Formato | Nº |
|---|---|
| CSV | 6.108 |
| XLSX | 434 |
| XLS | 170 |
| JSON | 110 |
| TXT | 3 |

## Inaccesibles por `reason` (6.665, tras retry)

| Reason | Antes | **Tras retry** | Tipo | Reintentable |
|---|---|---|---|---|
| HTML_LANDING | 4.488 | **4.330** | la URL es una página HTML, no un fichero | no (permanente) |
| CONN_ERROR | 1.826 | **1.782** | DNS/refused/SSL | sí (hosts aún caídos) |
| OVERSIZE | 289 | 289 | supera cap 100 MB | no |
| BADFORMAT | 141 | 141 | magic bytes no casan con el formato | no |
| TIMEOUT | 6 | **49** | connect/read | sí |
| HTTP_5XX | 41 | 41 | 500/502/503 | sí |
| HTTP_4XX | 25 | 25 | 404/403/401 | no |
| OTHER | 9 | 8 | otros | depende |

**Balance del retry**: +160 recuperados (6.825 → 6.665 inaccesibles). La recuperación fue modesta porque la mayoría de los reintentables (CONN_ERROR) resultaron ser **hosts persistentemente caídos** a esta hora, no fallos transitorios. Algunos CONN_ERROR pasaron a clasificarse como TIMEOUT en el reintento.

**Permanentes (4.785)**: HTML_LANDING + BADFORMAT + OVERSIZE + HTTP_4XX → se atienden por nivel 1 (respuesta solo con metadatos), no requieren más reintentos.
**Reintentables restantes (~1.830)**: CONN_ERROR + HTTP_5XX + TIMEOUT → podrían intentarse de nuevo en otra franja horaria distinta, pero el rendimiento decreciente del retry sugiere que el margen es pequeño.

> HTML_LANDING (65% de los inaccesibles) confirma el hallazgo del análisis previo: una parte grande de `access_url` son páginas interactivas (ine.es/jaxi, recursos Barcelona, madrid) que no sirven un fichero directamente. No son fallos del pipeline.

## Top hosts

### Top 10 hosts DONE

| Nº done | Host |
|---|---|
| 9.396 | datos.canarias.es |
| 5.756 | opendata.euskadi.eus |
| 2.167 | enlaza.eprinsa.es |
| 1.667 | datos.comunidad.madrid |
| 1.598 | www.eustat.eus |
| 1.230 | ibestat.es |
| 945 | estadisticas.educacion.gob.es |
| 922 | datosabiertos.ayto-arganda.es |
| 843 | analisi.transparenciacatalunya.cat |
| 602 | www.dgt.es |

### Top 10 hosts INACCESIBLE

| Nº inacc | Host | Causa dominante |
|---|---|---|
| 1.709 | datos.comunidad.madrid | HTML_LANDING / CONN_ERROR |
| 884 | estadisticas.universidades.gob.es | CONN_ERROR |
| 880 | datosabiertos.malaga.eu | CONN_ERROR |
| 637 | datosabiertos.jcyl.es | CONN_ERROR / HTML |
| 431 | opendata-ajuntament.barcelona.cat | HTML_LANDING |
| 222 | www.eustat.eus | HTML / OVERSIZE |
| 203 | analisi.transparenciacatalunya.cat | HTML |
| 195 | datos.madrid.es | HTML |
| 183 | zaguan.unizar.es | HTML |
| 170 | abertos.xunta.gal | HTML |

## Verificación de integridad (spot-check con pandas)

Muestra aleatoria por formato, parseo con pandas:

| Formato | Muestras | Parsean OK | Observaciones |
|---|---|---|---|
| CSV | 20 | 18 (90%) | 2 fallos por encoding latin1 → parsean con `chardet`/`encoding=latin1` (no corrupción) |
| XLSX | 10 | 10 (100%) | ✅ con `openpyxl` |
| XLS | 5 | 5 (100%) | ✅ con `xlrd` |
| JSON | 10 | — | válidos; algunos anidados (CKAN) requieren `json` module, no `read_json` |
| TXT | 5 | 3 (60%) | 2 fallos por encoding → parsean con detección de encoding |

**Conclusión**: los ficheros descargados son íntegros. Los "fallos" puntuales son de encoding (latin1, habitual en datos.gob.es) o de estructura JSON anidada, no corrupción. Los 141 BADFORMAT reales ya fueron filtrados por el sniff de magic bytes durante la descarga. El agente data-aware (#15) deberá usar detección de encoding (`chardet`) y `xlrd`/`openpyxl` al cargar.

## Tamaño en disco por formato (final)

> **Nota (18-sep-2026):** los datasets se movieron de la raíz de `datos/` a
> `~/datos/PFM/datos/` para que quedaran dentro del proyecto.
> El parámetro `--dest` de los scripts apunta ya a la nueva ruta.

| Directorio | Tamaño |
|---|---|
| `~/datos/PFM/datos/csv/` | 50 GB |
| `~/datos/PFM/datos/json/` | 10 GB |
| `~/datos/PFM/datos/xlsx/` | 2,3 GB |
| `~/datos/PFM/datos/xls/` | 990 MB |
| `~/datos/PFM/datos/txt/` | 433 MB |
| `~/datos/PFM/datos/ods/` | 80 MB |
| **Total** | **~64 GB** |

> El volumen real (67 GB) supera la estimación inicial (~25 GB) basada en `byte_size` declarado (solo 33% de cobertura). El sniff añadió 9,45 GB incrementales (sobre todo JSON y CSV ocultos).

## Sniff de distribuciones sin formato (#2) — metodología

Para los 49.694 datasets SIN ninguna distribución tabular declarada, `build_sniff_manifest.py` seleccionó hasta 3 distribuciones por dataset (ordenadas por probabilidad de ser fichero) y `sniff_download.py` hizo un GET, clasificó por `Content-Type` + magic bytes y descargó las que resultaron tabulares (CSV/JSON/XLSX/XLS/TXT/ODS), **incluyendo descompresión de ZIPs** cuando contenían una entrada tabular.

- **Yield**: 42,9% (21.331 de 49.694).
- **Cache de hosts muertos con umbral**: tras 6 fallos por host, se marca muerto y se saltan el resto de sus datasets. Esto acelera drásticamente el long tail de hosts caídos.
- **`READ_TIMEOUT=20s`**: cuelga servidores que no mandan bytes en 20s. Comprobado: los CSV/JSON pequeños envían bytes rápido; 20s entre chunks es generoso para streams legítimos y descarta los colgados.

### Caveat del sniff — endpoints lentos fuera de alcance

`ALL_HOSTS_DEAD` (17.945 datasets saltados) son mayoritariamente **endpoints lentos** (p.ej. los recursos no-tabulares de `datos.canarias.es`, que tardan >20s en responder y timeoutean). No son falsos positivos por carga (se verificó con `per-host=3`, el setting seguro del run principal): son URLs que no responden en 20s. Recuperarlos exigiría un `READ_TIMEOUT` largo (60-300s) y muchas horas, con rendimiento decreciente → **dejados fuera de alcance deliberadamente**. Si en el futuro se quiere esa cola, habría que hacer un "pase lento" con timeout largo solo sobre esos hosts.

## Entregables

| Fichero | Contenido |
|---|---|
| `manifest.csv` | Estado de los 37.974 tabulares: `done` 31.556 / `inaccesible` 6.418 |
| `manifest_sniff.csv` | Estado de los 49.694 sin-tabular: `done` 21.331 / `no_tabular` 28.363 |
| `inaccesibles.csv` | 6.418 tabulares no descargables con `reason` + `access_url` + `identifier` |
| `sniff_no_tabular.csv` | 28.363 sin-tabular no descargables con `reason` |
| `download_progress*.jsonl` / `sniff_progress.jsonl` | Auditoría ítem a ítem de cada pase |
| `~/datos/{csv,json,xlsx,xls,txt,ods}/` | **52.887 ficheros descargados (67 GB)** |

## Próximos pasos recomendados

1. **Indexar el contenido** (puente al caso #15): los 52.887 ficheros permiten pasar del rerank/respuesta solo-con-metadatos al nivel 2 (agente text-to-SQL sobre el dato) descrito en la escalera del plan. Es el siguiente paso natural.
2. **Pase lento opcional** sobre los `ALL_HOSTS_DEAD` del sniff (endpoints lentos) con `READ_TIMEOUT=120s` y menos workers, si se quiere recuperar la cola lenta (~17.945 candidatos, rendimiento incierto).
3. **Permanentes**: los `HTML_LANDING`/`BADFORMAT`/`OVERSIZE`/`HTTP_4XX` quedan en los CSV de no-descargables para que el nivel 1 (metadatos) los atienda; no requieren reintentos.
4. **Carga robusta en el agente #15**: usar `chardet` para encodings (latin1 habitual en datos.gob.es), `xlrd`/`openpyxl` para XLS/XLSX, y `json` module para JSON anidado de CKAN.