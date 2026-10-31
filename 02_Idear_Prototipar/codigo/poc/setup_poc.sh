#!/bin/bash
# Setup script para el POC de DatasetSeeker
# Uso: bash setup_poc.sh

set -e

echo "🚀 Configurando entorno para DatasetSeeker POC..."

# Verificar Python 3.11
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Error: Python 3.11 no está instalado"
    echo "Instálalo con: sudo apt install python3.11 python3.11-venv"
    exit 1
fi

echo "✓ Python 3.11 encontrado"

# Crear entorno virtual con Python 3.11
if [ ! -d "venv_poc" ]; then
    echo "📦 Creando entorno virtual venv_poc..."
    python3.11 -m venv venv_poc
fi

# Activar entorno
echo "🔄 Activando entorno virtual..."
source venv_poc/bin/activate

# Verificar versión
PYTHON_VERSION=$(python --version)
echo "✓ Entorno activado: $PYTHON_VERSION"

# Instalar dependencias
echo "📥 Instalando dependencias..."
pip install --upgrade pip
pip install sentence-transformers==2.7.0 transformers==4.41.0 torch==2.3.0 numpy scipy scikit-learn streamlit

echo ""
echo "✅ Entorno configurado correctamente"
echo ""
echo "Para ejecutar el POC:"
echo "  source venv_poc/bin/activate"
echo "  python utils/search_semantic.py  # Generar embeddings"
echo "  streamlit run app_v2.py            # Iniciar app"
