#!/bin/bash
# Setup automatizado para Fase 07: Integración y Despliegue
# Uso: ./setup.sh [--no-docker] [--verify-only]

set -e  # Exit on error

echo "=========================================="
echo "Setup Fase 07: Integración y Despliegue"
echo "=========================================="

# Parse arguments
USE_DOCKER=true
VERIFY_ONLY=false

for arg in "$@"; do
    case $arg in
        --no-docker)
            USE_DOCKER=false
            shift
            ;;
        --verify-only)
            VERIFY_ONLY=true
            shift
            ;;
    esac
done

# Detect Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "❌ Python no encontrado. Instálalo e intenta de nuevo."
    exit 1
fi

echo "✅ Python: $PYTHON"

# Crear directorio de trabajo
WORK_DIR="$(pwd)"
DB_DIR="$WORK_DIR/db"

cd "$WORK_DIR"

# Verificar dependencias Python
echo -e "\n📦 Verificando dependencias Python..."
$PYTHON -c "import psycopg2, numpy" 2>/dev/null || {
    echo "⚠️ Instalando dependencias..."
    pip install psycopg2-binary numpy 2>/dev/null || pip3 install psycopg2-binary numpy
}

# Verificar conexión a PostgreSQL
echo -e "\n🗄️ Verificando conexión a PostgreSQL..."
if $PYTHON "$DB_DIR/migrate_from_numpy.py" --verify-only; then
    echo "✅ PostgreSQL conectado"
else
    echo "❌ No se pudo conectar a PostgreSQL"
    echo "   Asegúrate de que PostgreSQL esté corriendo en localhost:5432"
    echo "   y que la base de datos 'buscador' exista."
    exit 1
fi

if [ "$VERIFY_ONLY" = true ]; then
    echo -e "\n✅ Verificación completada"
    exit 0
fi

# Inicializar schema
echo -e "\n🔄 Inicializando schema PostgreSQL..."
export PGPASSWORD=postgres
psql -h localhost -p 5432 -U postgres -d buscador -f "$DB_DIR/init.sql" || {
    echo "⚠️ Error ejecutando init.sql (puede que ya exista el schema)"
}

# Migrar datos
echo -e "\n🔄 Migrando datos desde NumPy a PostgreSQL..."
$PYTHON "$DB_DIR/migrate_from_numpy.py" "$@"

echo -e "\n=========================================="
echo "✅ Setup completado exitosamente!"
echo "=========================================="
echo -e "\nServicios disponibles:"
echo "  - PostgreSQL: localhost:5432"
echo "  - API REST:   http://localhost:8000"
echo "  - Frontend:   http://localhost:8501"
echo -e "\nPara iniciar la aplicación:"
echo "  API:     cd api && ./launch_dev.sh"
echo "  Frontend: cd frontend && streamlit run app.py"
