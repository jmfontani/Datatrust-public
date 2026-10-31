# Sprint 3: Motor de Búsqueda Híbrida - Documentación

## 📋 Índice

1. [Resumen](#resumen)
2. [Arquitectura](#arquitectura)
3. [Prerrequisitos](#prerrequisitos)
4. [Configuración del Entorno](#configuración-del-entorno)
5. [Ejecución del Motor CLI](#ejecución-del-motor-cli)
6. [Ejecución de la API REST](#ejecución-de-la-api-rest)
7. [Endpoints de la API](#endpoints-de-la-api)
8. [Ejemplos de Uso](#ejemplos-de-uso)
9. [Solución de Problemas](#solución-de-problemas)

---

## Resumen

El **Sprint 3** implementa un motor de búsqueda híbrida que combina:

- **Búsqueda Semántica**: Basada en embeddings de `sentence-transformers` (similitud coseno)
- **Búsqueda Léxica**: Basada en BM25 para coincidencias de términos exactos
- **Filtros Facetados**: Por territorio, tema, formato y publisher
- **Explicaciones de Relevancia**: Para entender por qué aparece cada resultado

**Modelo utilizado**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

---

## Arquitectura

```
Datatrust/
├── 03_Sprint1_Ingesta/
│   └── datos/processed/
│       └── datasets_clean.jsonl          # Datasets normalizados
├── 04_Sprint2_Embeddings/
│   └── datos/
│       ├── processed/
│       │   └── embeddings.npy              # Vectores de embeddings
│       └── indices/                       # Índices invertidos
│           ├── id_position_map.json
│           ├── index_tema.json
│           ├── index_territorio.json
│           ├── index_formato.json
│           ├── index_publisher.json
│           └── bm25_index.pkl
└── 05_Sprint3_Busqueda_UI/
    └── codigo/
        ├── motor/
        │   └── search_engine.py            # Motor híbrido (CLI)
        ├── api/
        │   └── main.py                     # API REST (FastAPI)
        └── tests/
            └── test_search.py
```

### Flujo de Datos

```
Query de usuario
       ↓
┌─────────────────┐
│  Tokenización   │
└────────┬────────┘
         ↓
┌──────────────┐  ┌─────────────┐
│  Semántica   │  │   Léxica   │
│  (Embeddings)│  │   (BM25)   │
└──────┬───────┘  └──────┬──────┘
       │                 │
       ↓                 ↓
   Scores de      Scores de
   similitud      relevancia
       │                 │
       └────────┬────────┘
                ↓
        ┌──────────────┐
        │  Combinación │  ← Pesos configurables
        │   ponderada  │
        └──────┬───────┘
               ↓
        ┌──────────────┐
        │   Filtros    │  ← Facetas (territorio, tema, etc.)
        │   facetados  │
        └──────┬───────┘
               ↓
        ┌──────────────┐
        │   Ranking    │
        │   final      │
        └──────┬───────┘
               ↓
        Resultados ordenados
```

---

## Prerrequisitos

### Software Requerido

| Componente | Versión | Propósito |
|-----------|---------|-----------|
| Python | 3.11+ | Runtime |
| PostgreSQL | 15+ | Base de datos (si se usa pgvector) |
| pip o uv | - | Gestor de paquetes |

### Dependencias Principales

```
sentence-transformers>=2.2.2
torch>=2.1.0
fastapi>=0.104.0
uvicorn>=0.24.0
numpy>=1.24.0
pandas>=2.1.0
scikit-learn>=1.3.0
psycopg2-binary>=2.9.9
pgvector>=0.2.0
streamlit>=1.28.0
```

### Recursos Generados en Sprints Anteriores

Antes de ejecutar el Sprint 3, deben existir:

1. **`datasets_clean.jsonl`**: Datos normalizados del Sprint 1
2. **`embeddings.npy`**: Matriz de embeddings del Sprint 2
3. **Índices JSON**: Mapas de posición e índices invertidos del Sprint 2

---

## Configuración del Entorno

### Paso 1: Activar el Virtualenv

```bash
cd ~/datos/PFM/Datatrust

# Activar entorno virtual
source venv/bin/activate

# Verificar Python del venv
which python3
# Debería mostrar: .../Datatrust/venv/bin/python3
```

### Paso 2: Instalar Dependencias (si es necesario)

```bash
# Si hay nuevas dependencias por instalar
pip install -r 99_Compartido/herramientas/requirements.txt

# O solo las esenciales si ya están instaladas
pip install sentence-transformers torch fastapi uvicorn numpy scikit-learn
```

### Variables de Entorno Recomendadas

```bash
export TMPDIR=~/pip-tmp
export PIP_CACHE_DIR=~/pip-cache
```

---

## Ejecución del Frontend Streamlit

### Opción recomendada: Script único (Backend + Frontend)

```bash
cd ~/datos/PFM/Datatrust/05_Sprint3_Busqueda_UI/codigo
./lanzar_sistema.sh
```

Este script automatiza TODO:
1. Activa el virtualenv
2. Verifica/instala dependencias
3. Libera puertos ocupados
4. Inicia Backend (API) en puerto 8000
5. Espera a que la API esté lista
6. Inicia Frontend en puerto 8501
7. Muestra logs en tiempo real

**Acceso:**
- Frontend: http://localhost:8501
- API: http://localhost:8000

### Opción Manual (si necesitas control total)

**Terminal 1 - Backend (API):**
```bash
cd ~/datos/PFM/Datatrust/05_Sprint3_Busqueda_UI/codigo/api
source ../../../venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd ~/datos/PFM/Datatrust/05_Sprint3_Busqueda_UI/codigo/frontend
source ../../../venv/bin/activate
streamlit run app.py --server.port 8501
```

- **Barra de búsqueda** con placeholder de ejemplo
- **Controles de pesos**: Sliders para ajustar semántico/léxico (0.0-1.0)
- **Filtros facetados**: Dropdowns para territorio, tema, formato, publisher
- **Tarjetas de resultados** con:
  - Score coloreado (🟢🟡🟠🔴)
  - Título, metadatos, descripción
  - Explicación de relevancia (💡)
  - Enlace al dataset original
- **Estadísticas**: Resultados, tiempo, pesos utilizados
- **Panel de ayuda** integrado

### Flujo Completo

```bash
# Terminal 1: API (Backend)
cd 05_Sprint3_Busqueda_UI/codigo/api
source ../../../venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd 05_Sprint3_Busqueda_UI/codigo/frontend
source ../../../venv/bin/activate
streamlit run app.py --server.port 8501
```

---

## Ejecución del Motor CLI

### Sintaxis Básica

```bash
cd ~/datos/PFM/Datatrust/05_Sprint3_Busqueda_UI/codigo/motor

python3 search_engine.py "<consulta>" [opciones]
```

### Opciones Disponibles

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `query` | str | obligatorio | Consulta de búsqueda |
| `--top-k` | int | 10 | Número de resultados |
| `--territorio` | str | None | Filtrar por territorio |
| `--tema` | str | None | Filtrar por tema |
| `--formato` | str | None | Filtrar por formato |
| `--publisher` | str | None | Filtrar por publisher |
| `--semantic-weight` | float | 0.7 | Peso para búsqueda semántica (0-1) |
| `--lexical-weight` | float | 0.3 | Peso para búsqueda léxica (0-1) |
| `--no-explain` | flag | False | Omitir explicaciones de relevancia |

### Ejemplos de Comandos CLI

#### Búsqueda simple
```bash
python3 search_engine.py "datos de tráfico en Madrid"
```

#### Búsqueda con filtros
```bash
python3 search_engine.py "datos de tráfico en Madrid" \
  --territorio "Comunidad de Madrid" \
  --top-k 5
```

#### Búsqueda con pesos ajustados
```bash
# Más énfasis en búsqueda léxica (palabras exactas)
python3 search_engine.py "educación primaria" \
  --semantic-weight 0.4 \
  --lexical-weight 0.6 \
  --tema "educacion"
```

#### Búsqueda con múltiples filtros
```bash
python3 search_engine.py "población municipal" \
  --territorio "España" \
  --formato "CSV" \
  --publisher "Instituto Nacional de Estadística" \
  --top-k 20
```

### Salida Esperada

```
================================================================================
🔍 Query: 'datos de tráfico en Madrid'
   Filtro territorio: Comunidad de Madrid
   Pesos: semántico=0.7, léxico=0.3
   Tiempo: 145.32ms
================================================================================

1. [0.892] Accidentalidad en accidentes de tráfico de la Comunidad de Madrid
   🏛️  Comunidad de Madrid | 🌍 Comunidad de Madrid
   🏷️  Transporte, Seguridad vial | 📄 CSV, JSON
   Estadísticas de accidentalidad en vías interurbanas y urbanas de la Com...
   💡 Alta similitud semántica con la consulta; territorio coincidente: Comunidad de Madrid.
   🔗 https://datos.madrid.es/.../accidentalidad_trafico.csv

2. [0.845] Puntos negros de tráfico en la Comunidad de Madrid
   ...

================================================================================
Total: 5/42 resultados
```

---

## Ejecución de la API REST

### Iniciar el Servidor

```bash
cd ~/datos/PFM/Datatrust/05_Sprint3_Busqueda_UI/codigo/api

# Opción A: Con recarga automática (desarrollo)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Opción B: Producción (más rendimiento)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Opción C: Con HTTPS (si tienes certificados)
uvicorn main:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile /path/to/key.pem \
  --ssl-certfile /path/to/cert.pem
```

### Verificar que está funcionando

```bash
curl http://localhost:8000/
# O si usas HTTPS:
curl -k https://servidor1.local:8443/
```

Respuesta esperada:
```json
{
  "name": "Buscador Semántico de Datasets",
  "version": "0.3.0",
  "endpoints": {
    "search": "POST /search",
    "health": "GET /health",
    "facets": "GET /facets/{tema|territorio|formato|publisher}"
  }
}
```

### Ejecutar como Servicio (systemd)

Crear archivo `/etc/systemd/system/buscador-api.service`:

```ini
[Unit]
Description=Buscador Semántico API
After=network.target

[Service]
Type=simple
User=fonta
WorkingDirectory=%h/datos/PFM/Datatrust/05_Sprint3_Busqueda_UI/codigo/api
Environment=PATH=~/datos/PFM/Datatrust/venv/bin
ExecStart=%h/datos/PFM/Datatrust/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8443
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable buscador-api
sudo systemctl start buscador-api
sudo systemctl status buscador-api
```

---

## Endpoints de la API

### 1. Health Check

```bash
GET /health
```

Respuesta:
```json
{
  "status": "healthy",
  "engine_loaded": true,
  "datasets_count": 113313
}
```

### 2. Búsqueda

```bash
POST /search
Content-Type: application/json
```

**Body de la petición:**

```json
{
  "query": "datos de tráfico en Madrid",
  "top_k": 10,
  "semantic_weight": 0.7,
  "lexical_weight": 0.3,
  "territorio": "Comunidad de Madrid",
  "tema": null,
  "formato": null,
  "publisher": null,
  "explain": true
}
```

**Respuesta:**

```json
{
  "query": "datos de tráfico en Madrid",
  "filters": {
    "territorio": "Comunidad de Madrid",
    "tema": null,
    "formato": null,
    "publisher": null
  },
  "total_results": 42,
  "returned_results": 10,
  "semantic_weight": 0.7,
  "lexical_weight": 0.3,
  "search_time_ms": 145.32,
  "results": [
    {
      "id": "dataset-12345",
      "score": 0.8923,
      "title": "Accidentalidad en accidentes de tráfico de la Comunidad de Madrid",
      "description": "Estadísticas de accidentalidad en vías interurbanas y urbanas...",
      "territorio": ["Comunidad de Madrid"],
      "tema": ["Transporte", "Seguridad vial"],
      "formato": ["CSV", "JSON"],
      "publisher": "Comunidad de Madrid",
      "url": "https://datos.madrid.es/...",
      "explanation": "Alta similitud semántica con la consulta; territorio coincidente: Comunidad de Madrid."
    }
  ]
}
```

### 3. Facetas

Obtener valores disponibles para una faceta:

```bash
GET /facets/{tema|territorio|formato|publisher}?limit=100
```

Ejemplos:
```bash
# Temas disponibles
curl http://localhost:8000/facets/tema

# Territorios (primeros 50)
curl "http://localhost:8000/facets/territorio?limit=50"

# Formatos
curl http://localhost:8000/facets/formato
```

Respuesta:
```json
{
  "facet": "tema",
  "count": 156,
  "values": ["Educación", "Transporte", "Economía", "Medio Ambiente", ...]
}
```

---

## Ejemplos de Uso

### cURL

```bash
# Búsqueda básica
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"datos de tráfico","top_k":5}'

# Búsqueda con filtros
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "educación primaria",
    "territorio": "España",
    "tema": "Educación",
    "formato": "CSV",
    "top_k": 10,
    "semantic_weight": 0.6,
    "lexical_weight": 0.4
  }'

# Solo búsqueda léxica (BM25)
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "INE población municipal",
    "semantic_weight": 0.0,
    "lexical_weight": 1.0
  }'
```

### Python (requests)

```python
import requests

API_URL = "https://servidor1.local:8443"

# Búsqueda
response = requests.post(
    f"{API_URL}/search",
    json={
        "query": "datos de tráfico en Madrid",
        "territorio": "Comunidad de Madrid",
        "top_k": 5
    },
    verify=False  # Solo si usas certificado autofirmado
)

results = response.json()
for r in results["results"]:
    print(f"{r['title']} ({r['score']:.3f})")
```

### JavaScript (fetch)

```javascript
const response = await fetch('https://servidor1.local:8443/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'datos de tráfico en Madrid',
    territorio: 'Comunidad de Madrid',
    top_k: 5
  })
});

const data = await response.json();
console.log(data.results);
```

---

## Solución de Problemas

### Error: `ModuleNotFoundError: No module named 'sentence_transformers'`

**Causa**: No estás usando el Python del virtualenv.

**Solución**:
```bash
# Verificar que venv está activado
which python3
# Debe mostrar: .../venv/bin/python3

# Si no, activarlo:
source ~/datos/PFM/Datatrust/venv/bin/activate

# Instalar dependencias si faltan:
pip install sentence-transformers torch fastapi uvicorn
```

### Error: `uvicorn: orden no encontrada`

**Causa**: El venv no está activado o uvicorn no está instalado.

**Solución**:
```bash
# Activar venv
source venv/bin/activate

# Verificar uvicorn está instalado
which uvicorn
# Debe mostrar: .../venv/bin/uvicorn

# Si no, instalarlo:
pip install uvicorn[standard]
```

### Error: `FileNotFoundError` en embeddings o índices

**Causa**: No se han generado los datos en los Sprints 1 y 2.

**Solución**: Ejecutar los pipelines de los sprints anteriores:
```bash
# Sprint 1: Ingesta
python3 03_Sprint1_Ingesta/codigo/pipeline_ingesta.py

# Sprint 2: Embeddings
python3 04_Sprint2_Embeddings/codigo/generar_embeddings.py
python3 04_Sprint2_Embeddings/codigo/construir_indices.py
```

### Error: Puerto ocupado

```bash
# Encontrar proceso en puerto 8000
lsof -i :8000

# Matar proceso
kill -9 <PID>

# O usar otro puerto
uvicorn main:app --port 8001
```

### API muy lenta en primera carga

**Causa**: El modelo de embeddings se carga en memoria la primera vez.

**Solución**: Es normal. La primera búsqueda tarda ~10-30s. Las siguientes son instantáneas.

### Error de certificado SSL (self-signed)

Al hacer curl a `https://servidor1.local:8443/`:
```bash
# Ignorar verificación (solo desarrollo)
curl -k https://servidor1.local:8443/

# O instalar el certificado
sudo cp /path/to/cert.pem /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

---

## Notas de Rendimiento

- **Tiempo de carga inicial**: 10-30 segundos (carga del modelo de embeddings)
- **Tiempo de búsqueda**: 50-200ms por query
- **Memoria RAM requerida**: ~2-4 GB (dependiendo del tamaño del índice)
- **CPU**: Primera carga usa 100% de un core; búsquedas son ~30% de un core

---

## Próximos Pasos (Sprint 4+)

- Integrar con base de datos PostgreSQL + pgvector
- Caché de resultados frecuentes
- Búsqueda por lote (batch)
- Autocompletado de queries
- Historial de búsquedas

---

*Documento generado el 2026-05-23 para el PFM Buscador Semántico de Datasets Públicos*
