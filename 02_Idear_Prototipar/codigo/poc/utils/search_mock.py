"""
Búsqueda TF-IDF sobre datasets de muestra.
Módulo de búsqueda semántica simulada (mock) para el POC.
"""
import json
import os
from typing import List, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import time

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_datasets.json")

# Spanish stop words (basic) - reemplazar por lista completa en producción
_STOP_WORDS_ES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "al", "y", "o", "que", "en", "con", "por",
    "para", "porque", "como", "pero", "más", "menos", "entre",
    "sobre", "también", "ya", "aún", "este", "esta", "estos", "estas",
    "ese", "esa", "esos", "esas", "aquél", "aquella", "aquellos", "aquellas",
    "mi", "tu", "su", "nuestro", "vuestro", "sus", "mis", "tus",
    "me", "te", "se", "nos", "os", "lo", "le", "les",
    "hay", "son", "es", "fue", "era", "ser", "estar",
    "según", "hasta", "desde", "ante", "tras", "sin", "bajo",
    "a", "ante", "bajo", "cabe", "con", "contra", "de", "desde",
    "durante", "en", "entre", "hacia", "hasta", "mediante", "para",
    "por", "según", "sin", "so", "sobre", "tras", "versus", "vía"
}

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_datasets() -> List[Dict[str, Any]]:
    """Carga los datasets de muestra desde JSON."""
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_searchable_text(ds: Dict[str, Any]) -> str:
    """Construye texto consolidado para TF-IDF: título + descripción + temas + keywords."""
    parts = [
        ds.get("title_es", ""),
        ds.get("description_es", ""),
        " ".join(ds.get("keywords", [])),
    ]
    # Extraer etiquetas legibles de las URIs de temas
    themes_labels = []
    for theme_uri in ds.get("themes", []):
        # Extraer la última parte de la URI como etiqueta legible
        if "/" in theme_uri:
            themes_labels.append(theme_uri.split("/")[-1])
        else:
            themes_labels.append(theme_uri)
    parts.append(" ".join(themes_labels))
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Search engine
# ---------------------------------------------------------------------------

class TfidfSearchEngine:
    """
    Motor de búsqueda basado en TF-IDF (scikit-learn).
    Carga los datasets al inicializar y mantiene el vectorizador en memoria.
    """

    def __init__(self):
        self.datasets: List[Dict[str, Any]] = _load_datasets()
        self.texts: List[str] = [_build_searchable_text(ds) for ds in self.datasets]
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            stop_words=list(_STOP_WORDS_ES),
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.texts)

    # ------------------------------------------------------------------
    # Public API
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
        Busca datasets relevantes para la consulta y aplica filtros.

        Args:
            query: Texto libre de búsqueda.
            theme_filter: URI o label de tema para filtrar.
            spatial_filter: Nombre del territorio.
            format_filter: Tipo MIME de formato.
            top_k: Máximo número de resultados.

        Returns:
            Lista de dicts con los datos del dataset + score.
        """
        start = time.perf_counter()

        # 1. Filtrado estructural previo
        candidates = self._apply_filters(theme_filter, spatial_filter, format_filter)

        # 2. Si no hay query, devolver todos (ordenados aleatoriamente o por fecha)
        if not query or not query.strip():
            results = [
                {**self.datasets[idx], "score": 1.0} for idx in candidates
            ]
            # Ordenar por fecha de modificación descendente como fallback
            results.sort(
                key=lambda x: x.get("modified", ""), reverse=True
            )
            return results[:top_k]

        # 3. TF-IDF similarity sobre candidatos
        query_vec = self.vectorizer.transform([query])
        candidate_indices = np.array(candidates, dtype=int)
        candidate_matrix = self.tfidf_matrix[candidate_indices]

        scores = np.asarray(candidate_matrix.dot(query_vec.T).todense()).flatten()

        # Ordenar por score descendente
        sorted_idx = np.argsort(scores)[::-1]
        sorted_scores = scores[sorted_idx]

        # Solo devolver resultados con score > 0
        results = []
        for rank, idx_in_candidates in enumerate(sorted_idx):
            score = float(sorted_scores[rank])
            if score <= 0:
                break
            ds_idx = int(candidate_indices[idx_in_candidates])
            dataset = {**self.datasets[ds_idx], "score": round(score, 4)}
            results.append(dataset)
            if len(results) >= top_k:
                break

        elapsed = time.perf_counter() - start
        # Inyectar tiempo de respuesta para UI
        for r in results:
            r["_response_time_ms"] = round(elapsed * 1000, 2)

        return results

    # ------------------------------------------------------------------
    # Filter helpers
    # ------------------------------------------------------------------

    def _apply_filters(
        self, theme_filter: str, spatial_filter: str, format_filter: str
    ) -> List[int]:
        """Devuelve índices de datasets que cumplen los filtros."""
        indices = []
        for idx, ds in enumerate(self.datasets):
            # Filtro por tema (match parcial en URI o label)
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
    # Aggregation helpers (for UI filters)
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
        text = " ".join([
            ds.get("publisher_name", ""),
            ds.get("title_es", ""),
            ds.get("description_es", ""),
            " ".join(ds.get("tags", [])),
        ]).lower()
        patterns = [
            (["tenerife", "gran canaria", "lanzarote", "la palma", "fuerteventura",
              "la gomera", "el hierro", "istac", "gobierno de canarias"], "Canarias"),
            (["canarias", "canario", "canaria"], "Canarias"),
            (["zaragoza", "huesca", "teruel", "gobierno de aragón"], "Aragón"),
            (["aragón", "aragon"], "Aragón"),
            (["barcelona", "girona", "lleida", "tarragona", "generalitat"], "Cataluña"),
            (["cataluña", "catalunya", "catalonia"], "Cataluña"),
            (["comunidad de madrid", "ayuntamiento de madrid"], "Madrid"),
            (["madrid"], "Madrid"),
            (["sevilla", "málaga", "granada", "córdoba", "almería", "jaén", "huelva", "cádiz"], "Andalucía"),
            (["andalucía", "andalucia"], "Andalucía"),
            (["bilbao", "donostia", "vitoria", "euskadi", "gobierno vasco"], "País Vasco"),
            (["país vasco", "euskal"], "País Vasco"),
            (["coruña", "pontevedra", "ourense", "lugo", "xunta"], "Galicia"),
            (["galicia", "galego"], "Galicia"),
            (["valenciana", "valencia", "alicante", "castellón"], "C. Valenciana"),
            (["mallorca", "menorca", "ibiza", "eivissa", "govern balear"], "Baleares"),
            (["baleares", "illes balears"], "Baleares"),
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
            (["españa", "espana", "gobierno de españa", "administración general"], "España"),
        ]
        for keywords, label in patterns:
            if any(kw in text for kw in keywords):
                return label
        return "España"

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
                # Simplificar MIME a nombre legible
                simple = _simplify_format(fmt)
                if simple:
                    seen.add(simple)
        return sorted(seen)


# ---------------------------------------------------------------------------
# Format simplification helper
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


# Singleton para reutilizar en toda la app Streamlit
_search_engine: TfidfSearchEngine | None = None


def get_engine() -> TfidfSearchEngine:
    """Devuelve el motor de búsqueda (singleton)."""
    global _search_engine
    if _search_engine is None:
        _search_engine = TfidfSearchEngine()
    return _search_engine
