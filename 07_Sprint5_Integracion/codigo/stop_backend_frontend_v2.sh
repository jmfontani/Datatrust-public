#!/bin/bash
# Script para detener Backend V2 + Frontend V2

echo "=========================================="
echo "🛑 Deteniendo Backend + Frontend V2"
echo "=========================================="

# Detener backend
if [ -f /tmp/backend_v2.pid ]; then
    BACKEND_PID=$(cat /tmp/backend_v2.pid)
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "📡 Deteniendo Backend (PID: $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null
        sleep 1
        echo "   ✅ Backend detenido"
    else
        echo "   ⚠️  Backend ya no estaba corriendo"
    fi
    rm -f /tmp/backend_v2.pid
else
    echo "   ℹ️  No se encontró PID del backend"
fi

# Detener frontend
if [ -f /tmp/frontend_v2.pid ]; then
    FRONTEND_PID=$(cat /tmp/frontend_v2.pid)
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "🎨 Deteniendo Frontend (PID: $FRONTEND_PID)..."
        kill "$FRONTEND_PID" 2>/dev/null
        sleep 1
        echo "   ✅ Frontend detenido"
    else
        echo "   ⚠️  Frontend ya no estaba corriendo"
    fi
    rm -f /tmp/frontend_v2.pid
else
    echo "   ℹ️  No se encontró PID del frontend"
fi

# Limpieza adicional
pkill -f "uvicorn main_v2:app" 2>/dev/null || true
pkill -f "streamlit run app.py" 2>/dev/null || true

echo ""
echo "✅ Todos los servicios detenidos"
echo "=========================================="
