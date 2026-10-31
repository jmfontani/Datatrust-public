#!/usr/bin/env python3
"""
Script de benchmark para evaluar búsqueda de datasets en datos.gob.es
Genera queries de prueba y permite registrar resultados manuales.

Uso:
    python benchmark_queries.py --user tu_nombre --num 10
    python benchmark_queries.py --export resultados.csv

Equipo: Buscador Semántico de Datasets Públicos (PFM)
Fecha: Junio 2026
"""

import json
import csv
import argparse
from datetime import datetime
from pathlib import Path

# Queries de benchmark predefinidas
BENCHMARK_QUERIES = {
    "faciles": [
        {"id": "Q001", "query": "población por municipio", "categoria": "Demografía", "dataset_esperado": "Censo INE"},
        {"id": "Q002", "query": "calidad del aire Madrid", "categoria": "Medio ambiente", "dataset_esperado": "Estaciones contaminación"},
        {"id": "Q003", "query": "paro por provincia", "categoria": "Economía", "dataset_esperado": "EPA, paro registado"},
        {"id": "Q004", "query": "hospitales públicos España", "categoria": "Salud", "dataset_esperado": "Catálogo centros sanitarios"},
        {"id": "Q005", "query": "precio vivienda 2024", "categoria": "Vivienda", "dataset_esperado": "Índice precio vivienda"},
    ],
    "medias": [
        {"id": "Q010", "query": "¿Por qué se están vaciando los pueblos?", "categoria": "Despoblación", "dataset_esperado": "Censo, movimiento natural, migraciones"},
        {"id": "Q011", "query": "datos para estudiar el impacto del turismo", "categoria": "Turismo", "dataset_esperado": "Turistas por CCAA, alojamientos"},
        {"id": "Q012", "query": "información sobre desigualdad educativa", "categoria": "Educación", "dataset_esperado": "Tasa escolarización, repetición"},
        {"id": "Q013", "query": "datasets sobre cambio climático en España", "categoria": "Clima", "dataset_esperado": "Temperaturas, emisiones CO2"},
        {"id": "Q014", "query": "datos de movilidad urbana", "categoria": "Transporte", "dataset_esperado": "Transporte público, tráfico"},
    ],
    "dificiles": [
        {"id": "Q020", "query": "relación entre renta y esperanza de vida", "categoria": "Salud/Social", "dataset_esperado": "Renta por hogar, mortalidad"},
        {"id": "Q021", "query": "impacto de las renovables en el empleo rural", "categoria": "Energía/Empleo", "dataset_esperado": "Instalaciones renovables, empleo"},
        {"id": "Q022", "query": "patrones de consumo y obesidad infantil", "categoria": "Salud/Consumo", "dataset_esperado": "Encuesta hogar, prevalencia obesidad"},
        {"id": "Q023", "query": "eficiencia del gasto sanitario por CCAA", "categoria": "Salud/Economía", "dataset_esperado": "Gasto sanitario, indicadores"},
        {"id": "Q024", "query": "vulnerabilidad al cambio climático por región", "categoria": "Clima/Social", "dataset_esperado": "Variables climáticas, socioeconómicas"},
    ],
    "lenguaje_natural": [
        {"id": "Q030", "query": "Necesito datos para mi tesis sobre despoblación", "categoria": "Despoblación", "dataset_esperado": "Censo, movimiento natural"},
        {"id": "Q031", "query": "¿Qué datasets hay sobre contaminación acústica?", "categoria": "Medio ambiente", "dataset_esperado": "Mapas estratégicos ruido"},
        {"id": "Q032", "query": "Busco información de tráfico en Barcelona", "categoria": "Transporte", "dataset_esperado": "Tráfico urbano Barcelona"},
        {"id": "Q033", "query": "Datos de mortalidad por causas en España", "categoria": "Salud", "dataset_esperado": "Defunciones por causa"},
        {"id": "Q034", "query": "Información sobre ayudas al alquiler", "categoria": "Vivienda/Social", "dataset_esperado": "Ayudas vivienda, alquiler"},
    ]
}


def get_random_queries(num: int, dificultad: str = None) -> list:
    """Obtiene N queries aleatorias del benchmark."""
    import random
    
    todas = []
    if dificultad and dificultad in BENCHMARK_QUERIES:
        todas = BENCHMARK_QUERIES[dificultad]
    else:
        for categoria in BENCHMARK_QUERIES.values():
            todas.extend(categoria)
    
    random.shuffle(todas)
    return todas[:min(num, len(todas))]


def ejecutar_busqueda_manual(queries: list, usuario: str) -> list:
    """
    Ejecuta búsqueda manual interactiva.
    El usuario busca en datos.gob.es y registra resultados.
    """
    resultados = []
    
    print(f"\n{'='*60}")
    print(f"BENCHMARK DE BÚSQUEDA - Usuario: {usuario}")
    print(f"{'='*60}")
    print("\nInstrucciones:")
    print("1. Ve a datos.gob.es")
    print("2. Busca cada query con su terminología")
    print("3. Registra tiempo y resultados")
    print(f"{'='*60}\n")
    
    for q in queries:
        print(f"\n{'─'*60}")
        print(f"Query [{q['id']}]: {q['query']}")
        print(f"Categoría: {q['categoria']}")
        print(f"Dataset esperado: {q['dataset_esperado']}")
        print(f"{'─'*60}")
        
        # Entrada manual del usuario
        try:
            tiempo = input("Tiempo hasta primer resultado relevante (min): ")
            resultados_count = input("Nº de resultados relevantes en top 5: ")
            encontrado = input("¿Encontraste el dataset esperado? (s/n/p): ")
            frustracion = input("Nivel de frustración (1-5): ")
            notas = input("Notas adicionales (opcional): ")
            
            resultados.append({
                "query_id": q['id'],
                "query": q['query'],
                "categoria": q['categoria'],
                "dataset_esperado": q['dataset_esperado'],
                "tiempo_min": tiempo,
                "resultados_relevantes": resultados_count,
                "encontrado": encontrado,
                "frustracion": frustracion,
                "notas": notas,
                "usuario": usuario,
                "timestamp": datetime.now().isoformat()
            })
        except KeyboardInterrupt:
            print("\n\nBúsqueda interrumpida. Guardando resultados parciales...")
            break
    
    return resultados


def exportar_csv(resultados: list, archivo: str):
    """Exporta resultados a CSV."""
    if not resultados:
        print("No hay resultados para exportar.")
        return
    
    path = Path(archivo)
    existe = path.exists()
    
    with open(path, 'a' if existe else 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=resultados[0].keys())
        if not existe:
            writer.writeheader()
        writer.writerows(resultados)
    
    print(f"\n✅ {len(resultados)} resultados guardados en {archivo}")


def generar_informe(archivo_csv: str):
    """Genera informe resumen del benchmark."""
    resultados = []
    with open(archivo_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        resultados = list(reader)
    
    if not resultados:
        print("No hay datos para generar informe.")
        return
    
    print(f"\n{'='*60}")
    print(f"INFORME DE BENCHMARK")
    print(f"{'='*60}")
    print(f"Total queries evaluadas: {len(resultados)}")
    print(f"Usuarios participantes: {len(set(r['usuario'] for r in resultados))}")
    
    # Métricas agregadas
    tiempos = [float(r['tiempo_min']) for r in resultados if r['tiempo_min']]
    if tiempos:
        print(f"\nTiempo promedio: {sum(tiempos)/len(tiempos):.1f} min")
        print(f"Tiempo máximo: {max(tiempos):.1f} min")
        print(f"Tiempo mínimo: {min(tiempos):.1f} min")
    
    # Tasa de éxito
    exitos = sum(1 for r in resultados if r['encontrado'].lower() == 's')
    print(f"\nTasa de éxito: {exitos}/{len(resultados)} ({exitos/len(resultados)*100:.0f}%)")
    
    # Frustración promedio
    frustraciones = [int(r['frustracion']) for r in resultados if r['frustracion'].isdigit()]
    if frustraciones:
        print(f"Frustración promedio: {sum(frustraciones)/len(frustraciones):.1f}/5")


def main():
    parser = argparse.ArgumentParser(description='Benchmark de búsqueda de datasets')
    parser.add_argument('--user', '-u', default='anonimo', help='Nombre del evaluador')
    parser.add_argument('--num', '-n', type=int, default=10, help='Número de queries a evaluar')
    parser.add_argument('--dificultad', '-d', choices=['faciles', 'medias', 'dificiles', 'lenguaje_natural'], 
                        help='Filtrar por dificultad')
    parser.add_argument('--export', '-e', default='benchmark_resultados.csv', help='Archivo CSV de salida')
    parser.add_argument('--informe', '-i', help='Generar informe desde CSV existente')
    
    args = parser.parse_args()
    
    if args.informe:
        generar_informe(args.informe)
        return
    
    # Obtener queries
    queries = get_random_queries(args.num, args.dificultad)
    print(f"\n🎯 Seleccionadas {len(queries)} queries de benchmark")
    
    # Ejecutar búsqueda manual
    resultados = ejecutar_busqueda_manual(queries, args.user)
    
    if resultados:
        exportar_csv(resultados, args.export)
        print(f"\n📊 Ejecuta: python benchmark_queries.py --informe {args.export}")


if __name__ == '__main__':
    main()
