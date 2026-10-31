#!/usr/bin/env python3
"""
Ejemplo de cómo se vería la validación de metadatos en el frontend
Simulación en consola de alertas visuales
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'codigo/validator'))

from metadata_validator import MetadataValidator

# Inicializar validador
validator = MetadataValidator().add_default_rules()

# Dataset con error UEx/Barcelona (usar el mismo que funciona en tests)
dataset_ejemplo = {
    "dataset_id": "datosgob-u00200001",
    "title": "Proyectos Investigación UEx - Portal de Investigación",
    "description": "Proyectos de investigación de la Universidad de Extremadura",
    "publisher": "Universidad de Barcelona",
    "territory": "Cataluña",
    "theme": "investigacion",
    "format": "JSON"
}

print("=" * 70)
print("🔍 SIMULACIÓN DE FRONTEND - Validación de Metadatos")
print("=" * 70)

print("\n📄 DATASET ENCONTRADO:")
print(f"   ID: {dataset_ejemplo['dataset_id']}")
print(f"   Título: {dataset_ejemplo['title']}")
print(f"   Publisher: {dataset_ejemplo['publisher']}")
print(f"   Territorio: {dataset_ejemplo['territory']}")

print("\n" + "=" * 70)
print("⚠️  VALIDANDO METADATOS...")
print("=" * 70)

issues = validator.validate_dataset(dataset_ejemplo)

if issues:
    print(f"\n❌ Se encontraron {len(issues)} problema(s):\n")

    for i, issue in enumerate(issues, 1):
        # Simular badges visuales con colores ANSI
        if issue.severity.value in ['critical', 'error']:
            badge = "🔴 ERROR"
        elif issue.severity.value == 'warning':
            badge = "⚠️  WARNING"
        else:
            badge = "ℹ️  INFO"

        print(f"┌─ {badge} #{i} ─{'─' * 50}")
        print(f"│ Campo: {issue.field}")
        print(f"│")
        print(f"│ {issue.message}")
        print(f"│")
        print(f"│ 💡 {issue.suggestion}")

        # Mostrar contexto si existe
        if issue.context:
            print(f"│")
            print(f"│ 📋 Contexto:")
            for key, value in issue.context.items():
                print(f"│   • {key}: {value}")
        print(f"└{'─' * 68}\n")

    print("🛠️  ACCIÓN RECOMENDADA:")
    print("   Este dataset debería ser revisado antes de ser indexado.")
    print("   Posible causa: Error de federación en metadatos.")

else:
    print("\n✅ Metadatos válidos - Sin problemas detectados")

print("\n" + "=" * 70)

# Mostrar comparación visual
print("\n📊 COMPARACIÓN VISUAL:")
print("\n   ANTES (como aparece actualmente):")
print("   ┌─────────────────────────────────────┐")
print("   │ Portal de investigación de la...    │")
print("   │ Universidad de Extremadura          │")
print("   │                                     │")
print("   │ 📍 Publisher: Universidad de Barcelona│")
print("   │ 🌍 Territorio: Cataluña             │")
print("   └─────────────────────────────────────┘")

print("\n   DESPUÉS (con validación):")
print("   ┌─────────────────────────────────────┐")
print("   │ Portal de investigación de la...    │")
print("   │ Universidad de Extremadura          │")
print("   │                                     │")
print("   │ ⚠️  ADVERTENCIA DE METADATOS        │")
print("   │                                     │")
print("   │ El título menciona 'UEx' pero el    │")
print("   │ publisher es 'Universidad de         │")
print("   │ Barcelona'. ¿Es correcto?            │")
print("   │                                     │")
print("   │ 💡 Sugerencia: Verificar que el     │")
print("   │ publisher corresponda al contenido  │")
print("   └─────────────────────────────────────┘")

print("\n" + "=" * 70)
print("✅ Demo completado")
print("=" * 70)
