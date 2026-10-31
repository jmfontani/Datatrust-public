#!/usr/bin/env python3
"""
API REST para el motor de búsqueda híbrida.

Ejecutar:
  uvicorn main:app --reload --port 8000

Endpoints:
  POST /search          - Búsqueda híbrida con filtros
  GET /health           - Health check
  GET /facets/{facet}   - Valores disponibles para una faceta
"""
import sys
from pathlib import Path

# Añadir motor al path
sys.path.insert(0, str(Path(__file__).parent.parent / "motor"))

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import json

from search_engine import HybridSearchEngine

app = FastAPI(
    title="Buscador Semántico de Datasets",
    description="API de búsqueda híbrida (semántica + léxica + filtros)",
    version="0.3.0",
)

# Inicializar motor (carga pesada, hacerlo una vez)
engine = None

@app.on_event("startup")
async def startup_event():
    global engine
    engine = HybridSearchEngine()


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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "engine_loaded": engine is not None,
        "datasets_count": len(engine.datasets) if engine else 0,
    }


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Realiza una búsqueda híbrida con filtros facetados.
    """
    if not engine:
        raise HTTPException(status_code=503, detail="Motor no inicializado")
    
    # Normalizar pesos
    total_weight = request.semantic_weight + request.lexical_weight
    sem_w = request.semantic_weight / total_weight
    lex_w = request.lexical_weight / total_weight
    
    result = engine.search(
        query=request.query,
        top_k=request.top_k,
        semantic_weight=sem_w,
        lexical_weight=lex_w,
        min_score_threshold=request.min_score,
        require_lexical_match=request.require_lexical_match,
        explain=request.explain,
        territorio=request.territorio,
        tema=request.tema,
        formato=request.formato,
        publisher=request.publisher,
    )
    
    return SearchResponse(**result)


@app.get("/facets/{facet}")
async def get_facet_values(facet: str, limit: int = Query(default=100, le=1000)):
    """
    Obtiene los valores disponibles para una faceta.
    
    Facetas: tema, territorio, formato, publisher
    """
    if not engine:
        raise HTTPException(status_code=503, detail="Motor no inicializado")
    
    facet_map = {
        "tema": engine.index_tema,
        "territorio": engine.index_territorio,
        "formato": engine.index_formato,
        "publisher": engine.index_publisher,
    }
    
    if facet not in facet_map:
        raise HTTPException(
            status_code=400,
            detail=f"Faceta '{facet}' no válida. Opciones: {list(facet_map.keys())}"
        )
    
    values = list(facet_map[facet].keys())[:limit]
    return {"facet": facet, "count": len(values), "values": values}


@app.get("/")
async def root():
    """Info básica de la API."""
    return {
        "name": "Buscador Semántico de Datasets",
        "version": "0.3.0",
        "endpoints": {
            "search": "POST /search",
            "health": "GET /health",
            "facets": "GET /facets/{tema|territorio|formato|publisher}",
        },
    }
