#!/bin/bash
#
# Script para lanzar el frontend de Query Enhanced
# Fase 08: Sprint 6 - Query Preprocessor
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"

echo "🔍 Query Preprocessor - Frontend"
echo "=================================="

# Verificar entorno virtual
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Entorno virtual no encontrado: $VENV_DIR"
    echo "   Crea el entorno virtual primero"
    exit 1
fi

echo "✅ Entorno virtual encontrado"

# Activar entorno
source "$VENV_DIR/bin/activate"
echo "✅ Entorno activado"

# Verificar dependencias
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "⚠️  Streamlit no instalado. Instalando..."
    pip install streamlit -q
fi

echo "✅ Dependencias verificadas"

# Puerto
PORT=${1:-8503}

echo ""
echo "🚀 Lanzando Streamlit en puerto $PORT..."
echo ""
echo "   URL: http://localhost:$PORT"
echo ""
echo "   Presiona Ctrl+C para detener"
echo ""

# Lanzar
cd "$SCRIPT_DIR"
streamlit run app_query_enhanced.py --server.port $PORT "$@"
