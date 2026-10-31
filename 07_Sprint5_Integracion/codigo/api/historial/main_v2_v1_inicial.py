#!/usr/bin/env python3
"""
Backend API V2 para el motor de búsqueda híbrida con PostgreSQL.
Versión adaptada para PostgreSQL + pgvector.

Ejecutar:
    uvicorn main_v2:app --host 0.0.0.0 --port 8000

Endpoints:
    POST /search          - Búsqueda híbrida con filtros
    GET /health           - Health check
    GET /facets/{facet}   - Valores disponibles para una faceta
"""
import sys
from pathlib import Path
import json
import ast

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "db"))

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import logging
import time

import psycopg2
from psycopg2.extras import RealDictCursor

# Intentar cargar sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_MODEL = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    logger.info("✅ Modelo de embeddings cargado: paraphrase-multilingual-MiniLM-L12-v2")
    USE_REAL_EMBEDDINGS = True
except Exception as e:
    logger.warning(f"⚠️ No se pudo cargar sentence-transformers: {e}")
    EMBEDDING_MODEL = None
    USE_REAL_EMBEDDINGS = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Buscador Semántico de Datasets (PostgreSQL + pgvector)",
    description="API de búsqueda híbrida con PostgreSQL y pgvector",
    version="2.0.0",
)

# Configuración de conexión PostgreSQL
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "buscador",
    "user": "postgres",
    "password": "postgres",
}


def get_embedding(text: str) -> list:
    """Genera embedding para un texto usando sentence-transformers."""
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


def parse_embedding(emb_str: str) -> list:
    """Parsea un embedding desde string a lista de floats."""
    try:
        if isinstance(emb_str, str):
            return ast.literal_eval(emb_str)
        return emb_str
    except Exception as e:
        logger.error(f"Error parseando embedding: {e}")
        return []


def vector_to_pgvector(emb_list: list) -> str:
    """Convierte una lista de floats a string de pgvector."""
    return '[' + ','.join(str(x) for x in emb_list) + ']'
    """Crea conexión a PostgreSQL."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Error conectando a PostgreSQL: {e}")
        return None


def get_dataset_count() -> int:
    """Obtiene número de datasets en la base de datos."""
    conn = get_db_connection()
    if not conn:
        return 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM datasets")
            return cur.fetchone()[0]
    except Exception as e:
        logger.error(f"Error contando datasets: {e}")
        return 0
    finally:
        conn.close()


# ============================================
# MODELOS DE DATOS
# ============================================

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Consulta de búsqueda")
    top_k: int = Field(default=10, ge=1, le=100, description="Número de resultados")
    semantic_weight: float = Field(default=0.7, ge=0, le=1, description="Peso semántico")
    lexical_weight: float = Field(default=0.3, ge=0, le=1, description="Peso léxico")
    min_score: float = Field(default=0.20, ge=0, le=1, description="Score mínimo de relevancia (0-1)")
    require_lexical_match: bool = Field(default=True, description="Requerir al menos una coincidencia léxica")
    territorio: Optional[str] = Field(default=None, description="Filtrar por territorio")
    tema: Optional[str] = Field(default=None, description="Filtrar por tema")
    formato: Optional[str] = Field(default=None, description="Filtrar por formato")
    publisher: Optional[str] = Field(default=None, description="Filtrar por publisher")
    explain: bool = Field(default=True, description="Incluir explicaciones")


class SearchResponse(BaseModel):
    query: str
    filters: Dict
    total_results: int
    returned_results: int
    semantic_weight: float
    lexical_weight: float
    search_time_ms: float
    results: List[Dict]


# ============================================
# ENDPOINTS
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint con info de PostgreSQL."""
    conn = get_db_connection()
    if not conn:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": "No se pudo conectar a PostgreSQL",
        }
    
    try:
        with conn.cursor() as cur:
            # Verificar extensión pgvector
            cur.execute("SELECT version();")
            pg_version = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM datasets")
            dataset_count = cur.fetchone()[0]
            
            cur.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            has_vector = cur.fetchone()[0]
        
        return {
            "status": "healthy",
            "database": "connected",
            "postgres_version": pg_version,
            "datasets_count": dataset_count,
            "pgvector_installed": has_vector,
        }
    except Exception as e:
        return {
            "status": "degraded",
            "database": "error",
            "error": str(e),
        }
    finally:
        conn.close()


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Realiza una búsqueda híbrida con filtros facetados usando PostgreSQL.
    """
    start = time.perf_counter()
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="No se pudo conectar a PostgreSQL")
    
    try:
        # Normalizar pesos
        total_weight = request.semantic_weight + request.lexical_weight
        sem_w = request.semantic_weight / total_weight
        lex_w = request.lexical_weight / total_weight
        
        results = []
        
        # BÚSQUEDA SEMÁNTICA con pgvector
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Construir query semántica con filtros
            where_clauses = ["1=1"]
            params = []
            
            if request.territorio:
                where_clauses.append("territory = %s")
                params.append(request.territorio)
            if request.tema:
                where_clauses.append("theme = %s")
                params.append(request.tema)
            if request.formato:
                where_clauses.append("format = %s")
                params.append(request.formato)
            if request.publisher:
                where_clauses.append("publisher = %s")
                params.append(request.publisher)
            
            where_sql = " AND ".join(where_clauses)
            
            # Generar embedding de la consulta (simulado - en producción usar sentence-transformers)
            # Para demostración, usamos búsqueda por texto similar
            if sem_w > 0:
                # Formatear vector como string para pgvector
                query_vector_str = '[' + ','.join(['0.1'] * 384) + ']'
                
                cur.execute(f"""
                    SELECT 
                        dataset_id, title, description, publisher, theme, territory, format,
                        url, language, license, frequency, temporal_coverage,
                        1 - (embedding <=> '{query_vector_str}'::vector) as similarity
                    FROM datasets
                    WHERE {where_sql}
                    ORDER BY embedding <=> '{query_vector_str}'::vector
                    LIMIT %s
                """, tuple(params + [request.top_k * 3]))
                
                semantic_results = cur.fetchall()
                
                for row in semantic_results:
                    score = float(row['similarity'])
                    if score >= request.min_score:
                        results.append({
                            "id": row['dataset_id'],
                            "score": round(score * sem_w, 4),
                            "title": row['title'] or "Sin título",
                            "description": (row['description'] or "")[:200],
                            "territorio": [row['territory']] if row['territory'] else [],
                            "tema": [row['theme']] if row['theme'] else [],
                            "formato": [row['format']] if row['format'] else [],
                            "publisher": row['publisher'] or "Desconocido",
                            "url": row['url'] or "",
                            "language": row['language'] or "es",
                            "license": row['license'] or "",
                            "frequency": row['frequency'] or "",
                            "temporal_coverage": row['temporal_coverage'] or "",
                            "semantic_score": round(score, 4),
                            "lexical_score": 0.0,
                            "explanation": f"Similitud semántica: {score:.2%}"
                        })
        
        # BÚSQUEDA LÉXICA con TSVECTOR
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if lex_w > 0 and request.query:
                # Parsear query para tsquery - usar OR en lugar de AND para más resultados
                ts_query = " | ".join(request.query.split())
                
                cur.execute(f"""
                    SELECT 
                        dataset_id, title, description, publisher, theme, territory, format,
                        url, language, license, frequency, temporal_coverage,
                        ts_rank_cd(search_vector, to_tsquery('spanish', %s)) as rank
                    FROM datasets
                    WHERE {where_sql}
                        AND search_vector @@ to_tsquery('spanish', %s)
                    ORDER BY ts_rank_cd(search_vector, to_tsquery('spanish', %s)) DESC
                    LIMIT %s
                """, (ts_query, *params, ts_query, ts_query, request.top_k * 3))
                
                lexical_results = cur.fetchall()
                
                # Fusionar con resultados semánticos
                existing_ids = {r["id"] for r in results}
                
                for row in lexical_results:
                    ds_id = row['dataset_id']
                    score = float(row['rank'])
                    
                    if ds_id in existing_ids:
                        # Actualizar score existente
                        for r in results:
                            if r["id"] == ds_id:
                                r["score"] += round(score * lex_w, 4)
                                r["lexical_score"] = round(score, 4)
                                r["explanation"] += f"; Coincidencia léxica: {score:.2%}"
                                break
                    else:
                        if score >= request.min_score:
                            results.append({
                                "id": ds_id,
                                "score": round(score * lex_w, 4),
                                "title": row['title'] or "Sin título",
                                "description": (row['description'] or "")[:200],
                                "territorio": [row['territory']] if row['territory'] else [],
                                "tema": [row['theme']] if row['theme'] else [],
                                "formato": [row['format']] if row['format'] else [],
                                "publisher": row['publisher'] or "Desconocido",
                                "url": row['url'] or "",
                                "language": row['language'] or "es",
                                "license": row['license'] or "",
                                "frequency": row['frequency'] or "",
                                "temporal_coverage": row['temporal_coverage'] or "",
                                "semantic_score": 0.0,
                                "lexical_score": round(score, 4),
                                "explanation": f"Coincidencia léxica: {score:.2%}"
                            })
        
        # Ordenar por score final y limitar
        results.sort(key=lambda x: x["score"], reverse=True)
        total_results = len(results)
        results = results[:request.top_k]
        
        elapsed = time.perf_counter() - start
        
        return SearchResponse(
            query=request.query,
            filters={
                "territorio": request.territorio,
                "tema": request.tema,
                "formato": request.formato,
                "publisher": request.publisher,
            },
            total_results=total_results,
            returned_results=len(results),
            semantic_weight=sem_w,
            lexical_weight=lex_w,
            search_time_ms=round(elapsed * 1000, 2),
            results=results,
        )
        
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")
    finally:
        conn.close()


@app.get("/facets/{facet}")
async def get_facet_values(facet: str, limit: int = Query(default=100, le=1000)):
    """
    Obtiene los valores disponibles para una faceta.
    
    Facetas: tema, territorio, formato, publisher
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="No se pudo conectar a PostgreSQL")
    
    try:
        facet_map = {
            "tema": "theme",
            "territorio": "territory",
            "formato": "format",
            "publisher": "publisher",
        }
        
        if facet not in facet_map:
            raise HTTPException(
                status_code=400,
                detail=f"Faceta '{facet}' no válida. Opciones: {list(facet_map.keys())}"
            )
        
        column = facet_map[facet]
        
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT {column}, COUNT(*) as count
                FROM datasets
                WHERE {column} IS NOT NULL AND {column} != ''
                GROUP BY {column}
                ORDER BY count DESC
                LIMIT %s
            """, (limit,))
            
            rows = cur.fetchall()
            values = [{"value": row[0], "count": row[1]} for row in rows]
        
        return {"facet": facet, "count": len(values), "values": values}
        
    except Exception as e:
        logger.error(f"Error obteniendo facetas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/")
async def root():
    """Info básica de la API."""
    return {
        "name": "Buscador Semántico de Datasets (PostgreSQL + pgvector)",
        "version": "2.0.0",
        "endpoints": {
            "search": "POST /search",
            "health": "GET /health",
            "facets": "GET /facets/{tema|territorio|formato|publisher}",
        },
    }


# ============================================
# INICIALIZACIÓN
# ============================================

@app.on_event("startup")
async def startup_event():
    """Verificar conexión a PostgreSQL al iniciar."""
    logger.info("Verificando conexión a PostgreSQL...")
    conn = get_db_connection()
    if conn:
        logger.info("✅ Conectado a PostgreSQL")
        conn.close()
    else:
        logger.error("❌ No se pudo conectar a PostgreSQL")
