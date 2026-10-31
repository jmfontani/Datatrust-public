# Frontend B — Documentación Sprint 10

**Fecha:** 2026-06-03  
**Sprint:** 10 (Documentación y preparación de defensa)  
**Producto:** Frontend B Intermedio — Producto principal de la defensa

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Instrucciones de Arranque](#instrucciones-de-arranque)
3. [Journey Map del Usuario](#journey-map-del-usuario)
4. [Capturas y Flujo](#capturas-y-flujo)
5. [Características Técnicas](#características-técnicas)
6. [Preparación para la Defensa](#preparación-para-la-defensa)

---

## 🎯 Resumen Ejecutivo

### ¿Qué es el Frontend B?

El **Frontend B** es la interfaz principal del Buscador Semántico de Datasets Públicos. Es el producto que se demostrará durante la defensa del TFM ante el tribunal.

**Características clave:**
- 🔍 **Búsqueda híbrida:** Combina búsqueda semántica (IA) + léxica (palabras clave)
- 🎨 **Dos modos:** Versión pública (limpia) + versión avanzada (controles técnicos)
- 📱 **Responsive:** Diseñado en Streamlit, accesible desde cualquier navegador
- ⚡ **Rápido:** Resultados en <500ms para búsquedas simples
- 🌐 **Multi-usuario:** Soporta múltiples usuarios simultáneos

### ¿Por qué dos versiones?

| Versión | Público | Cuándo usar |
|---------|---------|-------------|
| **Pública** (`app_public.py`) | Usuarios finales, tribunal, demo principal | Defensa 15 min, uso diario |
| **Avanzada** (`app.py` o `?mode=advanced`) | Equipo técnico, debugging, preguntas específicas | Coloquio, demostración de capacidades |

---

## 🚀 Instrucciones de Arranque

### Pre-requisitos

1. **Entorno virtual activado:**
   ```bash
   cd ~/datos/PFM/Datatrust
   source venv/bin/activate
   ```

2. **API corriendo (Terminal 1):**
   ```bash
   cd 07_Sprint5_Integracion/codigo/api
   uvicorn main_v2_final_v07:app --reload --port 8000
   ```
   
   **Verificar API:**
   ```bash
   curl http://localhost:8000/health
   # Respuesta: {"status":"ok","engine":"postgresql+pgvector"}
   ```

3. **Base de datos PostgreSQL con pgvector:**
   ```bash
   # Verificar que PostgreSQL está corriendo
   psql -U postgres -d datasets -c "SELECT COUNT(*) FROM datasets;"
   # Esperado: ~87,676 datasets
   ```

### Arrancar Frontend B (Terminal 2)

```bash
# Navegar al frontend
cd 15_Frontends/frontend_b_intermedio

# Versión PÚBLICA (recomendada para defensa)
streamlit run app_public.py --server.port 8501

# Versión AVANZADA (controles técnicos)
streamlit run app.py --server.port 8501

# Versión con ROUTER automático (detecta ?mode=advanced en URL)
streamlit run app_router.py --server.port 8501
```

### Acceder al Frontend

| Versión | URL |
|---------|-----|
| Pública | http://localhost:8501 |
| Avanzada | http://localhost:8501/?mode=advanced |
| Alternativa | http://localhost:8501/app |

### Verificar que funciona

1. Abrir navegador en http://localhost:8501
2. Verificar que aparece el header con logo y título
3. Escribir una query de prueba: "empleo juvenil"
4. Verificar que aparecen resultados con tarjetas de datasets

---

## 🗺️ Journey Map del Usuario

### Persona: "Ana, investigadora de políticas públicas"

**Perfil:** Técnica de ayuntamiento, necesita datos para diseñar políticas de empleo juvenil. No es experta en tecnología.

| Fase | Acción | Pensamiento | Punto de contacto | Oportunidad de mejora |
|------|--------|-------------|-------------------|----------------------|
| **1. Descubrimiento** | "Necesito datos sobre empleo juvenil" | "¿Habrá datasets públicos sobre esto?" | Barra de búsqueda | Texto placeholder sugiere queries |
| **2. Búsqueda** | Escribe "empleo juvenil" en el buscador | "Espero que encuentre algo relevante" | Input de texto + botón 🔍 | Enter funciona, no hace falta clicar |
| **3. Resultados** | Ve 10-15 tarjetas con datasets | "Muchos resultados... ¿cuál elijo?" | Lista de resultados | Re-ranking con LLM ayuda a priorizar |
| **4. Evaluación** | Lee título, descripción, tema, territorio | "Este parece útil para mi análisis" | Cards con metadata | Explicaciones LLM justifican relevancia |
| **5. Acción** | Click en "Ver más" o "Descargar" | "¿Cómo accedo al dataset completo?" | Botones en cada card | Enlace directo a datos.gob.es |
| **6. Refinamiento** | Filtra por territorio o tema | "Solo me interesa Andalucía" | Filtros laterales | Facetas cargan automáticamente |

### Journey Map: "Carlos, desarrollador técnico"

**Perfil:** Quiere entender cómo funciona el sistema, prueba límites, hace preguntas técnicas.

| Fase | Acción | Pensamiento | Punto de contacto | Oportunidad |
|------|--------|-------------|-------------------|-------------|
| **1. Acceso** | Abre http://localhost:8501/?mode=advanced | "Quiero ver las opciones técnicas" | URL con parámetro | Router detecta automáticamente |
| **2. Configuración** | Ajusta pesos semántico/léxico | "¿Qué pasa si doy más peso a léxico?" | Sliders de pesos | Feedback inmediato en resultados |
| **3. Debugging** | Mira scores de cada resultado | "Este resultado tiene score 0.85" | Scores visibles | Transparencia del ranking |
| **4. Validación** | Prueba queries ambiguas | "¿Qué pasa con 'paro' (desempleo vs parada)?" | Query ambigua | Fallback a búsqueda léxica |

---

## 📸 Capturas y Flujo

### Flujo Principal (Versión Pública)

```
┌─────────────────────────────────────────────────────────────┐
│  1. PANTALLA DE INICIO                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  🔍 Buscador Semántico de Datasets Públicos           │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  [Escribe tu búsqueda...]              [🔍]     │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  Búsquedas populares:                                 │  │
│  │  [empleo juvenil] [vulnerabilidad] [censo]            │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓ (usuario escribe "empleo juvenil")
┌─────────────────────────────────────────────────────────────┐
│  2. RESULTADOS DE BÚSQUEDA                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Resultados para "empleo juvenil" (15 datasets)       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Filtros: [Tema ▼] [Territorio ▼] [Formato ▼]   │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  1. Estadísticas de Empleo Juvenil 2024         │  │  │
│  │  │     Instituto Nacional de Estadística           │  │  │
│  │  │     📊 Tema: Empleo | 📍 España                 │  │  │
│  │  │     Datos sobre empleo de jóvenes 16-29 años... │  │  │
│  │  │     [Ver más] [Descargar]                       │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  2. Paro Registrado por Edades                  │  │  │
│  │  │     Ministerio de Trabajo                       │  │  │
│  │  │     📊 Tema: Empleo | 📍 Andalucía              │  │  │
│  │  │     Estadísticas mensuales de paro registrado...│  │  │
│  │  │     [Ver más] [Descargar]                       │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓ (usuario aplica filtro "Andalucía")
┌─────────────────────────────────────────────────────────────┐
│  3. RESULTADOS FILTRADOS                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Resultados para "empleo juvenil" + Andalucía (5)     │  │
│  │  Filtros activos: [Andalucía ✕]                       │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  1. Paro Registrado por Edades - Andalucía      │  │  │
│  │  │  2. Empleo Joven Andalucía 2024                 │  │  │
│  │  │  3. Formación Profesional - Andalucía           │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Flujo Avanzado (Modo Técnico)

```
┌─────────────────────────────────────────────────────────────┐
│  MODO AVANZADO (?mode=advanced)                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  🔍 Buscador Semántico (Modo Avanzado)                │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Búsqueda: [empleo juvenil]            [🔍]     │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  CONFIGURACIÓN                                  │  │  │
│  │  │  Peso semántico: ████████░░ 75%                 │  │  │
│  │  │  Peso léxico:    ████░░░░░░ 25%                 │  │  │
│  │  │  Resultados:     [25 ▼]                          │  │  │
│  │  │  Score mínimo:   [0.15]                          │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  FILTROS                                        │  │  │
│  │  │  ☑ Andalucía  ☑ Cataluña  ☑ Madrid             │  │  │
│  │  │  ☑ Empleo     ☑ Educación  ☑ Salud             │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  [🔄 Buscar]  [🗑️ Limpiar filtros]                    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Características Técnicas

### Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     USUARIO (Navegador)                     │
│                     http://localhost:8501                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  STREAMLIT (Frontend B)                                     │
│  ├── app_public.py         (versión limpia)                 │
│  ├── app.py                (versión avanzada)               │
│  ├── app_router.py         (detección automática)           │
│  ├── components_v2.py      (UI components)                  │
│  ├── components_public.py  (UI pública)                     │
│  └── utils_v2.py           (API client, detección entorno)  │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP REST API
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  FASTAPI (Backend - Sprint 7)                               │
│  ├── main_v2_final_v07.py    (API principal)                │
│  ├── routes_search.py        (endpoint /search)             │
│  └── routes_llm.py           (endpoint /llm/rerank)         │
└─────────────────────┬───────────────────────────────────────┘
                      │ psycopg2 + pgvector
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  PostgreSQL 15.4 + pgvector 0.5.1                           │
│  ├── datasets (87,676 registros)                            │
│  ├── embedding (VECTOR(384))                                │
│  ├── search_vector (TSVECTOR)                               │
│  ├── HNSW index (búsqueda semántica)                        │
│  └── GIN index (búsqueda léxica)                            │
└─────────────────────────────────────────────────────────────┘
```

### Endpoints de la API utilizados

| Endpoint | Método | Parámetros | Descripción |
|----------|--------|------------|-------------|
| `/search` | POST | `query`, `top_k`, `semantic_weight`, `lexical_weight`, `min_score`, `require_lexical`, `territorio`, `tema` | Búsqueda híbrida |
| `/health` | GET | - | Verifica estado de la API |
| `/facets/{facet_name}` | GET | `facet_name` (territorio, tema, formato, publisher) | Obtener valores de facetas |
| `/llm/search/rerank` | POST | `query`, `results`, `top_n` | Re-ranking con LLM (opcional) |

### Configuración de la Búsqueda

| Parámetro | Valor por defecto | Rango válido | Descripción |
|-----------|-------------------|--------------|-------------|
| `top_k` | 25 | 1-100 | Número máximo de resultados |
| `semantic_weight` | 0.75 | 0.0-1.0 | Peso de la búsqueda semántica |
| `lexical_weight` | 0.25 | 0.0-1.0 | Peso de la búsqueda léxica |
| `min_score` | 0.15 | 0.0-1.0 | Score mínimo para mostrar resultado |
| `require_lexical` | False | True/False | Exige match léxico (evita falsos positivos) |

### Detección Automática de Entorno

El archivo `utils_v2.py` incluye `detect_base_dir()` con 5 estrategias de fallback:

1. Busca directorio padre con `05_Sprint3_Busqueda_UI/` o `api/`
2. Prueba entorno OpenCLaw (`/home/node/.openclaw/workspace`)
3. Fallback a `~/datos/PFM/Datatrust`

Esto permite ejecutar el frontend desde cualquier ubicación.

---

## 🎓 Preparación para la Defensa

### Demo Principal (15 minutos)

**Guión recomendado:**

| Tiempo | Acción | Query de ejemplo |
|--------|--------|------------------|
| 0:00-2:00 | Introducción: qué es el buscador | - |
| 2:00-5:00 | Demo búsqueda simple | "empleo juvenil" |
| 5:00-8:00 | Demo filtros | + "Andalucía" |
| 8:00-11:00 | Demo búsqueda ambigua (precisión) | "paro" (explicar que detecta desempleo, no parada) |
| 11:00-14:00 | Demo modo avanzado (si preguntan) | `?mode=advanced`, ajustar pesos |
| 14:00-15:00 | Cierre: valor aportado | - |

### Queries de Reserva (por si fallan)

| Query | Resultados esperados | Por qué funciona |
|-------|---------------------|------------------|
| "censo población" | INE, censos municipales | Datos muy explícitos |
| "delitos seguridad" | Estadísticas criminales | Tema bien etiquetado |
| "bibliotecas públicas" | Catálogos culturales | Metadata clara |
| "vulnerabilidad económica" | Estudios sociales | Embedding captura semántica |

### Posibles Preguntas del Tribunal + Respuestas

| Pregunta | Respuesta |
|----------|-----------|
| ¿Cómo funciona la búsqueda semántica? | "Usamos sentence-transformers para convertir queries y datasets a vectores 384D. PostgreSQL + pgvector hace la búsqueda por similitud coseno." |
| ¿Qué pasa si la API no responde? | "El frontend muestra un panel de error claro indicando que la API no está disponible. No hay fallback offline." |
| ¿Por qué dos versiones? | "La versión pública es para usuarios finales. La avanzada es para debugging y demostración técnica. En producción sería una sola con toggle." |
| ¿Cómo se evalúa la precisión? | "Hicimos tests con 20 queries reales. Precisión @5: 94.8%. Ver `07_Sprint5_Integracion/codigo/docs/MEJORAS_CALIDAD.md`." |
| ¿Qué aporta el LLM? | "Re-ranking (caso #1) y explicaciones (caso #2). Mejora la relevancia percibida, no el score técnico." |

### Checklist Pre-Defensa

- [ ] API corriendo y saludable (`curl http://localhost:8000/health`)
- [ ] PostgreSQL con datos (`psql -c "SELECT COUNT(*) FROM datasets;"` → ~87k)
- [ ] Frontend B accesible (http://localhost:8501)
- [ ] Queries de prueba funcionan ("empleo juvenil", "paro", "censo")
- [ ] Filtros cargan (temas, territorios visibles)
- [ ] Navegador limpio (pestañas, caché)
- [ ] Backup: tener `app.py` abierto en otra pestaña por si `app_public.py` falla

---

## 📁 Estructura de Archivos

```
15_Frontends/frontend_b_intermedio/
├── app.py                    # Versión avanzada (controles técnicos)
├── app_public.py             # Versión pública (recomendada para defensa)
├── app_router.py             # Router automático (?mode=advanced)
├── components_v2.py          # Componentes UI personalizables
├── components_public.py      # Componentes UI pública
├── utils_v2.py               # Utilidades + detección de entorno
├── README.md                 # Documentación básica
├── README_V2_ORIGEN.md       # Documentación original del Sprint 5
├── README_VERSIONS.md        # Comparativa versiones
└── DOCUMENTACION_SPRINT10.md # ESTE ARCHIVO (documentación completa)
```

---

## 🔗 Enlaces Relacionados

- **15_Frontends/README.md** — Visión general de los 3 frontends
- **15_Frontends/MAPA_DECISION.md** — Cuándo usar cada frontend
- **07_Sprint5_Integracion/codigo/docs/MEJORAS_CALIDAD.md** — Precisión 94.8%
- **metodologia/MAPA_NIVELES.md** — Arquitectura completa del proyecto

---

*Documento creado para el Sprint 10 (2026-06-03). Última actualización: 2026-06-03*
