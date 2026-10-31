#!/usr/bin/env python3
"""
Routes API para chat sobre datasets - Sprint 8 (#10)

Endpoints:
    POST /dataset/chat - Responde una pregunta sobre un dataset usando metadatos
"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent / "motor"))
from dataset_chat_engine import answer_question


router_dataset_chat = APIRouter(prefix="/dataset", tags=["dataset_chat"])


class DatasetChatRequest(BaseModel):
    dataset_id: str
    question: str
    model: str = "deepseek-v4.1-flash:cloud"


class DatasetChatResponse(BaseModel):
    dataset_id: str
    question: str
    answer: str
    source: str
    model: str
    latency_ms: int
    dataset_title: str


@router_dataset_chat.post("/chat", response_model=DatasetChatResponse)
async def dataset_chat(request: DatasetChatRequest):
    """
    Responde una pregunta sobre un dataset usando sus metadatos (RAG simple).

    El asistente solo utiliza:
    - Título y descripción del dataset
    - TL;DR generado previamente
    - Perfil estructurado (variables, cobertura temporal, nivel geográfico, frecuencia, formatos)

    No accede a los datos reales del dataset.
    """
    if not request.dataset_id or not request.question:
        raise HTTPException(status_code=400, detail="dataset_id y question son obligatorios")

    result = answer_question(
        dataset_id=request.dataset_id,
        question=request.question,
        modelo=request.model
    )

    if result["source"] == "not_found":
        raise HTTPException(status_code=404, detail=result["answer"])

    return DatasetChatResponse(**result)
