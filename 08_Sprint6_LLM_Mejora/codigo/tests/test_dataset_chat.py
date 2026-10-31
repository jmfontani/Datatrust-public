#!/usr/bin/env python3
"""
Tests para Sprint 8 - Caso de Uso #10: Respuestas a preguntas sobre datasets.

Valida:
1. Motor de chat obtiene contexto del dataset
2. Endpoint /dataset/chat responde correctamente
3. Respuesta basada en metadatos, sin inventar información
"""

import sys
import json
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "motor"))
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

import requests
import psycopg2
from dataset_chat_engine import get_dataset_context, answer_question


DB_CONFIG = {
    "host": "172.17.0.1",
    "port": 5432,
    "database": "buscador",
    "user": "postgres",
    "password": "postgres"
}

API_URL = "http://localhost:8001"


def get_sample_dataset_id():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT dataset_id
        FROM dataset_profiles
        WHERE tldr IS NOT NULL
        ORDER BY random()
        LIMIT 1
    """)
    dataset_id = cur.fetchone()[0]
    conn.close()
    return dataset_id


def test_get_dataset_context():
    dataset_id = get_sample_dataset_id()
    context = get_dataset_context(dataset_id)

    assert context is not None, f"No se encontró contexto para {dataset_id}"
    assert context["dataset_id"] == dataset_id
    assert "title" in context
    assert "description" in context

    print(f"✅ Test 1: Contexto obtenido para {dataset_id[:60]}")
    return dataset_id


def test_answer_question_engine():
    dataset_id = get_sample_dataset_id()
    result = answer_question(dataset_id, "¿Qué datos contiene este dataset?")

    assert result is not None
    assert "answer" in result
    assert len(result["answer"]) > 10
    assert result["source"] == "llm_metadata"

    print(f"✅ Test 2: Motor responde pregunta ({result['latency_ms']} ms)")
    print(f"   Respuesta: {result['answer'][:120]}...")
    return dataset_id


def test_api_dataset_chat():
    dataset_id = get_sample_dataset_id()
    response = requests.post(
        f"{API_URL}/dataset/chat",
        json={
            "dataset_id": dataset_id,
            "question": "¿Qué territorio cubre este dataset?"
        },
        timeout=60
    )

    assert response.status_code == 200, f"Status code: {response.status_code}"

    data = response.json()
    assert "answer" in data
    assert "model" in data
    assert data["source"] == "llm_metadata"

    print(f"✅ Test 3: Endpoint /dataset/chat funciona ({data['latency_ms']} ms)")
    print(f"   Respuesta: {data['answer'][:120]}...")
    return data


def test_chat_refuses_unknown_info():
    """El asistente no debe inventar información que no esté en metadatos."""
    dataset_id = get_sample_dataset_id()
    result = answer_question(dataset_id, "¿Cuál es el color favorito del alcalde de este municipio?")

    # No debería contestar con un color concreto
    color_words = ["rojo", "azul", "verde", "amarillo", "negro", "blanco"]
    answer_lower = result["answer"].lower()

    assert not any(c in answer_lower for c in color_words), "El modelo inventó información"
    assert len(result["answer"]) > 5

    print(f"✅ Test 4: Asistente evita inventar información")


def test_chat_not_found():
    response = requests.post(
        f"{API_URL}/dataset/chat",
        json={
            "dataset_id": "no-existe-12345",
            "question": "¿Qué datos contiene?"
        },
        timeout=10
    )

    assert response.status_code == 404, f"Esperado 404, obtenido {response.status_code}"
    print("✅ Test 5: Endpoint devuelve 404 para dataset inexistente")


def main():
    print("=" * 60)
    print("TESTS CASO DE USO #10 - CHAT SOBRE DATASETS")
    print("=" * 60)

    try:
        test_get_dataset_context()
        test_answer_question_engine()
        test_api_dataset_chat()
        test_chat_refuses_unknown_info()
        test_chat_not_found()

        print("\n" + "=" * 60)
        print("✅ TODOS LOS TESTS PASARON")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test fallido: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
