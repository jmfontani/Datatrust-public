#!/usr/bin/env python3
"""
Backend API V2 - Versión Final con Mejoras de Calidad
=====================================================

Mejoras implementadas:
1. Stop words filtering
2. Expansión de sinónimos con OR para palabras ambiguas
3. Filtrado post-proceso para palabras ambiguas (ej: paro vs parada)
4. Validación semántica con embeddings reales (sentence-transformers)
5. Configuración automática de PostgreSQL desde .env
6. Búsqueda híbrida: semántica (pgvector) + léxica (tsvector)

Autor: Fonta
Fecha: 2026-05-25
"""

import sys
from pathlib import Path
import json
import ast
import logging
import time
import re
import os

# Configurar logging primero
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "db"))

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================
# CORS - Permitir conexiones desde el frontend
# ============================================
from fastapi.middleware.cors import CORSMiddleware

# ============================================
# STOP WORDS EN ESPAÑOL
# ============================================

STOP_WORDS = {
    'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
    'y', 'o', 'pero', 'si', 'no', 'en', 'de', 'del', 'al',
    'con', 'por', 'para', 'desde', 'hasta', 'entre', 'sobre',
    'tras', 'durante', 'mediante', 'excepto', 'salvo',
    'a', 'ante', 'bajo', 'segun', 'según', 'sin', 'so',
    'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
    'aquel', 'aquella', 'aquellos', 'aquellas',
    'que', 'cual', 'cuales', 'quien', 'quienes', 'cuyo', 'cuya',
    'como', 'cuando', 'donde', 'adonde', 'cuanto', 'cuanta',
    'yo', 'tu', 'tú', 'el', 'ella', 'nosotros', 'vosotros', 'ellos',
    'me', 'te', 'se', 'nos', 'os', 'lo', 'la', 'le', 'les',
    'mi', 'mis', 'tu', 'tus', 'su', 'sus', 'nuestro', 'vuestro',
    'suyo', 'mio', 'mío', 'tuyo', 'tuyo',
    'es', 'son', 'era', 'fue', 'ser', 'estar', 'está', 'están',
    'hay', 'hubo', 'ha', 'han', 'habia', 'había',
    'muy', 'mas', 'más', 'menos', 'todo', 'toda', 'todos', 'todas',
    'algo', 'alguien', 'alguno', 'alguna', 'ninguno', 'ninguna',
    'otro', 'otra', 'otros', 'otras', 'mismo', 'misma', 'mismos', 'mismas',
    'tal', 'tales', 'cual', 'cuales', 'donde', 'cuando',
    'bien', 'mal', 'tal', 'tan', 'tanto', 'tanta',
    'sí', 'no', 'tambien', 'también', 'ya', 'aun', 'aún', 'ain',
    'ni', 'sino', 'excepto', 'incluso', 'inclus',
}

# ============================================
# PALABRAS AMBIGUAS Y SUS CORRECCIONES
# ============================================

PALABRAS_AMBIGUAS = {
    'paro': {
        'contexto': 'empleo desempleo',
        'sinonimos': ['desempleo', 'desempleado', 'parados', 'tasa de paro', 'atur', 'aturado'],
        'stop_patterns': ['parada', 'paradas', 'parador'],
        'boost_keywords': ['desempleo', 'desempleado', 'parados', 'tasa', 'tasa de paro', 'atur'],
    },
    'calle': {
        'contexto': 'urbanismo vial',
        'sinonimos': ['tráfico', 'vial', 'carretera', 'avenida'],
        'stop_patterns': ['calles', 'callejero'],
        'boost_keywords': ['tráfico', 'vial', 'carretera', 'avenida'],
    },
    'banco': {
        'contexto': 'finanzas economía',
        'sinonimos': ['financiero', 'monetario', 'crédito', 'dinero'],
        'stop_patterns': ['bancos', 'bancaria'],
        'boost_keywords': ['financiero', 'monetario', 'crédito', 'dinero'],
    },
    'mesa': {
        'contexto': 'educación reunión',
        'sinonimos': ['educativa', 'reunión', 'organización'],
        'stop_patterns': ['mesas'],
        'boost_keywords': ['educativa', 'reunión', 'organización'],
    },
}

# ============================================
# EXPANSION DE SINONIMOS
# ============================================

SINONIMOS = {
    'paro': ['desempleo', 'desempleado', 'parados', 'tasa de paro', 'atur', 'aturado'],
    'educacion': ['enseñanza', 'escuela', 'universidad', 'estudios', 'formación'],
    'hospital': ['centro sanitario', 'clínica', 'salud', 'sanitario'],
    'trafico': ['transporte', 'carretera', 'vial', 'circulación', 'movilidad'],
    'contaminacion': ['calidad del aire', 'emisiones', 'polución', 'medio ambiente'],
    'covid': ['coronavirus', 'pandemia', 'sars-cov-2', 'sanidad'],
    'pib': ['producto interior bruto', 'economía', 'crecimiento', 'gdp'],
    'turismo': ['viajeros', 'hospedaje', 'hotel', 'ocio', 'vacaciones'],
    'vivienda': ['casa', 'hogar', 'residencial', 'edificación', 'construcción'],
    'censo': ['población', 'demografía', 'habitantes', 'censos', 'padrón'],
    'delitos': ['criminalidad', 'infracciones', 'penales'],
    'bibliotecas': ['biblioteca', 'libros', 'lectura', 'cultura', 'archivos'],
    'hoteles': ['hotel', 'alojamiento', 'hostelería', 'turismo', 'establecimientos hoteleros'],
    'museos': ['museo', 'arte', 'exposiciones', 'cultura', 'patrimonio'],
    'policia': ['policía', 'seguridad', 'fuerzas del orden', 'delincuencia', 'protección'],
    'empresas': ['empresa', 'negocios', 'compañías', 'economía', 'comercio'],
    'poblacion': ['habitantes', 'demografía', 'censo', 'población', 'residentes'],
}


def limpiar_stop_words(query: str) -> str:
    """Elimina stop words de la query."""
    words = query.lower().split()
    cleaned = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    return ' '.join(cleaned) if cleaned else query


def detectar_palabra_ambigua(query: str) -> tuple:
    """Detecta si la query contiene palabras ambiguas."""
    words = query.lower().split()
    for word in words:
        if word in PALABRAS_AMBIGUAS:
            return True, word, PALABRAS_AMBIGUAS[word]
    return False, None, None


# ============================================
# MAPEO DE TERRITORIOS
# ============================================
TERRITORIO_MAP = {
    'madrid': ['%Madrid%', '%madrid%'],
    'comunidad de madrid': ['%Madrid%', '%madrid%'],
    'cantabria': ['%Cantabria%', '%cantabria%'],
    'pais vasco': ['%Pais-Vasco%', '%pais-vasco%', '%País Vasco%'],
    'euskadi': ['%Pais-Vasco%', '%pais-vasco%'],
    'aragon': ['%Aragon%', '%aragon%', '%Aragón%'],
    'navarra': ['%Navarra%', '%navarra%'],
    'cataluna': ['%Cataluna%', '%cataluna%', '%Cataluña%'],
    'cataluña': ['%Cataluna%', '%cataluna%', '%Cataluña%'],
    'galicia': ['%Galicia%', '%galicia%'],
    'asturias': ['%Asturias%', '%asturias%'],
    'castilla y leon': ['%Castilla-Leon%', '%castilla-leon%'],
    'castilla la mancha': ['%Castilla-La-Mancha%', '%castilla-la-mancha%'],
    'malaga': ['%Malaga%', '%malaga%', '%Málaga%'],
    'zaragoza': ['%Zaragoza%', '%zaragoza%', '%Saragossa%'],
    'españa': ['%España%', '%españa%', '%Pais/España%'],
    'espana': ['%España%', '%españa%', '%Pais/España%'],
    'barcelona': ['%ESP_BCN%', '%barcelona%', '%Barcelona%'],
    'valencia': ['%Valencia%', '%valencia%'],
    'andalucia': ['%Andalucia%', '%andalucia%', '%Andalucía%'],
    'extremadura': ['%Extremadura%', '%extremadura%'],
    'la rioja': ['%Rioja%', '%rioja%'],
    'murcia': ['%Murcia%', '%murcia%'],
    'canarias': ['%Canarias%', '%canarias%'],
    'baleares': ['%Balears%', '%balears%', '%Baleares%'],
    'illes balears': ['%Balears%', '%balears%'],
}


def detectar_territorio_query(query: str) -> tuple:
    """Detecta si la query menciona un territorio. Devuelve (territorio_filtro, query_sin_territorio)."""
    query_lower = query.lower()
    for nombre, patterns in sorted(TERRITORIO_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if nombre in query_lower:
            # Remover el nombre del territorio de la query
            query_clean = query_lower.replace(nombre, '').strip()
            return patterns, query_clean
    return None, query


# ============================================
# BUSQUEDA: PARAMETROS DE ESCALA (NO CAMBIAR SIN MEDIR)
# ============================================
# BUG CORREGIDO (25-sep-2026): el ranking dependia de `top_k`.
#
# Antes: los dos motores recuperaban `LIMIT top_k * 3` y luego normalizaban
# dividiendo por el MAXIMO DEL CONJUNTO RECUPERADO:
#     max_rank = max(rank de las filas traidas);  r['rank'] /= max_rank
# Cambiar `top_k` cambiaba el corte, el maximo y TODOS los scores, asi que el
# ranking se reorganizaba. Medido: el primer resultado cambiaba en 9/47
# consultas (19 %) y el top-5 en 21/47 (45 %).
#
# Detalle que agravaba el bug: la normalizacion estaba guardada tras
# `if max_rank > 1.0`, asi que solo se aplicaba cuando el maximo del corte
# pasaba de 1 (ts_rank_cd suele quedarse por debajo). El comportamiento era
# inconsistente POR CONSULTA, no solo por top_k.
#
# Ahora: la escala lexica se fija con una funcion del score SOLA, sin depender
# de que ni cuantas filas entren en el corte. `rank/(rank+k)` es monotona,
# acotada en [0,1) y no saturada.
#
# `k` no es arbitrario: se eligio con la distribucion real de ts_rank_cd medida
# sobre las 47 consultas del ground truth (script 116, entregables/
# ts_rank_distribucion.json). El maximo por consulta va de 0,0008 a 13,40
# (mediana 0,74); con k=0,2 el maximo tipico queda en 0,79 y la mediana en 0,21,
# o sea la misma escala relativa de antes sin heredar su dependencia del corte.
LEXICAL_RANK_K = 0.2

# Recorte interno de cada motor. Antes era `top_k * 3`, y era parte del bug: un
# corte pequeno hace inestable la magnitud recuperada. Ahora es un suelo
# generoso e INDEPENDIENTE de top_k; el recorte visible a `top_k` se aplica una
# sola vez, al final, tras fusionar los dos motores.
DEFAULT_INTERNAL_LIMIT = 150


def normalizar_rank_lexico(raw: float) -> float:
    """
    Lleva ts_rank_cd a [0,1) con una funcion del score SOLA.

    No depende del conjunto recuperado, asi que el valor de una fila no cambia
    porque se pidan mas o menos resultados. Ver el bug documentado arriba.
    """
    raw = max(0.0, float(raw))
    return raw / (raw + LEXICAL_RANK_K)


# ============================================
# EXPANSION CONTEXTUAL PARA QUERIES DE 1 PALABRA
# ============================================
# Para queries cortas, añadimos contexto semántico que guíe los embeddings
CONTEXTUAL_EXPAND = {
    'censo': 'censo población demografía habitantes',
    'delitos': 'delitos criminalidad infracciones penales seguridad',
    'bibliotecas': 'bibliotecas cultura ocio lectura archivos',
    'hoteles': 'hoteles turismo alojamiento hostelería',
    'museos': 'museos cultura ocio arte exposiciones patrimonio',
    'paro': 'paro desempleo desempleo tasa de paro atur',
    'poblacion': 'población demografía censo habitantes residentes',
    'policia': 'policía seguridad fuerzas del orden protección',
    'empresas': 'empresas economía negocios compañías comercio',
}

def expandir_query(query: str, is_ambiguous: bool = False, ambiguous_info: dict = None) -> str:
    """Expande la query con sinónimos y contexto para mejorar recall."""
    original_query = query.lower().strip()
    words = original_query.split()
    expanded = set(words)
    
    # Para queries de 1 palabra, añadir contexto semántico
    if len(words) == 1 and original_query in CONTEXTUAL_EXPAND:
        expanded.update(CONTEXTUAL_EXPAND[original_query].split())
    
    for word in words:
        if word in SINONIMOS:
            expanded.update(SINONIMOS[word])
        
        if is_ambiguous and ambiguous_info and word in PALABRAS_AMBIGUAS:
            expanded.update(ambiguous_info['sinonimos'])
    
    # Eliminar duplicados manteniendo el orden original aproximado.
    # OJO: recorrer `expanded` (un set) directamente NO es determinista: el orden de
    # iteracion de un set de str depende de PYTHONHASHSEED, que es aleatorio en cada
    # arranque del proceso. Eso cambia el texto expandido (y por tanto el vector) en
    # cada reinicio. Medido en Fase G: reordenar los sinonimos mueve el vector con
    # coseno 0,990-0,994 en BGE y 0,978-0,992 en MiniLM, suficiente para alterar el
    # ranking de 14 de las 214 consultas. Se ordena para que sea reproducible.
    result = [w for w in words]  # palabras originales primero
    for w in sorted(expanded):
        if w not in result:
            result.append(w)
    
    return ' '.join(result)


# ============================================
# FUNCION DE BUSQUEDA MEJORADA PARA PALABRAS AMBIGUAS
# ============================================

def buscar_con_filtro_ambiguo(conn, query: str, ambiguous_info: dict, limit: int = 5, where_clauses=None, params=None):
    """
    Búsqueda especial para palabras ambiguas usando OR y filtrado post-proceso.
    
    Estrategia:
    1. Buscar con OR (|) de la palabra + sinónimos
    2. Recuperar top 20 resultados
    3. Filtrar: incluir solo si contiene términos positivos y NO negativos
    4. Devolver top N resultados filtrados
    """
    sinonimos = ambiguous_info.get('sinonimos', [])
    stop_patterns = ambiguous_info.get('stop_patterns', [])

    # Construir tsquery con OR usando plainto_tsquery() para manejar frases con espacios
    terminos_list = [query] + sinonimos
    tsquery_parts = [f"plainto_tsquery('spanish', %s)" for _ in terminos_list]
    tsquery_or = ' || '.join(tsquery_parts)

    # Aplicar filtros WHERE si se pasan (territorio, tema, etc.)
    extra_where = ""
    extra_params = []
    if where_clauses and len(where_clauses) > 1:  # more than just "1=1"
        extra_where = " AND " + " AND ".join(where_clauses[1:])  # skip "1=1"
        extra_params = list(params) if params else []

    with conn.cursor() as cur:
        query_sql = f"""
            SELECT
                dataset_id, title, description, publisher, theme, territory, format,
                ts_rank_cd(search_vector, ({tsquery_or})) as rank
            FROM datasets
            WHERE search_vector @@ ({tsquery_or}){extra_where}
            ORDER BY ts_rank_cd(search_vector, ({tsquery_or})) DESC
            LIMIT 20
        """
        # Orden de los placeholders del SQL: SELECT(N) -> WHERE tsquery(N) ->
        # extra_where(M) -> ORDER BY(N). Si los extra van al final, PostgreSQL
        # recibe los valores del filtro en el WHERE (territory ILIKE 'paro') y
        # devuelve 0 filas sin error. Deben ir en su posicion.
        cur.execute(
            query_sql,
            tuple(terminos_list * 2) + tuple(extra_params) + tuple(terminos_list),
        )
        
        results = []
        for row in cur.fetchall():
            title = (row[1] or '').lower()
            desc = (row[2] or '').lower()
            
            # Verificar si contiene patrones de parada (negativos)
            has_stop = any(pat in title or pat in desc for pat in stop_patterns)
            
            # Verificar si contiene términos positivos
            has_positive = any(
                kw in title or kw in desc 
                for kw in [query] + sinonimos
            )
            
            if has_positive and not has_stop:
                results.append({
                    "id": row[0],
                    "title": row[1] or "Sin título",
                    "description": (row[2] or "")[:200],
                    "theme": row[4] or "",
                    "territory": row[5] or "",
                    "score": float(row[7]),
                })
                if len(results) >= limit:
                    break
        
        return results


# ============================================
# CONFIGURACION DB - DETECCION AUTOMATICA
# ============================================

# Detectar si estamos en Docker (conectando por nombre de servicio: 'postgres')
# o en local (conectando por: 'localhost')
# En Docker: docker-compose.yml configura POSTGRES_HOST=postgres
# En local: valor por defecto 'localhost'
# FUERA de Docker (este contenedor OpenClaw): PostgreSQL está en 172.17.0.1
DB_HOST = os.getenv('POSTGRES_HOST', '172.17.0.1')  # IP del host Docker desde contenedor
DB_PORT = int(os.getenv('POSTGRES_PORT', '5432'))
DB_NAME = os.getenv('POSTGRES_DB', 'buscador')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'postgres')

# Fallback: leer de archivo .env si existe
ENV_FILE = Path(__file__).parent.parent / "docker" / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith('POSTGRES_PASSWORD='):
                DB_PASSWORD = line.split('=', 1)[1]
            elif line.startswith('POSTGRES_HOST='):
                DB_HOST = line.split('=', 1)[1]
            elif line.startswith('POSTGRES_PORT='):
                DB_PORT = int(line.split('=', 1)[1])
            elif line.startswith('POSTGRES_DB='):
                DB_NAME = line.split('=', 1)[1]
            elif line.startswith('POSTGRES_USER='):
                DB_USER = line.split('=', 1)[1]

DB_CONFIG = {
    "host": DB_HOST,
    "port": DB_PORT,
    "database": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
}

logger.info(f"Configuración DB: host={DB_HOST}, port={DB_PORT}, db={DB_NAME}")

# ============================================
# CONFIGURACION DE EMBEDDINGS
# ============================================

# Modelo de embeddings: nombre COMPLETO y REVISION FIJADA.
# El nombre corto ('paraphrase-multilingual-MiniLM-L12-v2') lo resolvia una
# heuristica de sentence-transformers, y al no fijar revision se descargaba la
# rama 'main', que es un puntero movil: un rebuild podia traer pesos distintos
# bajo el mismo nombre y los embeddings guardados dejaban de corresponderse.
# La revision es el commit de HuggingFace validado con el catalogo actual.
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"

# ============================================================
# MOTOR DE EMBEDDINGS (Fase G/H — despliegue de BGE-M3)
# Por variable de entorno, con el comportamiento historico como DEFECTO:
#   EXPERIMENTO_MOTOR   = "minilm" | "bge"      (defecto: minilm)
#   EXPERIMENTO_COLUMNA = columna de `datasets` (defecto: embedding)
# Con "minilm" esta version se comporta EXACTAMENTE como antes del cambio.
# Vuelta atras sin rebuild: EXPERIMENTO_MOTOR=minilm EXPERIMENTO_COLUMNA=embedding
# ============================================================
import os as _os
EXPERIMENTO_MOTOR = _os.getenv("EXPERIMENTO_MOTOR", "minilm").strip().lower()
EXPERIMENTO_COLUMNA = _os.getenv("EXPERIMENTO_COLUMNA", "embedding").strip()
OLLAMA_EMBED_URL = _os.getenv("OLLAMA_EMBED_URL", "http://172.17.0.1:11434/api/embed")

EMBEDDING_MODEL = None
USE_REAL_EMBEDDINGS = False

if EXPERIMENTO_MOTOR == "bge":
    # BGE-M3 no se sirve local: se vectoriza via ollama (GPU AMD/ROCm del host).
    logger.info("Motor de embeddings: BGE-M3 via ollama (columna %s)", EXPERIMENTO_COLUMNA)
    USE_REAL_EMBEDDINGS = True
else:
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Cargando modelo de embeddings...")
        EMBEDDING_MODEL = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)
        USE_REAL_EMBEDDINGS = True
        logger.info(f"✅ Modelo de embeddings cargado: {MODEL_NAME}@{MODEL_REVISION[:8]}")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo cargar sentence-transformers: {e}")
        logger.warning("Se usarán embeddings aleatorios para demo")

# ============================================
# APLICACION FASTAPI
# ============================================

app = FastAPI(
    title="Buscador Semántico de Datasets (PostgreSQL + pgvector) - V2.2",
    description="API de búsqueda híbrida con stop words, sinónimos y validación semántica",
    version="2.2.0",
)

# Configurar CORS - Permitir peticiones desde cualquier origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# V10: Router LLM Optimizado (Re-ranking desactivado)
# ============================================
try:
    from routes_v10 import router_v10
    app.include_router(router_v10)
    logger.info("V10: Router LLM Optimizado cargado correctamente (fast search + explain on-demand)")
except ImportError as e:
    logger.error(f"V10: Router LLM Optimizado no disponible: {e}")

# ============================================
# V09: Router LLM (Endpoints separados) - DESACTIVADO
# ============================================
# Comentar para evitar conflicto de rutas con V10
# try:
#     from routes_v09 import router_v09
#     app.include_router(router_v09)
#     logger.info("V09: Router LLM cargado correctamente (LEGACY)")
# except ImportError as e:
#     logger.warning(f"V09: Router LLM no disponible: {e}")

# ============================================
# Enhanced Query Processing (#3, #4, #12)
# ============================================
try:
    from routes_query_enhanced import router_query_enhanced
    app.include_router(router_query_enhanced)
    logger.info("Query Enhanced: Router cargado correctamente (#3, #4, #12)")
except ImportError as e:
    logger.warning(f"Query Enhanced: Router no disponible: {e}")

# ============================================
# Sprint 8: Datasets Complementarios (#5)
# ============================================
try:
    from routes_complementary import router_complementary
    app.include_router(router_complementary)
    logger.info("Sprint 8: Complementarios router cargado correctamente (#5)")
except ImportError as e:
    logger.warning(f"Sprint 8: Complementarios router no disponible: {e}")

# ============================================
# Sprint 8: Chat sobre datasets (#10)
# ============================================
try:
    from routes_dataset_chat import router_dataset_chat
    app.include_router(router_dataset_chat)
    logger.info("Sprint 8: Dataset Chat router cargado correctamente (#10)")
except ImportError as e:
    logger.warning(f"Sprint 8: Dataset Chat router no disponible: {e}")

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def get_db_connection():
    """Crea conexión a PostgreSQL."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Error conectando a PostgreSQL: {e}")
        return None


def _embed_bge(text: str) -> list:
    """Embedding con BGE-M3 (1024 dims) via ollama.

    Devuelve la LISTA directamente, no el .tolist() de un ndarray: ollama ya
    devuelve JSON, y encadenar .tolist() lanzaba AttributeError que caia en el
    fallback de vector aleatorio (cero resultados, en silencio).
    """
    import urllib.request as _ur
    body = json.dumps({"model": "bge-m3", "input": [text],
                       "options": {"num_ctx": 1024}}).encode()
    req = _ur.Request(OLLAMA_EMBED_URL, data=body,
                      headers={"Content-Type": "application/json"})
    d = json.loads(_ur.urlopen(req, timeout=300).read())
    return d["embeddings"][0]


def get_embedding(text: str) -> list:
    """Genera embedding para un texto usando el motor activo."""
    # Con BGE no hay modelo local (EMBEDDING_MODEL es None por diseno), asi que
    # esta guarda NO debe exigirlo: si se exige, aborta y devuelve en silencio
    # un vector aleatorio de 384 dims que no compara contra una columna de 1024.
    if EXPERIMENTO_MOTOR == "bge":
        try:
            return _embed_bge(text)
        except Exception as e:
            logger.error(f"Error generando embedding BGE-M3: {e}")
            raise

    if not USE_REAL_EMBEDDINGS or not EMBEDDING_MODEL:
        logger.warning("Usando embedding aleatorio (modelo no disponible)")
        import random
        return [random.uniform(-0.1, 0.1) for _ in range(384)]
    
    try:
        embedding = EMBEDDING_MODEL.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error generando embedding: {e}")
        import random
        return [random.uniform(-0.1, 0.1) for _ in range(384)]


def vector_to_pgvector(emb_list: list) -> str:
    """Convierte una lista de floats a string de pgvector."""
    return '[' + ','.join(str(x) for x in emb_list) + ']'


# ============================================
# MODELOS DE DATOS
# ============================================

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Consulta de búsqueda")
    top_k: int = Field(default=10, ge=1, le=100, description="Número de resultados")
    semantic_weight: float = Field(default=0.7, ge=0, le=1, description="Peso semántico")
    lexical_weight: float = Field(default=0.3, ge=0, le=1, description="Peso léxico")
    min_score: float = Field(default=0.15, ge=0, le=1, description="Score mínimo de relevancia")
    territorio: Optional[str] = Field(default=None, description="Filtrar por territorio")
    tema: Optional[str] = Field(default=None, description="Filtrar por tema")
    formato: Optional[str] = Field(default=None, description="Filtrar por formato")
    publisher: Optional[str] = Field(default=None, description="Filtrar por publisher")
    explain: bool = Field(default=True, description="Incluir explicaciones")
    use_synonyms: bool = Field(default=True, description="Usar expansión de sinónimos")
    remove_stopwords: bool = Field(default=True, description="Eliminar stop words")

    # ============================================
    # EXPERIMENTAL: Normalización Conceptual
    # ============================================
    # NO activar por defecto - solo para pruebas experimentales
    conceptual_normalization: bool = Field(
        default=False,
        description="[EXPERIMENTAL] Activar normalización conceptual de queries"
    )
    conceptual_adjust_scores: bool = Field(
        default=False,
        description="[EXPERIMENTAL] Ajustar scores según clasificación conceptual"
    )


class SearchResponse(BaseModel):
    query: str
    expanded_query: Optional[str]
    filters: Dict
    total_results: int
    returned_results: int
    semantic_weight: float
    lexical_weight: float
    search_time_ms: float
    results: List[Dict]
    warnings: Optional[List[str]]

    # ============================================
    # EXPERIMENTAL: Metadatos de Normalización Conceptual
    # ============================================
    # Solo se incluyen cuando conceptual_normalization=True
    conceptual_normalization_active: bool = Field(default=False)
    detected_concept: Optional[Dict] = Field(default=None)


# ============================================
# ENDPOINTS
# ============================================

@app.on_event("startup")
async def startup_event():
    """Verifica conexión a PostgreSQL al iniciar."""
    logger.info("Verificando conexión a PostgreSQL...")
    conn = get_db_connection()
    if conn:
        logger.info("✅ Conectado a PostgreSQL")
        conn.close()
    else:
        logger.error("❌ No se pudo conectar a PostgreSQL")


@app.get("/", include_in_schema=False)
def root():
    """Redirige a la documentación."""
    return {"message": "Buscador Semántico V2.2", "docs": "/docs"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="PostgreSQL no disponible")
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM datasets")
            count = cur.fetchone()[0]
            
            cur.execute("SELECT version()")
            pg_version = cur.fetchone()[0]
            
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            has_pgvector = cur.fetchone() is not None
            
            return {
                "status": "ok",
                "postgresql": "connected",
                "pg_version": pg_version.split()[1] if pg_version else "unknown",
                "pgvector": has_pgvector,
                "datasets_count": count,
                "embedding_model": (
                    f"{EXPERIMENTO_MOTOR} ({EXPERIMENTO_COLUMNA})"
                    if USE_REAL_EMBEDDINGS else "random"
                ),
                "motor": {
                    "nombre": EXPERIMENTO_MOTOR,
                    "columna": EXPERIMENTO_COLUMNA,
                    "dim": 1024 if EXPERIMENTO_MOTOR == "bge" else 384,
                    "revision": MODEL_REVISION if EXPERIMENTO_MOTOR != "bge" else "bge-m3 (ollama)",
                },
                "features": {
                    "stop_words": True,
                    "synonyms": True,
                    "semantic_validation": USE_REAL_EMBEDDINGS,
                    "ambiguous_word_filtering": True,
                }
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error PostgreSQL: {e}")
    finally:
        conn.close()


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    """
    Búsqueda híbrida mejorada con:
    - Eliminación de stop words
    - Expansión de sinónimos
    - Detección de palabras ambiguas con filtrado post-proceso
    - Validación semántica con embeddings
    - [EXPERIMENTAL] Normalización conceptual de queries
    """
    start = time.perf_counter()
    warnings = []

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="No se pudo conectar a PostgreSQL")

    try:
        # ==========================================
        # PREPROCESAMIENTO DE LA QUERY
        # ==========================================
        original_query = request.query
        processed_query = original_query

        # ==========================================
        # [EXPERIMENTAL] Normalización Conceptual
        # ==========================================
        detected_concept = None
        conceptual_expansion_applied = False

        if request.conceptual_normalization:
            try:
                from motor.concept_normalizer import detect_concept, build_conceptual_expansion

                detected_concept = detect_concept(original_query)
                if detected_concept:
                    # Expandir query con equivalentes del concepto
                    expanded_concept_query = build_conceptual_expansion(
                        original_query, detected_concept
                    )
                    if expanded_concept_query != original_query:
                        processed_query = expanded_concept_query
                        conceptual_expansion_applied = True
                        logger.info(
                            f"[CONCEPTUAL] Query: '{original_query}' → "
                            f"concepto='{detected_concept['concept_label']}' → "
                            f"'{expanded_concept_query}'"
                        )
            except ImportError as e:
                logger.warning(f"[CONCEPTUAL] Módulo no disponible: {e}")
            except Exception as e:
                logger.warning(f"[CONCEPTUAL] Error en normalización conceptual: {e}")

        # Detectar palabras ambiguas
        is_ambiguous, ambiguous_word, ambiguous_info = detectar_palabra_ambigua(original_query)
        if is_ambiguous:
            warnings.append(f"⚠️ Palabra ambigua detectada: '{ambiguous_word}'. Usando filtrado especial.")
            logger.info(f"Palabra ambigua: {ambiguous_word}, aplicando filtrado post-proceso")

        # Detectar territorio en la query
        detected_territorio, query_sin_territorio = detectar_territorio_query(original_query)
        if detected_territorio:
            warnings.append(f"📍 Territorio detectado en query. Filtrando resultados.")
            logger.info(f"Territorio detectado en query: {detected_territorio}")
            # Usar la query sin el nombre del territorio para mejor búsqueda semántica
            processed_query = query_sin_territorio

        # Eliminar stop words
        if request.remove_stopwords:
            processed_query = limpiar_stop_words(processed_query)
            if processed_query != original_query:
                logger.info(f"Query limpiada: '{original_query}' → '{processed_query}'")

        # Expandir con sinónimos (solo si no se aplicó expansión conceptual)
        expanded_query = processed_query
        if request.use_synonyms and not conceptual_expansion_applied:
            expanded_query = expandir_query(processed_query, is_ambiguous, ambiguous_info)
            if expanded_query != processed_query:
                logger.info(f"Query expandida: '{processed_query}' → '{expanded_query}'")
        
        # Normalizar pesos
        total_weight = request.semantic_weight + request.lexical_weight
        sem_w = request.semantic_weight / total_weight
        lex_w = request.lexical_weight / total_weight
        
        results = []
        all_results = {}
        
        # Construir filtros WHERE
        where_clauses = ["1=1"]
        params = []
        
        # Filtro por territorio (explicito o detectado en query)
        territorio_filter = request.territorio
        territorio_patterns = None
        if territorio_filter:
            # Usar ILIKE para matching flexible (la BD guarda URLs, no nombres)
            where_clauses.append("(territory ILIKE %s OR territory_label ILIKE %s)")
            params.extend([f"%{territorio_filter}%", f"%{territorio_filter}%"])
        elif detected_territorio:
            # Usar ILIKE con los patrones detectados
            territorio_patterns = detected_territorio
            or_clauses = []
            for pattern in territorio_patterns:
                or_clauses.append("territory ILIKE %s")
                or_clauses.append("territory_label ILIKE %s")
                params.extend([pattern, pattern])
            where_clauses.append(f"({' OR '.join(or_clauses)})")
        if request.tema:
            where_clauses.append("theme = %s")
            params.append(request.tema)
        if request.formato:
            # Usar subquery sobre dataset_formats para filtrar.
            # OJO: 'dataset_id' sin prefijo es AMBIGUO (datasets y dataset_formats lo tienen)
            # y PostgreSQL aborta la consulta; hay que cualificarlo con d.
            where_clauses.append("""
                d.dataset_id IN (
                    SELECT dataset_id FROM dataset_formats WHERE format = %s
                )
            """)
            params.append(request.formato)
        if request.publisher:
            where_clauses.append("publisher = %s")
            params.append(request.publisher)
        
        where_sql = " AND ".join(where_clauses)
        
        # ==========================================
        # BÚSQUEDA SEMÁNTICA con pgvector
        # ==========================================
        if sem_w > 0:
            try:
                query_embedding = get_embedding(expanded_query)
                query_vector_str = vector_to_pgvector(query_embedding)
                
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # FASE H (01-oct): probada la reescritura con indice HNSW (30 ms).
                    # Medido sobre el GT v5 canonico: el ranking con HNSW no es
                    # equivalente al exacto (nDCG 0,5260 vs 0,5575, pareada -0,0315
                    # DISTINGUIBLE). La latencia (~2,5s) es el precio del exacto;
                    # el fix se RETIRA: se mantiene la SQL con JOIN+GROUP BY.
                    # Si se quiere latencia baja SIN cambiar rankings: reindexar con
                    # ef_construction mayor + ef_search alto, o usar la columna
                    # `embedding_minilm_aprox` como referencia.
                    cur.execute(f"""
                        SELECT
                            d.dataset_id, d.title, d.description, d.publisher, d.theme, d.territory,
                            d.url, d.language, d.license, d.frequency, d.temporal_coverage,
                            COALESCE(array_agg(DISTINCT df.format) FILTER (WHERE df.format IS NOT NULL), ARRAY[]::TEXT[]) as formatos,
                            1 - (d.{EXPERIMENTO_COLUMNA} <=> '{query_vector_str}'::vector) as similarity
                        FROM datasets d
                        LEFT JOIN dataset_formats df ON d.dataset_id = df.dataset_id
                        WHERE {where_sql}
                        GROUP BY d.dataset_id, d.title, d.description, d.publisher, d.theme, d.territory,
                                 d.url, d.language, d.license, d.frequency, d.temporal_coverage, d.{EXPERIMENTO_COLUMNA}
                        ORDER BY d.{EXPERIMENTO_COLUMNA} <=> '{query_vector_str}'::vector
                        LIMIT %s
                    """, tuple(params + [max(DEFAULT_INTERNAL_LIMIT, request.top_k * 3)]))

                    for row in cur.fetchall():
                        score = float(row['similarity'])
                        if score >= request.min_score:
                            ds_id = row['dataset_id']
                            if ds_id not in all_results:
                                all_results[ds_id] = {
                                    "id": ds_id,
                                    "score": round(score * sem_w, 4),
                                    "title": row['title'] or "Sin título",
                                    "description": (row['description'] or "")[:200],
                                    "territorio": [row['territory']] if row['territory'] else [],
                                    "tema": [row['theme']] if row['theme'] else [],
                                    "formato": row['formatos'] if row['formatos'] else [],
                                    "publisher": row['publisher'] or "Desconocido",
                                    "url": row['url'] or "",
                                    "language": row['language'] or "es",
                                    "license": row['license'] or "",
                                    "frequency": row['frequency'] or "",
                                    "temporal_coverage": row['temporal_coverage'] or "",
                                    "semantic_score": round(score, 4),
                                    "lexical_score": 0.0,
                                    "explanation": f"Similitud semántica: {score:.1%}"
                                }
                            else:
                                all_results[ds_id]["score"] += round(score * sem_w, 4)
                                all_results[ds_id]["semantic_score"] = round(score, 4)
                                
            except Exception as e:
                logger.error(f"Error en búsqueda semántica: {e}")
                import traceback
                traceback.print_exc()
        
        # ==========================================
        # BÚSQUEDA LÉXICA con TSVECTOR
        # ==========================================
        if lex_w > 0 and expanded_query:
            try:
                # Si es palabra ambigua, usar búsqueda especial con filtrado
                if is_ambiguous and ambiguous_info:
                    logger.info(f"Usando búsqueda especial para palabra ambigua: {ambiguous_word}")
                    lexical_results = buscar_con_filtro_ambiguo(
                        conn, ambiguous_word, ambiguous_info, limit=request.top_k * 3,
                        where_clauses=where_clauses, params=params
                    )
                    
                    # Escala lexica: funcion del score SOLA (ver arriba).
                    for r in lexical_results:
                        r["score"] = normalizar_rank_lexico(r["score"])
                    
                    for result in lexical_results:
                        ds_id = result["id"]
                        score = result["score"]
                        
                        if ds_id in all_results:
                            all_results[ds_id]["score"] += round(score * lex_w, 4)
                            all_results[ds_id]["lexical_score"] = round(score, 4)
                            all_results[ds_id]["explanation"] = (
                                f"Semántica: {all_results[ds_id]['semantic_score']:.1%}, "
                                f"Léxica (filtrada): {score:.1%}"
                            )
                        else:
                            all_results[ds_id] = {
                                "id": ds_id,
                                "score": round(score * lex_w, 4),
                                "title": result["title"],
                                "description": result["description"],
                                "territorio": [result["territory"]] if result["territory"] else [],
                                "tema": [result["theme"]] if result["theme"] else [],
                                "formato": [],
                                "publisher": "Desconocido",
                                "url": "",
                                "language": "es",
                                "license": "",
                                "frequency": "",
                                "temporal_coverage": "",
                                "semantic_score": 0.0,
                                "lexical_score": round(score, 4),
                                "explanation": f"Coincidencia léxica filtrada: {score:.1%}"
                            }
                else:
                    # Búsqueda léxica normal con AND
                    ts_query = " & ".join(expanded_query.split())

                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(f"""
                            SELECT
                                d.dataset_id, d.title, d.description, d.publisher, d.theme, d.territory,
                                d.url, d.language, d.license, d.frequency, d.temporal_coverage,
                                COALESCE(array_agg(DISTINCT df.format) FILTER (WHERE df.format IS NOT NULL), ARRAY[]::TEXT[]) as formatos,
                                ts_rank_cd(d.search_vector, to_tsquery('spanish', %s)) as rank
                            FROM datasets d
                            LEFT JOIN dataset_formats df ON d.dataset_id = df.dataset_id
                            WHERE {where_sql}
                                AND d.search_vector @@ to_tsquery('spanish', %s)
                            GROUP BY d.dataset_id, d.title, d.description, d.publisher, d.theme, d.territory,
                                     d.url, d.language, d.license, d.frequency, d.temporal_coverage, d.search_vector
                            ORDER BY ts_rank_cd(d.search_vector, to_tsquery('spanish', %s)) DESC
                            LIMIT %s
                        """, (ts_query, *params, ts_query, ts_query,
                              max(DEFAULT_INTERNAL_LIMIT, request.top_k * 3)))

                        rows = cur.fetchall()
                        # Escala lexica: funcion del score SOLA (ver arriba).
                        # Antes: dividir por el maximo del conjunto, que hacia
                        # que el ranking dependiera de top_k. La guarda
                        # `if max_rank > 1.0` ademas la aplicaba solo a veces.
                        for r in rows:
                            r['rank'] = normalizar_rank_lexico(float(r['rank']))

                        for row in rows:
                            ds_id = row['dataset_id']
                            score = float(row['rank'])

                            if ds_id in all_results:
                                all_results[ds_id]["score"] += round(score * lex_w, 4)
                                all_results[ds_id]["lexical_score"] = round(score, 4)
                                all_results[ds_id]["explanation"] = (
                                    f"Semántica: {all_results[ds_id]['semantic_score']:.1%}, "
                                    f"Léxica: {score:.1%}"
                                )
                            else:
                                all_results[ds_id] = {
                                    "id": ds_id,
                                    "score": round(score * lex_w, 4),
                                    "title": row['title'] or "Sin título",
                                    "description": (row['description'] or "")[:200],
                                    "territorio": [row['territory']] if row['territory'] else [],
                                    "tema": [row['theme']] if row['theme'] else [],
                                    "formato": row['formatos'] if row['formatos'] else [],
                                    "publisher": row['publisher'] or "Desconocido",
                                    "url": row['url'] or "",
                                    "language": row['language'] or "es",
                                    "license": row['license'] or "",
                                    "frequency": row['frequency'] or "",
                                    "temporal_coverage": row['temporal_coverage'] or "",
                                    "semantic_score": 0.0,
                                    "lexical_score": round(score, 4),
                                    "explanation": f"Coincidencia léxica: {score:.1%}"
                                }
                                
            except Exception as e:
                logger.error(f"Error en búsqueda léxica: {e}")
                import traceback
                traceback.print_exc()
        
        # ==========================================
        # [EXPERIMENTAL] Clasificación y Ajuste Conceptual
        # ==========================================
        if request.conceptual_normalization and detected_concept:
            try:
                from motor.concept_normalizer import (
                    classify_result_conceptually,
                    apply_conceptual_score_adjustment,
                )

                # Clasificar cada resultado conceptualmente
                for result in all_results.values():
                    classification = classify_result_conceptually(
                        result, detected_concept
                    )

                    # Añadir metadatos conceptuales al resultado
                    result['conceptual_relation'] = classification['conceptual_relation']
                    result['conceptual_explanation'] = classification['conceptual_explanation']
                    result['matched_concept_terms'] = classification.get('matched_terms', [])

                    # Ajustar score si se solicita
                    if request.conceptual_adjust_scores:
                        adjusted = apply_conceptual_score_adjustment(result, classification)
                        result['score_original'] = adjusted['score_original']
                        result['score'] = adjusted['score_conceptual_adjusted']

                # Re-ordenar si se ajustaron scores
                if request.conceptual_adjust_scores:
                    results = sorted(
                        all_results.values(),
                        key=lambda x: x.get('score_conceptual_adjusted', x['score']),
                        reverse=True
                    )
                else:
                    results = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)

                logger.info(
                    f"[CONCEPTUAL] {len(results)} resultados clasificados, "
                    f"ajuste={request.conceptual_adjust_scores}"
                )

            except ImportError as e:
                logger.warning(f"[CONCEPTUAL] Módulo no disponible para clasificación: {e}")
            except Exception as e:
                logger.warning(f"[CONCEPTUAL] Error en clasificación conceptual: {e}")
                # Fallback: ordenar por score original
                results = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)
        else:
            # Comportamiento normal sin normalización conceptual
            results = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)

        # Aplicar top_k
        total = len(results)
        results = results[:request.top_k]

        elapsed_ms = (time.perf_counter() - start) * 1000

        # ==========================================
        # RESPUESTA
        # ==========================================
        return SearchResponse(
            query=original_query,
            expanded_query=expanded_query if expanded_query != original_query else None,
            filters={
                "territorio": request.territorio,
                "tema": request.tema,
                "formato": request.formato,
                "publisher": request.publisher,
            },
            total_results=total,
            returned_results=len(results),
            semantic_weight=sem_w,
            lexical_weight=lex_w,
            search_time_ms=round(elapsed_ms, 2),
            results=results,
            warnings=warnings if warnings else None,
            # Metadatos experimentales
            conceptual_normalization_active=request.conceptual_normalization,
            detected_concept=detected_concept,
        )
        
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")
    finally:
        conn.close()


@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str):
    """Obtiene un dataset por su ID."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="PostgreSQL no disponible")
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM datasets WHERE dataset_id = %s
            """, (dataset_id,))
            
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Dataset no encontrado")
            
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        conn.close()


@app.get("/datasets")
def list_datasets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    tema: Optional[str] = None,
    territorio: Optional[str] = None,
):
    """Lista datasets con filtros opcionales."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="PostgreSQL no disponible")
    
    try:
        where_clauses = ["1=1"]
        params = []
        
        if tema:
            where_clauses.append("theme = %s")
            params.append(tema)
        if territorio:
            where_clauses.append("(territory ILIKE %s OR territory_label ILIKE %s)")
            params.extend([f"%{territorio}%", f"%{territorio}%"])
        
        where_sql = " AND ".join(where_clauses)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"""
                SELECT COUNT(DISTINCT d.dataset_id) FROM datasets d
                LEFT JOIN dataset_formats df ON d.dataset_id = df.dataset_id
                WHERE {where_sql}
            """, tuple(params))

            total = cur.fetchone()['count']

            cur.execute(f"""
                SELECT
                    d.dataset_id, d.title, d.description, d.publisher, d.theme, d.territory,
                    d.url, d.language, d.license, d.frequency, d.temporal_coverage,
                    COALESCE(array_agg(DISTINCT df.format) FILTER (WHERE df.format IS NOT NULL), ARRAY[]::TEXT[]) as formatos
                FROM datasets d
                LEFT JOIN dataset_formats df ON d.dataset_id = df.dataset_id
                WHERE {where_sql}
                GROUP BY d.dataset_id, d.title, d.description, d.publisher, d.theme, d.territory,
                         d.url, d.language, d.license, d.frequency, d.temporal_coverage
                ORDER BY d.title
                LIMIT %s OFFSET %s
            """, tuple(params + [limit, offset]))

            datasets = [dict(row) for row in cur.fetchall()]

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "datasets": datasets,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        conn.close()


# ============================================
# ENDPOINTS DE FACETAS
# ============================================

FACET_COLUMN_MAP = {
    # territory guarda URIs (http://.../territorio/Autonomia/Pais-Vasco); territory_label
    # guarda el nombre legible ("País Vasco"). La faceta debe mostrar el nombre.
    "territorio": "territory_label",
    "tema": "theme",
    "formato": "format",
    "publisher": "publisher",
}

@app.get("/facets/{facet_type}")
def get_facet_values(facet_type: str, limit: int = Query(default=100, ge=1, le=500)):
    """Obtiene valores únicos de una faceta (columna) de los datasets."""
    if facet_type not in FACET_COLUMN_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Faceta no válida: '{facet_type}'. Opciones: {list(FACET_COLUMN_MAP.keys())}"
        )
    
    column = FACET_COLUMN_MAP[facet_type]
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="PostgreSQL no disponible")
    
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT {column}, COUNT(*) as freq
                FROM datasets
                WHERE {column} IS NOT NULL AND {column} != ''
                GROUP BY {column}
                ORDER BY freq DESC, {column} ASC
                LIMIT %s
            """, (limit,))
            
            values = [row[0] for row in cur.fetchall()]
            
            return {"values": values}
    except Exception as e:
        logger.error(f"Error obteniendo faceta {facet_type}: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo faceta: {str(e)}")
    finally:
        conn.close()


# ============================================
# ENDPOINTS EXPERIMENTALES
# ============================================

@app.post("/experimental/concept-normalize")
def concept_normalize(query: str):
    """
    [EXPERIMENTAL] Analiza una query y devuelve el concepto detectado + expansión.

    Ejemplo:
        POST /experimental/concept-normalize
        {"query": "paro juvenil por municipio"}

    Response:
        {
            "detected": true,
            "concept_id": "desempleo_juvenil",
            "concept_label": "Desempleo juvenil",
            "expanded_query": "...",
            "equivalentes": [...],
            "relacionados": [...],
            "complementarios": [...],
            "no_equivalentes": [...]
        }
    """
    from motor.concept_normalizer import (
        detect_concept,
        build_conceptual_expansion,
        get_concept_info,
        load_concepts,
    )

    concepts = load_concepts()
    detected = detect_concept(query, concepts)

    if not detected:
        return {
            "detected": False,
            "query": query,
            "message": "No se detectó ningún concepto conocido en la query.",
        }

    # Obtener información completa del concepto
    concept_info = get_concept_info(detected['concept_id'], concepts)

    # Construir expansión
    expanded = build_conceptual_expansion(query, detected, concepts)

    return {
        "detected": True,
        "query": query,
        "concept_id": detected['concept_id'],
        "concept_label": detected['concept_label'],
        "domain": detected['domain'],
        "confidence": detected['confidence'],
        "matched_trigger": detected.get('matched_trigger', ''),
        "expanded_query": expanded,
        "equivalentes": concept_info.get('equivalentes', []) if concept_info else [],
        "relacionados": concept_info.get('relacionados', []) if concept_info else [],
        "complementarios": concept_info.get('complementarios', []) if concept_info else [],
        "no_equivalentes": concept_info.get('no_equivalentes', []) if concept_info else [],
    }


@app.post("/experimental/conceptual-search")
def conceptual_search(request: SearchRequest):
    """
    [EXPERIMENTAL] Wrapper sobre /search con normalización conceptual activada.

    Equivalente a POST /search con:
        - conceptual_normalization: true
        - conceptual_adjust_scores: true

    Los resultados incluyen metadatos conceptuales:
        - conceptual_relation: equivalente | relacionado | complementario | no_equivalente
        - conceptual_explanation: Explicación de la clasificación
        - score_original: Score antes del ajuste
        - score_conceptual_adjusted: Score después del ajuste conceptual
    """
    # Forzar activación de normalización conceptual
    request.conceptual_normalization = True
    request.conceptual_adjust_scores = True

    # Llamar al endpoint search existente
    return search(request)


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
