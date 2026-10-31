#!/usr/bin/env python3
"""
Motor de búsqueda híbrida (semántica + léxica + filtros facetados).
Versión mejorada para Sprint 3.

Uso:
  python search_engine.py "datos de tráfico en Madrid" --territorio "Comunidad de Madrid" --top-k 10
  python search_engine.py "educación primaria" --tema "educacion" --formato "CSV" --top-k 20
"""
import argparse
import json
import logging
import pickle
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Rutas relativas al proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
INDICES_DIR = PROJECT_ROOT / "04_Sprint2_Embeddings" / "datos" / "indices"
DATASETS_PATH = PROJECT_ROOT / "03_Sprint1_Ingesta" / "datos" / "processed" / "datasets_clean.jsonl"
EMBEDDINGS_PATH = PROJECT_ROOT / "04_Sprint2_Embeddings" / "datos" / "processed" / "embeddings.npy"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Revision fijada: sin ella se descarga la rama "main", que es un puntero movil
# y puede devolver pesos distintos bajo el mismo nombre (ver docs/PINNING-DEPENDENCIAS.md).
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"


class HybridSearchEngine:
    """Motor de búsqueda híbrida con ranking combinado."""
    
    def __init__(self):
        logger.info("Inicializando motor de búsqueda híbrida...")
        start = time.perf_counter()
        
        # Cargar modelo de embeddings
        self.model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)
        
        # Cargar embeddings
        self.embeddings = np.load(EMBEDDINGS_PATH)
        logger.info(f"Embeddings cargados: {self.embeddings.shape}")
        
        # Cargar índices invertidos
        self._load_indices()
        
        # Cargar BM25
        self._load_bm25()
        
        # Cargar datasets en memoria
        self.datasets = self._load_datasets()
        
        elapsed = time.perf_counter() - start
        logger.info(f"Motor listo en {elapsed:.2f}s")
    
    def _load_indices(self):
        """Carga índices invertidos desde JSON."""
        with open(INDICES_DIR / "id_position_map.json", "r") as f:
            self.id_to_pos = json.load(f)
        self.pos_to_id = {v: k for k, v in self.id_to_pos.items()}
        
        with open(INDICES_DIR / "index_tema.json", "r") as f:
            self.index_tema = json.load(f)
        
        with open(INDICES_DIR / "index_territorio.json", "r") as f:
            self.index_territorio = json.load(f)
        
        with open(INDICES_DIR / "index_formato.json", "r") as f:
            self.index_formato = json.load(f)
        
        with open(INDICES_DIR / "index_publisher.json", "r") as f:
            self.index_publisher = json.load(f)
    
    def _load_bm25(self):
        """Carga índice BM25."""
        with open(INDICES_DIR / "bm25_index.pkl", "rb") as f:
            bm25_data = pickle.load(f)
            self.bm25 = bm25_data["bm25"]
            self.bm25_id_map = bm25_data["id_map"]
    
    def _load_datasets(self) -> Dict:
        """Carga datasets en memoria para mostrar resultados."""
        datasets = {}
        with open(DATASETS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                ds = json.loads(line)
                datasets[ds["identifier"]] = ds
        logger.info(f"Datasets cargados: {len(datasets)}")
        return datasets
    
    def search_semantic(self, query: str, top_k: int = 100) -> List[Dict]:
        """Búsqueda semántica por similitud coseno."""
        query_embedding = self.model.encode([query], normalize_embeddings=True)[0]
        similarities = np.dot(self.embeddings, query_embedding)
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        return [
            {
                "id": self.pos_to_id[int(idx)],
                "score_semantic": float(similarities[idx]),
                "position": int(idx),
            }
            for idx in top_indices
        ]
    
    def search_lexical(self, query: str, top_k: int = 100) -> List[Dict]:
        """Búsqueda léxica con BM25."""
        import re
        tokenized_query = re.findall(r"\b\w+\b", query.lower())
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        return [
            {
                "id": self.bm25_id_map[idx],
                "score_lexical": float(scores[idx]),
                "position": idx,
            }
            for idx in top_indices
            if scores[idx] > 0
        ]
    
    def filter_by_facet(self, candidates: List[Dict], **filters) -> List[Dict]:
        """Filtrar candidatos por facetas."""
        filtered = candidates
        
        if filters.get("territorio"):
            terr_ids = set(self.index_territorio.get(filters["territorio"], []))
            filtered = [c for c in filtered if c["id"] in terr_ids]
        
        if filters.get("tema"):
            tema_ids = set(self.index_tema.get(filters["tema"], []))
            filtered = [c for c in filtered if c["id"] in tema_ids]
        
        if filters.get("formato"):
            fmt_ids = set(self.index_formato.get(filters["formato"], []))
            filtered = [c for c in filtered if c["id"] in fmt_ids]
        
        if filters.get("publisher"):
            pub_ids = set(self.index_publisher.get(filters["publisher"], []))
            filtered = [c for c in filtered if c["id"] in pub_ids]
        
        return filtered
    
    def _normalize_scores_with_threshold(self, scores: Dict[str, float], min_threshold: float = 0.0) -> Dict[str, float]:
        """Normaliza scores con min-max y aplica umbral mínimo."""
        if not scores:
            return scores
        
        max_score = max(scores.values())
        if max_score == 0:
            return {k: 0 for k in scores}
        
        # Normalizar
        normalized = {k: v / max_score for k, v in scores.items()}
        
        # Aplicar umbral mínimo
        if min_threshold > 0:
            normalized = {k: v for k, v in normalized.items() if v >= min_threshold}
        
        return normalized
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.7,
        lexical_weight: float = 0.3,
        explain: bool = True,
        min_score_threshold: float = 0.30,
        require_lexical_match: bool = True,
        **filters,
    ) -> Dict:
        """
        Búsqueda híbrida con re-ranking y filtrado de calidad.
        
        Args:
            query: Consulta de búsqueda
            top_k: Número de resultados a retornar
            semantic_weight: Peso para score semántico (0-1)
            lexical_weight: Peso para score léxico (0-1)
            explain: Incluir explicaciones de relevancia
            min_score_threshold: Score mínimo para incluir un resultado (0-1)
            require_lexical_match: Si True, requiere al menos una coincidencia léxica real
            **filters: Filtros facetados (territorio, tema, formato, publisher)
        
        Returns:
            Dict con resultados y metadatos de la búsqueda
        """
        start = time.perf_counter()
        
        # Extraer términos de la consulta para verificación léxica
        import re
        query_lower = query.lower()
        query_terms = set(re.findall(r'\b\w+\b', query_lower))
        
        # Filtrar términos muy cortos (menos de 4 caracteres son ruido)
        # EXCEPCIÓN: permitir términos de 3 caracteres si son términos clave específicos
        short_allowed = {"paro", "agua", "gas", "sun", "uvi", "may", "min"}
        significant_terms = []
        for t in query_terms:
            if len(t) >= 4 or t in short_allowed:
                significant_terms.append(t)
        
        # Detectar términos compuestos y negativos de la consulta original
        negative_terms = []
        if "no " in query_lower or "sin " in query_lower:
            # Extraer términos después de "no" o "sin"
            neg_patterns = re.findall(r'(?:no|sin)\s+(\w+)', query_lower)
            negative_terms = [p for p in neg_patterns if len(p) >= 3]
        
        # Detectar contexto educativo (escolar vs universidad)
        education_context = None
        if "escolar" in query_lower or "colegio" in query_lower or "primaria" in query_lower or "secundaria" in query_lower or "bachillerato" in query_lower:
            education_context = "escolar"
        elif "universidad" in query_lower or "universitario" in query_lower or "master" in query_lower or "grado" in query_lower:
            education_context = "universidad"
        
        # Búsquedas individuales
        semantic_results = self.search_semantic(query, top_k=top_k * 3)
        lexical_results = self.search_lexical(query, top_k=top_k * 3)
        
        # Scores normalizados
        semantic_scores = {r["id"]: r["score_semantic"] for r in semantic_results}
        lexical_scores = {r["id"]: r["score_lexical"] for r in lexical_results}
        
        # Normalizar con umbral mínimo más estricto
        sem_norm = self._normalize_scores_with_threshold(semantic_scores, min_threshold=0.5)
        lex_norm = self._normalize_scores_with_threshold(lexical_scores, min_threshold=0.2)
        
        # Combinar scores con re-ranking inteligente
        all_ids = set(semantic_scores.keys()) | set(lexical_scores.keys())
        combined = []
        
        for ds_id in all_ids:
            s_score = sem_norm.get(ds_id, 0)
            l_score = lex_norm.get(ds_id, 0)
            
            # Score base combinado
            combined_score = semantic_weight * s_score + lexical_weight * l_score
            
            # VERIFICACIÓN DE CONTENIDO REAL (obligatoria)
            ds = self.datasets.get(ds_id, {})
            title = ds.get("title_es", "").lower()
            desc = ds.get("description_es", "").lower()
            content = title + " " + desc
            
            # Verificar coincidencias léxicas REALES (incluyendo variantes y términos relacionados)
            has_real_match = False
            matching_terms = []
            
            # Crear lista de términos a buscar (incluyendo sinónimos y variantes)
            search_terms = []
            for term in significant_terms:
                search_terms.append(term)
                # Añadir variantes comunes
                if term == "despoblacion":
                    search_terms.extend(["poblacion", "demografia", "habitantes", "municipios", "riesgo", "antidespoblamiento", "despoblado"])
                elif term == "paro":
                    search_terms.extend(["desempleo", "empleo", "trabajo", "garantia", "inscripcion", "mercado laboral", "ocupacion", "abandono", "educativo", "prematuro"])
                elif term == "juvenil":
                    search_terms.extend(["joven", "jovenes", "juvenil", "adolescente", "garantia juvenil", "18 a 24", "16 a 29", "jóvenes", "jóven"])
                elif term == "natalidad":
                    search_terms.extend(["nacimientos", "fecundidad", "natal", "natalidad", "fertilidad", "maternidad"])
                elif term == "energia":
                    search_terms.extend(["energetico", "electrica", "electricidad", "potencia", "generacion"])
                elif term == "solar":
                    search_terms.extend(["fotovoltaica", "renovable", "placa solar", "radiacion solar", "panel"])
                elif term == "rendimiento":
                    search_terms.extend(["resultados", "evaluacion", "exito", "aprobado", "suspense", "nota", "calificacion"])
                elif term == "academico":
                    search_terms.extend(["escolar", "educativo", "estudios", "ensenanza", "formacion", "universidad"])
                elif term == "potable":
                    search_terms.extend(["abastecimiento", "agua", "hídrico", "suministro", "consumo"])
                elif term == "gas":
                    search_terms.extend(["gas natural", "combustible", "emision"])
            
            # Normalizar texto para búsqueda (eliminar acentos)
            def normalize_text(text):
                import unicodedata
                return ''.join(c for c in unicodedata.normalize('NFD', text)
                              if unicodedata.category(c) != 'Mn').lower()
            
            content_normalized = normalize_text(content)
            
            # Buscar cualquiera de los términos
            for term in search_terms:
                if len(term) >= 3:  # Reducido a 3 para "paro", "gas", etc.
                    pattern = r'\b' + re.escape(term) + r'\b'
                    if re.search(pattern, content) or re.search(pattern, content_normalized):
                        has_real_match = True
                        matching_terms.append(term)
                        break  # Con una coincidencia suficiente
            
            # PENALIZACIÓN POR TÉRMINOS NEGATIVOS (términos que NO deberían aparecer)
            has_negative_match = False
            for neg_term in negative_terms:
                if neg_term in content or neg_term in content_normalized:
                    has_negative_match = True
                    combined_score *= 0.1  # Penalizar fuertemente
                    break
            
            # PENALIZACIÓN POR CONTEXTO EDUCATIVO INCORRECTO
            if education_context == "escolar":
                # Si busca escolar pero aparece universidad, penalizar fuertemente
                if "universidad" in content or "universitario" in content or "master" in content or "máster" in content:
                    # Solo penalizar si NO contiene términos escolares
                    escolar_terms = ["escolar", "primaria", "secundaria", "colegio", "bachillerato", "eso", "bachiller"]
                    if not any(t in content or t in content_normalized for t in escolar_terms):
                        combined_score *= 0.1  # Penalizar MUY fuertemente (reducir a 10%)
            elif education_context == "universidad":
                # Si busca universidad pero aparece escolar, penalizar
                escolar_terms = ["escolar", "primaria", "secundaria", "colegio", "bachillerato", "eso"]
                if any(t in content or t in content_normalized for t in escolar_terms):
                    univ_terms = ["universidad", "universitario", "master", "máster", "grado"]
                    if not any(t in content or t in content_normalized for t in univ_terms):
                        combined_score *= 0.1
            
            # Si NO hay coincidencia léxica real, aplicar penalización
            if require_lexical_match:
                if not has_real_match:
                    # No hay coincidencia real
                    # Si el score semántico es alto, puede ser relevante
                    if s_score > 0.5:
                        combined_score *= 0.3  # Reducir pero no eliminar
                    else:
                        combined_score *= 0.01  # Reducir a 1%
                else:
                    combined_score *= 1.2  # Boost por coincidencia
            
            # RE-RANKING: Penalizar si solo un sistema lo encontró
            if s_score > 0 and l_score > 0:
                combined_score *= 1.3  # Boost confirmación cruzada
            elif l_score > 0 and s_score == 0:
                combined_score *= 0.6  # Penalizar solo BM25
            elif s_score > 0 and l_score == 0:
                combined_score *= 0.7  # Penalizar solo semántico
            
            # Filtrar por umbral mínimo
            if combined_score >= min_score_threshold:
                item = {
                    "id": ds_id,
                    "score": combined_score,
                    "score_semantic": s_score,
                    "score_lexical": l_score,
                    "matching_terms": matching_terms,
                }
                combined.append(item)
        
        # Ordenar por score combinado
        combined.sort(key=lambda x: x["score"], reverse=True)
        
        # Aplicar filtros facetados
        filtered = self.filter_by_facet(combined, **filters)
        
        # Construir resultados finales
        results = []
        for item in filtered[:top_k]:
            ds = self.datasets.get(item["id"], {})
            result = {
                "id": item["id"],
                "score": round(item["score"], 4),
                "title": ds.get("title_es", ds.get("title", "Sin título")),
                "description": self._truncate_text(ds.get("description_es", ""), 200),
                "territorio": ds.get("spatial_name", []),
                "tema": ds.get("theme_labels", []),
                "formato": ds.get("format_labels", []),
                "publisher": ds.get("publisher_name", "Desconocido"),
                "url": ds.get("source_url", ""),
            }
            
            if explain:
                result["explanation"] = self._explain_relevance(
                    item, ds, query
                )
            
            results.append(result)
        
        elapsed = time.perf_counter() - start
        logger.info(f"Búsqueda completada en {elapsed:.3f}s | {len(results)} resultados")
        
        return {
            "query": query,
            "filters": filters,
            "total_results": len(filtered),
            "returned_results": len(results),
            "semantic_weight": semantic_weight,
            "lexical_weight": lexical_weight,
            "search_time_ms": round(elapsed * 1000, 2),
            "results": results,
        }
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Trunca texto con elipsis."""
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
    
    def _explain_relevance(self, item: Dict, dataset: Dict, query: str) -> str:
        """Genera explicación de relevancia para un resultado."""
        parts = []
        
        if item["score_semantic"] > 0.5:
            parts.append("alta similitud semántica con la consulta")
        elif item["score_semantic"] > 0.2:
            parts.append("similitud semántica moderada")
        
        if item["score_lexical"] > 0.5:
            parts.append("términos de la consulta aparecen en título/descripción")
        elif item["score_lexical"] > 0.2:
            parts.append("algunos términos coinciden textualmente")
        
        # Detectar territorio coincidente
        query_lower = query.lower()
        for terr in dataset.get("spatial_name", []):
            if terr.lower() in query_lower:
                parts.append(f"territorio coincidente: {terr}")
                break
        
        # Detectar tema coincidente
        for tema in dataset.get("theme_labels", []):
            if tema.lower() in query_lower:
                parts.append(f"tema coincidente: {tema}")
                break
        
        if not parts:
            return "Relevancia basada en similitud general"
        
        return "; ".join(parts).capitalize() + "."


def main():
    parser = argparse.ArgumentParser(description="Motor de búsqueda híbrida de datasets")
    parser.add_argument("query", help="Consulta de búsqueda")
    parser.add_argument("--top-k", type=int, default=10, help="Número de resultados")
    parser.add_argument("--territorio", help="Filtrar por territorio")
    parser.add_argument("--tema", help="Filtrar por tema")
    parser.add_argument("--formato", help="Filtrar por formato")
    parser.add_argument("--publisher", help="Filtrar por publisher")
    parser.add_argument(
        "--semantic-weight", type=float, default=0.7, help="Peso semántico (0-1)"
    )
    parser.add_argument(
        "--lexical-weight", type=float, default=0.3, help="Peso léxico (0-1)"
    )
    parser.add_argument(
        "--no-explain", action="store_true", help="Omitir explicaciones"
    )
    
    args = parser.parse_args()
    
    # Validar pesos
    if not (0 <= args.semantic_weight <= 1 and 0 <= args.lexical_weight <= 1):
        print("Error: Los pesos deben estar entre 0 y 1")
        return
    
    # Inicializar motor
    engine = HybridSearchEngine()
    
    # Ejecutar búsqueda
    result = engine.search(
        query=args.query,
        top_k=args.top_k,
        semantic_weight=args.semantic_weight,
        lexical_weight=args.lexical_weight,
        explain=not args.no_explain,
        territorio=args.territorio,
        tema=args.tema,
        formato=args.formato,
        publisher=args.publisher,
    )
    
    # Mostrar resultados
    print(f"\n{'='*80}")
    print(f"🔍 Query: '{result['query']}'")
    if result['filters']:
        for k, v in result['filters'].items():
            if v:
                print(f"   Filtro {k}: {v}")
    print(f"   Pesos: semántico={result['semantic_weight']}, léxico={result['lexical_weight']}")
    print(f"   Tiempo: {result['search_time_ms']}ms")
    print(f"{'='*80}\n")
    
    for i, r in enumerate(result["results"], 1):
        print(f"{i}. [{r['score']:.3f}] {r['title']}")
        print(f"   🏛️  {r['publisher']} | 🌍 {', '.join(r['territorio'][:3])}")
        print(f"   🏷️  {', '.join(r['tema'][:3])} | 📄 {', '.join(r['formato'][:3])}")
        print(f"   {r['description'][:150]}...")
        if "explanation" in r:
            print(f"   💡 {r['explanation']}")
        print(f"   🔗 {r['url']}")
        print()
    
    print(f"{'='*80}")
    print(f"Total: {result['returned_results']}/{result['total_results']} resultados")


if __name__ == "__main__":
    main()
