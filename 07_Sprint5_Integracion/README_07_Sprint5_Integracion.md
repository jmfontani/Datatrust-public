# Fase 07 - Sprint 5: Integración y Despliegue

## 📋 Resumen

Migración completa del backend desde NumPy en memoria a PostgreSQL + pgvector, con Dockerización y **nueva versión pública del frontend** diseñada para usuarios finales.

## 🎯 Objetivos

- [x] Migrar datos de NumPy/JSONL a PostgreSQL + pgvector
- [x] Adaptar motor de búsqueda para usar PostgreSQL
- [x] Crear schema con índices HNSW y GIN
- [x] Scripts de setup automatizado
- [x] Documentación de despliegue
- [x] Tests de integración
- [x] **Nueva versión pública del frontend** (interfaz limpia para usuarios finales)

## ✅ Estado: COMPLETADO

Implementado el 2026-05-24. Última actualización: 2026-05-25 (nueva versión pública del frontend).

---

## 🆕 Versión Pública del Frontend (Nuevo)

### Dos Interfaces Disponibles

| Versión | URL | Descripción | Público |
|---------|-----|-------------|---------|
| **Pública** (por defecto) | `http://localhost:8501` | Interfaz limpia, sin controles técnicos | Ciudadanos, periodistas, investigadores |
| **Avanzada** | `http://localhost:8501?mode=advanced` | Controles técnicos completos | Desarrolladores, admins |

### Características Versión Pública

#### Diseño
- ✅ **Header minimalista**: "🔍 Datos Abiertos"
- ✅ **Barra de búsqueda estilo Google**: Redondeada, sombra suave
- ✅ **Búsquedas populares**: Chips rápidos (Empleo, Educación, etc.)
- ✅ **Sin sidebar técnico**: Interfaz limpia y centrada

#### Funcionalidad
- ✅ **Búsqueda con Enter**: Funciona directamente al pulsar Enter
- ✅ **Filtros desplegables**: Todas las opciones disponibles (territorio, categoría)
- ✅ **Relevancia visual**: Estrellas ⭐⭐⭐⭐⭐ en lugar de scores numéricos
- ✅ **Indicador de tipo de enlace**:
  - 📥 Archivo descargable directo (CSV, XLSX, PDF, etc.)
  - 🌐 Página web donde buscar el dataset
- ✅ **Formatos disponibles**: Muestra todos los formatos (CSV, PDF, JSON...)
- ✅ **Metadatos simplificados**: Título, descripción, publisher, ubicación

#### UX Mejorada
- ✅ Responsive (móvil y desktop)
- ✅ Estados vacíos amigables
- ✅ Sin controles técnicos (pesos optimizados automáticamente)

---

## 📁 Estructura

```
07_Sprint5_Integracion/
├── codigo/
│   ├── db/
│   │   ├── init.sql                    # Schema PostgreSQL + pgvector
│   │   ├── migrate_from_numpy.py       # Migración de datos
│   │   └── update_metadata_fixed.py    # Actualización de metadatos
│   ├── motor/
│   │   └── search_engine_pgvector.py   # Motor adaptado a PostgreSQL
│   ├── api/                            # API REST (FastAPI)
│   ├── frontend_v2/                    # Frontend V2 (Streamlit)
│   │   ├── app.py                      # Versión avanzada (técnica)
│   │   ├── app_public.py               # ✅ Versión pública (nueva)
│   │   ├── app_router.py               # ✅ Router entre versiones
│   │   ├── components_v2.py            # Componentes versión avanzada
│   │   ├── components_public.py        # ✅ Componentes versión pública
│   │   └── utils_v2.py                 # Utilidades compartidas
│   ├── setup.sh                        # Script de setup automatizado
│   └── setup_no_docker.sh              # Script alternativo sin Docker
├── docs/
│   ├── DESPLIEGUE.md                   # Guía completa de despliegue
│   ├── NOTA_EJECUCION.md               # Notas sobre ejecución
│   ├── ESTADO_FINAL.md                 # Estado final actualizado
│   └── arquitectura/
│       └── DIAGRAMA_COMPONENTES.md     # Diagrama de arquitectura
└── entregables/
    └── resumen_fase07.md               # Resumen ejecutivo completo
```

---

## 🗄️ Arquitectura PostgreSQL + pgvector

### Schema

```sql
-- Tabla principal
datasets (
    id SERIAL PRIMARY KEY,
    dataset_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT,
    description TEXT,
    publisher VARCHAR(500),
    theme VARCHAR(255),
    territory VARCHAR(255),
    format VARCHAR(50),
    embedding VECTOR(384),           -- Embeddings semánticos
    search_vector TSVECTOR,          -- Índice de texto para búsqueda léxica
    raw_metadata JSONB,              -- Metadatos originales
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Índices clave
CREATE INDEX idx_embedding_hnsw ON datasets USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_search_vector ON datasets USING GIN(search_vector);
CREATE INDEX idx_theme ON datasets(theme);
CREATE INDEX idx_territory ON datasets(territory);
```

### Comparación: NumPy vs PostgreSQL

| Aspecto | NumPy (Fase 05) | PostgreSQL + pgvector |
|---------|-----------------|----------------------|
| **Persistencia** | En memoria (volátil) | Persistente en disco |
| **Concurrencia** | 1 usuario | Múltiples usuarios |
| **Escalabilidad** | Limitada a RAM | Escalable verticalmente |
| **Búsqueda** | Lineal O(n) | HNSW O(log n) |
| **Backups** | Manual | Automático (pg_dump) |
| **Tiempo respuesta** | ~105ms | ~2ms (con índice HNSW) |

---

## 📊 Métricas Post-Migración

| Métrica | Valor |
|---------|-------|
| Datasets migrados | 87.676 |
| Embeddings | 87.676 × 384 |
| Índice HNSW | Creado (m=16, ef=64) |
| Índices B-tree | 7 (filtros facetados) |
| Índice GIN | 1 (búsqueda de texto) |
| Tiempo de carga inicial | ~2-3 minutos |
| Tamaño tabla | ~724 MB |
| Búsqueda semántica | ~2-50ms |
| Búsqueda léxica | ~1-2ms |

---

## 🚀 Despliegue

### Opción 1: Con Docker (Recomendado)

```bash
cd 07_Sprint5_Integracion/codigo/docker

# Versión pública (por defecto)
docker compose -f docker-compose.override.yml up -d

# Acceder a:
# - Pública: http://localhost:8501
# - Avanzada: http://localhost:8501?mode=advanced
```

### Opción 2: Versión Avanzada por Defecto

```bash
# Usar docker-compose.override-advanced.yml
docker compose -f docker-compose.override-advanced.yml up -d
```

### Opción 3: Sin Docker

```bash
# Requiere PostgreSQL local
./setup_no_docker.sh
```

---

## 🔧 Configuración de Versiones

### Por Defecto (Versión Pública)

El `Dockerfile.frontend` usa `app_router.py` que carga la versión pública por defecto:

```dockerfile
CMD ["streamlit", "run", "app_router.py"]
```

### Cambiar a Versión Avanzada

**Opción A - URL:**
```
http://localhost:8501?mode=advanced
```

**Opción B - Variable de entorno:**
```yaml
services:
  frontend:
    environment:
      - APP_MODE=advanced
```

**Opción C - Directo:**
```bash
docker exec buscador_frontend streamlit run app.py
```

---

## 🐛 Troubleshooting

### Frontend muestra versión avanzada en ambas URLs

**Solución:** Reconstruir el contenedor:
```bash
docker compose -f docker-compose.override.yml down
docker compose -f docker-compose.override.yml build --no-cache frontend
docker compose -f docker-compose.override.yml up -d
```

### Errores de sintaxis en componentes

Verificar que no haya:
- `in in` (doble `in`)
- Problemas de indentación
- Faltan imports

---

## 🔗 Relación con otras fases

- **Fase 03**: Proporcionó datasets_clean.jsonl (378MB)
- **Fase 04**: Proporcionó embeddings.npy (129MB)
- **Fase 05**: Recibe motor de búsqueda y datos
- **Fase 06**: Los resultados de evaluación guían optimizaciones
- **Fase 08**: Mejoras con LLM (si se implementan) usarán esta infraestructura
- **Fase 09**: Documentación técnica para la memoria

---

## 📚 Documentación Adicional

- [Guía de ejecución (Fase 05)](../05_Sprint3_Busqueda_UI/docs/GUIA_EJECUCION.md)
- [Arquitectura de almacenamiento (Fase 05)](../05_Sprint3_Busqueda_UI/docs/arquitectura/ALMACENAMIENTO.md)
- [Análisis de métricas (Fase 06)](../06_Sprint4_Evaluacion/docs/metricas/ANALISIS_BATERIA_EXTENDIDA.md)
- **[Guía de Despliegue](docs/DESPLIEGUE.md)** - Instrucciones paso a paso
- **[README_VERSIONS.md](../frontend_v2/README_VERSIONS.md)** - Guía de versiones del frontend

---

## 🛠️ Mejoras Recientes (2026-05-25)

### Frontend Público v1.0
1. ✅ **Router dual**: Versión pública por defecto, avanzada vía URL
2. ✅ **Búsqueda con Enter**: Detecta Enter automáticamente
3. ✅ **Filtros desplegables**: Todas las opciones disponibles, sin duplicados
4. ✅ **Indicador de tipo de enlace**: 📥 archivo vs 🌐 página web
5. ✅ **Formatos múltiples**: Muestra todos los formatos disponibles
6. ✅ **UX limpia**: Sin controles técnicos, diseño tipo Google

---

**Fase completada el:** 2026-05-24
**Última actualización:** 2026-05-25 (nueva versión pública del frontend)
**Estado:** Operativo y listo para usuarios finales
