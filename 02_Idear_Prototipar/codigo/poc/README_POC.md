# POC DatasetSeeker – Prototipo de Búsqueda

## 🎯 Objetivo

Demostrar la viabilidad técnica de un buscador semántico de datasets públicos usando embeddings de lenguaje natural, comparado con un baseline de TF-IDF.

---

## 📁 Estructura

```
poc/
├── app.py                    # Aplicación Streamlit (TF-IDF - v1)
├── app_v2.py                 # Aplicación Streamlit (Embeddings - v2)
├── data/
│   ├── sample_datasets.json   # 100 datasets reales de datos.gob.es
│   └── embeddings.npy         # Embeddings pre-calculados (100 × 384)
├── utils/
│   ├── search_mock.py         # Motor TF-IDF (v1)
│   └── search_semantic.py     # Motor Semántico con Sentence Transformers (v2)
├── requirements.txt
└── README_POC.md              # Este archivo
```

---

## 🚀 Instalación

```bash
# Crear entorno virtual
python3 -m venv --without-pip venv_poc
curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py
venv_poc/bin/python get-pip.py

# Activar e instalar dependencias
source venv_poc/bin/activate
pip install sentence-transformers numpy scipy streamlit scikit-learn
```

---

## 🎮 Ejecución

### Versión 1: TF-IDF (Baseline)

```bash
source venv_poc/bin/activate
streamlit run app.py
```

- Motor basado en coincidencia de palabras clave
- No entiende sinónimos ni contexto semántico
- Útil como baseline de comparación

### Versión 2: Embeddings Semánticos (Recomendada)

```bash
source venv_poc/bin/activate
streamlit run app_v2.py
```

- Motor basado en Sentence Transformers (`paraphrase-multilingual-MiniLM-L12-v2`)
- Entiende contexto, sinónimos y lenguaje natural
- Embeddings precalculados para velocidad

---

## 🔬 Comparación de Motores

| Característica | TF-IDF (v1) | Semántico (v2) |
|---|---|---|
| **Tecnología** | TF-IDF + scikit-learn | Sentence Transformers + Cosine Similarity |
| **Entiende sinónimos** | ❌ No | ✅ Sí |
| **Lenguaje natural** | ❌ Palabras clave exactas | ✅ Consultas conversacionales |
| **Contexto** | ❌ No | ✅ Sí (embeddings contextuales) |
| **Velocidad** | ✅ Rápido (~1ms) | ✅ Rápido (~5ms con precálculo) |
| **Requiere GPU** | ❌ No | ❌ No (CPU es suficiente) |
| **Tamaño modelo** | 0 MB | ~120 MB (MiniLM-L12-v2) |
| **Dimensión embeddings** | N/A | 384 dimensiones |

---

## 📊 Ejemplos de Búsqueda Comparativos

### Ejemplo 1: "pueblos que se vacían"

**TF-IDF (v1):**
- ❌ No encuentra resultados (score: 0%)
- No contiene las palabras exactas

**Semántico (v2):**
- ✅ "Población en municipios de Canarias" (score: 72%)
- ✅ "Superficie de los municipios de Canarias" (score: 65%)
- ✅ "Densidad de población en municipios" (score: 58%)
- Entiende concepto de despoblación sin palabras exactas

### Ejemplo 2: "accidentes de trabajo"

**TF-IDF (v1):**
- ✅ "Accidentes de trabajo en jornada..." (score: 38%)
- ✅ Coincidencia exacta de palabras

**Semántico (v2):**
- ✅ "Accidentes de trabajo en jornada..." (score: 60%)
- ✅ "Accidentes de trabajo con baja..." (score: 41%)
- Mayor precisión y mejor ranking

### Ejemplo 3: "renta media de las familias"

**TF-IDF (v1):**
- ✅ "Renta bruta media de los hogares..." (score: 37%)
- ✅ Match parcial de palabras

**Semántico (v2):**
- ✅ "Renta bruta media de los hogares..." (score: 85%)
- Mayor precisión por entender concepto de "renta familiar"

---

## 🧪 Test Rápido del Motor

```bash
source venv_poc/bin/activate
python utils/search_semantic.py
```

Generará embeddings si no existen y ejecutará una búsqueda de prueba.

---

## 🏗️ Arquitectura del Motor Semántico

```
Query del usuario
      ↓
SentenceTransformer.encode() → Embedding (384D)
      ↓
Cosine Similarity con embeddings precalculados
      ↓
Ranking por score (0-100%)
      ↓
Filtros estructurales (tema, territorio, formato)
      ↓
Resultados + Explicaciones
```

### Ventajas clave:

1. **Embeddings L2-normalizados**: El dot product = cosine similarity, evitando cálculos de raíz cuadrada
2. **Precálculo**: Los embeddings de datasets se calculan una vez y se guardan en `embeddings.npy`
3. **In-memory**: Todo en NumPy, sin dependencias de PostgreSQL/pgvector para el POC
4. **Modelo multilingual**: Funciona en español, inglés y otros idiomas

---

## 📦 Dependencias

| Paquete | Versión | Propósito |
|---|---|---|
| `sentence-transformers` | 5.5.1+ | Generación de embeddings |
| `torch` | 2.12.0+ | Backend de deep learning |
| `numpy` | 2.4.6+ | Operaciones vectoriales |
| `scikit-learn` | 1.8.0+ | TF-IDF baseline |
| `streamlit` | 1.57.0+ | UI web interactiva |
| `scipy` | 1.17.1+ | Utilidades matemáticas |

---

## 🔮 Evolución a Producción

Para producción (Sprint 3+), el motor evolucionará a:

```
PostgreSQL + pgvector
      ↓
Embeddings almacenados en tabla `dataset_embeddings`
      ↓
Consulta SQL con `ORDER BY embedding <-> query_embedding`
      ↓
Índice IVFFlat para búsqueda aproximada en millones de registros
```

---

## ✅ Estado

- [x] Motor TF-IDF funcional (v1)
- [x] Motor semántico con embeddings (v2)
- [x] App Streamlit para ambos motores
- [x] Embeddings precalculados para 100 datasets
- [x] Comparativa de rendimiento documentada
- [ ] Integración con PostgreSQL/pgvector (Sprint 3)
- [ ] Fine-tuning del modelo (Sprint 4)

---

## 📝 Notas

- **Datos**: Muestra de 100 datasets reales de datos.gob.es (Canarias y Aragón)
- **Modelo**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384D)
- **Rendimiento**: ~5ms por búsqueda en CPU con embeddings precalculados
- **Memoria**: ~150KB para embeddings de 100 datasets (~1.5MB para 1000 datasets)
