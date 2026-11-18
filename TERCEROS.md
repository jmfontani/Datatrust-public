# Material de terceros y exclusiones de licencia

DataTrust se publica con dos licencias propias —**AGPL-3.0-or-later** para el código
([`LICENSE`](LICENSE)) y **CC BY 4.0** para la documentación ([`LICENSE-docs`](LICENSE-docs))—
pero **no todo lo que hay en el repositorio es del equipo**. Este fichero enumera lo que
conserva su licencia original para que nadie atribuya al equipo derechos que no tiene.

## 1. Artículos y publicaciones académicas

`docs/research/pdfs/` contiene los artículos citados en
[`docs/BIBLIOGRAFIA.md`](docs/BIBLIOGRAFIA.md) y en `docs/research/FUNDAMENTACION_BIBLIOGRAFICA.md`:
40 PDFs en el repositorio privado y 20 en la publicación. Son **obras de sus autores**, la
mayoría con identificador arXiv, y se incluyen únicamente como referencia bibliográfica.

No se relicencian. Cada fichero se rige por la licencia que declare su editor o sus autores
(arXiv dispone de una licencia no exclusiva de distribución; los PDFs de revistas y congresos
conservan el copyright editorial, y en varios casos solo permiten el autoarchivo del preprint).
Para reutilizar su contenido hay que acudir a la fuente original.

## 2. Material docente de EOI

El repositorio de trabajo incluye la carpeta `metodologia/` con las guías del máster. Es
material de EOI y **no se publica**: no forma parte del repositorio público y no está bajo
AGPL ni CC BY.

Al menos uno de esos documentos, *Claves del proyecto* (Valvanera Castro), declara en su
primera página **CC BY-NC-SA 4.0** —uso no comercial y compartir igual—, que es incompatible
con relicenciarlo aquí. El resto conserva los derechos de EOI.

## 3. Datos del Catálogo Nacional de Datos Abiertos

Los metadatos y los ficheros del catálogo **pertenecen a sus respectivos publicadores** y se
rigen por la licencia de cada conjunto, consultable en [datos.gob.es](https://datos.gob.es).
El catálogo agrega administraciones con condiciones distintas (buena parte en CC BY 4.0, pero
no todas).

Consecuencias prácticas:

- El corpus descargado (CSV, JSON, XLSX) —unos 64 GB— **no está en el repositorio**: vive en
  el disco de trabajo y se regenera con el pipeline de `03_Sprint1_Ingesta`.
- Las muestras y agregados versionados (`benchmark_test_*`, `metadata_audit.csv`, perfiles
  TL;DR) son derivados; su reutilización queda sujeta a la licencia del conjunto de origen.
- El ground truth anotado a mano (`gt_etiquetas_v6.json`) y los criterios de evaluación **sí
  son obra del equipo** y van bajo CC BY 4.0.

## 4. Modelos y servicios de terceros

| Componente | Licencia |
|---|---|
| BAAI/bge-m3 (embeddings en producción) | MIT |
| sentence-transformers/all-MiniLM-L6-v2 (fallback) | Apache-2.0 |
| Modelos de LLM vía API (DeepSeek, Nemotron, Qwen) | Términos de cada proveedor; no se redistribuyen pesos |
| Dependencias de Python (`requirements.txt`) | Las de cada paquete |
| Imágenes de contenedor (PostgreSQL 15, pgvector, Python slim, nginx) | Las de cada imagen base |

Los pesos de los modelos **no se versionan** en este repositorio: se descargan del Hub, y su
licencia es la del modelo, no la del proyecto.

## 5. Marcas y logotipos

Los nombres y logotipos de **EOI**, **Red.es**, **datos.gob.es** y **Gobierno de España** son
marcas de sus titulares. Su aparición en la memoria, en las presentaciones o en capturas de
pantalla es **uso descriptivo** del contexto del proyecto y no implica cesión de marca ni
respaldo. Las licencias del proyecto no conceden derecho alguno sobre ellos.

El logotipo propio del buscador (`99_Compartido/recursos/logo_buscador_semantico.svg`, y sus
copias en `15_Frontends/*/assets/`) sí es del equipo y va bajo AGPL-3.0-or-later junto con el
código que lo acompaña.

## 6. Capturas de pantalla y figuras

Las capturas del producto y las figuras generadas por el equipo (`figuras/*.png`,
`docs/diagrama_datatrust.svg`) son obra propia y van bajo CC BY 4.0, con una salvedad: si una
captura muestra datos o interfaces de terceros, esos elementos conservan su licencia.

## Cómo citar

    Equipo 2 (2026). DataTrust — Buscador semántico sobre el Catálogo Nacional de Datos
    Abiertos. TFM del Máster en IA y Ciencia de Datos, EOI.
    https://github.com/jmfontani/Datatrust-public
    Código: AGPL-3.0-or-later · Documentación: CC BY 4.0

La autoría individual del equipo consta en la memoria del TFM.
