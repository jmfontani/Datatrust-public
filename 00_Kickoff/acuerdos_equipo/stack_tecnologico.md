# Stack Tecnológico

## Proyecto: Buscador Semántico de Datasets Públicos (datos.gob.es)

---

## 1. LENGUAJE Y FRAMEWORKS

### Backend
| Tecnología | Versión | Uso | Justificación |
|------------|---------|-----|---------------|
| **Python** | 3.11+ | Lenguaje principal | Ecosistema ML maduro, legible, usado en todo el pipeline |
| **FastAPI** | 0.100+ | API REST | Asíncrono, auto-documentado con OpenAPI, rendimiento superior |
| **SQLAlchemy** | 2.0+ | ORM | Abstracción de base de datos, migrations, tipado |

### Frontend
| Tecnología | Versión | Uso | Justificación |
|------------|---------|-----|---------------|
| **Streamlit** | 1.28+ | Interfaz de usuario | Rápido para prototipos, Python nativo, ideal para demos |

---

## 2. BASE DE DATOS Y VECTOR STORE

| Tecnología | Versión | Uso | Justificación |
|------------|---------|-----|---------------|
| **PostgreSQL** | 15+ | Base de datos principal | Robusta, ACID, soporte JSON, extensible |
| **pgvector** | 0.5+ | Extensión vectorial | Búsqueda por similitud en SQL nativo, eficiente |

### Schema propuesto (inicial)
```sql
-- Tabla principal de datasets
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    ckan_id VARCHAR(255) UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    organization TEXT,
    tags TEXT[],
    categories TEXT[],
    frequency VARCHAR(100),
    spatial_coverage TEXT,
    temporal_coverage TEXT,
    format VARCHAR(50),
    license VARCHAR(100),
    source_url TEXT,
    metadata_vector vector(384),  -- Dimensión del modelo embeddings
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índice para búsqueda por similitud
CREATE INDEX idx_datasets_vector ON datasets USING ivfflat (metadata_vector vector_cosine_ops);

-- Tabla para queries de benchmark
CREATE TABLE benchmark_queries (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    expected_dataset_ids INTEGER[],
    category VARCHAR(100),
    difficulty VARCHAR(20) CHECK (difficulty IN ('fácil', 'medio', 'difícil'))
);
```

---

## 3. MACHINE LEARNING / NLP

| Tecnología | Versión | Uso | Justificación |
|------------|---------|-----|---------------|
| **sentence-transformers** | 2.2+ | Generación de embeddings | Estado del arte para embeddings semánticos, multilingüe |
| **paraphrase-multilingual-MiniLM-L12-v2** | - | Modelo por defecto | 384 dimensiones, español nativo, rápido, calidad aceptable |

### Modelos alternativos a evaluar
| Modelo | Dimensiones | Idioma | Ventaja |
|--------|-------------|--------|---------|
| `distiluse-base-multilingual-cased-v2` | 512 | Multilingüe | Mejor para oraciones cortas |
| `multi-qa-MiniLM-L6-cos-v1` | 384 | Multilingüe | Optimizado para Q&A |
| `LaBSE` | 768 | Multilingüe | Mejor para cross-lingual |

---

## 4. INFRAESTRUCTURA Y DESPLIEGUE

| Tecnología | Versión | Uso | Justificación |
|------------|---------|-----|---------------|
| **Docker** | 24+ | Containerización | Aislamiento, reproducibilidad, fácil deploy |
| **Docker Compose** | 2.20+ | Orquestación local | Multi-contenedor sencillo, ideal para desarrollo |
| **Git** | - | Control de versiones | Colaboración, historial, branches |

### Estructura Docker
```yaml
# docker-compose.yml (esqueleto)
version: '3.8'
services:
  db:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: datosgob
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  api:
    build: ./src/api
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/datosgob
  
  frontend:
    build: ./src/frontend
    ports:
      - "8501:8501"
    depends_on:
      - api

volumes:
  pgdata:
```

---

## 5. HERRAMIENTAS DE DESARROLLO

| Categoría | Herramienta | Uso |
|-----------|-------------|-----|
| **IDE** | VS Code / PyCharm | Desarrollo |
| **Jupyter** | Jupyter Lab / Google Colab | Experimentación, notebooks |
| **Testing** | pytest | Tests unitarios y de integración |
| **Linting** | ruff / black / mypy | Calidad de código, formateo, tipado |
| **API Testing** | HTTPie / curl | Pruebas manuales de endpoints |

---

## 6. GESTIÓN DE PROYECTO

| Herramienta | Uso | Notas |
|-------------|-----|-------|
| **GitHub** | Repositorio de código | Issues, PRs, Actions |
| **Google Drive** | Documentación compartida | Estructura de carpetas acordada |
| **Slack/Discord** | Comunicación diaria | Dailies, bloqueos, avances |
| **Notion/Obsidian** | Wiki técnica | Decisiones, ADRs, conocimiento |

---

## 7. FUENTES DE DATOS

| Fuente | API/Formato | Uso | Prioridad |
|--------|-------------|-----|-----------|
| **datos.gob.es** | CKAN API v3 | Principal fuente de datasets | Crítica |
| **data.europa.eu** | CKAN API v3 | Extensión futura (Phase 2) | Baja |

---

## 8. DECISIONES PENDIENTES

- [ ] **GPU vs CPU** para embeddings: ¿Necesitamos GPU o es suficiente CPU? 
  - *Evaluar:* Tiempo de generación de embeddings con CPU vs coste de GPU cloud
- [ ] **Hosting:** ¿Dónde se despliega la demo final?
  - *Opciones:* Render, Railway, VPS propio, universidad
- [ ] **Cache:** ¿Redis para caché de queries frecuentes?
  - *Decisión:* Evaluar después del Sprint 3
- [ ] **Observabilidad:** ¿Logging estructurado (Promtail + Grafana)?
  - *Decisión:* Solo si hay tiempo en Sprint 6

---

## 9. RESTRICCIONES

- **Presupuesto:** ~0€ (usar herramientas open source y tiers gratuitos)
- **Hardware:** Desarrollo en laptops personales
- **Datos sensibles:** No manejar datos personales (solo metadatos públicos)

---

*Documento vivo: Actualizar cuando se tomen decisiones pendientes*
