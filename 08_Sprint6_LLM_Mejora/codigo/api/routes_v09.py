#!/usr/bin/env python3
"""
Router V09 - Arquitectura de Endpoints Separados para LLM
===========================================================

Implementa Opción 3: Endpoints independientes para funcionalidades LLM
- /llm/enhance  : Búsqueda con re-ranking LLM (fusión híbrida + LLM)
- /llm/explain  : Explicaciones de relevancia para resultados

Autor: Fonta
Fecha: 2026-05-27
"""

import sys
import os
import time
import json
from typing import List, Dict, Optional
from types import SimpleNamespace
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import requests

# Paths para imports
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../motor'))

from llm_reranker import LLMReranker
from llm_client import LLMClient, create_llm_client


# ============================================================================
# ROUTER PRINCIPAL
# ============================================================================

router_v09 = APIRouter(prefix="/llm", tags=["V09 - LLM Features"])


# ============================================================================
# MODELOS DE REQUEST/RESPONSE
# ============================================================================

class EnhanceRequest(BaseModel):
    """Request para búsqueda mejorada con LLM re-ranking."""
    query: str = Field(..., min_length=1, max_length=500, description="Consulta del usuario")
    filters: Optional[Dict] = Field(None, description="Filtros opcionales (theme, territory, etc.)")
    limit: int = Field(10, ge=1, le=50, description="Número de resultados finales")
    rerank_top_n: int = Field(15, ge=5, le=50, description="Cuántos items re-rankear con LLM")
    include_explanations: bool = Field(True, description="Incluir explicaciones de relevancia")


class DatasetEnhanced(BaseModel):
    """Resultado de dataset con información de re-ranking."""
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


class EnhanceResponse(BaseModel):
    """Response de búsqueda mejorada."""
    query: str
    results: List[DatasetEnhanced]
    total: int
    metadata: Dict


class ExplainRequest(BaseModel):
    """Request para explicación de relevancia."""
    query: str = Field(..., min_length=1, max_length=500, description="Consulta original")
    dataset_id: str = Field(..., description="ID del dataset a explicar")
    context: Optional[str] = Field(None, description="Contexto adicional opcional")


class RelevanceFactor(BaseModel):
    """Factor de relevancia identificado."""
    factor: str
    score: float
    description: str


class ExplainResponse(BaseModel):
    """Response con explicación detallada."""
    dataset_id: str
    title: str
    explanation: str
    relevance_score: float
    factors: List[RelevanceFactor]
    metadata: Dict


# ============================================================================
# SINGLETONS - Cache de objetos reutilizables
# ============================================================================

_reranker: Optional[LLMReranker] = None
_explanation_client: Optional[LLMClient] = None


def get_reranker() -> LLMReranker:
    """Obtener instancia cacheada del re-ranker."""
    global _reranker
    if _reranker is None:
        _reranker = LLMReranker(
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434")
        )
    return _reranker


def get_explanation_client() -> LLMClient:
    """Obtener instancia cacheada del cliente LLM para explicaciones."""
    global _explanation_client
    if _explanation_client is None:
        _explanation_client = create_llm_client(
            use_case="explanation",
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            verbose=False
        )
    return _explanation_client


def get_v07_url() -> str:
    """Obtener URL base de la API v07."""
    api_port = os.getenv('API_PORT', '8000')
    return f"http://localhost:{api_port}"


# ============================================================================
# ENDPOINT: /llm/enhance
# ============================================================================

@router_v09.post("/enhance", response_model=EnhanceResponse, summary="Búsqueda con re-ranking LLM")
async def enhance_search(request: EnhanceRequest):
    """
    Búsqueda híbrida mejorada con re-ranking LLM.

    Combina el motor híbrido v07 (semántico + léxico) con re-ranking
    inteligente usando LLM para mejorar el orden de resultados.

    - **query**: Consulta del usuario
    - **filters**: Filtros opcionales (theme, territory, etc.)
    - **limit**: Cuántos resultados devolver (1-50)
    - **rerank_top_n**: Cuántos items analizar con LLM (5-50)
    - **include_explanations**: Incluir justificaciones del LLM

    **Tiempo típico**: 50-90 segundos (depende del LLM)
    """
    start_time = time.time()

    try:
        # -----------------------------------------------------------------
        # PASO 1: Obtener resultados del motor v07 vía HTTP
        # -----------------------------------------------------------------
        v07_request = {
            "query": request.query,
            "top_k": request.rerank_top_n,
            "semantic_weight": 0.7,
            "lexical_weight": 0.3,
            "min_score": 0.15,
            "remove_stopwords": True,
            "use_synonyms": True
        }

        # Aplicar filtros si existen
        if request.filters:
            if request.filters.get('theme'):
                v07_request['tema'] = request.filters['theme']
            if request.filters.get('territory'):
                v07_request['territorio'] = request.filters['territory']
            if request.filters.get('publisher'):
                v07_request['publisher'] = request.filters['publisher']

        v07_url = get_v07_url()
        response = requests.post(
            f"{v07_url}/search",
            json=v07_request,
            timeout=30
        )
        response.raise_for_status()
        v07_data = response.json()

        initial_results = v07_data.get("results", [])

        if not initial_results:
            return EnhanceResponse(
                query=request.query,
                results=[],
                total=0,
                metadata={
                    "status": "no_results",
                    "message": "El motor v07 no encontró resultados",
                    "time_ms": (time.time() - start_time) * 1000
                }
            )

        # -----------------------------------------------------------------
        # PASO 2: Re-ranking con LLM
        # -----------------------------------------------------------------
        reranker = get_reranker()

        search_results = []
        for r in initial_results[:request.rerank_top_n]:
            # v07 devuelve 'id', normalizamos a 'dataset_id'
            sr = SimpleNamespace(
                dataset_id=r.get("id") or r.get("dataset_id", ""),
                title=r.get("title", ""),
                description=r.get("description", ""),
                publisher=r.get("publisher", ""),
                theme=r.get("theme", ""),
                territory=r.get("territory", ""),
                format=r.get("format", ""),
                score_semantic=r.get("score_semantic", 0.0),
                score_lexical=r.get("score_lexical", 0.0),
                score_final=r.get("score_final", 0.0) or r.get("score", 0.0)
            )
            search_results.append(sr)

        reranked, llm_metadata = reranker.rerank(
            query=request.query,
            results=search_results,
            top_n=request.rerank_top_n,
            verbose=False
        )

        # Limitar a los solicitados
        reranked = reranked[:request.limit]

        # Construir respuesta
        results = []
        for r in reranked:
            explanation = r.explanation if request.include_explanations else ""
            results.append(DatasetEnhanced(
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
                explanation=explanation
            ))

        total_time = (time.time() - start_time) * 1000

        return EnhanceResponse(
            query=request.query,
            results=results,
            total=len(results),
            metadata={
                "status": llm_metadata.get("status", "success"),
                "model": llm_metadata.get("model", "unknown"),
                "initial_count": len(initial_results),
                "reranked_count": len(reranked),
                "v07_time_ms": v07_data.get("metadata", {}).get("duration_ms", 0),
                "llm_time_ms": llm_metadata.get("duration_ms", total_time - v07_data.get("metadata", {}).get("duration_ms", 0)),
                "total_time_ms": total_time
            }
        )

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error comunicación con motor v07: {str(e)}"
        )
    except Exception as e:
        import traceback
        print(f"Error en /llm/enhance: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================================================================
# ENDPOINT: /llm/explain
# ============================================================================

@router_v09.post("/explain", response_model=ExplainResponse, summary="Explicación de relevancia")
async def explain_relevance(request: ExplainRequest):
    """
    Genera una explicación detallada de por qué un dataset es relevante.

    Usa LLM para analizar la relación entre la query y los metadatos
    del dataset, identificando factores específicos de relevancia.

    - **query**: Consulta original del usuario
    - **dataset_id**: ID del dataset a explicar
    - **context**: Contexto adicional opcional

    **Tiempo típico**: 5-15 segundos
    """
    start_time = time.time()

    try:
        # -----------------------------------------------------------------
        # PASO 1: Obtener datos del dataset desde v07
        # -----------------------------------------------------------------
        v07_url = get_v07_url()
        response = requests.get(
            f"{v07_url}/datasets/{request.dataset_id}",
            timeout=10
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{request.dataset_id}' no encontrado"
            )

        response.raise_for_status()
        dataset = response.json()

        # -----------------------------------------------------------------
        # PASO 2: Generar explicación con LLM
        # -----------------------------------------------------------------
        client = get_explanation_client()

        prompt = _build_explanation_prompt(
            query=request.query,
            dataset=dataset,
            context=request.context
        )

        llm_response = client.generate(prompt, format="json")

        # Parsear respuesta
        explanation_data = _parse_explanation_response(llm_response.text)

        total_time = (time.time() - start_time) * 1000

        return ExplainResponse(
            dataset_id=request.dataset_id,
            title=dataset.get("title", ""),
            explanation=explanation_data.get("explanation", ""),
            relevance_score=explanation_data.get("relevance_score", 5.0),
            factors=[
                RelevanceFactor(**f) for f in explanation_data.get("factors", [])
            ],
            metadata={
                "model": client.model,
                "time_ms": total_time,
                "prompt_tokens": llm_response.prompt_tokens,
                "response_tokens": llm_response.response_tokens
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error en /llm/explain: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


def _build_explanation_prompt(query: str, dataset: Dict, context: Optional[str] = None) -> str:
    """Construir prompt para generar explicación de relevancia."""

    desc = dataset.get("description", "")[:400]
    if len(dataset.get("description", "")) > 400:
        desc += "..."

    ctx_line = f"\nContexto adicional: {context}" if context else ""

    prompt = f"""Analiza por qué este dataset es relevante para la búsqueda.

Query: "{query}"{ctx_line}

Dataset:
- ID: {dataset.get('id', '')}
- Título: {dataset.get('title', '')}
- Descripción: {desc}
- Tema: {dataset.get('theme', 'N/A')}
- Territorio: {dataset.get('territory', 'N/A')}
- Publisher: {dataset.get('publisher', 'N/A')}

Responde con JSON:
{{
  "relevance_score": 8.5,
  "explanation": "Explicación clara y concisa en español (2-3 frases)",
  "factors": [
    {{"factor": "Coincidencia temática", "score": 0.9, "description": "El tema coincide con la query"}},
    {{"factor": "Cobertura geográfica", "score": 0.8, "description": "El territorio es relevante"}},
    {{"factor": "Calidad metadatos", "score": 0.7, "description": "Descripción completa y clara"}}
  ]
}}

Los factores deben cubrir: coincidencia temática, cobertura territorial/temporal,
calidad de metadatos, granularidad de datos, y actualidad."""

    return prompt


def _parse_explanation_response(response: str) -> Dict:
    """Parsear respuesta JSON del LLM."""
    try:
        # Extraer JSON si viene en backticks
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        return json.loads(json_str)
    except json.JSONDecodeError:
        # Fallback si no es JSON válido
        return {
            "relevance_score": 5.0,
            "explanation": response[:500] if response else "No se pudo generar explicación",
            "factors": []
        }


# ============================================================================
# ENDPOINT: /llm/health (health check del módulo LLM)
# ============================================================================

@router_v09.get("/health", summary="Estado del servicio LLM")
async def health_check_llm():
    """Verificar estado de conexión con Ollama y disponibilidad de modelos."""
    try:
        reranker = get_reranker()
        llm_available = reranker.llm.is_available()

        status = {
            "status": "ok" if llm_available else "degraded",
            "ollama_available": llm_available,
            "reranker_model": reranker.llm.model,
            "explanation_model": get_explanation_client().model if _explanation_client else "not_initialized"
        }

        if llm_available:
            try:
                models = reranker.llm.list_models()
                status["available_models"] = models[:10]
            except:
                status["available_models"] = []

        return status

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "ollama_available": False
        }


# ============================================================================
# QUERY PREPROCESSOR ENDPOINTS (#3, #4, #12) - Añadido 2026-06-01
# ============================================================================

# Importar query preprocessor
try:
    from query_preprocessor import QueryPreprocessor, get_preprocessor
    _preprocessor_available = True
except ImportError:
    _preprocessor_available = False


class PreprocessRequest(BaseModel):
    """Request para pre-procesamiento de query."""
    query: str = Field(..., min_length=1, max_length=500)
    apply_strict_filters: bool = Field(False, description="Si True, aplica filtros estrictos (recomendado: False)")


class PreprocessResponse(BaseModel):
    """Respuesta de pre-procesamiento."""
    query_original: str
    query_expandida: str
    is_valid: bool
    intencion: str
    temas: List[str]
    territorio: Optional[str]
    años: List[int]
    conceptos_implicitos: List[str]
    filtros_sugeridos: Dict
    terminos_añadidos: List[str]
    duration_ms: float


@router_v09.post("/preprocess", response_model=PreprocessResponse)
async def preprocess_query(request: PreprocessRequest):
    """
    Pre-procesa una query con LLM (#3, #4, #12).

    - #12: Valida la query
    - #3: Extrae estructura (temas, territorio, años)
    - #4: Expande con sinónimos y términos relacionados
    """
    if not _preprocessor_available:
        raise HTTPException(status_code=503, detail="Query Preprocessor no disponible")

    try:
        preprocessor = get_preprocessor(verbose=False)
        result = preprocessor.process(
            request.query,
            apply_strict_filters=request.apply_strict_filters
        )

        return PreprocessResponse(
            query_original=result.query_original,
            query_expandida=result.expansion.query_expandida,
            is_valid=result.validation.is_valid,
            intencion=result.validation.intencion,
            temas=result.structure.temas,
            territorio=result.structure.territorio,
            años=result.structure.años,
            conceptos_implicitos=result.structure.conceptos_implicitos,
            filtros_sugeridos=result.filtros_aplicables,
            terminos_añadidos=result.expansion.terminos_añadidos,
            duration_ms=result.metadata.get("duration_ms", 0)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en pre-procesamiento: {str(e)}")


class SearchEnhancedRequest(BaseModel):
    """Request para búsqueda con pre-procesamiento."""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(10, ge=1, le=50)
    use_expansion: bool = Field(True)
    use_filters: bool = Field(False, description="⚠️ Recomendado: False. Los filtros estrictos pueden excluir resultados relevantes")


@router_v09.post("/search-enhanced")
async def search_enhanced_v09(request: SearchEnhancedRequest):
    """
    Búsqueda con pre-procesamiento LLM.

    Diferencia con /search/rerank: este endpoint NO re-ordena con LLM,
    solo expande la query y opcionalmente filtra.
    """
    if not _preprocessor_available:
        raise HTTPException(status_code=503, detail="Query Preprocessor no disponible")

    try:
        # Pre-procesar
        preprocessor = get_preprocessor(verbose=False)
        preprocessed = preprocessor.process(
            request.query,
            apply_strict_filters=request.use_filters
        )

        if not preprocessed.validation.is_valid:
            return {
                "query_original": request.query,
                "query_expandida": request.query,
                "is_valid": False,
                "alertas": preprocessed.validation.alertas,
                "results": []
            }

        # Construir query para búsqueda
        query_buscar = (
            preprocessed.expansion.query_expandida if request.use_expansion
            else request.query
        )

        # Llamar al motor base (usar URL relativa)
        try:
            response = requests.post(
                "http://localhost:8000/search",
                json={"query": query_buscar, "limit": request.limit},
                timeout=30,
                verify=False
            )
            response.raise_for_status()
            search_results = response.json()
        except Exception as e:
            search_results = {"results": [], "error": str(e)}

        return {
            "query_original": request.query,
            "query_expandida": query_buscar,
            "is_valid": True,
            "intencion": preprocessed.validation.intencion,
            "temas_detectados": preprocessed.structure.temas,
            "territorio_detectado": preprocessed.structure.territorio,
            "años_detectados": preprocessed.structure.años,
            "terminos_añadidos": preprocessed.expansion.terminos_añadidos,
            "filtros_aplicados": preprocessed.filtros_aplicables if request.use_filters else {},
            "results": search_results.get("results", []),
            "total_results": search_results.get("total_results", 0),
            "metadata": {
                "duration_ms": preprocessed.metadata.get("duration_ms", 0),
                "cached": preprocessed.metadata.get("cached", False)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en búsqueda mejorada: {str(e)}")
