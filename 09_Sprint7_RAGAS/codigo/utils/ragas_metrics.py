#!/usr/bin/env python3
"""
utils/ragas_metrics.py — métricas de evaluación del Buscador Semántico.

ESTADO: ACTUALIZADO (01-oct-2026) al instrumento canónico del proyecto.

Lo que NO cambia: `evaluar_con_ragas()`, el wrapper del framework RAGAS real
(context precision/recall, faithfulness, answer relevancy con LLM). Es el uso
legítimo del nombre y sigue disponible con `pip install ragas datasets`.

Lo que SÍ cambia: las funciones `calcular_precision_at_k`, `calcular_ndcg_at_k`,
`calcular_mrr` y `evaluar_query_individual` ANTES decidían relevancia buscando
PATRONES DE TEXTO en el título (`any(patron in titulo ...)`). Medido contra los
470 juicios humanos de la Fase A, ese criterio marcaba como relevante el 41 % de
lo que el juicio RECHAZA (96 falsos positivos de 232 no relevantes; lo documenta
`utils/gt_metrics.py`). AHORA todo delega en `utils/gt_metrics.py`, el
instrumento canónico:

- Relevancia por JUICIO (LLM juez, temperatura 0) sobre GT v5
  (`entregables/gt_etiquetas_v5.json`, 10.653 etiquetas, 214 consultas), clave
  (query_id, dataset_id), NO por título (2.144 títulos duplicados lo hacían
  ambiguo).
- Escala gradada 0/1/2 (no responde / tema correcto otro alcance / responde),
  nDCG que distingue orden de presencia.
- Los resultados SIN juicio se EXCLUYEN del cálculo y se reportan en
  `cobertura_top10`; no cuentan como no relevantes (el error antiguo).

Interfaz:
    calcular_precision_at_k(resultados, gt, query_id, k=5, umbral=2)
    calcular_ndcg_at_k(resultados, gt, query_id, k=10, niveles_consulta=None)
    calcular_mrr(por_query, gt, query_ids)
    evaluar_query_individual(query_id, query, resultados, gt)

donde `gt` es un EtiquetasGT, una ruta al JSON de etiquetas, o None (v5).
"""

import json
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

try:
    from ragas import evaluate
    from ragas.metrics import (
        context_precision,
        context_recall,
        faithfulness,
        answer_relevancy,
    )
    from datasets import Dataset
    RAGAS_DISPONIBLE = True
except ImportError:
    RAGAS_DISPONIBLE = False

# ----------------------------------------------------------------------
# Instrumento canonico (juez 0/1/2 sobre GT v5)
# ----------------------------------------------------------------------
from utils.gt_metrics import (
    EtiquetasGT,
    evaluar as _evaluar_canonico,
    precision_at_k as _precision_k,
    ndcg_at_k_detallado,
    mrr as _mrr_k,
)

ETIQUETAS_V5 = (Path(__file__).resolve().parent.parent.parent
                / "entregables" / "gt_etiquetas_v5.json")


def cargar_gt_v5(ruta=None) -> EtiquetasGT:
    """Carga el GT v5 del juez. Acepta ruta alternativa."""
    return EtiquetasGT(ruta or ETIQUETAS_V5)


def _a_gt(gt) -> EtiquetasGT:
    """Acepta EtiquetasGT, ruta str/Path o None (usa el v5)."""
    if isinstance(gt, EtiquetasGT):
        return gt
    return EtiquetasGT(gt) if gt else EtiquetasGT(ETIQUETAS_V5)


@dataclass
class RAGASEvaluationResult:
    """Resultado de evaluación RAGAS (framework real)."""
    context_precision: float  # 0-1
    context_recall: float  # 0-1
    faithfulness: float  # 0-1
    answer_relevancy: float  # 0-1
    n_queries: int

    def to_dict(self) -> dict:
        return {
            "context_precision": round(self.context_precision, 4),
            "context_recall": round(self.context_recall, 4),
            "faithfulness": round(self.faithfulness, 4),
            "answer_relevancy": round(self.answer_relevancy, 4),
            "n_queries": self.n_queries,
        }

    def summary(self) -> str:
        return (
            f"RAGAS Scores (n={self.n_queries}):\n"
            f"  Context Precision: {self.context_precision:.3f}\n"
            f"  Context Recall:    {self.context_recall:.3f}\n"
            f"  Faithfulness:      {self.faithfulness:.3f}\n"
            f"  Answer Relevancy:  {self.answer_relevancy:.3f}"
        )


def evaluar_con_ragas(
    queries: list[str],
    respuestas: list[str],
    contextos: list[list[str]],
    ground_truths: list[list[str]]
) -> Optional[RAGASEvaluationResult]:
    """Evalúa un conjunto de queries usando el framework RAGAS real."""
    if not RAGAS_DISPONIBLE:
        print("❌ RAGAS no disponible. Asegúrate de instalar: pip install ragas datasets langchain")
        return None

    if len(queries) != len(respuestas) or len(queries) != len(contextos):
        print(f"❌ Error: longitudes inconsistentes. queries={len(queries)}, respuestas={len(respuestas)}, contextos={len(contextos)}")
        return None

    data_dict = {
        "question": queries,
        "answer": respuestas,
        "contexts": contextos,
        "ground_truth": ground_truths,
    }

    dataset = Dataset.from_dict(data_dict)

    print("🔍 Ejecutando evaluación RAGAS...")
    try:
        result = evaluate(
            dataset,
            metrics=[
                context_precision,
                context_recall,
                faithfulness,
                answer_relevancy,
            ],
        )

        scores = result.to_pandas()

        return RAGASEvaluationResult(
            context_precision=scores["context_precision"].mean(),
            context_recall=scores["context_recall"].mean(),
            faithfulness=scores["faithfulness"].mean(),
            answer_relevancy=scores["answer_relevancy"].mean(),
            n_queries=len(queries),
        )

    except Exception as e:
        print(f"❌ Error en evaluación RAGAS: {e}")
        return None


# ----------------------------------------------------------------------
# Metricas de retrieval: delegan en gt_metrics (juez), NO en patrones
# ----------------------------------------------------------------------

def calcular_precision_at_k(
    resultados: list[dict],
    gt=None,
    query_id: str = "",
    k: int = 5,
    umbral: int = 2,
) -> float:
    """
    Precisión@K según el JUICIO del GT v5 (dataset_id, escala 0/1/2).

    `resultados`: dicts del buscador con 'dataset_id' o 'id'.
    `gt`: EtiquetasGT | ruta al JSON de etiquetas | None (v5 por defecto).
    `umbral`: 2 = solo "responde"; 1 = incluye "tema correcto, otro alcance".
    """
    if not resultados or not query_id:
        return 0.0
    return _precision_k(resultados, _a_gt(gt), query_id, k, umbral=umbral)


def calcular_ndcg_at_k(
    resultados: list[dict],
    gt=None,
    query_id: str = "",
    k: int = 10,
    niveles_consulta=None,
) -> float:
    """nDCG@K según el JUICIO del GT v5 (dataset_id)."""
    if not resultados or not query_id:
        return 0.0
    g = _a_gt(gt)
    if niveles_consulta is None:
        pref = f"{query_id}|"
        niveles_consulta = [int(v) for kk, v in g._et.items() if kk.startswith(pref)]
    return ndcg_at_k_detallado(resultados, g, query_id, k, niveles_consulta)


def calcular_mrr(
    resultados_por_query: list[list[dict]],
    gt=None,
    query_ids: Optional[list[str]] = None,
    umbral: int = 2,
) -> float:
    """
    MRR según el JUICIO del GT v5.

    `query_ids`: lista paralela a `resultados_por_query` con los query_id.
    (La firma antigua por patrones de título ya no existe.)
    """
    if not resultados_por_query:
        return 0.0
    g = _a_gt(gt)
    if query_ids is None:
        raise ValueError("calcular_mrr requiere query_ids alineados con resultados_por_query")
    rrs = [_mrr_k(res, g, qid, umbral=umbral)
           for res, qid in zip(resultados_por_query, query_ids)]
    return sum(rrs) / len(rrs)


def evaluar_query_individual(
    query_id: str,
    query: str,
    resultados: list[dict],
    gt=None,
    k_precision: int = 5,
    k_ndcg: int = 10,
    umbral: int = 2,
) -> dict:
    """
    Evaluación de una consulta con el instrumento canónico (GT v5, juez 0/1/2).

    `query` se mantiene en la firma por trazabilidad (va al output); la
    relevancia NO depende del texto, solo de (query_id, dataset_id).

    Devuelve las métricas + `cobertura_top10` (fracción JUZGADA de los
    resultados; sin ella la métrica no es interpretable) + conteos de niveles.
    """
    g = _a_gt(gt)
    if not query_id:
        return {"query": query, "error": "falta query_id: el GT v5 indexa por id de consulta"}
    out = dict(_evaluar_canonico(query_id, resultados, g, k_precision, k_ndcg, umbral))
    out["query"] = query
    # compatibilidad con los consumers: precision@10 y recall@10 por juicio
    out["precision_at_10"] = round(_precision_k(resultados, g, query_id, 10, umbral=umbral), 4)
    pref = f"{query_id}|"
    niveles_consulta = [int(v) for kk, v in g._et.items() if kk.startswith(pref)]
    n2_disp = sum(1 for v in niveles_consulta if v >= umbral)
    from utils.gt_metrics import _niveles_de
    n2_top10 = sum(1 for x in _niveles_de(resultados[:10], g, query_id)
                   if x is not None and x >= umbral)
    out["recall"] = round(n2_top10 / n2_disp, 4) if n2_disp else 0.0
    out["recall_base"] = f"{n2_disp} fichas nivel>={umbral} juzgadas para esta consulta"
    out["instrumento"] = "gt_v5_juez (ver meta en gt_etiquetas_v5.json)"
    out["nota_cobertura"] = (
        "Resultados sin juicio: excluidos del calculo y contados en "
        "n_sin_juicio. Si cobertura_top10 es baja, NO compares metricas: "
        "son de poblaciones distintas."
    )
    return out


__all__ = [
    "RAGAS_DISPONIBLE",
    "RAGASEvaluationResult",
    "evaluar_con_ragas",
    "calcular_precision_at_k",
    "calcular_ndcg_at_k",
    "calcular_mrr",
    "evaluar_query_individual",
    "cargar_gt_v5",
]