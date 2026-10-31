#!/bin/bash
# Script para lanzar Backend V2 + Frontend V2 simultáneamente
# Detecta automáticamente el entorno (venv local, venv del proyecto, o sistema)

set -e

echo "=========================================="
echo "🚀 Lanzando Backend + Frontend V2"
echo "=========================================="

# Directorio base (detecta automáticamente el directorio del script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${BASE_DIR:-$SCRIPT_DIR}"

# Detectar Python y entorno
VENV_PATH=""
PYTHON_CMD="python3"

# 1. Buscar venvs en el proyecto
for venv_dir in "$BASE_DIR/.venv" "$BASE_DIR/venv" "$BASE_DIR/venv_migracion" "$BASE_DIR/venv_dev" "$BASE_DIR/venv_integracion"; do
    if [ -f "$venv_dir/bin/python" ]; then
        VENV_PATH="$venv_dir"
        PYTHON_CMD="$venv_dir/bin/python"
        echo "🐍 Usando venv: $venv_dir"
        break
    fi
done

# 2. Si no hay venv con deps, verificar si python3 del sistema las tiene
if [ -z "$VENV_PATH" ]; then
    if python3 -c "import fastapi, uvicorn, psycopg2, streamlit" 2>/dev/null; then
        echo "🐍 Usando Python del sistema"
        PYTHON_CMD="python3"
    else
        echo "❌ No se encontró un entorno con las dependencias necesarias"
        echo "   Crea un venv o instala: pip install fastapi uvicorn psycopg2-binary streamlit"
        exit 1
    fi
fi

# Verificar que el Python elegido tiene las dependencias
echo "📦 Verificando dependencias con: $PYTHON_CMD"
$PYTHON_CMD -c "
import importlib
modules = ['fastapi', 'uvicorn', 'psycopg2', 'streamlit', 'requests']
missing = []
for m in modules:
    try:
        importlib.import_module(m)
        print(f'   ✅ {m}')
    except ImportError:
        missing.append(m)
        print(f'   ❌ {m}')

if missing:
    print(f'\n❌ Dependencias faltantes: {', '.join(missing)}')
    print('   Instala con: pip install ' + ' '.join(missing))
    exit(1)
" || exit 1

# Función para verificar si un puerto está libre
check_port() {
    local port=$1
    if command -v netstat >/dev/null 2>&1; then
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            echo "❌ Puerto $port ya está en uso"
            return 1
        fi
    elif command -v ss >/dev/null 2>&1; then
        if ss -tuln 2>/dev/null | grep -q ":$port "; then
            echo "❌ Puerto $port ya está en uso"
            return 1
        fi
    fi
    return 0
}

# Verificar dependencias (ya verificadas arriba, solo mostrar resumen)
echo "📦 Verificando dependencias..."
$PYTHON_CMD -c "
import importlib
modules = ['fastapi', 'uvicorn', 'psycopg2', 'streamlit', 'requests']
for m in modules:
    try:
        importlib.import_module(m)
        print(f'   ✅ {m}')
    except ImportError:
        print(f'   ❌ {m}')
        exit(1)
" || exit 1

# Verificar PostgreSQL
echo "🗄️  Verificando PostgreSQL..."
$PYTHON_CMD -c "
import psycopg2
try:
    conn = psycopg2.connect(host='localhost', port=5432, database='buscador', user='postgres', password='postgres')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM datasets')
    count = cur.fetchone()[0]
    print(f'   ✅ PostgreSQL OK - {count} datasets')
    conn.close()
except Exception as e:
    print(f'   ❌ Error PostgreSQL: {e}')
    exit(1)
" || exit 1

# Verificar puertos
echo "🔌 Verificando puertos..."
check_port 8000 || exit 1
check_port 8501 || exit 1

# Función para lanzar backend
launch_backend() {
    echo "🌐 Lanzando Backend API V2..."
    cd "$BASE_DIR/api"
    export PYTHONPATH="$BASE_DIR:$PYTHONPATH"
    
    # Detectar si estamos en un venv o no
    if [ -n "$VENV_PATH" ]; then
        UVICORN_CMD="$VENV_PATH/bin/uvicorn"
    else
        UVICORN_CMD="$PYTHON_CMD -m uvicorn"
    fi
    
    # Lanzar en background
    $UVICORN_CMD main_v2:app \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info &
    
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/backend_v2.pid
    echo "   PID: $BACKEND_PID"
    
    # Esperar a que esté listo
    sleep 3
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ Backend listo en http://localhost:8000"
    else
        echo "   ⚠️  Backend iniciando..."
    fi
}

# Función para lanzar frontend
launch_frontend() {
    echo "🎨 Lanzando Frontend V2..."
    cd "$BASE_DIR/frontend_v2"
    export PYTHONPATH="$BASE_DIR:$PYTHONPATH"
    
    # Detectar si estamos en un venv o no
    if [ -n "$VENV_PATH" ]; then
        STREAMLIT_CMD="$VENV_PATH/bin/streamlit"
    else
        STREAMLIT_CMD="$PYTHON_CMD -m streamlit"
    fi
    
    # Lanzar en background
    $STREAMLIT_CMD run app.py \
        --server.port 8501 \
        --server.address 0.0.0.0 \
        --theme.base light \
        --theme.primaryColor "#667eea" \
        --theme.backgroundColor "#ffffff" \
        --theme.secondaryBackgroundColor "#f8f9fa" \
        --theme.textColor "#1a1a1a" &
    
    FRONTEND_PID=$!
    echo $FRONTEND_PID > /tmp/frontend_v2.pid
    echo "   PID: $FRONTEND_PID"
    
    sleep 2
    echo "   ✅ Frontend listo en http://localhost:8501"
}

# Lanzar servicios
launch_backend
launch_frontend

echo ""
echo "=========================================="
echo "✅ Servicios lanzados correctamente!"
echo "=========================================="
echo ""
echo "📡 Backend API:  http://localhost:8000"
echo "   - Health:     http://localhost:8000/health"
echo "   - Docs:       http://localhost:8000/docs"
echo ""
echo "🎨 Frontend V2:  http://localhost:8501"
echo ""
echo "🛑 Para detener:"
echo "   ./stop_backend_frontend_v2.sh"
echo ""
echo "=========================================="

# Mantener script corriendo para no matar los procesos hijos
echo "Presiona Ctrl+C para detener ambos servicios..."
wait
