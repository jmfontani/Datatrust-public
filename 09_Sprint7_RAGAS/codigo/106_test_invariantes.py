#!/usr/bin/env python3
"""
106_test_invariantes.py — FASE A, criterio de aceptacion.

Verifica que la IMPLEMENTACION de las metricas es correcta mediante invariantes
matematicas. Sin esto, un nDCG mal implementado daria numeros plausibles y falsos.

Invariantes que deben cumplirse SIEMPRE:
  1. orden IDEAL (relevantes delante)      -> nDCG = 1,000
  2. orden INVERTIDO (relevantes al final) -> nDCG ~ 0
  3. orden ALEATORIO                       -> nDCG intermedio, < ideal > invertido
  4. P@5 con 5 relevantes en cabeza        -> 1,000
  5. P@5 con los relevantes en 6-10        -> 0,000
  6. MRR: relevantes en 1a posicion        -> 1,000
  7. nDCG con ganancia gradada: 2,1,0 ordenados > 0,2,1
  8. monotonia: mejorar el orden no puede BAJAR la metrica
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.gt_metrics import EtiquetasGT, evaluar, mrr, ndcg_at_k_detallado, precision_at_k

RUTA = Path(__file__).resolve().parent.parent / "entregables" / "gt_etiquetas.json"

fallos = []


def comprueba(nombre, cond, detalle=""):
    estado = "OK " if cond else "FALLO"
    print(f"  [{estado}] {nombre}" + (f"   {detalle}" if detalle else ""))
    if not cond:
        fallos.append(nombre)


def main():
    random.seed(7)
    gt = EtiquetasGT(RUTA)
    print("=" * 74)
    print("TEST DE INVARIANTES DE LAS METRICAS (Fase A)")
    print("=" * 74)
    print(f"\n  indice: {len(gt)} etiquetas\n")

    # Conjunto SINTETICO de control: mezcla conocida y equilibrada.
    # No se usa una consulta real porque su distribucion de niveles es
    # arbitraria (p.ej. 9 relevantes y 1 no relevante), y entonces el "orden
    # invertido" no llega a colocar 5 no relevantes en cabeza: el invariante
    # no seria comprobable. Con datos de control, SI.
    qid = "test_sintetico"
    mezcla = ([2, 2, 2, 2, 2] + [1, 1, 1] + [0, 0, 0, 0, 0, 0, 0])
    gt._et = {f"{qid}|ficha_{i:02d}": v for i, v in enumerate(mezcla)}
    niveles = sorted(mezcla, reverse=True)
    print(f"  conjunto SINTETICO de control: {len(mezcla)} fichas "
          f"(5 nivel-2, 3 nivel-1, 7 nivel-0)\n")

    ids = [f"ficha_{i:02d}" for i in range(len(mezcla))]
    niv = {f"ficha_{i:02d}": v for i, v in enumerate(mezcla)}

    def R(orden_ids):
        return [{"dataset_id": i, "title": f"ficha {i[:8]}"} for i in orden_ids]

    rel2 = [i for i in ids if niv[i] == 2]
    rel1 = [i for i in ids if niv[i] == 1]
    rel0 = [i for i in ids if niv[i] == 0]

    ideal = rel2 + rel1 + rel0
    invertido = rel0 + rel1 + rel2
    alea = ids[:]
    random.shuffle(alea)

    # --- 1 y 2: orden ideal e invertido ---
    n_ideal = ndcg_at_k_detallado(R(ideal), gt, qid, 10, niveles)
    n_inv = ndcg_at_k_detallado(R(invertido), gt, qid, 10, niveles)
    comprueba("orden IDEAL -> nDCG = 1,000", abs(n_ideal - 1.0) < 1e-9,
              f"nDCG={n_ideal:.4f}")
    comprueba("orden INVERTIDO -> nDCG mucho menor", n_inv < n_ideal,
              f"nDCG={n_inv:.4f} vs {n_ideal:.4f}")

    # --- 3: aleatorio intermedio ---
    n_alea = ndcg_at_k_detallado(R(alea), gt, qid, 10, niveles)
    comprueba("orden ALEATORIO entre invertido e ideal",
              n_inv <= n_alea <= n_ideal, f"nDCG={n_alea:.4f}")
    comprueba("orden INVERTIDO -> nDCG claramente menor",
              n_inv < 0.5 * n_ideal, f"nDCG={n_inv:.4f} vs ideal 1,0")

    # --- 4 y 5: P@5 ---
    p5_bien = precision_at_k(R(ideal), gt, qid, 5)
    p5_mal = precision_at_k(R(invertido), gt, qid, 5)
    comprueba("P@5 con relevantes en cabeza -> 1,0", abs(p5_bien - 1.0) < 1e-9,
              f"P@5={p5_bien:.4f}")
    comprueba("P@5 con relevantes al final -> 0,0", abs(p5_mal) < 1e-9,
              f"P@5={p5_mal:.4f}")

    # --- 6: MRR ---
    mr_1 = mrr(R(ideal), gt, qid)
    mr_inv = mrr(R(invertido), gt, qid)
    comprueba("MRR con relevante en 1a posicion -> 1,0", abs(mr_1 - 1.0) < 1e-9,
              f"MRR={mr_1:.4f}")
    comprueba("MRR con relevante al final -> menor", mr_inv < mr_1,
              f"MRR={mr_inv:.4f}")

    # --- 7: ganancia gradada ---
    if True:
        a = ndcg_at_k_detallado(R(rel2 + rel1 + rel0), gt, qid, 10, niveles)
        b = ndcg_at_k_detallado(R(rel1 + rel2 + rel0), gt, qid, 10, niveles)
        comprueba("ganancia gradada: (2,1,0) > (1,2,0)", a > b,
                  f"{a:.4f} > {b:.4f}")


    # --- 8: monotonia por intercambios ---
    base = ideal[:]
    mejoras = 0
    for _ in range(40):
        v = base[:]
        i, j = random.sample(range(len(v)), 2)
        if niv[v[i]] < niv[v[j]]:
            v[i], v[j] = v[j], v[i]      # subir el mas relevante
        else:
            continue
        if ndcg_at_k_detallado(R(v), gt, qid, 10, niveles) >= \
           ndcg_at_k_detallado(R(base), gt, qid, 10, niveles) - 1e-12:
            mejoras += 1
    comprueba("monotonia: subir un relevante no baja la metrica",
              mejoras == 0, f"violaciones={mejoras}")

    # --- 9: los SIN JUICIO no cuentan como relevantes ---
    r_falso = R([i for i in ids if niv[i] == 0] + ["no-juzgado-1", "no-juzgado-2"])
    n_falso = ndcg_at_k_detallado(r_falso, gt, qid, 10, niveles)
    comprueba("fichas SIN juicio -> ganancia 0", n_falso < 0.01,
              f"nDCG={n_falso:.4f} (deberia ser ~0)")

    # --- 10: cobertura bien calculada ---
    mezcla = R([ids[0], "no-juzgado-1", "no-juzgado-2", "no-juzgado-3"])
    ev = evaluar(qid, mezcla, gt)
    comprueba("cobertura = juzgados/total", abs(ev["cobertura_top10"] - 0.25) < 1e-9,
              f"cobertura={ev['cobertura_top10']} con 1 de 4 juzgado")

    print()
    if fallos:
        print(f"### RESULTADO: {len(fallos)} FALLOS ###")
        for f in fallos:
            print(f"   - {f}")
        return 1
    print("### RESULTADO: TODOS LOS INVARIANTES SE CUMPLEN ###")
    print("   La implementacion de las metricas es correcta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
