#!/usr/bin/env python3
"""
Cliente genérico para LLMs (Ollama) - Configurable para diferentes modelos y casos de uso.
Fase 08: Sprint 6 - Integración de LLM

Este cliente permite:
- Cambiar fácilmente entre modelos (flash para re-ranking, pro para análisis complejo)
- Configurar temperatura, tokens, timeout por caso de uso
- Fallback graceful si el LLM falla
- Logging de prompts/respuestas para debugging

Uso:
    from llm_client import LLMClient

    # Re-ranking (rápido, determinista)
    client = LLMClient(model="deepseek-v4.1-flash:cloud", temperature=0.1)

    # Análisis complejo (futuro - modelo grande)
    client = LLMClient(model="deepseek-v4-pro:cloud", temperature=0.3)
"""

import json
import requests
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import time


@dataclass
class LLMResponse:
    """Respuesta estructurada del LLM."""
    text: str
    model: str
    prompt_tokens: int = 0
    response_tokens: int = 0
    duration_ms: float = 0.0
    timestamp: str = ""
    raw_response: Dict = None


class LLMClient:
    """
    Cliente configurable para Ollama.

    Soporta múltiples configuraciones para diferentes casos de uso:
    - Re-ranking: Flash, baja temperatura, pocos tokens
    - Explicaciones: Flash/Cualquiera, media temperatura
    - Análisis complejo: Pro/Grande, temperatura variable, más tokens
    """

    # Configuraciones predefinidas por caso de uso
    PRESETS = {
        "reranking": {
            "model": "deepseek-v4.1-flash:cloud",  # Modelo por defecto
            "temperature": 0.1,
            "num_predict": 4000,
            "top_p": 0.9,
            "timeout": 300  # Aumentado para pruebas con modelos locales (qwen2.5:7b)
        },
        "explanation": {
            "model": "deepseek-v4.1-flash:cloud",
            "temperature": 0.2,
            "num_predict": 800,
            "top_p": 0.95,
            "timeout": 30
        },
        "analysis": {
            "model": "deepseek-v4-pro:cloud",  # Modelo grande para análisis complejo
            "temperature": 0.3,
            "num_predict": 4000,
            "top_p": 0.95,
            "timeout": 120
        },
        "query_expansion": {
            "model": "deepseek-v4.1-flash:cloud",
            "temperature": 0.3,  # Reducido para más determinismo
            "num_predict": 800,  # Aumentado para respuestas completas
            "top_p": 0.9,
            "timeout": 60  # Aumentado: expansión puede tardar más
        }
    }

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: Optional[str] = None,
        temperature: float = 0.1,
        num_predict: int = 1500,
        top_p: float = 0.9,
        top_k: int = 40,
        timeout: int = 60,
        preset: Optional[str] = None,
        verbose: bool = False
    ):
        """
        Inicializar cliente LLM.

        Args:
            ollama_url: URL base de Ollama
            model: Nombre del modelo (sobreescribe preset)
            temperature: Temperatura de generación
            num_predict: Máximo tokens de respuesta
            top_p: Nucleus sampling
            top_k: Top-k sampling
            timeout: Timeout en segundos
            preset: Usar configuración predefinida ("reranking", "explanation", etc.)
            verbose: Mostrar logs detallados
        """
        self.ollama_url = ollama_url.rstrip('/')
        self.verbose = verbose

        # Aplicar preset si se especifica
        if preset and preset in self.PRESETS:
            config = self.PRESETS[preset].copy()
            if model:
                config['model'] = model
            self.model = config['model']
            self.temperature = config.get('temperature', temperature)
            self.num_predict = config.get('num_predict', num_predict)
            self.top_p = config.get('top_p', top_p)
            self.timeout = config.get('timeout', timeout)
            if self.verbose:
                print(f"[LLMClient] Usando preset '{preset}': {self.model}")
        else:
            self.model = model or "deepseek-v4.1-flash:cloud"
            self.temperature = temperature
            self.num_predict = num_predict
            self.top_p = top_p
            self.timeout = timeout

        self.top_k = top_k
        self.api_generate = f"{self.ollama_url}/api/generate"

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        format: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generar texto con el LLM.

        Args:
            prompt: Prompt principal
            system: Mensaje de sistema (opcional)
            format: Forzar formato JSON si "json"
            **kwargs: Sobrescribir parámetros de generación

        Returns:
            LLMResponse con metadatas
        """
        start_time = time.time()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get('temperature', self.temperature),
                "num_predict": kwargs.get('num_predict', self.num_predict),
                "top_p": kwargs.get('top_p', self.top_p),
                "top_k": kwargs.get('top_k', self.top_k),
                "stop": kwargs.get('stop', None)
            }
        }

        if system:
            payload["system"] = system

        if format == "json":
            payload["format"] = "json"

        try:
            if self.verbose:
                print(f"[LLMClient] Generando con {self.model}...")
                print(f"[LLMClient] Prompt: {len(prompt)} chars")

            response = requests.post(
                self.api_generate,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            duration = (time.time() - start_time) * 1000

            result = LLMResponse(
                text=data.get("response", ""),
                model=data.get("model", self.model),
                prompt_tokens=data.get("prompt_eval_count", 0),
                response_tokens=data.get("eval_count", 0),
                duration_ms=duration,
                timestamp=datetime.now().isoformat(),
                raw_response=data
            )

            if self.verbose:
                print(f"[LLMClient] Respuesta: {len(result.text)} chars")
                print(f"[LLMClient] Tokens: {result.prompt_tokens} → {result.response_tokens}")
                print(f"[LLMClient] Tiempo: {duration:.0f}ms")

            return result

        except requests.exceptions.Timeout:
            raise RuntimeError(f"Timeout ({self.timeout}s) llamando a Ollama")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error conectando a Ollama: {e}")

    def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Generar y parsear JSON directamente.

        Args:
            prompt: Prompt que solicita JSON
            system: Mensaje de sistema
            **kwargs: Parámetros adicionales

        Returns:
            Dict parseado del JSON de respuesta
        """
        response = self.generate(prompt, system=system, format="json", **kwargs)

        if not response.text:
            raise ValueError("Respuesta vacía del LLM")

        # Intentar extraer JSON de la respuesta
        text = response.text.strip()

        # Buscar entre backticks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON inválido: {e}\nTexto: {text[:200]}...")

    def is_available(self) -> bool:
        """Verificar si Ollama está disponible."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

    def list_models(self) -> list:
        """Listar modelos disponibles en Ollama."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except:
            return []


# Factory para crear clientes preconfigurados
def create_llm_client(
    use_case: str = "reranking",
    ollama_url: str = "http://localhost:11434",
    verbose: bool = False
) -> LLMClient:
    """
    Factory para crear cliente LLM configurado según caso de uso.

    Args:
        use_case: "reranking", "explanation", "analysis", "query_expansion"
        ollama_url: URL de Ollama
        verbose: Logs detallados

    Returns:
        LLMClient configurado
    """
    return LLMClient(ollama_url=ollama_url, preset=use_case, verbose=verbose)


if __name__ == "__main__":
    # Tests del cliente
    print("=" * 60)
    print("TEST DEL CLIENTE LLM")
    print("=" * 60)

    # Test 1: Cliente con preset de re-ranking
    print("\n1. Test con preset 'reranking':")
    client = create_llm_client(use_case="reranking", verbose=True)
    print(f"   Modelo: {client.model}")
    print(f"   Temperatura: {client.temperature}")

    # Test 2: Generación simple
    print("\n2. Test de generación:")
    try:
        response = client.generate(
            "Responde en JSON: {\"saludo\": \"hola\"}",
            format="json"
        )
        print(f"   ✅ Respuesta: {response.text[:100]}...")
        print(f"   ✅ Tiempo: {response.duration_ms:.0f}ms")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Disponibilidad
    print("\n3. Test de disponibilidad:")
    if client.is_available():
        print("   ✅ Ollama disponible")
        models = client.list_models()
        print(f"   Modelos: {models[:3]}...")
    else:
        print("   ❌ Ollama no disponible")

    print("\n" + "=" * 60)
