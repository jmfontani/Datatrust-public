# Integración de `proyecto/` en Datatrust

> **Nota:** Este documento es histórico. Para información actualizada sobre estrategia de ramas y evolución del proyecto, ver [ESTRATEGIA_GIT.md](ESTRATEGIA_GIT.md) y [NARRATIVA_TFM.md](NARRATIVA_TFM.md).

---

**Fecha:** 2026-05-22  
**Acción:** Consolidación de la carpeta `PFM/proyecto/` en la estructura EOI de `Datatrust/`

## Origen
La carpeta `PFM/proyecto/` contenía el desarrollo inicial (ingesta, arquitectura base, config) iniciado el 2026-05-20. Se integra ahora en la estructura oficial de fases EOI.

## Mapeo de archivos

### Origen → Destino

| Archivo/Carpeta Origen | Destino en Datatrust | Fase EOI | Notas |
|------------------------|-----------------------------------|----------|-------|
| `src/ingestion/ingest_datos_gob.py` | `03_Sprint1_Ingesta/codigo/conectores/ingest_datos_gob.py` | Sprint 1 | Script de ingesta original (datos.gob.es) |
| `src/ingestion/ingest_datos_gob_v2.py` | `03_Sprint1_Ingesta/codigo/conectores/ingest_datos_gob_v2.py` | Sprint 1 | Versión con lógica anti-duplicados |
| `src/ingestion/test_api.py` | `03_Sprint1_Ingesta/codigo/conectores/test_api.py` | Sprint 1 | Test de conectividad API |
| `src/ingestion/README_INGESTA.md` | `03_Sprint1_Ingesta/codigo/conectores/README.md` | Sprint 1 | Documentación de la ingesta |
| `data/raw_v2/` (batches .jsonl) | `03_Sprint1_Ingesta/datos/raw/` | Sprint 1 | Datos descargados: **134.150 datasets** (22 batches) |
| `data/raw_v2/.ingest_state_v2.json` | `03_Sprint1_Ingesta/datos/raw/.ingest_state.json` | Sprint 1 | Estado de reanudación |
| `data/raw_v2/ingest_v2.log` | `03_Sprint1_Ingesta/datos/raw/ingest.log` | Sprint 1 | Logs de la ingesta |
| `docs/ARQUITECTURA.md` | `99_Compartido/recursos/ARQUITECTURA.md` | Compartido | Documento de arquitectura general |
| `docs/DATOS_GOB_ES.md` | `03_Sprint1_Ingesta/docs/ficha_tecnica_datos_gob_es.md` | Sprint 1 | Ficha técnica de la fuente de datos |
| `config/settings.yaml` | `99_Compartido/herramientas/config_proyecto.yaml` | Compartido | Configuración del proyecto |
| `requirements.txt` | `99_Compartido/herramientas/requirements.txt` | Compartido | Dependencias Python |
| `README.md` (raíz) | `README.md` (raíz Datatrust) | Compartido | README principal actualizado |
| `src/api/__init__.py` | `06_Sprint4_Chatbot/codigo/api_rest/__init__.py` | Sprint 4 | Placeholder API (vacío) |
| `src/frontend/__init__.py` | `06_Sprint4_Chatbot/codigo/frontend/__init__.py` | Sprint 4 | Placeholder frontend (vacío) |
| `src/search/__init__.py` | `05_Sprint3_Busqueda_UI/codigo/__init__.py` | Sprint 3 | Placeholder búsqueda (vacío) |

## Estado de la ingesta (después de integración)
- **Datasets totales:** 134.150
- **Batches:** 22 archivos .jsonl
- **Errores:** 0
- **Estado:** Completado (`completed: true`)
- **API usada:** Linked Data API de datos.gob.es
- **Formato:** JSONL con metadatos normalizados (DCAT-AP)

## Siguientes pasos
1. **Sprint 1 — Ingesta (CONTINÚA):** Limpieza de datos, normalización de campos, generación de `embedding_text`
2. **Sprint 2 — Embeddings:** Generar vectores con sentence-transformers
3. **Sprint 3 — Búsqueda:** Motor híbrido (semántico + léxico)
4. **Sprint 4 — Chatbot/Frontend:** API REST + interfaz de usuario
5. **Sprints 5-8:** Evaluación, integración, documentación, defensa

## Decisiones pendientes de la fase 01 (Empatizar/Definir)
- ✅ Los usuarios prefieren **lista de resultados** sobre chatbot (4/5)
- ✅ **No** se implementará chatbot conversacional; se prioriza búsqueda semántica con filtros facetados
- ⏳ Definir dataset de benchmark (25-30 queries para evaluación)

## Notas técnicas
- Los scripts de ingesta usan **solo librerías estándar de Python** (sin dependencias externas)
- Rate limiting: 0.5s entre requests
- Retry automático con backoff exponencial
- La v2 incluye deduplicación por `identifier`
