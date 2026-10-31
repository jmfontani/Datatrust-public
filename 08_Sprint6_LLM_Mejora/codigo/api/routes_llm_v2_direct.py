#!/usr/bin/env python3
"""Rutas LLM que importan directamente desde main_v2_final.py"""

import sys
import os
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(__file__))

from llm_reranker import LLMReranker
from llm_client import LLMClient

# Importar funciones de v07
try:
    from main_v2_final import (
        search as v07_search,
        SearchRequest as V07SearchRequest
    )
    V07_IMPORTS_OK = True
except ImportError as e:
    V07_IMPORTS_OK = False
    print(f"⚠️ No se pudieron importar funciones de v07: {e}")

router_llm = APIRouter(prefix="/llm", tags=["LLM"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    filters: Optional[Dict] = Field(None)
    limit: int = Field(10, ge=1, le=50)
    rerank_top_n: int = Field(20, ge=5, le=50)
    use_llm: bool = Field(True)


_reranker = None

def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = LLMReranker()
    return _reranker


@router_llm.post("/search/rerank")
async def search_with_rerank(request: SearchRequest):
    """Buscar con re-ranking usando motor v07 directamente."""
    import time
    from types import SimpleNamespace

    start = time.time()

    if not V07_IMPORTS_OK:
        raise HTTPException(status_code=503, detail="Motor v07 no disponible")

    try:
        # Llamar directamente a la función search de v07
        v07_req = V07SearchRequest(
            query=request.query,
            top_k=request.rerank_top_n,
            semantic_weight=0.7,
            lexical_weight=0.3,
            min_score=0.15,
            remove_stopwords=True,
            use_synonyms=True
        )

        # Llamar a v07_search
        v07_response = v07_search(v07_req)

        initial_results = v07_response.results if hasattr(v07_response, 'results') else []

        if not initial_results:
            return {
                "query": request.query,
                "results": [],
                "total": 0,
                "metadata": {"status": "no_results"}
            }

        # Re-ranking con LLM
        if request.use_llm:
            reranker = get_reranker()

            search_results = []
            for r in initial_results[:request.rerank_top_n]:
                # v07 devuelve dicts con 'id', no 'dataset_id'
                if isinstance(r, dict):
                    ds_id = r.get('id') or r.get('dataset_id', '')
                    title = r.get('title', '')
                    description = r.get('description', '')
                    publisher = r.get('publisher', '')
                    theme = r.get('theme', '') if 'theme' in r else r.get('tema', '')
                    territory = r.get('territory', '') if 'territory' in r else r.get('territorio', '')
                    format = r.get('format', '') if 'format' in r else r.get('formato', '')
                    score_semantic = r.get('semantic_score', 0.0)
                    score_lexical = r.get('lexical_score', 0.0)
                    score_final = r.get('score', 0.0)
                else:
                    ds_id = getattr(r, 'dataset_id', '') or getattr(r, 'id', '')
                    title = getattr(r, 'title', '')
                    description = getattr(r, 'description', '')
                    publisher = getattr(r, 'publisher', '')
                    theme = getattr(r, 'theme', '')
                    territory = getattr(r, 'territory', '')
                    format = getattr(r, 'format', '')
                    score_semantic = getattr(r, 'score_semantic', 0.0)
                    score_lexical = getattr(r, 'score_lexical', 0.0)
                    score_final = getattr(r, 'score_final', 0.0)

                sr = SimpleNamespace(
                    dataset_id=ds_id,
                    title=title,
                    description=description,
                    publisher=publisher,
                    theme=theme,
                    territory=territory,
                    format=format,
                    score_semantic=score_semantic,
                    score_lexical=score_lexical,
                    score_final=score_final,
                    metadata={}
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
                {
                    "dataset_id": r.dataset_id,
                    "title": r.title,
                    "description": r.description,
                    "publisher": r.publisher,
                    "theme": r.theme,
                    "territory": r.territory,
                    "format": r.format,
                    "original_rank": r.original_rank,
                    "new_rank": r.new_rank,
                    "original_score": r.original_score,
                    "llm_relevance_score": r.llm_relevance_score,
                    "explanation": r.explanation
                }
                for r in reranked_results
            ]

            return {
                "query": request.query,
                "results": results,
                "total": len(results),
                "metadata": {
                    "status": llm_metadata.get("status", "success"),
                    "model": llm_metadata.get("model", "unknown"),
                    "initial_count": len(initial_results),
                    "reranked_count": len(reranked_results),
                    "total_time_ms": (time.time() - start) * 1000
                }
            }
        else:
            results = []
            for i, r in enumerate(initial_results[:request.limit]):
                if isinstance(r, dict):
                    ds_id = r.get('id') or r.get('dataset_id', '')
                    title = r.get('title', '')
                    description = r.get('description', '')
                    publisher = r.get('publisher', '')
                    theme = r.get('theme', '')
                    territory = r.get('territory', '')
                    format = r.get('format', '')
                    score = r.get('score', 0.0)
                else:
                    ds_id = getattr(r, 'dataset_id', '') or getattr(r, 'id', '')
                    title = getattr(r, 'title', '')
                    description = getattr(r, 'description', '')
                    publisher = getattr(r, 'publisher', '')
                    theme = getattr(r, 'theme', '')
                    territory = getattr(r, 'territory', '')
                    format = getattr(r, 'format', '')
                    score = getattr(r, 'score_final', 0.0)

                results.append({
                    "dataset_id": ds_id,
                    "title": title,
                    "description": description,
                    "publisher": publisher,
                    "theme": theme,
                    "territory": territory,
                    "format": format,
                    "original_rank": i+1,
                    "new_rank": i+1,
                    "original_score": score,
                    "llm_relevance_score": 0.0,
                    "explanation": "Re-ranking desactivado"
                })

            return {
                "query": request.query,
                "results": results,
                "total": len(results),
                "metadata": {"status": "no_llm", "total_time_ms": (time.time() - start) * 1000}
            }

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router_llm.get("/health")
async def health_check():
    try:
        reranker = get_reranker()
        is_available = reranker.llm.is_available()
        models = reranker.llm.list_models() if is_available else []

        return {
            "status": "ok" if is_available else "degraded",
            "v07_imports_ok": V07_IMPORTS_OK,
            "ollama_available": is_available,
            "current_model": reranker.llm.model,
            "available_models": models[:5]
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "v07_imports_ok": V07_IMPORTS_OK}
