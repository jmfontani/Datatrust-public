#!/usr/bin/env python3
"""
Generar muestra representativa estratificada de datasets.

Estratificación:
    - theme (tema principal)
    - description_length_bucket (corta | media | larga)

Uso:
    python generar_muestra_representativa.py --size 2000 --table dataset_sample_2k
"""

import argparse
import sys
import os
import psycopg2
from pathlib import Path


DB_CONFIG = {
    "host": "172.17.0.1",
    "port": 5432,
    "database": "buscador",
    "user": "postgres",
    "password": "postgres"
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def ensure_sample_table(conn, table_name: str):
    """Crea tabla de muestra si no existe."""
    with conn.cursor() as cur:
        cur.execute(f"""
            DROP TABLE IF EXISTS {table_name};
            CREATE TABLE {table_name} (
                dataset_id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                theme TEXT,
                theme_label TEXT,
                territory TEXT,
                format TEXT,
                description_length_bucket TEXT,
                sampled_at TIMESTAMP DEFAULT NOW()
            );
        """)
    conn.commit()


def populate_sample(conn, table_name: str, target_size: int):
    """
    Extrae muestra estratificada.
    Estrategia: repartir cuotas proporcionales por theme, y dentro de cada theme
    estratificar por longitud de descripción.
    """
    with conn.cursor() as cur:
        # Total y frecuencia por tema
        cur.execute("""
            SELECT theme, COUNT(*) AS n
            FROM datasets
            WHERE theme IS NOT NULL AND theme != ''
            GROUP BY theme
            ORDER BY n DESC;
        """)
        theme_counts = cur.fetchall()

        total_valid = sum(n for _, n in theme_counts)

        print(f"📊 Datasets con tema válido: {total_valid}")
        print(f"📊 Temas distintos: {len(theme_counts)}")
        print(f"🎯 Tamaño objetivo de muestra: {target_size}")

        # 1) Cuotas proporcionales redondeadas, mínimo 1 por tema
        quotas = []
        for theme, n in theme_counts:
            quota = max(1, round(target_size * n / total_valid))
            quotas.append((theme, quota))

        # 2) Ajustar exactamente al tamaño objetivo recortando los temas más grandes
        total_quota = sum(q for _, q in quotas)
        if total_quota > target_size:
            # Ordenar por cuota descendente para recortar de los más grandes
            quotas.sort(key=lambda x: x[1], reverse=True)
            excess = total_quota - target_size
            idx = 0
            while excess > 0:
                theme, q = quotas[idx % len(quotas)]
                if q > 1:
                    quotas[idx % len(quotas)] = (theme, q - 1)
                    excess -= 1
                idx += 1

        inserted = 0
        for theme, quota in quotas:
            if quota <= 0:
                continue

            cur.execute(f"""
                INSERT INTO {table_name} (
                    dataset_id, title, description, theme, theme_label,
                    territory, format, description_length_bucket
                )
                SELECT
                    dataset_id,
                    title,
                    description,
                    theme,
                    theme_label,
                    territory,
                    format,
                    CASE
                        WHEN LENGTH(COALESCE(description, '')) < 200 THEN 'corta'
                        WHEN LENGTH(COALESCE(description, '')) < 600 THEN 'media'
                        ELSE 'larga'
                    END AS description_length_bucket
                FROM datasets
                WHERE theme = %s
                ORDER BY
                    CASE
                        WHEN LENGTH(COALESCE(description, '')) < 200 THEN 3
                        WHEN LENGTH(COALESCE(description, '')) < 600 THEN 2
                        ELSE 1
                    END,
                    random()
                LIMIT %s;
            """, (theme, quota))

            inserted += cur.rowcount

        conn.commit()
        print(f"✅ Insertados {inserted} datasets en `{table_name}`")


def verify_representativeness(conn, table_name: str):
    """Compara distribución de la muestra vs población."""
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT
                COALESCE(d.theme, 'SIN_TEMA') AS theme,
                COUNT(d.dataset_id) AS total,
                COUNT(s.dataset_id) AS en_muestra,
                ROUND(100.0 * COUNT(s.dataset_id) / NULLIF(COUNT(d.dataset_id), 0), 2) AS pct
            FROM datasets d
            LEFT JOIN {table_name} s USING (dataset_id)
            GROUP BY d.theme
            ORDER BY total DESC;
        """)
        rows = cur.fetchall()

    print("\n📊 Verificación de representatividad (top 15 temas):")
    print(f"{'Tema':<40} {'Total':>8} {'Muestra':>8} {'%':>6}")
    print("-" * 65)
    for theme, total, muestra, pct in rows[:15]:
        print(f"{theme[:39]:<40} {total:>8} {muestra:>8} {pct:>6}")

    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT description_length_bucket, COUNT(*)
            FROM {table_name}
            GROUP BY description_length_bucket
            ORDER BY COUNT(*) DESC;
        """)
        buckets = cur.fetchall()

    print("\n📊 Distribución por longitud de descripción:")
    for bucket, n in buckets:
        print(f"  {bucket}: {n}")


def main():
    parser = argparse.ArgumentParser(description="Generar muestra representativa de datasets")
    parser.add_argument("--size", type=int, default=2000, help="Tamaño de la muestra")
    parser.add_argument("--table", type=str, default="dataset_sample_2k", help="Nombre de la tabla destino")
    args = parser.parse_args()

    conn = get_db_connection()
    print(f"🎯 Generando muestra representativa de {args.size} datasets en tabla `{args.table}`...")

    ensure_sample_table(conn, args.table)
    populate_sample(conn, args.table, args.size)
    verify_representativeness(conn, args.table)

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {args.table}")
        final_size = cur.fetchone()[0]

    conn.close()
    print(f"\n✅ Muestra final: {final_size} datasets en `{args.table}`")


if __name__ == "__main__":
    main()
