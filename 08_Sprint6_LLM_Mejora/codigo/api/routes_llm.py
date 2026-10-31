#!/usr/bin/env python3
"""
Rutas API para mejoras con LLM (Fase 08)
Integra re-ranking y explicaciones con el motor de búsqueda existente.

Endpoints:
    POST /search/rerank     - Búsqueda con re-ranking LLM
    POST /search/explain    - Explicación de por qué un dataset es relevante

Uso:
    from routes_llm import router_llm
    app.include_router(router_llm, prefix="/llm")
"""

import sys
import os
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
import numpy as np

# Añadir rutas necesarias
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'motor'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../07_Sprint5_Integracion/codigo/motor'))

from llm_reranker import LLMReranker, RerankedResult
from search_engine_pgvector import SearchEnginePgvector, SearchResult


# Modelo de embeddings: nombre completo y revision fijada (ver docs/PINNING-DEPENDENCIAS.md).
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


# Instancias de servicios
_engine = SearchEnginePgvector()
_reranker = LLMReranker()


@router_llm.post("/search/rerank", response_model=SearchResponse)
async def search_with_rerank(request: SearchRequest):
    """
    Buscar datasets con re-ranking inteligente por LLM.

    El flujo es:
    1. Búsqueda híbrida (semántica + léxica) sobre PostgreSQL
    2. Top N resultados pasan al LLM para re-ranking
    3. El LLM reordena según relevancia analítica real
    4. Se devuelven los resultados reordenados con explicaciones

    Ejemplo:
        POST /llm/search/rerank
        {
            "query": "vulnerabilidad económica juvenil",
            "limit": 10,
            "rerank_top_n": 20
        }
    """
    try:
        # 1. Generar embedding de la query
        model = get_embedding_model()
        query_embedding = model.encode(request.query, normalize_embeddings=True).tolist()

        # 2. Búsqueda híbrida inicial
        initial_results, search_time = _engine.search_hybrid(
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
            reranked_results, llm_metadata = _reranker.rerank(
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
                    dataset_id=r.dataset_id,
                    title=r.title,
                    description=r.description,
                    publisher=r.publisher,
                    theme=r.theme,
                    territory=r.territory,
                    format=r.format,
                    original_rank=i+1,
                    new_rank=i+1,
                    original_score=r.score_final,
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

    Ejemplo:
        POST /llm/search/explain
        {
            "query": "paro juvenil",
            "dataset_id": "ine-001"
        }
    """
    # TODO: Implementar cuando tengamos acceso a metadatos individuales
    return ExplainResponse(
        dataset_id=request.dataset_id,
        explanation="Explicación de ejemplo: Este dataset contiene datos de empleo juvenil...",
        relevance_factors={
            "tema": "empleo",
            "granularidad": "provincial",
            "actualidad": "2023"
        }
    )


@router_llm.get("/health")
async def health_check():
    """Verificar estado del servicio LLM."""
    is_available = _reranker.llm.is_available()
    models = _reranker.llm.list_models() if is_available else []

    return {
        "status": "ok" if is_available else "degraded",
        "ollama_available": is_available,
        "current_model": _reranker.llm.model,
        "available_models": models[:5],
        "presets": list(_reranker.llm.PRESETS.keys())
    }


# Test simple
if __name__ == "__main__":
    print("Test de rutas LLM")
    print("=" * 50)

    # Test 1: Health check
    print("\n1. Health check:")
    import asyncio
    result = asyncio.run(health_check())
    print(f"   Status: {result['status']}")
    print(f"   Modelo actual: {result['current_model']}")
    print(f"   Presets: {result['presets']}")

    # Test 2: Búsqueda con re-ranking
    print("\n2. Test de búsqueda (requiere motor funcionando):")
    print("   Iniciar con: uvicorn routes_llm:router_llm --reload")
