# Historial del API — Buscador Semántico

**Carpeta de archivo histórico**  
**Fecha:** 2026-06-03

Esta carpeta contiene las **4 versiones intermedias** del backend API que precedieron al `main_v2_final_v07.py` actual (que vive en `08_Sprint6_LLM_Mejora/codigo/api/`).

## ¿Por qué existen?

Cada versión refleja una iteración del Sprint 7 (Integración). Se preservan como **documentación de proceso** para:

1. **Memoria del TFM (Cap. 6 — Implementación):** mostrar la evolución del diseño y las decisiones iterativas.
2. **Trazabilidad:** ante una pregunta del tribunal del tipo "¿por qué lo hicisteis así?" se puede mostrar el camino.
3. **Trabajo futuro:** si hay que revertir algún cambio, las versiones anteriores son accesibles.

## Versiones

| Archivo | Versión | Tamaño (líneas) | Mejora clave sobre la anterior |
|---------|---------|------------------|-------------------------------|
| `main_v2_v1_inicial.py` | v1 (inicial) | 436 | Primera versión con PostgreSQL+pgvector |
| `main_v2_v2_fixed.py` | v2 (fixed) | 463 | Embeddings reales con sentence-transformers |
| `main_v2_v3_improved.py` | v3 (improved) | 624 | Stop words, validación semántica, fallback ambiguas |
| `main_v2_v3_improved_backup.py` | v3 (backup) | 624 | Backup de seguridad antes de "final" |
| **`main_v2_final_v07.py`** (en `08_Sprint6_LLM_Mejora/`) | final | 865 | Todas las mejoras + integraciones con LLM (Sprint 6) |

## Cómo se relacionan con el actual

El archivo canónico en ejecución es `08_Sprint6_LLM_Mejora/codigo/api/main_v2_final_v07.py` (865 líneas, ~20 líneas más que `main_v2_final.py` original del Sprint 7, con las integraciones del Sprint 6 LLM).

**No ejecutar estos archivos** sin entender qué versión es: cada uno registra un módulo `main_v2` con un nombre distinto (`main_v2`, `main_v2_fixed`, `main_v2_improved`), por lo que técnicamente se pueden ejecutar, pero representan estados obsoletos del sistema.
