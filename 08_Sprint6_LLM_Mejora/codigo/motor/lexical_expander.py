#!/usr/bin/env python3
"""
Lexical Expander - Expansión léxica simple basada en diccionario
Fase 08: Sprint 6 - Fallback para expansión semántica (#4)

Cuando el LLM falla o tarda demasiado, esta clase proporciona
expansión rápida basada en un diccionario de sinónimos del dominio.

Uso:
    from lexical_expander import LexicalExpander

    expander = LexicalExpander()
    resultado = expander.expand("paro juvenil")
    # resultado: {"query_expandida": "paro desempleo juvenil jovenes...",
    #           "terminos_añadidos": ["desempleo", "jovenes"], ...}
"""

import json
import re
from typing import Dict, List, Optional, Set
from pathlib import Path


# Ruta al diccionario de sinónimos externo
SINONIMOS_JSON_PATH = Path(__file__).parent / "sinonimos.json"


def cargar_sinonimos_desde_json(ruta: Optional[Path] = None) -> Dict:
    """
    Cargar diccionario de sinónimos desde archivo JSON.

    Args:
        ruta: Ruta al archivo JSON. Si None, usa la ruta por defecto.

    Returns:
        Diccionario de sinónimos
    """
    json_path = ruta or SINONIMOS_JSON_PATH

    if not json_path.exists():
        # Fallback: diccionario vacío (se usará el default embebido)
        return {}

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get('sinonimos', {})


def get_reglas_expansion(ruta: Optional[Path] = None) -> Dict:
    """
    Obtener reglas de expansión desde JSON.

    Returns:
        Dict con reglas de expansión
    """
    json_path = ruta or SINONIMOS_JSON_PATH

    if not json_path.exists():
        return {
            "max_terminos": 20,
            "peso_original": 1.0,
            "peso_sinonimo_directo": 0.9,
            "peso_relacionado": 0.8,
            "peso_frase_completa": 0.95
        }

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get('reglas_expansion', {})


class LexicalExpander:
    """
    Expansión léxica basada en diccionario de sinónimos.

    Ventajas:
    - Rápida (<1ms)
    - Determinística
    - No depende de LLM
    - Funciona offline
    - Diccionario externalizado en JSON (fácil mantenimiento)
    """

    # Diccionario por defecto (se carga desde sinonimos.json)
    SINONIMOS_DEFAULT = None  # Se inicializa en __init__
    REGLAS_DEFAULT = None  # Se inicializa en __init__

    def __init__(self, sinonimos: Optional[Dict] = None, reglas: Optional[Dict] = None,
                 json_path: Optional[Path] = None):
        """
        Inicializar expander léxico.

        Args:
            sinonimos: Diccionario opcional de sinónimos.
                      Si None, carga desde sinonimos.json
            reglas: Reglas de expansión opcionales.
                   Si None, carga desde sinonimos.json
            json_path: Ruta personalizada al archivo JSON
        """
        # Cargar desde JSON si no se proporcionan
        if sinonimos is None:
            sinonimos = cargar_sinonimos_desde_json(json_path)

        if reglas is None:
            reglas = get_reglas_expansion(json_path)

        self.sinonimos = sinonimos
        self.reglas = reglas
        self._compilar_terminos()

    def _compilar_terminos(self):
        """Compilar términos para búsqueda rápida."""
        # Crear índice inverso: sinónimo -> términos originales
        self.indice_inverso: Dict[str, List[str]] = {}
        for termino, sinonimos_list in self.sinonimos.items():
            for sinonimo in sinonimos_list:
                if sinonimo not in self.indice_inverso:
                    self.indice_inverso[sinonimo] = []
                self.indice_inverso[sinonimo].append(termino)

    def expand(self, query: str, max_terminos: int = 20) -> Dict:
        """
        Expandir query usando sinónimos del diccionario.

        Args:
            query: Query original
            max_terminos: Máximo de términos a añadir

        Returns:
            Dict con query expandida, términos añadidos, pesos
        """
        query_lower = query.lower()
        palabras = self._extraer_palabras_significativas(query_lower)

        terminos_añadidos: Set[str] = set()
        pesos: Dict[str, float] = {}

        # 1. Primero buscar frases completas en la query (multi-word terms)
        for frase, sinonimos_list in self.sinonimos.items():
            if frase in query_lower and len(terminos_añadidos) < max_terminos:
                for sinonimo in sinonimos_list:
                    if sinonimo not in terminos_añadidos:
                        terminos_añadidos.add(sinonimo)
                        pesos[sinonimo] = 0.95  # Frase completa = alta relevancia

        # 2. Para cada palabra en la query, buscar sinónimos
        for palabra in palabras:
            pesos[palabra] = 1.0  # Término original

            if palabra in self.sinonimos:
                # Esta palabra tiene sinónimos definidos
                for sinonimo in self.sinonimos[palabra]:
                    if sinonimo not in terminos_añadidos and len(terminos_añadidos) < max_terminos:
                        terminos_añadidos.add(sinonimo)
                        pesos[sinonimo] = 0.9  # Sinónimo directo

            # También buscar en índice inverso (sinónimos que contengan esta palabra)
            for sinonimo_base, terminos_origen in self.indice_inverso.items():
                if palabra in sinonimo_base and len(terminos_añadidos) < max_terminos:
                    for termino_orig in terminos_origen:
                        if termino_orig not in terminos_añadidos:
                            terminos_añadidos.add(termino_orig)
                            pesos[termino_orig] = 0.8

        # Construir query expandida
        query_expandida = query + " " + " ".join(sorted(terminos_añadidos))

        return {
            "query_original": query,
            "query_expandida": query_expandida.strip(),
            "terminos_añadidos": sorted(list(terminos_añadidos)),
            "pesos": pesos,
            "fuente": "lexical",  # Indica que vino del expander léxico
            "tiempo_ms": 0  # Es instantáneo
        }

    def _extraer_palabras_significativas(self, query: str) -> List[str]:
        """Extraer palabras significativas de la query (sin stopwords)."""
        stopwords = {
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'y', 'o', 'pero', 'si', 'no', 'en', 'de', 'del', 'al',
            'con', 'por', 'para', 'desde', 'hasta', 'entre', 'sobre',
            'a', 'ante', 'bajo', 'segun', 'según', 'sin', 'so',
            'que', 'cual', 'cuales', 'quien', 'quienes', 'como', 'cuando',
            'donde', 'adonde', 'cuanto', 'cuanta', 'es', 'son',
            'en', 'durante', 'mediante', 'salvo', 'excepto',
            'muy', 'mas', 'más', 'menos', 'tanto', 'tan',
        }

        # Limpiar y tokenizar
        palabras = re.findall(r'\b[a-záéíóúñ]+\b', query.lower())
        return [p for p in palabras if p not in stopwords and len(p) > 2]

    def agregar_sinonimos(self, termino: str, sinonimos: List[str]):
        """Agregar nuevos sinónimos al diccionario en runtime."""
        if termino not in self.sinonimos:
            self.sinonimos[termino] = []
        self.sinonimos[termino].extend(sinonimos)
        self.sinonimos[termino] = list(set(self.sinonimos[termino]))  # Eliminar duplicados
        self._compilar_terminos()


# Función de conveniencia
_expanders: Dict[str, LexicalExpander] = {}

def get_lexical_expander() -> LexicalExpander:
    """Obtener instancia singleton del expander léxico."""
    global _expanders
    if "default" not in _expanders:
        _expanders["default"] = LexicalExpander()
    return _expanders["default"]


if __name__ == "__main__":
    # Tests básicos
    print("=" * 60)
    print("TEST DEL LEXICAL EXPANDER")
    print("=" * 60)

    expander = LexicalExpander()

    test_queries = [
        "paro juvenil",
        "pib per cápita",
        "turismo Barcelona",
        "vulnerabilidad económica",
        "población mayor 65",
    ]

    for query in test_queries:
        print(f"\n{'─' * 60}")
        print(f"📝 Query: '{query}'")
        print("─" * 60)

        import time
        t0 = time.time()
        result = expander.expand(query)
        t1 = time.time()

        print(f"⏱️  Tiempo: {(t1-t0)*1000:.2f}ms")
        print(f"🔍 Expandida: {result['query_expandida'][:100]}...")
        print(f"📊 Términos añadidos ({len(result['terminos_añadidos'])}): {result['terminos_añadidos']}")

    print("\n" + "=" * 60)
    print("TESTS COMPLETADOS")
    print("=" * 60)
