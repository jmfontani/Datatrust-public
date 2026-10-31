#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de los índices de la Sprint 2 para generar los facetas
Author: Fonta
"""

import json
import os
from pathlib import Path
from collections import Counter

# Detectar entorno y ajustar ruta base
if Path("/home/node/.openclaw/workspace").exists():
    BASE_DIR = Path("/home/node/.openclaw/workspace/PFM/Datatrust")
else:
    BASE_DIR = Path.home() / "datos/PFM/Datatrust"

INDICES_DIR = BASE_DIR / "04_Sprint2_Embeddings/datos/indices"

def analyze_territories():
    """Analizar los territorios disponibles"""
    print("="*80)
    print("🌍 ANÁLISIS DE TERRITORIOS")
    print("="*80)
    
    with open(INDICES_DIR / "index_territorio.json", "r") as f:
        territorios = json.load(f)
    
    # Los índices son diccionrios: territorio -> lista de IDs
    total_territorios = len(territorios)
    print(f"\nTotal territorios: {total_territorios}")
    
    # Mostrar algunos ejemplos
    print("\nPrimeros 30 territorios:")
    for i, (territorio, ids) in enumerate(sorted(territorios.items())[:30]):
        print(f"  {i+1:3d}. {territorio}: {len(ids)} datasets")
    
    return territorios

def analyze_themes():
    """Analizar los temas disponibles"""
    print("\n" + "="*80)
    print("📚 ANÁLISIS DE TEMAS")
    print("="*80)
    
    with open(INDICES_DIR / "index_tema.json", "r") as f:
        temas = json.load(f)
    
    total_temas = len(temas)
    print(f"\nTotal temas: {total_temas}")
    
    # Mostrar algunos ejemplos
    print("\nPrimeros 30 temas:")
    for i, (tema, ids) in enumerate(sorted(temas.items())[:30]):
        print(f"  {i+1:3d}. {tema}: {len(ids)} datasets")
    
    return temas

def analyze_formats():
    """Analizar los formatos disponibles"""
    print("\n" + "="*80)
    print("📄 ANÁLISIS DE FORMATOS")
    print("="*80)
    
    with open(INDICES_DIR / "index_formato.json", "r") as f:
        formatos = json.load(f)
    
    total_formatos = len(formatos)
    print(f"\nTotal formatos: {total_formatos}")
    
    # Mostrar algunos ejemplos
    print("\nFormatos:")
    for i, (formato, ids) in enumerate(sorted(formatos.items())[:30]):
        print(f"  {i+1:3d}. {formato}: {len(ids)} datasets")
    
    return formatos

def analyze_publishers():
    """Analizar los publishers disponibles"""
    print("\n" + "="*80)
    print("🏛️ ANÁLISIS DE PUBLISHERS")
    print("="*80)
    
    with open(INDICES_DIR / "index_publisher.json", "r") as f:
        publishers = json.load(f)
    
    total_publishers = len(publishers)
    print(f"\nTotal publishers: {total_publishers}")
    
    # Mostrar algunos ejemplos
    print("\nPrimeros 30 publishers:")
    for i, (publisher, ids) in enumerate(sorted(publishers.items())[:30]):
        print(f"  {i+1:3d}. {publisher}: {len(ids)} datasets")
    
    return publishers

def generate_facet_options(territorios, temas, formatos, publishers):
    """Generar las opciones de facetas para el frontend"""
    print("\n" + "="*80)
    print("🔧 GENERANDO OPCIONES DE FACETAS")
    print("="*80)
    
    # Crear estructura de facetas
    facets = {
        "territorios": sorted([{"value": t, "count": len(ids)} for t, ids in territorios.items()], 
                               key=lambda x: x["count"], reverse=True)[:100],  # Top 100
        "temas": sorted([{"value": t, "count": len(ids)} for t, ids in temas.items()], 
                        key=lambda x: x["count"], reverse=True)[:100],
        "formatos": sorted([{"value": f, "count": len(ids)} for f, ids in formatos.items()], 
                           key=lambda x: x["count"], reverse=True)[:50],
        "publishers": sorted([{"value": p, "count": len(ids)} for p, ids in publishers.items()], 
                              key=lambda x: x["count"], reverse=True)[:50]
    }
    
    print(f"\nFacetas generadas:")
    print(f"  - Territorios: {len(facets['territorios'])} (de {len(territorios)})")
    print(f"  - Temas: {len(facets['temas'])} (de {len(temas)})")
    print(f"  - Formatos: {len(facets['formatos'])} (de {len(formatos)})")
    print(f"  - Publishers: {len(facets['publishers'])} (de {len(publishers)})")
    
    # Guardar en JSON
    output_file = BASE_DIR / "05_Sprint3_Busqueda/codigo/frontend/facetas.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(facets, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Facetas guardadas en: {output_file}")
    
    return facets

def main():
    print("🚀 Analizando índices de la Sprint 2...")
    print(f"📂 Directorio: {INDICES_DIR}")
    
    # Verificar que existen los archivos
    if not INDICES_DIR.exists():
        print(f"❌ Error: No existe el directorio {INDICES_DIR}")
        return
    
    territorios = analyze_territories()
    temas = analyze_themes()
    formatos = analyze_formats()
    publishers = analyze_publishers()
    
    facets = generate_facet_options(territorios, temas, formatos, publishers)
    
    print("\n" + "="*80)
    print("✅ ANÁLISIS COMPLETADO")
    print("="*80)
    print("\nAhora puedes usar las facetas en el frontend de Streamlit")
    print(f"Archivo generado: {BASE_DIR / '05_Sprint3_Busqueda/codigo/frontend/facetas.json'}")

if __name__ == "__main__":
    main()
