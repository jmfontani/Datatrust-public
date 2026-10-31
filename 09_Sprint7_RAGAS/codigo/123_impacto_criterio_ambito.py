#!/usr/bin/env python3
"""
123_impacto_criterio_ambito.py — coste CERO: leer las razones ya guardadas.

CONTEXTO
El prompt canonico define el nivel 1 como "tema correcto, OTRO ALCANCE", y
enumera: "otra comunidad, otro municipio, otro pais, otro periodo, o el desglose".
Es decir: el juez YA trataba "otra comunidad autonoma" como nivel 1.

El hallazgo de la Fase C (docs/FASE-C-PASO1-HALLAZGO.md) dice que eso es
incorrecto para este catalogo: la version de otra comunidad SI responde, porque
datos.gob.es es mayoritariamente autonomico.

PREGUNTA QUE RESPONDE ESTE SCRIPT
Si se cambia el criterio (nivel 1 solo para ambito INCOMPATIBLE, no para otra
comunidad), ¿cuantas de las 225 etiquetas de nivel 1 existentes cambiarian?

Se puede estimar SIN gastar una sola llamada al LLM: la razon de cada juicio esta
guardada en `detalle`. Basta con clasificar las razones.

LIMITACION (declarada)
Clasificar por palabras clave de la razon es una APROXIMACION. El juez a veces
menciona "otra comunidad" como un comentario lateral y a veces es el motivo real.
El numero que sale es una COTA, no una medida exacta. Para medirlo de verdad
habria que rejuzgar la muestra.
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ENTREG = Path(__file__).resolve().parent.parent / "entregables"
ETIQ = ENTREG / "gt_etiquetas_v2.json"

# patrones de ambito TERRITORIAL (los que el nuevo criterio convertiria en 2)
TERRITORIAL = [
    r"comunidad(es)? autonoma", r"otra comunidad", r"autonomic",
    r"otro municipio", r"municipal(es)? especific", r"otra provincia",
    r"provincial", r"andaluc", r"catalu", r"madrid", r"pais vasco", r"euskadi",
    r"galicia", r"valencia", r"navarra", r"aragon", r"castilla", r"extremadura",
    r"canarias", r"baleares", r"asturias", r"cantabria", r"murcia", r"rioja",
    r"otro territorio", r"ambito territorial", r"territorio especific",
    r"otro pais", r"internacional", r"europe", r"un municipio",
]
# patrones de ambito NO territorial (el nuevo criterio los mantiene en 1)
NO_TERRITORIAL = [
    r"periodo", r"a[nñ]o", r"fecha", r"temporal", r"serie historica",
    r"por sexo", r"por edad", r"desglose", r"desagregac", r"grupo de edad",
    r"otro nivel de detalle", r"otro fenomeno relacionado",
]


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def clasifica(razon):
    t = norm(razon)
    ter = [p for p in TERRITORIAL if re.search(p, t)]
    noter = [p for p in NO_TERRITORIAL if re.search(p, t)]
    if ter and not noter:
        return "territorial"
    if noter and not ter:
        return "no_territorial"
    if ter and noter:
        return "mixta"
    return "sin_pista"


def main():
    doc = json.loads(ETIQ.read_text(encoding="utf-8"))
    etiq, det = doc["etiquetas"], doc.get("detalle", {})

    niveles = Counter(etiq.values())
    print("=" * 78)
    print("IMPACTO DEL CAMBIO DE CRITERIO DE AMBITO (analisis de coste cero)")
    print("=" * 78)
    print(f"\n  etiquetas totales: {len(etiq)}")
    print(f"  distribucion     : {dict(sorted(niveles.items()))}")

    nivel1 = {k: v for k, v in etiq.items() if v == 1}
    print(f"\n  etiquetas de NIVEL 1 (las que el criterio nuevo revisaria): {len(nivel1)}")

    if not det:
        print("\n  ** no hay campo `detalle`: no se pueden leer las razones **")
        return 1

    sin_razon = [k for k in nivel1 if not str(det.get(k, {}).get("razon", "")).strip()]
    con_razon = [k for k in nivel1 if str(det.get(k, {}).get("razon", "")).strip()]
    print(f"  de ellas, con razon guardada: {len(con_razon)}  (sin razon: {len(sin_razon)})")

    clases = Counter()
    ejemplos = {}
    for k in con_razon:
        r = det[k]["razon"]
        c = clasifica(r)
        clases[c] += 1
        ejemplos.setdefault(c, []).append((k, r))

    print(f"\n### CLASIFICACION DE LAS RAZONES (nivel 1) ###\n")
    for c, n in clases.most_common():
        pct = 100 * n / len(con_razon) if con_razon else 0
        print(f"  {c:18} {n:>4}  ({pct:4.1f} %)")

    for c in ("territorial", "mixta", "sin_pista"):
        if ejemplos.get(c):
            print(f"\n  --- ejemplos de '{c}' ---")
            for k, r in ejemplos[c][:4]:
                print(f"     [{k.split('|')[0]:12}] {r[:88]}")

    ter = clases["territorial"]
    mix = clases["mixta"]
    print(f"\n### ESTIMACION DEL IMPACTO ###\n")
    print(f"  Cambiarian a nivel 2 (ambito territorial, no incompatible):")
    print(f"     con certeza  : {ter:>4}  ({100*ter/len(nivel1):4.1f} % del nivel 1)")
    print(f"     en el limite : {mix:>4}  (mixtas: mencionan territorio Y otra cosa)")
    print(f"     cota superior: {ter + mix:>4}  ({100*(ter+mix)/len(nivel1):4.1f} % del nivel 1)")
    print(f"\n  Sobre el GT completo ({len(etiq)} etiquetas):")
    print(f"     {100*ter/len(etiq):4.1f} % a {100*(ter+mix)/len(etiq):4.1f} % de las etiquetas cambiarian de nivel")

    print(f"\n### CONSECUENCIA ###\n")
    print(f"  Las etiquetas existentes NO son comparables con las nuevas si se cambia")
    print(f"  el criterio y no se rejuzgan. Las opciones:")
    print(f"    A) Rejuzgar las {len(nivel1)} de nivel 1 con el criterio nuevo (~{len(nivel1)//10+1} llamadas).")
    print(f"    B) Dejar las viejas con el criterio viejo y declarar la incomparabilidad.")
    print(f"    C) Adoptar el criterio nuevo SOLO para las consultas nuevas, con la")
    print(f"       consulta escrita de forma que la ambiguedad no exista.")
    print(f"  El criterio nuevo es el CORRECTO para este catalogo (medido), asi que")
    print(f"  dejarlo sin aplicar mantiene el sesgo contra el catalogo autonomico.")

    salida = {
        "total_etiquetas": len(etiq), "nivel1": len(nivel1),
        "con_razon": len(con_razon), "sin_razon": len(sin_razon),
        "clases": dict(clases),
        "cambiarian_con_certeza": ter, "mixtas": mix,
        "cota_superior": ter + mix,
        "pct_gt_afectado_min": round(100 * ter / len(etiq), 2),
        "pct_gt_afectado_max": round(100 * (ter + mix) / len(etiq), 2),
    }
    (ENTREG / "impacto_criterio_ambito.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  guardado: {ENTREG / 'impacto_criterio_ambito.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
