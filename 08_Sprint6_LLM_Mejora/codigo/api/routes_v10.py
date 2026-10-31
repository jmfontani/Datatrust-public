#!/usr/bin/env python3
"""
Router V10 - Arquitectura Optimizada (Re-ranking Desactivado)
==============================================================

Implementa Opción B: Explicaciones bajo demanda sin re-ranking automático
- /llm/search/fast  : Búsqueda rápida sin LLM (motor híbrido v07 directo)
- /llm/explain      : Explicaciones de relevancia bajo demanda
- /llm/enhance      : Búsqueda con re-ranking (legacy, desactivado por defecto)

Autor: Fonta
Fecha: 2026-06-04
"""

import sys
import os
import time
import json
import logging
from typing import List, Dict, Optional
from types import SimpleNamespace
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np

# Paths para imports
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../motor'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../db'))

from llm_client import LLMClient, create_llm_client

# Lexical expander simple (inline para evitar dependencias)
class LexicalExpanderSimple:
    """Expansor léxico simplificado."""
    SINONIMOS = {
        'paro': ['desempleo', 'desempleado', 'parados', 'atur'],
        'banco': ['financiero', 'entidad bancaria', 'crédito'],
        'planta': ['vegetación', 'instalación', 'industrial'],
        'empleo': ['trabajo', 'ocupación', 'laboral'],
        'vivienda': ['casa', 'hogar', 'residencial', 'inmueble'],
    }

    def expand(self, query: str) -> dict:
        words = query.lower().split()
        expanded_terms = []
        for w in words:
            if w in self.SINONIMOS:
                expanded_terms.extend(self.SINONIMOS[w])
        return {
            'query_expandida': query + ' ' + ' '.join(expanded_terms) if expanded_terms else query,
            'terminos_añadidos': expanded_terms
        }

logger = logging.getLogger(__name__)

# DB config
def get_db_config():
    from dotenv import load_dotenv
    load_dotenv()
    # Las variables del contenedor son POSTGRES_*, como en main_v2_final_v07.
    # Antes solo miraba DB_* (que no existen en el compose) y caia a 'localhost',
    # asi que /llm/search/fast no encontraba la base y devolvia [] SIN error.
    return {
        'host': os.getenv('POSTGRES_HOST') or os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT') or os.getenv('DB_PORT', 5432)),
        'database': os.getenv('POSTGRES_DB') or os.getenv('DB_NAME', 'buscador'),
        'user': os.getenv('POSTGRES_USER') or os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD') or os.getenv('DB_PASSWORD', 'postgres')
    }

DB_CONFIG = get_db_config()


# ============================================================================
# ROUTER PRINCIPAL
# ============================================================================

router_v10 = APIRouter(prefix="/llm", tags=["V10 - LLM Optimizado"])


# ============================================================================
# MODELOS DE REQUEST/RESPONSE
# ============================================================================

class FastSearchRequest(BaseModel):
    """Request para búsqueda rápida sin re-ranking."""
    query: str = Field(..., min_length=1, max_length=500, description="Consulta del usuario")
    filters: Optional[Dict] = Field(None, description="Filtros opcionales (theme, territory, etc.)")
    limit: int = Field(10, ge=1, le=50, description="Número de resultados a devolver")
    semantic_weight: float = Field(0.75, ge=0, le=1, description="Peso de búsqueda semántica")
    lexical_weight: float = Field(0.25, ge=0, le=1, description="Peso de búsqueda léxica")


class DatasetResult(BaseModel):
    """Resultado de dataset en búsqueda rápida."""
    dataset_id: str
    title: str
    description: str
    publisher: str
    theme: str
    territory: str
    format: str
    score: float
    explanation: Optional[str] = None  # Solo si se pide explícitamente


class FastSearchResponse(BaseModel):
    """Response de búsqueda rápida."""
    query: str
    results: List[DatasetResult]
    total: int
    metadata: Dict


class ExplainRequest(BaseModel):
    """Request para explicación de relevancia bajo demanda."""
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

_explanation_client: Optional[LLMClient] = None


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


# STOP WORDS (simplificado)
STOP_WORDS = {
    'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
    'y', 'o', 'pero', 'si', 'no', 'en', 'de', 'del', 'al',
    'con', 'por', 'para', 'que', 'cual', 'como', 'cuando', 'donde',
}

# PALABRAS AMBIGUAS
PALABRAS_AMBIGUAS = {
    'paro': {'contexto': 'empleo desempleo', 'sinonimos': ['desempleo', 'desempleado', 'parados']},
    'banco': {'contexto': 'finanzas economía', 'sinonimos': ['financiero', 'monetario', 'crédito']},
    'planta': {'contexto': 'vegetación industria', 'sinonimos': ['vegetación', 'industrial', 'instalación']},
}


def get_db_connection():
    """Crea conexión a PostgreSQL."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Error conectando a PostgreSQL: {e}")
        return None


# Modelo de embeddings: nombre completo y revision fijada (ver docs/PINNING-DEPENDENCIAS.md).
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"

# Motor de embeddings: mismo switch por entorno que main_v2_final_v07. Este router
# es el de /search/fast y tiene su PROPIA copia de la logica; si no se parametriza
# aqui, este endpoint seguiria comparando contra `embedding` (384) mientras la
# columna activa seria de 1024 -> error de dimension en cada peticion.
import os as _os
EXPERIMENTO_MOTOR = _os.getenv("EXPERIMENTO_MOTOR", "minilm").strip().lower()
EXPERIMENTO_COLUMNA = _os.getenv("EXPERIMENTO_COLUMNA", "embedding").strip()
OLLAMA_EMBED_URL = _os.getenv("OLLAMA_EMBED_URL", "http://172.17.0.1:11434/api/embed")

# Cache del modelo: antes se instanciaba dentro de get_embedding(), es decir en
# CADA peticion, lo que recargaba los pesos (~470 MB) una y otra vez.
_modelo_embeddings = None


def _get_modelo():
    """Devuelve el modelo de embeddings, cargandolo una sola vez."""
    global _modelo_embeddings
    if _modelo_embeddings is None:
        from sentence_transformers import SentenceTransformer
        _modelo_embeddings = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)
    return _modelo_embeddings


def _embed_bge(text: str) -> list:
    """Embedding BGE-M3 (1024 dims) via ollama. Devuelve la lista directamente."""
    import urllib.request as _ur
    body = json.dumps({"model": "bge-m3", "input": [text],
                       "options": {"num_ctx": 1024}}).encode()
    req = _ur.Request(OLLAMA_EMBED_URL, data=body,
                      headers={"Content-Type": "application/json"})
    d = json.loads(_ur.urlopen(req, timeout=300).read())
    return d["embeddings"][0]


def get_embedding(text: str) -> list:
    """Genera embedding con el motor activo."""
    if EXPERIMENTO_MOTOR == "bge":
        # El fallback de ceros de 384 dims NO sirve aqui: se propaga el error.
        return _embed_bge(text)
    try:
        model = _get_modelo()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error generando embedding: {e}")
        return [0.0] * 384


def vector_to_pgvector(emb_list: list) -> str:
    """Convierte lista de floats a string de pgvector."""
    return '[' + ','.join(str(x) for x in emb_list) + ']'


def buscar_en_db(query: str, top_k: int = 10, semantic_weight: float = 0.75, lexical_weight: float = 0.25,
                 filters: Optional[Dict] = None) -> List[Dict]:
    """
    Búsqueda híbrida directa en DB (semántica + léxica).
    Sin llamadas HTTP externas.
    """
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 1. Generar embedding
        query_embedding = get_embedding(query)
        embedding_str = vector_to_pgvector(query_embedding)

        # 2. Expansión léxica
        expander = LexicalExpanderSimple()
        expanded = expander.expand(query)
        query_expandida = expanded.get('query_expandida', query)

        # 3. Construir query SQL híbrida
        # OJO: ha de ser f-string; el nombre de columna se interpola desde
        # EXPERIMENTO_COLUMNA. Sin la f, el placeholder viajaba literal a
        # PostgreSQL y el endpoint devolvia [] en silencio.
        sql = f"""
        SELECT id, title, description, publisher, theme, territory, format,
               (semantic_score * %s + lexical_score * %s) AS score_final
        FROM (
            SELECT
                d.id, d.title, d.description, d.publisher, d.theme, d.territory, d.format,
                (1 - (d.{EXPERIMENTO_COLUMNA} <=> %s::vector)) AS semantic_score,
                (
                    SELECT COALESCE(MAX(ts_rank(to_tsvector('spanish', COALESCE(d.title, '') || ' ' || COALESCE(d.description, '')), query)), 0)
                    FROM websearch_to_tsquery('spanish', %s) AS query
                ) AS lexical_score
            FROM datasets d
            WHERE 1=1
        """

        params = [semantic_weight, lexical_weight, embedding_str, query_expandida]

        # Añadir filtros
        if filters:
            if filters.get('theme'):
                sql += " AND d.theme = %s"
                params.append(filters['theme'])
            if filters.get('territory'):
                sql += " AND d.territory = %s"
                params.append(filters['territory'])

        sql += f"""
            LIMIT %s
        ) AS subq
        WHERE (semantic_score * %s + lexical_score * %s) > 0.1
        ORDER BY score_final DESC
        LIMIT %s
        """
        # El WHERE no puede referenciar el alias score_final (PostgreSQL lo
        # evalua antes del SELECT), asi que se repite la expresion. Los pesos
        # van otra vez como parametros, en el mismo orden.
        params.extend([top_k * 2, semantic_weight, lexical_weight, top_k])

        cur.execute(sql, params)
        resultados = cur.fetchall()
        cur.close()
        conn.close()

        return [dict(r) for r in resultados]

    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        return []


# ============================================================================
# ENDPOINT: /llm/search/fast (NUEVO - Búsqueda rápida sin LLM)
# ============================================================================

@router_v10.post("/search/fast", response_model=FastSearchResponse, summary="Búsqueda rápida sin re-ranking")
async def fast_search(request: FastSearchRequest):
    """
    Búsqueda híbrida rápida usando búsqueda directa en DB (semántica + léxica).

    **NO usa re-ranking con LLM** - resultados en <100ms.
    **NO llama a endpoints externos** - búsqueda directa en PostgreSQL.

    - **query**: Consulta del usuario
    - **filters**: Filtros opcionales (theme, territory, etc.)
    - **limit**: Cuántos resultados devolver (1-50)
    - **semantic_weight**: Peso de búsqueda semántica (0-1)
    - **lexical_weight**: Peso de búsqueda léxica (0-1)

    **Tiempo típico**: 0.03-0.1s
    """
    start_time = time.time()

    try:
        # Búsqueda directa en DB
        results_db = buscar_en_db(
            query=request.query,
            top_k=request.limit,
            semantic_weight=request.semantic_weight,
            lexical_weight=request.lexical_weight,
            filters=request.filters
        )

        # Construir respuesta.
        # OJO: el modelo Pydantic exige str en todos los campos, pero la BD
        # devuelve `id` como int y los campos vacios como None. Sin coercion
        # el endpoint respondia 500 con un error de validacion.
        def _s(v):
            return "" if v is None else str(v)

        results = []
        for r in results_db:
            results.append(DatasetResult(
                dataset_id=_s(r.get("id")),
                title=_s(r.get("title")),
                description=_s(r.get("description")),
                publisher=_s(r.get("publisher")),
                theme=_s(r.get("theme")),
                territory=_s(r.get("territory")),
                format=_s(r.get("format")),
                score=float(r.get("score_final") or 0.0)
            ))

        total_time = (time.time() - start_time) * 1000

        return FastSearchResponse(
            query=request.query,
            results=results,
            total=len(results),
            metadata={
                "status": "success",
                "mode": "fast",
                "llm_used": False,
                "total_time_ms": total_time
            }
        )

    except Exception as e:
        import traceback
        logger.error(f"Error en /llm/search/fast: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================================================================
# ENDPOINT: /llm/explain (Explicación bajo demanda)
# ============================================================================

@router_v10.post("/explain", response_model=ExplainResponse, summary="Explicación de relevancia bajo demanda")
async def explain_relevance(request: ExplainRequest):
    """
    Genera una explicación detallada de por qué un dataset es relevante.

    Usa LLM para analizar la relación entre la query y los metadatos
    del dataset, identificando factores específicos de relevancia.

    **Uso recomendado**: Llamar solo para el TOP-1 o cuando el usuario hace click.

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


# ============================================================================
# ENDPOINT: /llm/enhance (LEGACY - Re-ranking desactivado por defecto)
# ============================================================================

@router_v10.post("/enhance", response_model=FastSearchResponse, summary="Búsqueda con re-ranking (LEGACY)")
async def enhance_search_deprecated(request: FastSearchRequest):
    """
    ⚠️ **DEPRECATED**: Este endpoint ya NO hace re-ranking.

    Por compatibilidad, ahora es un alias de `/llm/search/fast`.

    Para usar re-ranking con LLM, implementar una nueva versión si es necesario.

    **Tiempo típico**: 0.03-0.1s (ya no 50-90s)
    """
    # Redirigir a fast_search
    return await fast_search(request)


# ============================================================================
# HELPERS
# ============================================================================

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

@router_v10.get("/health", summary="Estado del servicio LLM")
async def health_check_llm():
    """Verificar estado de conexión con Ollama y disponibilidad de modelos."""
    try:
        # Verificar solo el cliente de explicaciones (ya no usamos reranker)
        client = get_explanation_client()
        llm_available = client.is_available()

        status = {
            "status": "ok" if llm_available else "degraded",
            "ollama_available": llm_available,
            "explanation_model": client.model if llm_available else None,
            "features": {
                "fast_search": True,
                "explain_on_demand": True,
                "reranking": False  # Desactivado por defecto
            }
        }

        return status
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "features": {
                "fast_search": True,
                "explain_on_demand": False,
                "reranking": False
            }
        }
