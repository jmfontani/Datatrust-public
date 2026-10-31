#!/usr/bin/env python3
"""
Rutas API para búsqueda mejorada con pre-procesamiento LLM (#3, #4, #12)
Fase 08: Sprint 6 - Query Preprocessing

Endpoints:
    POST /search/enhanced     - Búsqueda con pre-procesamiento LLM
    POST /query/analyze       - Solo análisis de query (sin búsqueda)
    POST /query/validate      - Solo validación (#12)
    POST /query/expand        - Solo expansión (#4)

Uso:
    from routes_query_enhanced import router_query_enhanced
    app.include_router(router_query_enhanced, prefix="/enhanced")
"""

import sys
import os
import asyncio
import threading
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Añadir rutas necesarias
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../motor'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../05_Sprint3_Busqueda_UI/codigo/api'))

from query_preprocessor import QueryPreprocessor, get_preprocessor
from llm_client import LLMClient
from query_suggester import QuerySuggester, get_query_suggester

# Router de FastAPI
router_query_enhanced = APIRouter(prefix="/enhanced", tags=["Query Enhancement"])

# URL del motor base (v07)
MOTOR_BASE_URL = "http://localhost:8000"


# ==================== SCHEMAS PYDANTIC ====================

class EnhancedSearchRequest(BaseModel):
    """Request para búsqueda mejorada con pre-procesamiento."""
    query: str = Field(..., min_length=1, max_length=500, description="Query del usuario")
    limit: int = Field(10, ge=1, le=50, description="Máximo resultados")
    use_expansion: bool = Field(True, description="Activar expansión semántica (#4)")
    use_filters: bool = Field(True, description="Aplicar filtros estructurados (#3)")


class ValidationRequest(BaseModel):
    """Request para validación de query."""
    query: str = Field(..., min_length=1, max_length=500)


class ExpansionRequest(BaseModel):
    """Request para expansión de query."""
    query: str = Field(..., min_length=1, max_length=500)


class ValidationResponse(BaseModel):
    """Respuesta de validación (#12)."""
    is_valid: bool
    intencion: str
    confianza: float
    alertas: List[str]
    sugerencia_correccion: Optional[str] = None


class QueryStructureResponse(BaseModel):
    """Respuesta de interpretación estructurada (#3)."""
    temas: List[str]
    territorio: Optional[str]
    años: List[int]
    edad_rango: Optional[str]
    conceptos_implicitos: List[str]
    filtros_dcat: Dict
    confianza: float


class ExpansionResponse(BaseModel):
    """Respuesta de expansión semántica (#4)."""
    query_original: str
    query_expandida: str
    terminos_añadidos: List[str]
    pesos: Dict[str, float]


class EnhancedResult(BaseModel):
    """Resultado de búsqueda mejorado."""
    dataset_id: str
    title: str
    description: str
    publisher: str
    theme: str
    territory: str
    score: float
    explanation: Optional[str] = None


class EnhancedSearchResponse(BaseModel):
    """Respuesta completa de búsqueda mejorada."""
    query_original: str
    query_expandida: str
    validation: ValidationResponse
    structure: QueryStructureResponse
    filtros_aplicados: Dict
    results: List[EnhancedResult]
    metadata: Dict


class AnalysisOnlyResponse(BaseModel):
    """Respuesta de análisis sin búsqueda."""
    query: str
    validation: ValidationResponse
    structure: QueryStructureResponse
    expansion: ExpansionResponse
    filtros_sugeridos: Dict


# ==================== SCHEMAS PARA SUGERENCIAS (#13) ====================

class SuggestionRequest(BaseModel):
    """Request para sugerencias de queries."""
    query: str = Field(..., min_length=1, max_length=500, description="Query original")
    n: int = Field(5, ge=1, le=10, description="Número de sugerencias")
    categories: Optional[List[str]] = Field(None, description="Filtrar por categoría")


class SuggestionItem(BaseModel):
    """Una sugerencia individual."""
    text: str
    category: str
    reason: str
    confidence: float
    source: str = "lexical"


class SuggestionResponse(BaseModel):
    """Respuesta de sugerencias."""
    query_original: str
    suggestions: List[SuggestionItem]
    lexical_count: int = 0
    llm_count: int = 0
    duration_ms: float = 0.0
    llm_pending: bool = False


class SuggestionCombinedResponse(BaseModel):
    """Respuesta combinada (léxico + LLM pending)."""
    query_original: str
    suggestions: List[SuggestionItem]
    llm_pending: bool = True
    poll_url: Optional[str] = None
    lexical_count: int
    estimated_llm_time_ms: float = 5000.0


# ==================== ENDPOINTS ====================

@router_query_enhanced.post("/search", response_model=EnhancedSearchResponse)
async def search_enhanced(request: EnhancedSearchRequest):
    """
    Búsqueda mejorada con pre-procesamiento LLM (#3, #4, #12).

    Pipeline:
        1. Valida la query (#12)
        2. Extrae estructura (#3)
        3. Expande con sinónimos (#4)
        4. Ejecuta búsqueda con query enriquecida
    """
    try:
        # Obtener pre-procesador
        preprocessor = get_preprocessor()

        # PASO 1-3: Pre-procesamiento
        preprocessed = preprocessor.process(
            request.query,
            use_cache=True,
            apply_strict_filters=request.use_filters
        )

        # Si no es válida, retornar temprano
        if not preprocessed.validation.is_valid:
            return EnhancedSearchResponse(
                query_original=request.query,
                query_expandida=request.query,
                validation=ValidationResponse(
                    is_valid=False,
                    intencion=preprocessed.validation.intencion,
                    confianza=preprocessed.validation.confianza,
                    alertas=preprocessed.validation.alertas,
                    sugerencia_correccion=preprocessed.validation.sugerencia_correccion
                ),
                structure=QueryStructureResponse(
                    temas=[], territorio=None, años=[],
                    edad_rango=None, conceptos_implicitos=[],
                    filtros_dcat={}, confianza=0.0
                ),
                filtros_aplicados={},
                results=[],
                metadata={
                    "rejected": True,
                    "reason": "Query inválida",
                    "alertas": preprocessed.validation.alertas
                }
            )

        # PASO 4: Ejecutar búsqueda con motor base
        # Usar query expandida si está activada la opción
        query_para_buscar = (
            preprocessed.expansion.query_expandida if request.use_expansion
            else request.query
        )

        # Construir filtros
        filtros = {}
        if request.use_filters:
            filtros = preprocessed.filtros_aplicables

        # Llamar al motor base
        search_payload = {
            "query": query_para_buscar,
            "limit": request.limit
        }

        # Añadir filtros si existen
        if filtros:
            search_payload["filters"] = filtros

        try:
            response = requests.post(
                f"{MOTOR_BASE_URL}/search",
                json=search_payload,
                timeout=30,
                verify=False
            )
            response.raise_for_status()
            search_results = response.json()
        except Exception as e:
            # Fallback: buscar sin filtros
            response = requests.post(
                f"{MOTOR_BASE_URL}/search",
                json={"query": query_para_buscar, "limit": request.limit},
                timeout=30,
                verify=False
            )
            response.raise_for_status()
            search_results = response.json()

        # Formatear resultados
        results = [
            EnhancedResult(
                dataset_id=r.get("dataset_id", ""),
                title=r.get("title", ""),
                description=r.get("description", "")[:200],
                publisher=r.get("publisher", "N/A"),
                theme=r.get("theme", "N/A"),
                territory=r.get("territory", "N/A"),
                score=r.get("score", 0.0),
                explanation=None  # Podríamos añadir explicaciones aquí también
            )
            for r in search_results.get("results", [])
        ]

        return EnhancedSearchResponse(
            query_original=request.query,
            query_expandida=query_para_buscar,
            validation=ValidationResponse(
                is_valid=preprocessed.validation.is_valid,
                intencion=preprocessed.validation.intencion,
                confianza=preprocessed.validation.confianza,
                alertas=preprocessed.validation.alertas,
                sugerencia_correccion=preprocessed.validation.sugerencia_correccion
            ),
            structure=QueryStructureResponse(
                temas=preprocessed.structure.temas,
                territorio=preprocessed.structure.territorio,
                años=preprocessed.structure.años,
                edad_rango=preprocessed.structure.edad_rango,
                conceptos_implicitos=preprocessed.structure.conceptos_implicitos,
                filtros_dcat=preprocessed.structure.filtros_dcat,
                confianza=preprocessed.structure.confianza
            ),
            filtros_aplicados=filtros,
            results=results,
            metadata={
                "duration_ms": preprocessed.metadata.get("duration_ms", 0),
                "model": preprocessed.metadata.get("model", "unknown"),
                "terminos_expandidos": len(preprocessed.expansion.terminos_añadidos)
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en búsqueda mejorada: {str(e)}")


@router_query_enhanced.post("/query/analyze", response_model=AnalysisOnlyResponse)
async def analyze_query(request: ValidationRequest):
    """
    Solo analiza la query sin ejecutar búsqueda.
    Útil para previsualizar interpretación antes de buscar.
    """
    try:
        preprocessor = get_preprocessor()
        result = preprocessor.process(request.query)

        return AnalysisOnlyResponse(
            query=request.query,
            validation=ValidationResponse(
                is_valid=result.validation.is_valid,
                intencion=result.validation.intencion,
                confianza=result.validation.confianza,
                alertas=result.validation.alertas,
                sugerencia_correccion=result.validation.sugerencia_correccion
            ),
            structure=QueryStructureResponse(
                temas=result.structure.temas,
                territorio=result.structure.territorio,
                años=result.structure.años,
                edad_rango=result.structure.edad_rango,
                conceptos_implicitos=result.structure.conceptos_implicitos,
                filtros_dcat=result.structure.filtros_dcat,
                confianza=result.structure.confianza
            ),
            expansion=ExpansionResponse(
                query_original=result.expansion.query_original,
                query_expandida=result.expansion.query_expandida,
                terminos_añadidos=result.expansion.terminos_añadidos,
                pesos=result.expansion.pesos
            ),
            filtros_sugeridos=result.filtros_aplicables
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis: {str(e)}")


@router_query_enhanced.post("/query/validate", response_model=ValidationResponse)
async def validate_query(request: ValidationRequest):
    """
    Solo valida la query (#12).
    Útil para validación en tiempo real (mientras escribe el usuario).
    """
    try:
        preprocessor = get_preprocessor()
        result = preprocessor.process(request.query)

        return ValidationResponse(
            is_valid=result.validation.is_valid,
            intencion=result.validation.intencion,
            confianza=result.validation.confianza,
            alertas=result.validation.alertas,
            sugerencia_correccion=result.validation.sugerencia_correccion
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en validación: {str(e)}")


@router_query_enhanced.post("/query/expand", response_model=ExpansionResponse)
async def expand_query(request: ExpansionRequest):
    """
    Solo expande la query (#4).
    Útil para mostrar sugerencias de búsqueda ampliada.
    """
    try:
        preprocessor = get_preprocessor()
        result = preprocessor.process(request.query)

        return ExpansionResponse(
            query_original=result.expansion.query_original,
            query_expandida=result.expansion.query_expandida,
            terminos_añadidos=result.expansion.terminos_añadidos,
            pesos=result.expansion.pesos
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en expansión: {str(e)}")


# ==================== CACHE PARA RESULTADOS LLM ====================
# Almacena resultados LLM temporalmente para polling
_suggestion_cache: Dict[str, dict] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutos
_llm_threads: Dict[str, threading.Thread] = {}

def _generate_cache_key(query: str) -> str:
    """Generar clave de cache para una query."""
    import hashlib
    return hashlib.md5(query.lower().strip().encode()).hexdigest()


def _fetch_llm_background_sync(query: str, n: int, cache_key: str, initial_suggestions: list, ollama_url: str = None):
    """Función síncrona para ejecutar LLM en background."""
    try:
        # Marcar como pendiente
        _suggestion_cache[cache_key] = {
            "query": query,
            "lexical": initial_suggestions,
            "llm": [],
            "timestamp": datetime.now().isoformat(),
            "complete": False,
            "status": "running"
        }

        # Ejecutar LLM (con URL personalizada para Docker)
        suggester = get_query_suggester(ollama_url=ollama_url or "http://localhost:11434")
        llm_result = asyncio.run(suggester.suggest_llm(query, n=n))

        # Guardar resultado
        _suggestion_cache[cache_key] = {
            "query": query,
            "lexical": initial_suggestions,
            "llm": [
                {
                    "text": s.text,
                    "category": s.category,
                    "reason": s.reason,
                    "confidence": s.confidence,
                    "source": s.source
                }
                for s in llm_result.suggestions
            ],
            "timestamp": datetime.now().isoformat(),
            "complete": True,
            "status": "done"
        }
    except Exception as e:
        _suggestion_cache[cache_key] = {
            "query": query,
            "lexical": initial_suggestions,
            "llm": [],
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "complete": True,
            "status": "error"
        }


# ==================== ENDPOINTS PARA SUGERENCIAS (#13) ====================

@router_query_enhanced.post("/query/suggest", response_model=SuggestionCombinedResponse)
async def suggest_queries(request: SuggestionRequest):
    """
    Generar sugerencias de queries relacionadas (#13).

    Enfoque híbrido asíncrono:
    1. Retorna sugerencias léxicas inmediatamente (<5ms)
    2. Dispara LLM en background
    3. Frontend puede hacer poll para resultados LLM

    Útil para:
    - Mostrar "También podrías buscar: ..." en UI
    - Ayudar cuando hay 0 resultados
    - Exploración guiada
    """
    try:
        suggester = get_query_suggester()

        # Obtener sugerencias léxicas (instantáneo)
        lexical_result = suggester.suggest_lexical(
            request.query,
            n=request.n,
            categories=request.categories
        )

        # Formatear sugerencias
        suggestions = [
            SuggestionItem(
                text=sug.text,
                category=sug.category,
                reason=sug.reason,
                confidence=sug.confidence,
                source=sug.source
            )
            for sug in lexical_result.suggestions
        ]

        # Generar cache key para polling LLM
        cache_key = _generate_cache_key(request.query)

        # Disparar LLM en background usando threading (más robusto que asyncio.create_task)
        # Usar host.docker.internal para Ollama dentro de Docker
        llm_thread = threading.Thread(
            target=_fetch_llm_background_sync,
            args=(request.query, request.n, cache_key, suggestions, "http://host.docker.internal:11434"),
            daemon=True
        )
        llm_thread.start()
        _llm_threads[cache_key] = llm_thread

        return SuggestionCombinedResponse(
            query_original=request.query,
            suggestions=suggestions,
            llm_pending=True,
            poll_url=f"/enhanced/query/suggest/{cache_key}/result",
            lexical_count=len(suggestions)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en sugerencias: {str(e)}")


@router_query_enhanced.get("/query/suggest/{cache_key}/result")
async def get_suggestion_result(cache_key: str):
    """
    Obtener resultados completos (léxico + LLM) por cache key.

    El frontend hace poll a este endpoint después de recibir
    la respuesta inicial con llm_pending=True.
    """
    if cache_key not in _suggestion_cache:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")

    cached = _suggestion_cache[cache_key]

    if not cached.get("complete", False):
        # Todavía está procesando
        return {
            "query_original": cached.get("query", ""),
            "suggestions": cached.get("lexical", []),
            "llm_pending": True,
            "lexical_count": len(cached.get("lexical", []))
        }

    # Completo: mergear léxico + LLM
    all_suggestions = cached.get("lexical", []) + cached.get("llm", [])

    # Eliminar duplicados por texto (manejar tanto dicts como SuggestionItem)
    seen = set()
    unique = []
    for s in all_suggestions:
        # Manejar tanto dicts como objetos Pydantic
        if isinstance(s, dict):
            text = s.get("text", "")
        else:
            text = getattr(s, "text", "") or (s["text"] if hasattr(s, "__getitem__") else "")

        if text and text.lower() not in seen:
            seen.add(text.lower())
            # Convertir a dict si es objeto
            if isinstance(s, dict):
                unique.append(s)
            else:
                unique.append({
                    "text": getattr(s, "text", ""),
                    "category": getattr(s, "category", ""),
                    "reason": getattr(s, "reason", ""),
                    "confidence": getattr(s, "confidence", 0),
                    "source": getattr(s, "source", "lexical")
                })

    return {
        "query_original": cached.get("query", ""),
        "suggestions": unique,
        "llm_pending": False,
        "lexical_count": len(cached.get("lexical", [])),
        "llm_count": len(cached.get("llm", [])),
        "total_count": len(unique)
    }


@router_query_enhanced.post("/query/suggest/llm", response_model=SuggestionResponse)
async def suggest_queries_llm(request: SuggestionRequest):
    """
    Solo sugerencias LLM (síncrono, ~3-5s).

    Usar cuando se quiere esperar el resultado completo.
    """
    try:
        # Usar host.docker.internal dentro de Docker
        ollama_url = "http://host.docker.internal:11434"
        suggester = get_query_suggester(ollama_url=ollama_url)

        result = await suggester.suggest_llm(
            request.query,
            n=request.n
        )

        suggestions = [
            SuggestionItem(
                text=sug.text,
                category=sug.category,
                reason=sug.reason,
                confidence=sug.confidence,
                source=sug.source
            )
            for sug in result.suggestions
        ]

        return SuggestionResponse(
            query_original=request.query,
            suggestions=suggestions,
            llm_count=len(suggestions),
            duration_ms=result.duration_ms
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en sugerencias LLM: {str(e)}")


@router_query_enhanced.get("/query/suggest/lexical")
async def suggest_queries_lexical(
    query: str,
    n: int = 5,
    categories: Optional[str] = None
):
    """
    Solo sugerencias léxicas (GET, <5ms).

    Útil para llamadas simples desde frontend.
    """
    try:
        suggester = get_query_suggester()

        cats = categories.split(",") if categories else None
        result = suggester.suggest_lexical(query, n=n, categories=cats)

        suggestions = [
            {
                "text": sug.text,
                "category": sug.category,
                "reason": sug.reason,
                "confidence": sug.confidence,
                "source": sug.source
            }
            for sug in result.suggestions
        ]

        return {
            "query_original": query,
            "suggestions": suggestions,
            "lexical_count": len(suggestions),
            "duration_ms": result.duration_ms
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ==================== ENDPOINTS DE HEALTH ====================

@router_query_enhanced.get("/health")
async def health_check():
    """Estado del servicio de pre-procesamiento."""
    try:
        preprocessor = get_preprocessor()
        return {
            "status": "ok",
            "model": preprocessor.llm.model,
            "cache_size": len(preprocessor._cache),
            "features": {
                "validation": True,      # #12
                "interpretation": True,  # #3
                "expansion": True,        # #4
                "suggestions": True       # #13
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router_query_enhanced.get("/query/suggest/health")
async def suggest_health_check():
    """Estado del servicio de sugerencias."""
    try:
        suggester = get_query_suggester()
        return {
            "status": "ok",
            "cache_size": len(_suggestion_cache),
            "features": {
                "lexical": True,
                "llm": True,
                "async_polling": True
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    print("Routes Query Enhanced - Módulo de endpoints API")
    print("=" * 60)
    print("Endpoints disponibles:")
    print("  POST /enhanced/search      - Búsqueda completa")
    print("  POST /enhanced/query/analyze - Análisis sin búsqueda")
    print("  POST /enhanced/query/validate - Solo validación")
    print("  POST /enhanced/query/expand   - Solo expansión")
    print("  GET  /enhanced/health      - Estado del servicio")
    print()
    print("  (#13) SUGERENCIAS DE QUERIES:")
    print("  POST /enhanced/query/suggest        - Sugerencias (léxico + LLM background)")
    print("  GET  /enhanced/query/suggest/lexical - Solo léxico (<5ms)")
    print("  POST /enhanced/query/suggest/llm    - Solo LLM (~3-5s)")
    print("  GET  /enhanced/query/suggest/{key}/result - Polling resultado")
    print("  GET  /enhanced/query/suggest/health - Estado sugerencias")
