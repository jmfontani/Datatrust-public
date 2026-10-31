"""
Motor de búsqueda semántica con Sentence Transformers.

Usa embeddings pre-calculados para comparación por cosine similarity.
No requiere PostgreSQL/pgvector en el POC - todo en memoria con NumPy.
"""
import json
import os
import time
from typing import List, Dict, Any
import numpy as np

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_datasets.json")
EMBEDDINGS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "embeddings.npy")

# Modelo configurado en 99_Compartido/herramientas/config_proyecto.yaml
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Revision fijada: sin ella se descarga la rama "main", que es un puntero movil
# y puede devolver pesos distintos bajo el mismo nombre (ver docs/PINNING-DEPENDENCIAS.md).
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
EMBEDDING_DIM = 384  # Dimensión del modelo MiniLM-L12-v2

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

def _load_datasets() -> List[Dict[str, Any]]:
    """Carga los datasets de muestra desde JSON."""
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_searchable_text(ds: Dict[str, Any]) -> str:
    """Construye texto consolidado para embeddings: título + descripción + temas + keywords."""
    parts = [
        ds.get("title_es", ""),
        ds.get("description_es", ""),
    ]
    # Temas como texto
    themes_labels = []
    for theme_uri in ds.get("themes", []):
        if "/" in theme_uri:
            themes_labels.append(theme_uri.split("/")[-1].replace("-", " "))
        else:
            themes_labels.append(theme_uri)
    if themes_labels:
        parts.append("Temas: " + ", ".join(themes_labels))
    # Keywords
    keywords = ds.get("keywords", [])
    if keywords:
        parts.append("Palabras clave: " + ", ".join(keywords))
    return " \n ".join(parts)


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

class SemanticSearchEngine:
    """
    Motor de búsqueda semántica usando Sentence Transformers + Cosine Similarity.
    
    Los embeddings se calculan una vez y se guardan en disco para reutilizar.
    """

    def __init__(self):
        self.datasets: List[Dict[str, Any]] = _load_datasets()
        self.texts: List[str] = [_build_searchable_text(ds) for ds in self.datasets]
        
        # Lazy loading del modelo
        self._model = None
        self._embeddings: np.ndarray | None = None
        
        # Cargar embeddings si existen, sino calcular
        self._load_or_generate_embeddings()

    @property
    def model(self):
        """Lazy load del modelo sentence-transformers."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"[POC] Cargando modelo {MODEL_NAME}...")
                self._model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)
                print(f"[POC] Modelo cargado correctamente.")
            except ImportError:
                raise ImportError(
                    "sentence-transformers no está instalado. "
                    "Ejecuta: pip install sentence-transformers"
                )
        return self._model

    def _load_or_generate_embeddings(self):
        """Carga embeddings precalculados o los genera si no existen."""
        if os.path.exists(EMBEDDINGS_PATH):
            print(f"[POC] Cargando embeddings desde {EMBEDDINGS_PATH}...")
            self._embeddings = np.load(EMBEDDINGS_PATH)
            print(f"[POC] Embeddings cargados: {self._embeddings.shape}")
        else:
            print(f"[POC] Generando embeddings para {len(self.texts)} datasets...")
            self._embeddings = self._generate_embeddings()
            # Guardar para futuras ejecuciones
            np.save(EMBEDDINGS_PATH, self._embeddings)
            print(f"[POC] Embeddings guardados en {EMBEDDINGS_PATH}")

    def _generate_embeddings(self) -> np.ndarray:
        """Genera embeddings para todos los datasets usando sentence-transformers."""
        # Usar batch encoding para eficiencia
        embeddings = self.model.encode(
            self.texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2-normalizar para cosine similarity
        )
        return embeddings

    def _encode_query(self, query: str) -> np.ndarray:
        """Genera embedding para la query del usuario."""
        embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embedding[0]

    def _cosine_similarity(self, query_emb: np.ndarray, doc_emb: np.ndarray) -> float:
        """Calcula cosine similarity entre dos vectores L2-normalizados."""
        # Como están normalizados, dot product = cosine similarity
        return float(np.dot(query_emb, doc_emb))

    # ------------------------------------------------------------------
    # API Pública
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        theme_filter: str = "",
        spatial_filter: str = "",
        format_filter: str = "",
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Busca datasets relevantes usando búsqueda semántica con embeddings.

        Args:
            query: Texto libre de búsqueda en lenguaje natural.
            theme_filter: URI o label de tema para filtrar.
            spatial_filter: Nombre del territorio.
            format_filter: Tipo MIME de formato.
            top_k: Máximo número de resultados.

        Returns:
            Lista de dicts con los datos del dataset + score semántico (0-100%).
        """
        start = time.perf_counter()

        # 1. Filtrado estructural previo
        candidates = self._apply_filters(theme_filter, spatial_filter, format_filter)

        # 2. Si no hay query, devolver todos ordenados por fecha
        if not query or not query.strip():
            results = [
                {**self.datasets[idx], "score": 100.0} for idx in candidates
            ]
            results.sort(key=lambda x: x.get("modified", ""), reverse=True)
            return results[:top_k]

        # 3. Generar embedding de la query
        query_emb = self._encode_query(query)

        # 4. Calcular cosine similarity con todos los candidatos
        candidate_indices = np.array(candidates, dtype=int)
        candidate_embeddings = self._embeddings[candidate_indices]
        
        # Dot product = cosine similarity (vectores normalizados)
        similarities = np.dot(candidate_embeddings, query_emb)
        
        # Convertir a porcentaje (0-100)
        scores_pct = similarities * 100

        # 5. Ordenar por score descendente
        sorted_idx = np.argsort(scores_pct)[::-1]
        
        results = []
        for rank in range(len(sorted_idx)):
            score = float(scores_pct[sorted_idx[rank]])
            # Filtrar scores muy bajos (ruido)
            if score < 5.0:
                break
                
            ds_idx = int(candidate_indices[sorted_idx[rank]])
            dataset = {
                **self.datasets[ds_idx],
                "score": round(score, 1),
                "_spatial_inferred": self._infer_spatial(self.datasets[ds_idx]),
            }
            results.append(dataset)
            
            if len(results) >= top_k:
                break

        elapsed = time.perf_counter() - start
        for r in results:
            r["_response_time_ms"] = round(elapsed * 1000, 2)

        return results

    def search_with_explanation(
        self,
        query: str,
        theme_filter: str = "",
        spatial_filter: str = "",
        format_filter: str = "",
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """
        Versión extendida que incluye explicación de por qué es relevante.
        """
        results = self.search(
            query=query,
            theme_filter=theme_filter,
            spatial_filter=spatial_filter,
            format_filter=format_filter,
            top_k=top_k,
        )
        
        # Generar explicaciones semánticas
        explanations = []
        for r in results:
            exp = self._explain_relevance(query, r)
            explanations.append(exp)
            r["explanation"] = exp
        
        return {
            "query": query,
            "total_results": len(results),
            "results": results,
            "explanations": explanations,
        }

    def _explain_relevance(self, query: str, result: Dict[str, Any]) -> str:
        """Genera explicación de por qué este dataset es relevante para la query."""
        title = result.get("title_es", "")
        themes = result.get("themes", [])
        keywords = result.get("keywords", [])
        
        # Extraer tema principal
        theme_label = ""
        if themes:
            theme_label = themes[0].split("/")[-1].replace("-", " ") if "/" in themes[0] else themes[0]
        
        parts = []
        
        # Si el score es muy alto, probablemente match directo en título
        if result.get("score", 0) > 80:
            parts.append(f"El título del dataset coincide fuertemente con tu búsqueda.")
        elif result.get("score", 0) > 60:
            parts.append(f"El contenido del dataset está relacionado semánticamente con tu consulta.")
        else:
            parts.append(f"Temáticamente cercano a tu búsqueda.")
        
        if theme_label:
            parts.append(f"Categoría: {theme_label}.")
        if keywords:
            parts.append(f"Incluye información sobre: {', '.join(keywords[:3])}.")
        
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Filtros
    # ------------------------------------------------------------------

    def _apply_filters(
        self, theme_filter: str, spatial_filter: str, format_filter: str
    ) -> List[int]:
        """Devuelve índices de datasets que cumplen los filtros."""
        indices = []
        for idx, ds in enumerate(self.datasets):
            # Filtro por tema
            if theme_filter and theme_filter != "Todos":
                themes = ds.get("themes", [])
                theme_labels = [t.split("/")[-1] if "/" in t else t for t in themes]
                if not any(theme_filter.lower() in t.lower() for t in themes + theme_labels):
                    continue

            # Filtro por territorio (usa spatial inferido)
            if spatial_filter and spatial_filter != "Todos":
                spatial = self._infer_spatial(ds)
                if spatial_filter.lower() not in spatial.lower():
                    continue

            # Filtro por formato
            if format_filter and format_filter != "Todos":
                formats = ds.get("formats", [])
                if not any(format_filter.lower() in fmt.lower() for fmt in formats):
                    continue

            indices.append(idx)
        return indices

    # ------------------------------------------------------------------
    # Agregaciones para UI
    # ------------------------------------------------------------------

    def get_themes(self) -> List[Dict[str, str]]:
        """Devuelve lista de temas únicos con {value, label}."""
        seen = set()
        themes = []
        for ds in self.datasets:
            for t in ds.get("themes", []):
                label = t.split("/")[-1] if "/" in t else t
                if label not in seen:
                    seen.add(label)
                    themes.append({"value": label, "label": label.replace("-", " ").title()})
        return sorted(themes, key=lambda x: x["label"])

    def _infer_spatial(self, ds: Dict[str, Any]) -> str:
        """
        Infiere el territorio cuando spatial_name viene vacío.
        Busca menciones geográficas en publisher, título, descripción y etiquetas.
        """
        spatial = ds.get("spatial_name", "").strip()
        if spatial and spatial.lower() != "desconocido":
            return spatial

        # Inferir desde texto combinado
        text = " ".join([
            ds.get("publisher_name", ""),
            ds.get("title_es", ""),
            ds.get("description_es", ""),
            " ".join(ds.get("tags", [])),
        ]).lower()

        # Reglas de inferencia (orden de prioridad)
        patterns = [
            # Canarias e islas
            (["tenerife", "gran canaria", "lanzarote", "la palma", "fuerteventura",
              "la gomera", "el hierro", "istac", "gobierno de canarias"], "Canarias"),
            (["canarias", "canario", "canaria"], "Canarias"),
            # Aragón
            (["zaragoza", "huesca", "teruel", "gobierno de aragón"], "Aragón"),
            (["aragón", "aragon"], "Aragón"),
            # Cataluña
            (["barcelona", "girona", "lleida", "tarragona", "generalitat"], "Cataluña"),
            (["cataluña", "catalunya", "catalonia"], "Cataluña"),
            # Madrid
            (["comunidad de madrid", "ayuntamiento de madrid"], "Madrid"),
            (["madrid"], "Madrid"),
            # Andalucía
            (["sevilla", "málaga", "granada", "córdoba", "almería", "jaén", "huelva", "cádiz"], "Andalucía"),
            (["andalucía", "andalucia"], "Andalucía"),
            # País Vasco
            (["bilbao", "donostia", "vitoria", "euskadi", "gobierno vasco"], "País Vasco"),
            (["país vasco", "euskal"], "País Vasco"),
            # Galicia
            (["coruña", "pontevedra", "ourense", "lugo", "xunta"], "Galicia"),
            (["galicia", "galego"], "Galicia"),
            # Valencia
            (["valenciana", "valencia", "alicante", "castellón"], "C. Valenciana"),
            # Baleares
            (["mallorca", "menorca", "ibiza", "eivissa", "govern balear"], "Baleares"),
            (["baleares", "illes balears"], "Baleares"),
            # Otros
            (["navarra", "nafarroa"], "Navarra"),
            (["murcia"], "Murcia"),
            (["extremadura"], "Extremadura"),
            (["castilla y león", "junta de castilla"], "Castilla y León"),
            (["castilla-la mancha"], "Castilla-La Mancha"),
            (["asturias", "principado de asturias"], "Asturias"),
            (["cantabria"], "Cantabria"),
            (["la rioja"], "La Rioja"),
            (["ceuta"], "Ceuta"),
            (["melilla"], "Melilla"),
            # España genérico (catch-all)
            (["españa", "espana", "gobierno de españa", "administración general"], "España"),
        ]

        for keywords, label in patterns:
            if any(kw in text for kw in keywords):
                return label

        return "España"  # Default fallback

    def get_spatials(self) -> List[str]:
        """Devuelve territorios únicos, infiriendo los vacíos desde el texto."""
        seen = set()
        for ds in self.datasets:
            sp = self._infer_spatial(ds)
            if sp:
                seen.add(sp)
        return sorted(seen)

    def get_formats(self) -> List[str]:
        """Devuelve formatos únicos (simplificados)."""
        seen = set()
        for ds in self.datasets:
            for fmt in ds.get("formats", []):
                simple = _simplify_format(fmt)
                if simple:
                    seen.add(simple)
        return sorted(seen)

    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del motor para debugging."""
        return {
            "total_datasets": len(self.datasets),
            "embedding_dim": EMBEDDING_DIM,
            "model_name": MODEL_NAME,
            "embeddings_shape": self._embeddings.shape if self._embeddings is not None else None,
            "embeddings_path": EMBEDDINGS_PATH,
        }


# ---------------------------------------------------------------------------
# Helpers de formato
# ---------------------------------------------------------------------------

_FORMAT_MAP = {
    "application/json": "JSON",
    "text/csv": "CSV",
    "text/tab-separated-values": "TSV",
    "application/xml": "XML",
    "application/rdf+xml": "RDF/XML",
    "text/turtle": "Turtle",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
    "application/vnd.ms-excel": "Excel",
    "application/pdf": "PDF",
    "text/html": "HTML",
    "application/zip": "ZIP",
    "text/plain": "TXT",
    "application/geo+json": "GeoJSON",
    "application/sparql-results+json": "SPARQL/JSON",
    "text/pc-axis": "PC-Axis",
}


def _simplify_format(mime: str) -> str:
    """Convierte MIME a etiqueta legible."""
    mime = mime.lower().strip()
    return _FORMAT_MAP.get(mime, mime.split("/")[-1].upper() if "/" in mime else mime)


# Singleton
_search_engine: SemanticSearchEngine | None = None


def get_engine() -> SemanticSearchEngine:
    """Devuelve el motor de búsqueda semántica (singleton)."""
    global _search_engine
    if _search_engine is None:
        _search_engine = SemanticSearchEngine()
    return _search_engine


# ---------------------------------------------------------------------------
# CLI para generar embeddings offline
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Generando embeddings para el POC...")
    engine = get_engine()
    stats = engine.get_stats()
    print(f"✓ Embeddings generados: {stats['embeddings_shape']}")
    print(f"✓ Total datasets: {stats['total_datasets']}")
    print(f"✓ Modelo: {stats['model_name']}")
    
    # Test rápido
    print("\nTest de búsqueda:")
    results = engine.search("accidentes de trabajo", top_k=3)
    for r in results:
        print(f"  - {r['title_es'][:60]}... (score: {r['score']}%)")
