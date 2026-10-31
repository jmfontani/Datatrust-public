# 99_Compartido

**Carpeta de recursos y configuración centralizados**  
**Origen:** consolidación de `PFM/proyecto/` (2026-05-22)  
**Recuperado:** 2026-06-03 del backup histórico

Esta carpeta centraliza archivos que son transversales a múltiples sprints.

## Contenido

| Subcarpeta | Contenido |
|------------|-----------|
| `herramientas/` | Configuración técnica del proyecto (YAML, requirements) |
| `recursos/` | Documentos de arquitectura y referencias compartidas |

## Estado actual

⚠️ **El proyecto ha evolucionado significativamente** desde la creación de esta carpeta (2026-05-22). Los archivos aquí son **punto de partida histórico**, no configuración canónica.

- `herramientas/requirements.txt`: versión de mayo 2026, **anterior** al estado actual del proyecto. Las dependencias reales están en `venv/` y pueden haber cambiado. Usar como referencia, no como verdad.
- `herramientas/config_proyecto.yaml`: configuración del proyecto al 2026-05-22 (cuando el proyecto tenía 113.313 datasets de datos.gob.es). **NO refleja el estado actual** (134.150 ingestados, 87.676 limpios, 41 tests, RAGAS en planificación).
- `docs/ARQUITECTURA.md`: diagrama de componentes al cierre del Sprint 7. Sigue siendo válido como referencia de arquitectura general.

## Documentos de origen

- `docs/HISTORIAL_INTEGRACION.md` (en raíz `docs/`): log de la consolidación inicial de 2026-05-22, cuando se fusionó `PFM/proyecto/` en `Datatrust/`.
