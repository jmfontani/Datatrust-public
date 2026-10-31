#!/usr/bin/env python3
"""
126_aplicar_criterio_ambito.py — aplica el rejuicio del nivel 1 al GT.

QUE HACE
Sustituye las 225 etiquetas de nivel 1 por el resultado del rejuicio con el
criterio de ambito corregido (script 124 + recuperacion del 125).

POR QUE SOLO SE TOCA EL NIVEL 1 (justificacion)
El criterio nuevo es MAS PERMISIVO en territorio: acepta cualquier ambito espanol
(nacional, autonomico o municipal) como "responde". Por tanto:
  - un 2 viejo ya satisfacia la exigencia estricta -> sigue siendo 2;
  - un 0 viejo es otro fenomeno, y el territorio no interviene en esa decision
    -> sigue siendo 0;
  - solo el nivel 1 puede moverse, y solo porque su motivo era el ambito.
Los desgloses y periodos (casos b y c del criterio nuevo) SI se mantienen en 1,
y esos ya estaban en 1 con el criterio viejo.

TRAZABILIDAD
Guarda el GT anterior en `gt_etiquetas_v2_PRE-CRITERIO.json` y anota en cada
etiqueta modificada su nivel previo, para poder revertir y para poder auditar
caso por caso.
"""
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
ETIQ = ENTREG / "gt_etiquetas_v2.json"
REJ = ENTREG / "rejuicio_nivel1.json"
COPIA = ENTREG / "gt_etiquetas_v2_PRE-CRITERIO.json"


def main():
    doc = json.loads(ETIQ.read_text(encoding="utf-8"))
    rej = json.loads(REJ.read_text(encoding="utf-8"))
    etiq, det = doc["etiquetas"], doc.setdefault("detalle", {})

    antes = Counter(etiq.values())
    print("=" * 76)
    print("APLICAR EL CRITERIO DE AMBITO CORREGIDO AL GROUND TRUTH")
    print("=" * 76)
    print(f"\n  distribucion ANTES: {dict(sorted(antes.items()))}")
    print(f"  etiquetas totales : {len(etiq)}")

    nivel1 = [k for k, v in etiq.items() if v == 1]
    faltan = [k for k in nivel1 if k not in rej["detalle"]]
    print(f"\n  nivel 1 a reemplazar : {len(nivel1)}")
    print(f"  rejuicios disponibles: {len([k for k in nivel1 if k in rej['detalle']])}")
    if faltan:
        print(f"  ** FALTAN {len(faltan)} rejuicios: el GT NO se ha tocado **")
        for k in faltan[:5]:
            print(f"     {k}")
        return 2

    # copia de seguridad ANTES de escribir
    if not COPIA.exists():
        shutil.copy2(ETIQ, COPIA)
        print(f"\n  copia de seguridad: {COPIA.name}")
    else:
        print(f"\n  copia de seguridad ya existia: {COPIA.name}")

    cambios = []
    for k in nivel1:
        nuevo = rej["detalle"][k]
        doc["etiquetas"][k] = nuevo["nivel"]
        # conservar el nivel previo y anotar el origen del cambio
        prev = det.get(k, {})
        det[k] = {"nivel": nuevo["nivel"], "razon": nuevo.get("razon", ""),
                  "title": nuevo.get("title") or prev.get("title", ""),
                  "nivel_previo": 1,
                  "origen": "criterio_ambito_2026-09-25"}
        cambios.append((k, nuevo["nivel"]))

    despues = Counter(doc["etiquetas"].values())
    doc["meta"]["total"] = len(doc["etiquetas"])
    doc["meta"]["criterio_ambito"] = (
        "25-sep-2026: las 225 etiquetas de nivel 1 se rejuzgaron con el criterio "
        "corregido (acepta ambito autonomico/municipal como 'responde'; nivel 1 "
        "solo si territorio extranjero, desglose o periodo incompatible). "
        "Motivo: docs/FASE-C-PASO1-HALLAZGO.md")
    doc["meta"]["distribucion"] = dict(sorted(despues.items()))

    ETIQ.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    mov = Counter(n for _, n in cambios)
    print(f"\n### RESULTADO ###\n")
    print(f"  etiquetas reemplazadas: {len(cambios)}")
    print(f"  hacia nivel 2 (responde): {mov.get(2, 0)}")
    print(f"  siguen en nivel 1       : {mov.get(1, 0)}")
    print(f"  hacia nivel 0 (otro fen.): {mov.get(0, 0)}")
    print(f"\n  distribucion DESPUES: {dict(sorted(despues.items()))}")
    delta2 = despues.get(2, 0) - antes.get(2, 0)
    print(f"  fichas que ahora RESPONDEN: {antes.get(2,0)} -> {despues.get(2,0)} "
          f"({delta2:+d})")
    print(f"\n  guardado: {ETIQ.name}")
    print(f"  vuelta atras: cp {COPIA.name} {ETIQ.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
