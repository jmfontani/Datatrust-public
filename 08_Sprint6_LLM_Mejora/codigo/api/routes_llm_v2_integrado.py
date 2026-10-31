#!/usr/bin/env python3
"""
Rutas API para mejoras con LLM (Fase 08) - Versión Integrada con v07
Integra re-ranking con el motor de búsqueda v07 existente.
"""

import sys
import os
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import requests

sys.path.insert(0, os.path.dirname(__file__))

from llm_reranker import LLMReranker
from llm_client import LLMClient


router_llm = APIRouter(prefix="/llm", tags=["LLM Enhancements"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    filters: Optional[Dict] = Field(None)
    limit: int = Field(10, ge=1, le=50)
    rerank_top_n: int = Field(20, ge=5, le=50)
    use_llm: bool = Field(True)


class DatasetResult(BaseModel):
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
    query: str
    results: List[DatasetResult]
    total: int
    metadata: Dict


class ExplainRequest(BaseModel):
    query: str
    dataset_id: str


class ExplainResponse(BaseModel):
    dataset_id: str
    explanation: str
    relevance_factors: Dict


_reranker = None

def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = LLMReranker()
    return _reranker


@router_llm.post("/search/rerank", response_model=SearchResponse)
async def search_with_rerank(request: SearchRequest):
    """Buscar datasets con re-ranking LLM usando motor v07."""
    import time
    from types import SimpleNamespace

    start = time.time()

    try:
        # PASO 1: Obtener resultados del motor v07 via HTTP
        v07_request = {
            "query": request.query,
            "top_k": request.rerank_top_n,
            "semantic_weight": 0.7,
            "lexical_weight": 0.3,
            "min_score": 0.15,
            "remove_stopwords": True,
            "use_synonyms": True
        }

        if request.filters:
            if request.filters.get('theme'):
                v07_request['tema'] = request.filters['theme']
            if request.filters.get('territory'):
                v07_request['territorio'] = request.filters['territory']

        # Llamar al endpoint /search de v07
        api_port = os.getenv('API_PORT', '8000')
        v07_response = requests.post(
            f"http://localhost:{api_port}/search",
            json=v07_request,
            timeout=30
        )
        v07_response.raise_for_status()
        v07_data = v07_response.json()

        initial_results = v07_data.get("results", [])

        if not initial_results:
            return SearchResponse(
                query=request.query,
                results=[],
                total=0,
                metadata={"status": "no_results", "time_ms": (time.time() - start) * 1000}
            )

        # PASO 2: Re-ranking con LLM
        if request.use_llm:
            reranker = get_reranker()

            # Convertir a SimpleNamespace para compatibilidad
            search_results = []
            for r in initial_results[:request.rerank_top_n]:
                sr = SimpleNamespace(
                    dataset_id=r.get("dataset_id", ""),
                    title=r.get("title", ""),
                    description=r.get("description", ""),
                    publisher=r.get("publisher", ""),
                    theme=r.get("theme", ""),
                    territory=r.get("territory", ""),
                    format=r.get("format", ""),
                    score_semantic=r.get("score_semantic", 0.0),
                    score_lexical=r.get("score_lexical", 0.0),
                    score_final=r.get("score_final", 0.0)
                )
                search_results.append(sr)

            reranked_results, llm_metadata = reranker.rerank(
                query=request.query,
                results=search_results,
                top_n=request.rerank_top_n,
                verbose=False
            )

            reranked_results = reranked_results[:request.limit]

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
                    "total_time_ms": (time.time() - start) * 1000
                }
            )
        else:
            results = [
                DatasetResult(
                    dataset_id=r.get("dataset_id", ""),
                    title=r.get("title", ""),
                    description=r.get("description", ""),
                    publisher=r.get("publisher", ""),
                    theme=r.get("theme", ""),
                    territory=r.get("territory", ""),
                    format=r.get("format", ""),
                    original_rank=i+1,
                    new_rank=i+1,
                    original_score=r.get("score_final", 0.0),
                    llm_relevance_score=0.0,
                    explanation="Re-ranking desactivado"
                )
                for i, r in enumerate(initial_results[:request.limit])
            ]

            return SearchResponse(
                query=request.query,
                results=results,
                total=len(results),
                metadata={"status": "no_llm", "total_time_ms": (time.time() - start) * 1000}
            )

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Error motor v07: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router_llm.get("/health")
async def health_check():
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
        return {"status": "error", "error": str(e), "ollama_available": False}
