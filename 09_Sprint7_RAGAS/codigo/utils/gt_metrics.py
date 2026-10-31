#!/usr/bin/env python3
"""
gt_metrics.py — FASE A, paso 2. Metricas basadas en el JUICIO, no en patrones.

Sustituye a las funciones equivalentes de utils/ragas_metrics.py, que deciden
relevancia buscando patrones de texto en el titulo. Ese criterio, medido contra
los 470 juicios reales, marca como relevante el 41 % de lo que el juicio RECHAZA
(precision 0,697 · 96 falsos positivos de 232 no relevantes).

Tres cambios de fondo:

1. RELEVANCIA POR dataset_id, no por titulo.
   El catalogo tiene 2.144 grupos de titulos duplicados: cruzar por titulo
   asignaria juicios a fichas equivocadas de forma silenciosa.

2. LOS SIN JUICIO NO SON "NO RELEVANTES".
   Es el error que invalidaba la medicion anterior. Un documento sin juzgar se
   EXCLUYE del calculo y se contabiliza en la COBERTURA. Si la cobertura es baja,
   la metrica no es interpretable y la funcion lo dice.

3. ESCALA GRADADA (0/1/2) en lugar de binaria.
   Permite nDCG que distingue "acertar el orden" de "acertar la presencia".

La etiqueta depende de (consulta, documento), NO del encoder: es reutilizable
cuando se cambie el modelo de embeddings.
"""
import json
import math
from pathlib import Path

ETIQUETAS_POR_DEFECTO = (Path(__file__).resolve().parent.parent.parent
                         / "entregables" / "gt_etiquetas.json")

NIVEL_RESPONDE = 2
NIVEL_OTRO_ALCANCE = 1
NIVEL_NO_RESPONDE = 0


class EtiquetasGT:
    """Indice de juicios (consulta, dataset) -> nivel 0/1/2."""

    def __init__(self, ruta=None):
        self.ruta = Path(ruta or ETIQUETAS_POR_DEFECTO)
        d = json.loads(self.ruta.read_text(encoding="utf-8"))
        self.meta = d.get("meta", {})
        # clave "query_id|dataset_id"
        self._et = d.get("etiquetas", {})
        self.sin_resolver = d.get("sin_resolver", [])

    def nivel(self, query_id, dataset_id):
        """Nivel de relevancia, o None si no hay juicio para ese par."""
        if not query_id or not dataset_id:
            return None
        v = self._et.get(f"{query_id}|{dataset_id}")
        return None if v is None else int(v)

    def __len__(self):
        return len(self._et)


# --------------------------------------------------------------------------
# metricas
# --------------------------------------------------------------------------

def _niveles_de(resultados, gt, query_id):
    """Lista de niveles de los resultados, con None donde no hay juicio."""
    out = []
    for r in resultados:
        did = r.get("dataset_id") or r.get("id")
        out.append(gt.nivel(query_id, did))
    return out


def cobertura(resultados, gt, query_id):
    """Fraccion de resultados JUZGADOS. Sin esto la metrica no es interpretable."""
    niv = _niveles_de(resultados, gt, query_id)
    if not niv:
        return 0.0
    return sum(1 for x in niv if x is not None) / len(niv)


def precision_at_k(resultados, gt, query_id, k=5, denom_incluye_no_juzgados=True,
                   umbral=NIVEL_RESPONDE):
    """
    Precision@k: fraccion de los k primeros que son relevantes.

    UMBRAL: es una decision con consecuencias, no un detalle tecnico.
      umbral=2 -> solo cuenta "responde". Severo: una ficha que trata el tema
                  pero de otra comunidad NO cuenta. Apropiado para una metrica
                  de respuesta directa.
      umbral=1 -> cuenta tambien "mismo tema, otro alcance". Mide si el motor
                  acierta el tema, aunque falle el ambito.

    El nivel 1 es el 16 % del GT, asi que la eleccion mueve el resultado.

    denom_incluye_no_juzgados: si True, el denominador es k (el no juzgado ocupa
    puesto y por tanto "desplaza" a un relevante, asi que penaliza). Si False,
    solo se cuentan los juzgados.
    """
    top = resultados[:k]
    niv = _niveles_de(top, gt, query_id)
    rel = sum(1 for x in niv if x is not None and x >= umbral)
    if not denom_incluye_no_juzgados:
        den = sum(1 for x in niv if x is not None)
    else:
        den = min(k, len(resultados))
    return rel / den if den else 0.0


def ndcg_at_k_detallado(resultados, gt, query_id, k=10, niveles_consulta=None):
    """
    nDCG@k. `niveles_consulta` debe ser la lista de niveles de TODOS los juicios
    disponibles para esta consulta, para calcular el ideal correctamente.
    """
    top = resultados[:k]
    niv = _niveles_de(top, gt, query_id)
    dcg = sum((x or 0) / math.log2(i + 2) for i, x in enumerate(niv))
    if not niveles_consulta:
        return 0.0
    ideal = sorted(niveles_consulta, reverse=True)[:k]
    idcg = sum(v / math.log2(i + 2) for i, v in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def mrr(resultados, gt, query_id, umbral=NIVEL_RESPONDE):
    """Reciprocal rank del primer resultado relevante (segun `umbral`)."""
    for i, r in enumerate(resultados):
        did = r.get("dataset_id") or r.get("id")
        n = gt.nivel(query_id, did)
        if n is not None and n >= umbral:
            return 1.0 / (i + 1)
    return 0.0


def evaluar(query_id, resultados, gt, k_precision=5, k_ndcg=10,
            umbral=NIVEL_RESPONDE):
    """
    Evaluacion completa de una consulta.

    Devuelve las metricas MAS el contexto necesario para interpretarlas:
    cuantos resultados habia juicio y cuantos no.
    """
    niv = _niveles_de(resultados, gt, query_id)
    juzgados = [x for x in niv if x is not None]
    no_juzgados = len(niv) - len(juzgados)

    # niveles disponibles para esta consulta -> ideal del nDCG
    pref = f"{query_id}|"
    niveles_consulta = [int(v) for kk, v in gt._et.items() if kk.startswith(pref)]

    return {
        "query_id": query_id,
        "n_resultados": len(resultados),
        "n_juzgados": len(juzgados),
        "n_sin_juicio": no_juzgados,
        "cobertura_top10": round(cobertura(resultados, gt, query_id), 4),
        "precision_at_5": round(precision_at_k(resultados, gt, query_id, k_precision,
                                               umbral=umbral), 4),
        "ndcg_at_10": round(ndcg_at_k_detallado(resultados, gt, query_id, k_ndcg,
                                                niveles_consulta), 4),
        "mrr": round(mrr(resultados, gt, query_id, umbral=umbral), 4),
        "nivel_2_en_top5": sum(1 for x in niv[:k_precision] if x == NIVEL_RESPONDE),
        "nivel_1_en_top5": sum(1 for x in niv[:k_precision] if x == NIVEL_OTRO_ALCANCE),
        "nivel_0_en_top5": sum(1 for x in niv[:k_precision] if x == NIVEL_NO_RESPONDE),
    }


def intervalo_confianza(valores, z=1.96):
    """Intervalo de confianza al 95 % de la media. Obligatorio al reportar."""
    n = len(valores)
    if n < 2:
        return (None, None, None)
    media = sum(valores) / n
    var = sum((v - media) ** 2 for v in valores) / (n - 1)
    ee = math.sqrt(var / n)
    return (round(media, 4), round(media - z * ee, 4), round(media + z * ee, 4))


def mejora_minima_detectable(valores, z=1.96):
    """Diferencia minima que este tamano de muestra puede distinguir del ruido."""
    n = len(valores)
    if n < 2:
        return None
    media = sum(valores) / n
    var = sum((v - media) ** 2 for v in valores) / (n - 1)
    ee = math.sqrt(var / n)
    return round(z * ee, 4)
