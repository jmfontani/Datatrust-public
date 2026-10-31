#!/usr/bin/env python3
"""
Rutas API para mejoras con LLM (Fase 08) - Versión Integrada
Integra re-ranking y explicaciones con el motor de búsqueda existente.

Endpoints:
    POST /search/rerank     - Búsqueda con re-ranking LLM
    POST /search/explain    - Explicación de por qué un dataset es relevante
    GET /health             - Estado del servicio LLM

Uso:
    from routes_llm_v2 import router_llm
    app.include_router(router_llm, prefix="/llm")
"""

import sys
import os
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
from sentence_transformers import SentenceTransformer

# Añadir rutas necesarias
sys.path.insert(0, os.path.dirname(__file__))

from llm_reranker_qwen import LLMReranker
from llm_client import LLMClient


# Router de FastAPI
router_llm = APIRouter(prefix="/llm", tags=["LLM Enhancements"])


# Schemas de Pydantic
class SearchRequest(BaseModel):
    """Request para búsqueda con re-ranking."""
    query: str = Field(..., min_length=1, max_length=500, description="Texto de búsqueda")
    filters: Optional[Dict] = Field(None, description="Filtros {theme, territory, format}")
    limit: int = Field(10, ge=1, le=50, description="Máximo resultados a devolver")
    rerank_top_n: int = Field(20, ge=5, le=50, description="Top N a re-rankear con LLM")
    use_llm: bool = Field(True, description="Activar re-ranking con LLM")


class DatasetResult(BaseModel):
    """Resultado de dataset."""
    dataset_id: str
    title: str
    description: str
    publisher: str
    theme: str
    territory: str
    format: str
    original_rank: int
    new_rank: int
    original_score: float
    llm_relevance_score: float
    explanation: str


class SearchResponse(BaseModel):
    """Response de búsqueda con re-ranking."""
    query: str
    results: List[DatasetResult]
    total: int
    metadata: Dict


class ExplainRequest(BaseModel):
    """Request para explicación de relevancia."""
    query: str = Field(..., description="Query del usuario")
    dataset_id: str = Field(..., description="ID del dataset a explicar")


class ExplainResponse(BaseModel):
    """Response de explicación."""
    dataset_id: str
    explanation: str
    relevance_factors: Dict


# Configuración de base de datos desde variables de entorno
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DB', 'buscador'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
}


# Modelo de embeddings: nombre completo y revision fijada (ver docs/PINNING-DEPENDENCIAS.md).
# Sin revision se descargaba la rama 'main', un puntero movil que puede cambiar
# los pesos bajo el mismo nombre y desalinearlos de los embeddings guardados.
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"

# Modelo para embeddings (cargado una sola vez)
_modelo_embeddings = None

def get_embedding_model():
    """Singleton para el modelo de embeddings."""
    global _modelo_embeddings
    if _modelo_embeddings is None:
        _modelo_embeddings = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)
    return _modelo_embeddings


def get_db_connection():
    """Obtener conexión a PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)


def search_hybrid(query_text: str, query_embedding: list, filters: Optional[Dict] = None, limit: int = 20):
    """
    Búsqueda híbrida usando PostgreSQL + pgvector.

    Returns:
        tuple: (results, search_time_ms)
    """
    import time
    start = time.time()

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Construir query base
    base_sql = """
        SELECT
            dataset_id,
            title,
            description,
            publisher,
            theme,
            territory,
            format,
            1 - (embedding <=> %s::vector) as semantic_score,
            ts_rank_cd(search_vector, plainto_tsquery('spanish', %s), 32) as lexical_score
        FROM datasets
        WHERE 1=1
    """

    params = [str(query_embedding), query_text]

    # Aplicar filtros
    if filters:
        if filters.get('theme'):
            base_sql += " AND theme = %s"
            params.append(filters['theme'])
        if filters.get('territory'):
            base_sql += " AND territory = %s"
            params.append(filters['territory'])
        if filters.get('format'):
            base_sql += " AND format = %s"
            params.append(filters['format'])

    # Calcular score combinado
    base_sql += """
        ORDER BY (0.7 * (1 - (embedding <=> %s::vector)) + 0.3 * ts_rank_cd(search_vector, plainto_tsquery('spanish', %s), 32)) DESC
        LIMIT %s
    """
    params.extend([str(query_embedding), query_text, limit * 2])  # Traer más para re-ranking

    cursor.execute(base_sql, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    search_time = (time.time() - start) * 1000

    # Convertir a formato compatible
    formatted_results = []
    for i, row in enumerate(results[:limit]):
        formatted_results.append({
            'dataset_id': row['dataset_id'],
            'title': row['title'] or '',
            'description': row['description'] or '',
            'publisher': row['publisher'] or '',
            'theme': row['theme'] or '',
            'territory': row['territory'] or '',
            'format': row['format'] or '',
            'score_semantic': float(row['semantic_score'] or 0),
            'score_lexical': float(row['lexical_score'] or 0),
            'score_final': float(row['semantic_score'] or 0) * 0.7 + float(row['lexical_score'] or 0) * 0.3
        })

    return formatted_results, search_time


# Instancia del reranker
_reranker = None

def get_reranker():
    """Singleton para el reranker."""
    global _reranker
    if _reranker is None:
        _reranker = LLMReranker()
    return _reranker


@router_llm.post("/search/rerank", response_model=SearchResponse)
async def search_with_rerank(request: SearchRequest):
    """
    Buscar datasets con re-ranking inteligente por LLM.

    El flujo es:
    1. Búsqueda híbrida (semántica + léxica) sobre PostgreSQL
    2. Top N resultados pasan al LLM para re-ranking
    3. El LLM reordena según relevancia analítica real
    4. Se devuelven los resultados reordenados con explicaciones
    """
    try:
        # 1. Generar embedding de la query
        model = get_embedding_model()
        query_embedding = model.encode(request.query, normalize_embeddings=True).tolist()

        # 2. Búsqueda híbrida inicial
        initial_results, search_time = search_hybrid(
            query_text=request.query,
            query_embedding=query_embedding,
            filters=request.filters,
            limit=request.rerank_top_n
        )

        if not initial_results:
            return SearchResponse(
                query=request.query,
                results=[],
                total=0,
                metadata={"status": "no_results", "search_time_ms": search_time}
            )

        # 3. Re-ranking con LLM (si está activado)
        if request.use_llm:
            reranker = get_reranker()
            reranked_results, llm_metadata = reranker.rerank(
                query=request.query,
                results=initial_results,
                top_n=request.rerank_top_n,
                verbose=False
            )

            # Limitar a los solicitados
            reranked_results = reranked_results[:request.limit]

            # Convertir a respuesta API
            results = [
                DatasetResult(
                    dataset_id=r.dataset_id,
                    title=r.title,
                    description=r.description,
                    publisher=r.publisher,
                    theme=r.theme,
                    territory=r.territory,
                    format=r.format,
                    original_rank=r.original_rank,
                    new_rank=r.new_rank,
                    original_score=r.original_score,
                    llm_relevance_score=r.llm_relevance_score,
                    explanation=r.explanation
                )
                for r in reranked_results
            ]

            return SearchResponse(
                query=request.query,
                results=results,
                total=len(results),
                metadata={
                    "status": llm_metadata.get("status", "success"),
                    "model": llm_metadata.get("model", "unknown"),
                    "initial_count": len(initial_results),
                    "reranked_count": len(reranked_results),
                    "search_time_ms": search_time
                }
            )
        else:
            # Sin re-ranking, devolver originales
            results = [
                DatasetResult(
                    dataset_id=r['dataset_id'],
                    title=r['title'],
                    description=r['description'],
                    publisher=r['publisher'],
                    theme=r['theme'],
                    territory=r['territory'],
                    format=r['format'],
                    original_rank=i+1,
                    new_rank=i+1,
                    original_score=r['score_final'],
                    llm_relevance_score=0.0,
                    explanation="Re-ranking desactivado"
                )
                for i, r in enumerate(initial_results[:request.limit])
            ]

            return SearchResponse(
                query=request.query,
                results=results,
                total=len(results),
                metadata={"status": "no_llm", "search_time_ms": search_time}
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")


@router_llm.post("/search/explain", response_model=ExplainResponse)
async def explain_relevance(request: ExplainRequest):
    """
    Explicar por qué un dataset es relevante para una query.

    El LLM analiza el dataset y la query para generar una explicación
    en lenguaje natural sobre la relevancia.
    """
    try:
        # Obtener datos del dataset
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT title, description, theme, territory, publisher
            FROM datasets WHERE dataset_id = %s
        """, (request.dataset_id,))
        dataset = cursor.fetchone()
        cursor.close()
        conn.close()

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset no encontrado")

        # Generar explicación con LLM
        llm = LLMClient()
        prompt = f"""Explica por qué el siguiente dataset es relevante para la búsqueda "{request.query}":

Título: {dataset['title']}
Descripción: {dataset['description']}
Tema: {dataset['theme']}
Territorio: {dataset['territory']}
Publisher: {dataset['publisher']}

Proporciona una explicación concisa en español (2-3 oraciones) sobre la relevancia."""

        explanation = llm.generate(prompt, preset="explanation", max_tokens=200)

        return ExplainResponse(
            dataset_id=request.dataset_id,
            explanation=explanation.strip() if explanation else "No se pudo generar explicación",
            relevance_factors={
                "tema": dataset['theme'] or 'desconocido',
                "territorio": dataset['territory'] or 'desconocido',
                "publisher": dataset['publisher'] or 'desconocido'
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando explicación: {str(e)}")


@router_llm.get("/health")
async def health_check():
    """Verificar estado del servicio LLM."""
    try:
        reranker = get_reranker()
        is_available = reranker.llm.is_available()
        models = reranker.llm.list_models() if is_available else []

        return {
            "status": "ok" if is_available else "degraded",
            "ollama_available": is_available,
            "current_model": reranker.llm.model,
            "available_models": models[:5],
            "presets": list(reranker.llm.PRESETS.keys())
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "ollama_available": False
        }
