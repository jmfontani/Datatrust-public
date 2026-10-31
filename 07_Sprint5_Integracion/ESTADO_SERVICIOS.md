# Estado de Servicios en Contenedores - Fase 07

**Fecha:** 2026-05-25  
**Estado:** ✅ **SERVICIOS FUNCIONANDO**

---

## Resumen de Contenedores

| Contenedor | Estado | Puerto | Imagen | Health |
|------------|--------|--------|--------|--------|
| buscador_postgres | Up | 5432 | ankane/pgvector:latest | ✅ healthy |
| buscador_api | Up | 8000 | docker-api | ✅ healthy |
| buscador_frontend | Up | 8501 | docker-frontend | ✅ healthy |

---

## Endpoints Disponibles

| Servicio | URL | Estado |
|----------|-----|--------|
| PostgreSQL | localhost:5432 | ✅ Conectado (87.676 datasets) |
| API Health | http://localhost:8000/health | ✅ 200 OK |
| API Docs | http://localhost:8000/docs | ✅ Swagger UI |
| Frontend Público | http://localhost:8501 | ✅ Streamlit App (v. pública) |
| Frontend Avanzado | http://localhost:8501?mode=advanced | ✅ Streamlit App (v. técnica) |

---

## Tests Realizados

### 1. Health Check API
```json
{
  "status": "ok",
  "postgresql": "connected",
  "pg_version": "15.4",
  "pgvector": true,
  "datasets_count": 87676,
  "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
  "features": {
    "stop_words": true,
    "synonims": true,
    "semantic_validation": true,
    "ambiguous_word_filtering": true
  }
}
```

### 2. Búsqueda Semántica
- **Query:** "educacion"
- **Expansión:** "educacion formación escuela estudios enseñanza universidad"
- **Resultados:** 6 encontrados
- **Tiempo respuesta:** ~37ms

### 3. Búsqueda con Palabra Ambigua
- **Query:** "paro desempleo"
- **Expansión:** "paro desempleo aturado desempleado atur tasa de paro parados"
- **Resultados:** 9 encontrados
- **Tiempo respuesta:** ~73ms

### 4. Endpoint Facetas
- **URL:** `/facets/territorio?limit=10`
- **Resultado:** 10 territorios disponibles
- **Estado:** ✅ Funcionando

---

## ✅ Mejoras Implementadas

### 1. Filtros Reactivos (Auto-refresh)

**Problema:** Usuario tenía que volver a escribir la query para aplicar filtros.

**Solución:** Al cambiar un filtro, la búsqueda se actualiza automáticamente con la última query.

**Cambios en `app.py`:**

```python
# Nuevos estados en session_state
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "last_filters" not in st.session_state:
    st.session_state.last_filters = {}

# Detectar cambios en filtros
filters_changed = (current_filters != st.session_state.last_filters)

# Ejecutar búsqueda automática
if filters_changed and st.session_state.last_query:
    execute_search(
        query=st.session_state.last_query,  # Usar query anterior
        filters=current_filters,              # Usar nuevos filtros
        ...
    )
    st.success("🔄 Actualizado con filtro")
```

**Flujo de uso:**
1. Usuario escribe "paro desempleo" → Presiona Enter → Resultados aparecen
2. Usuario cambia filtro de Territorio: "Todos" → "Madrid"
3. Automáticamente se ejecuta búsqueda: "paro desempleo" + filtro "Madrid"
4. Se muestra mensaje: "🔄 Actualizado con filtro: 'paro desempleo'"

---

## ✅ Error Corregido

### Problema: Syntax Error en tsquery para palabras ambiguas (RESUELTO)

**Ubicación:** `api/main_v2_final.py`, función `buscar_con_filtro_ambiguo()`

**Error Original:**
```
syntax error in tsquery: "paro | desempleo | desempleado | parados | tasa de paro | atur | aturado"
```

**Causa:** La expansión de sinónimos incluye frases con espacios ("tasa de paro") que causaban error en `to_tsquery()`.

**Solución Aplicada:**
Usar `plainto_tsquery()` con el operador `||` (OR) de PostgreSQL:

```python
# ANTES (fallaba):
terminos_or = ' | '.join([query] + sinonimos)
cur.execute("... to_tsquery('spanish', %s) ...", (terminos_or,))

# DESPUÉS (funciona):
terminos_list = [query] + sinonimos
tsquery_parts = [f"plainto_tsquery('spanish', %s)" for _ in terminos_list]
tsquery_or = ' || '.join(tsquery_parts)
cur.execute(query_sql, tuple(terminos_list * 3))
```

**Verificación:**
```bash
$ curl -X POST http://localhost:8000/search -d '{"query": "paro desempleo", "top_k": 3}'
{
  "total_results": 17,
  "results": [...],
  "warnings": ["⚠️ Palabra ambigua detectada: 'paro'. Usando filtrado especial."]
}
```

**Resultado:** ✅ La búsqueda léxica y semántica ahora funcionan correctamente juntas.

---

## ✅ Nueva Versión Pública del Frontend (Implementado 2026-05-25)

### Dos Versiones Disponibles

| Versión | URL | Descripción | Público Objetivo |
|---------|-----|-------------|------------------|
| **Pública** (por defecto) | `http://localhost:8501` | Interfaz limpia, sin controles técnicos | Ciudadanos, periodistas |
| **Avanzada** | `http://localhost:8501?mode=advanced` | Controles técnicos completos | Desarrolladores, admins |

### Características Versión Pública

#### Diseño Limpio
- ✅ **Header minimalista**: "🔍 Datos Abiertos"
- ✅ **Barra de búsqueda estilo Google**: Redondeada, sombra suave
- ✅ **Búsquedas populares**: Chips rápidos (Empleo, Educación, etc.)
- ✅ **Sin sidebar técnico**: Interfaz centrada y limpia

#### Funcionalidad
- ✅ **Búsqueda con Enter**: Funciona directamente al pulsar Enter
- ✅ **Filtros desplegables**: Todas las opciones disponibles (territorio, categoría)
- ✅ **Relevancia con estrellas**: ⭐⭐⭐⭐⭐ en lugar de scores numéricos
- ✅ **Indicador de tipo de enlace**:
  - 📥 Archivo descargable directo (CSV, XLSX, PDF, etc.)
  - 🌐 Página web donde buscar el dataset
- ✅ **Formatos disponibles**: Muestra todos los formatos del dataset

#### UX Mejorada
- ✅ Responsive (móvil y desktop)
- ✅ Estados vacíos amigables
- ✅ Sin controles técnicos (pesos optimizados automáticamente: 75% semántico, 25% léxico)

### Ejemplo de Visualización

**Archivo Descargable:**
```
📈 Datos de paro registrado por municipios
🏛️ Ministerio de Economía | 📍 Madrid | 🕒 Hace 2 meses
Datos del paro registrado en la Comunidad de Madrid...

📄 Formato: CSV, XLSX
⭐⭐⭐⭐⭐ Muy relevante        📥 Descargar CSV →
```

**Página Web:**
```
📊 Indicadores de Tráfico y Movilidad
🏛️ Ayto. de Zaragoza | 📍 Aragón
Indicadores relacionados con movilidad...

⚠️ Página web - busca el archivo descargable en el enlace
⭐⭐⭐ Algo relevante          🌐 Ver página del dataset →
```

### Cómo Acceder

```bash
# Versión pública (por defecto)
http://localhost:8501

# Versión avanzada (técnica)
http://localhost:8501?mode=advanced

# O ejecutar directamente
docker exec buscador_frontend streamlit run app.py
```

### Archivos del Frontend

| Archivo | Propósito |
|---------|-----------|
| `frontend_v2/app_router.py` | Router entre versiones (punto de entrada) |
| `frontend_v2/app_public.py` | Versión pública (interfaz limpia) |
| `frontend_v2/app.py` | Versión avanzada (técnica) |
| `frontend_v2/components_public.py` | Componentes UI para versión pública |
| `frontend_v2/README_VERSIONS.md` | Guía de versiones del frontend |

---

## Red Docker

- **Red:** `docker_buscador_network`
- **Subnet:** 172.30.0.0/16
- **Gateway:** 172.30.0.1
- **Contenedores conectados:**
  - buscador_postgres (172.30.0.1)
  - buscador_api
  - buscador_frontend (172.30.0.5)

---

## Comandos Útiles

```bash
# Ver logs
docker logs -f buscador_api
docker logs -f buscador_frontend
docker logs -f buscador_postgres

# Reiniciar servicios
cd 07_Sprint5_Integracion/codigo/docker
docker compose -f docker-compose.override.yml restart

# Detener servicios
docker compose -f docker-compose.override.yml down

# Acceder a PostgreSQL
docker exec -it buscador_postgres psql -U postgres -d buscador

# Reconstruir frontend (después de cambios)
docker compose -f docker-compose.override.yml build --no-cache frontend
docker compose -f docker-compose.override.yml up -d
```

---

## ⚠️ Nota Importante: Reinicio Requerido

Si has actualizado el código del frontend y ves comportamiento inesperado:

```bash
cd 07_Sprint5_Integracion/codigo/docker
docker compose -f docker-compose.override.yml down
docker compose -f docker-compose.override.yml build --no-cache frontend
docker compose -f docker-compose.override.yml up -d
```

Luego podrás acceder a:
- **Pública:** http://localhost:8501 (o http://servidor1.local:8501)
- **Avanzada:** http://localhost:8501?mode=advanced

---

## Conclusión

✅ **Todos los servicios se lanzan correctamente**  
✅ **La búsqueda semántica funciona perfectamente**  
✅ **Versión pública del frontend implementada**  
✅ **Versión avanzada intacta y accesible**  
✅ **Indicador de tipo de enlace funcionando**  

El sistema está listo para:
- **Usuarios finales** (versión pública): Interfaz limpia, sin controles técnicos
- **Administradores/Técnicos** (versión avanzada): Control completo de parámetros

**Próximos pasos sugeridos:**
- Fase 08: Documentación y memoria del proyecto
- Posibles mejoras: guardar búsquedas favoritas, historial, modo oscuro

---

*Última actualización: 2026-05-25 - Implementada versión pública del frontend con indicador de tipo de enlace (archivo vs web)*
