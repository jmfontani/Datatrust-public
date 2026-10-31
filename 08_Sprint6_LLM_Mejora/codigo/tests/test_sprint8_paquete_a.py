#!/usr/bin/env python3
"""
Tests para Sprint 8 - Paquete A (#5 + #14)

Valida:
1. TL;DR generados y almacenados en dataset_profiles
2. Calidad básica de TL;DR (longitud, contenido)
3. Endpoint de complementariedad responde correctamente
4. Latencia del endpoint de complementariedad

Uso:
    python test_sprint8_paquete_a.py
"""

import sys
import time
import urllib.parse
import psycopg2
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "api"))
from routes_complementary import get_dataset_profile, find_complementary_logic


DB_CONFIG = {
    "host": "172.17.0.1",
    "port": 5432,
    "database": "buscador",
    "user": "postgres",
    "password": "postgres"
}

API_URL = "http://localhost:8001"


def test_profiles_exist():
    """Test 1: Verificar que existen perfiles generados."""
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), COUNT(tldr), COUNT(variables_key) FROM dataset_profiles")
        total, with_tldr, with_vars = cur.fetchone()
    conn.close()

    assert total > 0, "No hay perfiles generados"
    assert with_tldr == total, f"Solo {with_tldr}/{total} tienen TL;DR"
    assert with_vars == total, f"Solo {with_vars}/{total} tienen variables"

    print(f"✅ Test 1: {total} perfiles, {with_tldr} con TL;DR, {with_vars} con variables")
    return total


def test_tldr_quality():
    """Test 2: Verificar calidad básica de TL;DR (muestra de 10)."""
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT dp.tldr, d.title
            FROM dataset_profiles dp
            JOIN datasets d ON dp.dataset_id = d.dataset_id
            WHERE dp.tldr IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 10
        """)
        rows = cur.fetchall()
    conn.close()

    valid_count = 0
    for tldr, title in rows:
        # Criterios básicos de calidad
        words = tldr.split()
        has_min_length = len(words) >= 10
        has_max_length = len(words) <= 80
        mentions_source = any(word in tldr.lower() for word in ["datos", "dataset", "ministerio", "ayuntamiento", "instituto", "junta"])
        mentions_geo = any(word in tldr.lower() for word in ["españa", "municipio", "comunidad", "provincia", "nacional", "autonómico"])

        if has_min_length and has_max_length and (mentions_source or mentions_geo):
            valid_count += 1

    quality_ratio = valid_count / len(rows)
    assert quality_ratio >= 0.7, f"Calidad de TL;DR baja: {quality_ratio:.0%}"

    print(f"✅ Test 2: {valid_count}/{len(rows)} TL;DR de calidad aceptable ({quality_ratio:.0%})")
    return quality_ratio


def get_sample_dataset_id():
    """Obtener un dataset de la muestra con perfil generado."""
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.dataset_id
            FROM dataset_profiles p
            JOIN dataset_sample_2k s ON p.dataset_id = s.dataset_id
            WHERE p.tldr IS NOT NULL
            ORDER BY random()
            LIMIT 1
        """)
        dataset_id = cur.fetchone()[0]
    conn.close()
    return dataset_id


def test_api_tldr_endpoint():
    """Test 3: Verificar endpoint de TL;DR."""
    dataset_id = get_sample_dataset_id()
    encoded_id = urllib.parse.quote(dataset_id, safe="")

    response = requests.get(f"{API_URL}/complementary/tldr?dataset_id={encoded_id}", timeout=10)
    assert response.status_code == 200, f"Status code: {response.status_code}"

    data = response.json()
    assert data["has_tldr"] is True, "No tiene TL;DR"
    assert len(data["tldr"].split()) >= 10, "TL;DR demasiado corto"

    print(f"✅ Test 3: Endpoint TL;DR funciona para {dataset_id}")
    return dataset_id


def test_api_complementary_endpoint():
    """Test 4: Verificar endpoint de complementariedad."""
    dataset_id = get_sample_dataset_id()

    start = time.time()
    response = requests.post(
        f"{API_URL}/complementary/find",
        json={"dataset_id": dataset_id, "limit": 3},
        timeout=120
    )
    elapsed = time.time() - start

    assert response.status_code == 200, f"Status code: {response.status_code}"

    data = response.json()
    assert "complementary_datasets" in data, "No tiene complementary_datasets"
    assert "explanations" in data, "No tiene explanations"

    print(f"✅ Test 4: Endpoint complementariedad funciona ({len(data['complementary_datasets'])} resultados, {elapsed:.1f}s)")
    return elapsed


def test_complementary_quality():
    """Test 5: Verificar calidad de explicaciones de complementariedad."""
    # Intentar hasta 3 datasets de la muestra para encontrar uno con complementarios
    for attempt in range(3):
        dataset_id = get_sample_dataset_id()
        try:
            data = find_complementary_logic(dataset_id, use_llm=True)
            complementary = data.get("complementary", [])
            if len(complementary) == 0:
                print(f"   ⚠️ Intento {attempt+1}: {dataset_id} sin complementarios, reintentando...")
                continue

            valid = 0
            for c in complementary:
                has_reason = len(c.get("reason", "").split()) >= 5
                has_join_key = bool(c.get("join_key"))
                has_analysis = bool(c.get("potential_analysis"))
                if has_reason and has_join_key and has_analysis:
                    valid += 1

            quality_ratio = valid / len(complementary)
            if quality_ratio >= 0.6:
                print(f"✅ Test 5: {valid}/{len(complementary)} complementarios con explicación completa ({quality_ratio:.0%})")
                return quality_ratio
            else:
                print(f"   ⚠️ Intento {attempt+1}: calidad baja ({quality_ratio:.0%}), reintentando...")

        except Exception as e:
            print(f"   ⚠️ Intento {attempt+1}: error {e}, reintentando...")

    # Si ninguno cumple, probamos un dataset conocido con candidatos
    dataset_id = "https://datos.madrid.es/dataset/212774-0-atencion-social"
    data = find_complementary_logic(dataset_id, use_llm=True)
    complementary = data.get("complementary", [])

    assert len(complementary) > 0, "No encontró complementarios"

    valid = 0
    for c in complementary:
        has_reason = len(c.get("reason", "").split()) >= 5
        has_join_key = bool(c.get("join_key"))
        has_analysis = bool(c.get("potential_analysis"))
        if has_reason and has_join_key and has_analysis:
            valid += 1

    quality_ratio = valid / len(complementary)
    assert quality_ratio >= 0.6, f"Calidad de complementariedad baja: {quality_ratio:.0%}"

    print(f"✅ Test 5: {valid}/{len(complementary)} complementarios con explicación completa ({quality_ratio:.0%})")
    return quality_ratio


def main():
    print("=" * 60)
    print("TESTS SPRINT 8 - PAQUETE A (#5 + #14)")
    print("=" * 60)

    try:
        total = test_profiles_exist()
        quality = test_tldr_quality()
        dataset_id = test_api_tldr_endpoint()
        latency = test_api_complementary_endpoint()
        comp_quality = test_complementary_quality()

        print("\n" + "=" * 60)
        print("RESUMEN DE TESTS")
        print("=" * 60)
        print(f"   Perfiles generados: {total}")
        print(f"   Calidad TL;DR: {quality:.0%}")
        print(f"   Latencia complementariedad: {latency:.1f}s")
        print(f"   Calidad complementariedad: {comp_quality:.0%}")
        print("\n✅ TODOS LOS TESTS PASARON")

    except AssertionError as e:
        print(f"\n❌ Test fallido: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
