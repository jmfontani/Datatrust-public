#!/usr/bin/env python3
"""
104_construir_etiquetas.py — FASE A, paso 1.

Extrae los 470 juicios del LLM (que ya existen dentro del ground truth) y los
convierte en un INDICE DE ETIQUETAS indexado por dataset_id.

Motivo: hoy el evaluador decide relevancia con patrones de texto sobre el titulo,
ignorando estos juicios razonados. Medido: el criterio de patron marca como
relevante el 41 % de lo que el juicio RECHAZA (precisión 0,697; 96 falsos
positivos de 232).

El juicio es la verdad de referencia. Se indexa por dataset_id, que SI viene en
'resultados_reales', en lugar de por titulo (el catalogo tiene 2.144 grupos de
titulos duplicados: cruzar por titulo seria ambiguo).

Escala de relevancia (validada en el Paso 0: 90 % de acuerdo entre pasadas):
    2 = RESPONDE   | el LLM lo marco 'relevante'
    1 = tema correcto, otro alcance  | reservado para la Fase B
    0 = NO RESPONDE | el LLM lo marco 'no_relevante'

IMPORTANTE: la etiqueta depende del DOCUMENTO y de la CONSULTA, no del encoder.
Es reutilizable cuando se cambie de modelo de embeddings.

Salida: fichero JSON con el indice + informe de integridad por consola.
"""
import os
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

GT = Path.home() / ("datos/PFM/Datatrust/09_Sprint7_RAGAS/entregables/"
          "ground_truth.jsonl")
SALIDA = Path.home() / ("datos/PFM/Datatrust/09_Sprint7_RAGAS/entregables/"
              "gt_etiquetas.json")
MODELO_JUEZ = "llm (generar_ground_truth_real.py, junio 2026)"


def normaliza(t):
    return " ".join((t or "").lower().split())


def main():
    if not GT.exists():
        print(f"ERROR: no existe {GT}")
        return 1

    entradas = []
    for ln in GT.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                entradas.append(json.loads(ln))
            except json.JSONDecodeError as e:
                print(f"  aviso: linea no parseable ({e})")
    print(f"### ground truth de origen: {GT.name} — {len(entradas)} consultas ###\n")

    etiquetas = {}          # (query_id, dataset_id) -> nivel
    por_titulo = defaultdict(set)   # respaldo, marcado como ambiguo
    origen = {}             # (query_id, dato) -> como se resolvio
    sin_resolver = []
    stats = Counter()

    for q in entradas:
        qid = q.get("id")
        # mapa titulo -> dataset_id desde resultados_reales (via FIABLE)
        id_por_titulo = {}
        for r in (q.get("resultados_reales") or []):
            did = r.get("id")
            t = normaliza(r.get("title"))
            if did and t:
                id_por_titulo[t] = did
        for c in (q.get("ground_truth", {}).get("resultados_clasificados") or []):
            t = normaliza(c.get("title"))
            rel = c.get("relevancia")
            if rel not in ("relevante", "no_relevante"):
                stats["relevancia_desconocida"] += 1
                continue
            nivel = 2 if rel == "relevante" else 0

            did = id_por_titulo.get(t)
            if did:
                etiquetas[(qid, did)] = nivel
                origen[(qid, did)] = "resultados_reales"
                stats["resuelto_por_id"] += 1
            else:
                por_titulo[(qid, t)].add(nivel)
                sin_resolver.append({"query_id": qid, "title": c.get("title"),
                                     "relevancia": rel})
                stats["sin_resolver"] += 1

    total = stats["resuelto_por_id"] + stats["sin_resolver"]
    print(f"### extraccion ###\n")
    print(f"  juicios leidos          : {total}")
    print(f"  resueltos por dataset_id: {stats['resuelto_por_id']} "
          f"({100*stats['resuelto_por_id']/max(total,1):.0f} %)")
    print(f"  sin resolver            : {stats['sin_resolver']}")
    if stats["relevancia_desconocida"]:
        print(f"  relevancia desconocida  : {stats['relevancia_desconocida']}")

    dist = Counter(etiquetas.values())
    print(f"\n  distribucion de niveles: {dict(sorted(dist.items()))}")
    print(f"  (2 = responde, 0 = no responde; el nivel 1 llega en la Fase B)")

    # integridad: ¿aparecen las fichas etiquetadas en el catalogo?
    print(f"\n### verificacion de integridad ###\n")
    ids_etiq = {did for (_, did) in etiquetas}
    print(f"  dataset_id distintos etiquetados: {len(ids_etiq)}")

    # cobertura por consulta
    por_q = Counter(qid for (qid, _) in etiquetas)
    print(f"\n  etiquetas por consulta: min {min(por_q.values())}, "
          f"max {max(por_q.values())}, media {sum(por_q.values())/len(por_q):.1f}")
    flojas = [q for q, n in por_q.items() if n < 5]
    if flojas:
        print(f"  consultas con menos de 5 etiquetas: {len(flojas)} {sorted(flojas)[:8]}")

    # aviso sobre titulos ambiguos del catalogo
    print(f"\n### aviso de ambiguedad ###\n")
    print(f"  {len(sin_resolver)} juicios no se pudieron anclar a un dataset_id.")
    print(f"  NO se resuelven por titulo: el catalogo tiene grupos de titulos")
    print(f"  duplicados, y asignar por titulo es silenciosamente erroneo.")
    print(f"  Estos casos quedaran SIN ETIQUETA y asi deben tratarse (no como 0).")

    salida = {
        "meta": {
            "generado": datetime.now(timezone.utc).isoformat(),
            "origen": str(GT),
            "juez": MODELO_JUEZ,
            "escala": {"2": "responde", "1": "tema correcto, otro alcance",
                       "0": "no responde"},
            "total_juicios": total,
            "resueltos": stats["resuelto_por_id"],
            "sin_resolver": stats["sin_resolver"],
            "nota": ("La etiqueta depende de (consulta, documento), no del encoder. "
                     "Reutilizable al cambiar de modelo de embeddings."),
        },
        # clave compuesta en texto: "query_id|dataset_id"
        "etiquetas": {f"{qid}|{did}": niv for (qid, did), niv in etiquetas.items()},
        "sin_resolver": sin_resolver,
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    print(f"\n  guardado: {SALIDA}")
    print(f"  ({len(etiquetas)} etiquetas, {SALIDA.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
