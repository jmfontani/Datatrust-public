#!/usr/bin/env python3
"""
Backend API V2 para el motor de búsqueda híbrida con PostgreSQL.
Versión mejorada con sentence-transformers para embeddings reales.

Ejecutar:
    uvicorn main_v2_fixed:app --host 0.0.0.0 --port 8000

Endpoints:
    POST /search          - Búsqueda híbrida con filtros
    GET /health           - Health check
    GET /facets/{facet}   - Valores disponibles para una faceta
"""
import sys
from pathlib import Path
import json
import ast
import logging
import time

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
# CONFIGURACIÓN DE EMBEDDINGS
# ============================================

EMBEDDING_MODEL = None
USE_REAL_EMBEDDINGS = False

# Intentar cargar sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    logger.info("Cargando modelo de embeddings...")
    EMBEDDING_MODEL = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    USE_REAL_EMBEDDINGS = True
    logger.info("✅ Modelo de embeddings cargado: paraphrase-multilingual-MiniLM-L12-v2")
except Exception as e:
    logger.warning(f"⚠️ No se pudo cargar sentence-transformers: {e}")
    logger.warning("Se usarán embeddings aleatorios para demo")

# ============================================
# APLICACIÓN FASTAPI
# ============================================

app = FastAPI(
    title="Buscador Semántico de Datasets (PostgreSQL + pgvector)",
    description="API de búsqueda híbrida con PostgreSQL y pgvector",
    version="2.1.0",
)

# Configuración de conexión PostgreSQL
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "buscador",
    "user": "postgres",
    "password": "postgres",
}


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
    min_score: float = Field(default=0.15, ge=0, le=1, description="Score mínimo de relevancia (0-1)")
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
    return {"message": "Buscador Semántico V2", "docs": "/docs"}


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
            
            # Verificar pgvector
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            has_pgvector = cur.fetchone() is not None
            
            return {
                "status": "ok",
                "postgresql": "connected",
                "pg_version": pg_version.split()[1] if pg_version else "unknown",
                "pgvector": has_pgvector,
                "datasets_count": count,
                "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2" if USE_REAL_EMBEDDINGS else "random",
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error PostgreSQL: {e}")
    finally:
        conn.close()


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    """
    Búsqueda híbrida con PostgreSQL + pgvector.
    Combina búsqueda semántica (similitud de embeddings) y léxica (full-text search).
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
        all_results = {}  # dict para evitar duplicados por ID
        
        # Construir filtros WHERE
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
        
        # ==========================================
        # BÚSQUEDA SEMÁNTICA con pgvector
        # ==========================================
        if sem_w > 0:
            try:
                # Generar embedding real para la query
                query_embedding = get_embedding(request.query)
                query_vector_str = vector_to_pgvector(query_embedding)
                
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
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
                                    "formato": [row['format']] if row['format'] else [],
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
                                # Combinar scores
                                all_results[ds_id]["score"] += round(score * sem_w, 4)
                                all_results[ds_id]["semantic_score"] = round(score, 4)
                                
            except Exception as e:
                logger.error(f"Error en búsqueda semántica: {e}")
                import traceback
                traceback.print_exc()
        
        # ==========================================
        # BÚSQUEDA LÉXICA con TSVECTOR
        # ==========================================
        if lex_w > 0 and request.query:
            try:
                # Usar plainto_tsquery para AND lógico (requiere todas las palabras)
                ts_query = " & ".join(request.query.split())
                
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
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
                    
                    for row in cur.fetchall():
                        ds_id = row['dataset_id']
                        score = float(row['rank'])
                        
                        if ds_id in all_results:
                            # Combinar con resultado semántico existente
                            all_results[ds_id]["score"] += round(score * lex_w, 4)
                            all_results[ds_id]["lexical_score"] = round(score, 4)
                            all_results[ds_id]["explanation"] = (
                                f"Semántica: {all_results[ds_id]['semantic_score']:.1%}, "
                                f"Léxica: {score:.1%}"
                            )
                        else:
                            # Nuevo resultado léxico
                            all_results[ds_id] = {
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
                                "explanation": f"Coincidencia léxica: {score:.1%}"
                            }
                            
            except Exception as e:
                logger.error(f"Error en búsqueda léxica: {e}")
                import traceback
                traceback.print_exc()
        
        # Convertir a lista y ordenar por score
        results = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)
        
        # Aplicar top_k
        total = len(results)
        results = results[:request.top_k]
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        return SearchResponse(
            query=request.query,
            filters={
                "territorio": request.territorio,
                "tema": request.tema,
                "formato": request.formato,
                "publisher": request.publisher,
            },
            total_results=total,
            returned_results=len(results),
            semantic_weight=round(sem_w, 2),
            lexical_weight=round(lex_w, 2),
            search_time_ms=round(elapsed_ms, 2),
            results=results,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {e}")
    finally:
        conn.close()


@app.get("/facets/{facet}")
def get_facets(facet: str, limit: int = Query(default=50, le=200)):
    """
    Obtiene valores únicos para una faceta.
    Facetas disponibles: territorio, tema, formato, publisher
    """
    column_map = {
        "territorio": "territory",
        "tema": "theme",
        "formato": "format",
        "publisher": "publisher",
    }
    
    if facet not in column_map:
        raise HTTPException(
            status_code=400,
            detail=f"Faceta '{facet}' no válida. Opciones: {list(column_map.keys())}"
        )
    
    column = column_map[facet]
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="PostgreSQL no disponible")
    
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT {column}, COUNT(*) as count
                FROM datasets
                WHERE {column} IS NOT NULL AND {column} != ''
                GROUP BY {column}
                ORDER BY count DESC
                LIMIT %s
            """, (limit,))
            
            facets = [
                {"value": row[0], "count": row[1]}
                for row in cur.fetchall()
            ]
            
            return {
                "facet": facet,
                "total_values": len(facets),
                "values": facets,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo facetas: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)