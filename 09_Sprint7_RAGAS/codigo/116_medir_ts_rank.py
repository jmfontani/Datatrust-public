#!/usr/bin/env python3
"""
116_medir_ts_rank.py — antes de arreglar el bug, medir la magnitud real.

El bug es `r['rank'] / max(rank del conjunto)`. Para sustituirlo hace falta saber
en que rango se mueve `ts_rank_cd` de verdad, porque el sustituto
`rank / (rank + k)` colapsa a casi cero si k es mucho mayor que los valores
reales, y el peso lexico 0,3 quedaria anulado en silencio.

Se mide, por consulta:
  * el maximo de ts_rank_cd sobre el catalogo (es el divisor que usa hoy)
  * la mediana y el p90
  * cuanto se moveria el divisor al cambiar el corte (la magnitud del bug)

Y con esos numeros se elige k tal que el valor tipico quede en un rango
comparable al que produce hoy la division por el maximo.
"""
import json
import os
import sys
from pathlib import Path
from statistics import median

import psycopg2

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
GT = ENTREG / "ground_truth.jsonl"

# mismas stop words / expansion minima que usa el motor para el tsquery
def ts_query(texto):
    """El motor hace ' & '.join(expanded_query.split())."""
    return " & ".join(texto.split())


def main():
    consultas = [json.loads(l) for l in GT.read_text(encoding="utf-8").splitlines() if l.strip()]
    conn = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "postgres"),
                            dbname=os.getenv("POSTGRES_DB", "buscador"),
                            user=os.getenv("POSTGRES_USER", "postgres"),
                            password=os.getenv("POSTGRES_PASSWORD", "postgres"))

    print("=" * 76)
    print("DISTRIBUCION DE ts_rank_cd (magnitud real del componente lexico)")
    print("=" * 76)
    print(f"\n  consultas: {len(consultas)}\n")
    print(f"  {'query_id':14} {'maximo':>10} {'p90':>10} {'mediana':>10} {'n':>8}")
    print("  " + "-" * 60)

    filas = []
    with conn.cursor() as cur:
        for q in consultas:
            tq = ts_query(q["query"])
            try:
                cur.execute("""
                    SELECT ts_rank_cd(d.search_vector, to_tsquery('spanish', %s)) AS r
                    FROM datasets d
                    WHERE d.search_vector @@ to_tsquery('spanish', %s)
                    ORDER BY r DESC
                    LIMIT 2000
                """, (tq, tq))
                vals = [float(x[0]) for x in cur.fetchall()]
            except Exception as e:
                conn.rollback()
                print(f"  {q['id']:14} ERROR {str(e)[:40]}")
                continue
            if not vals:
                print(f"  {q['id']:14} {'-':>10} {'-':>10} {'-':>10} {0:>8}")
                continue
            mx = max(vals)
            p90 = vals[max(0, int(len(vals) * 0.10))]
            med = median(vals)
            filas.append({"query_id": q["id"], "max": mx, "p90": p90,
                          "mediana": med, "n": len(vals)})
            print(f"  {q['id']:14} {mx:>10.4f} {p90:>10.4f} {med:>10.4f} {len(vals):>8}")

    if not filas:
        print("\n  no se pudo medir nada")
        return 1

    med_mx = median([f["max"] for f in filas])
    med_p90 = median([f["p90"] for f in filas])
    med_med = median([f["mediana"] for f in filas])

    print(f"\n### RESUMEN ###\n")
    print(f"  maximo   - mediana entre consultas: {med_mx:.4f}")
    print(f"  p90      - mediana entre consultas: {med_p90:.4f}")
    print(f"  mediana  - mediana entre consultas: {med_med:.4f}")
    print(f"\n  El divisor que usa HOY el motor (max del corte) esta en torno a {med_mx:.4f}.")
    print(f"  El top-1 de cada consulta sale por tanto con score lexico normalizado 1,0.")

    # ---- eleccion de k ----
    print(f"\n### ELECCION DE k para rank/(rank+k) ###\n")
    print(f"  {'k':>8} {'valor tipico':>14} {'valor max':>12} {'rango [0,1]'}")
    print("  " + "-" * 56)
    cand = []
    for k in (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0):
        tip = med_med / (med_med + k)
        mx = med_mx / (med_mx + k)
        cand.append({"k": k, "tipico": round(tip, 4), "max": round(mx, 4)})
        print(f"  {k:>8} {tip:>14.4f} {mx:>12.4f}  compacto")

    # criterio: que el valor MAXIMO tipico quede cerca de 1,0 (uso la misma
    # escala relativa que hoy) sin saturar el valor tipico
    objetivo = 0.75
    mejor = min(cand, key=lambda c: abs(c["max"] - objetivo))
    print(f"\n  Criterio: que el maximo tipico quede cerca de {objetivo} (uso la misma")
    print(f"  escala relativa que hoy, para no alterar el equilibrio 0,7/0,3).")
    print(f"  -> k = {mejor['k']}  (tipico {mejor['tipico']}, maximo {mejor['max']})")

    salida = ENTREG / "ts_rank_distribucion.json"
    salida.write_text(json.dumps({
        "meta": {"consultas": len(filas), "k_recomendado": mejor["k"],
                 "criterio": f"maximo tipico cerca de {objetivo}",
                 "mediana_max": med_mx, "mediana_p90": med_p90,
                 "mediana_mediana": med_med},
        "por_consulta": filas, "candidatos_k": cand,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
