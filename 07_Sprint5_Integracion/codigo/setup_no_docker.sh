#!/bin/bash
# Setup sin Docker para entornos donde Docker no está disponible
# Requiere: PostgreSQL local con pgvector instalado

echo "=========================================="
echo "Setup Fase 07: Sin Docker"
echo "=========================================="

# Configuración
DB_HOST="${DB_HOST:-172.17.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-buscador}"
DB_USER="${DB_USER:-postgres}"
DB_PASS="${DB_PASS:-postgres}"

echo "Configuración:"
echo "  Host: $DB_HOST:$DB_PORT"
echo "  DB:   $DB_NAME"
echo "  User: $DB_USER"

# Detectar Python
PYTHON=$(which python3 || which python || echo "")
if [ -z "$PYTHON" ]; then
    echo "❌ Python no encontrado"
    exit 1
fi

echo -e "\n✅ Usando: $PYTHON"

# Verificar dependencias
echo -e "\n📦 Verificando dependencias..."
$PYTHON -c "import psycopg2" 2>/dev/null || {
    echo "Instalando psycopg2..."
    pip install psycopg2-binary 2>/dev/null || pip3 install psycopg2-binary
}

$PYTHON -c "import numpy" 2>/dev/null || {
    echo "Instalando numpy..."
    pip install numpy 2>/dev/null || pip3 install numpy
}

# Verificar conexión PostgreSQL
echo -e "\n🗄️ Verificando PostgreSQL..."
$PYTHON -c "
import psycopg2
try:
    conn = psycopg2.connect(host='$DB_HOST', port=$DB_PORT, database='$DB_NAME', user='$DB_USER', password='$DB_PASS')
    cur = conn.cursor()
    cur.execute('SELECT version()')
    version = cur.fetchone()[0]
    print(f'✅ PostgreSQL conectado: {version[:50]}...')
    cur.close()
    conn.close()
except Exception as e:
    print(f'❌ Error: {e}')
    exit(1)
"

echo -e "\n✅ PostgreSQL verificado"

echo -e "\n=========================================="
echo "✅ Setup completado"
echo "=========================================="
echo "La base de datos ya está configurada."
echo "Puedes continuar con la ejecución manual."
