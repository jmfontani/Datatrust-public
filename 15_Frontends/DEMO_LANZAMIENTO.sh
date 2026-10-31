#!/bin/bash
# =============================================================================
# Script de Lanzamiento para Demo en Vivo - Buscador Semántico
# =============================================================================
# Uso: ./DEMO_LANZAMIENTO.sh [A|B|C|all|stop]
#
# Opciones:
#   A     - Frontend A (básico) - Demo técnica con controles de pesos
#   B     - Frontend B (intermedio) - Producto principal (RECOMENDADO)
#   C     - Frontend C (avanzado) - Demo LLM con re-ranking + explicaciones
#   all   - Lanzar los 3 frontends simultáneamente
#   stop  - Detener todos los frontends
# =============================================================================

set -e

FRONTENDS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$FRONTENDS_DIR")"
VENV_ACTIVATE="$PROJECT_DIR/venv/bin/activate"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_api() {
    if curl -s http://localhost:8000/health | grep -q '"status":"ok"'; then
        log_success "API disponible en http://localhost:8000"
        return 0
    else
        log_error "API NO disponible. Inicia la API primero:"
        echo "  cd $PROJECT_DIR/07_Sprint5_Integracion/codigo/api"
        echo "  source $PROJECT_DIR/venv/bin/activate"
        echo "  uvicorn main:app --host 0.0.0.0 --port 8000"
        return 1
    fi
}

launch_frontend_a() {
    log_info "Lanzando Frontend A (básico) en puerto 8501..."
    cd "$FRONTENDS_DIR/frontend_a_basico"
    source "$VENV_ACTIVATE"
    streamlit run app.py --server.port 8501 &
    log_success "Frontend A corriendo en http://localhost:8501"
}

launch_frontend_b() {
    log_info "Lanzando Frontend B (intermedio) en puerto 8502..."
    cd "$FRONTENDS_DIR/frontend_b_intermedio"
    source "$VENV_ACTIVATE"
    streamlit run app_public.py --server.port 8502 &
    log_success "Frontend B corriendo en http://localhost:8502"
    log_info "Versión avanzada: http://localhost:8502/?mode=advanced"
}

launch_frontend_c() {
    log_info "Lanzando Frontend C (avanzado) en puerto 8503..."
    cd "$FRONTENDS_DIR/frontend_c_avanzado"
    source "$VENV_ACTIVATE"
    streamlit run app_v09_demo.py --server.port 8503 &
    log_success "Frontend C corriendo en http://localhost:8503"
}

stop_all() {
    log_info "Deteniendo frontends..."
    pkill -f "streamlit run.*app.py" 2>/dev/null || true
    pkill -f "streamlit run.*app_public.py" 2>/dev/null || true
    pkill -f "streamlit run.*app_v09_demo.py" 2>/dev/null || true
    log_success "Frontends detenidos"
}

show_status() {
    echo ""
    echo "=================================================="
    echo "  ESTADO DE FRONTENDS"
    echo "=================================================="

    if curl -s http://localhost:8000/health | grep -q '"status":"ok"'; then
        echo -e "API:          ${GREEN}✅ Disponible${NC}"
    else
        echo -e "API:          ${RED}❌ No disponible${NC}"
    fi

    if pgrep -f "streamlit.*8501" > /dev/null; then
        echo -e "Frontend A:   ${GREEN}✅ Puerto 8501${NC}"
    else
        echo -e "Frontend A:   ${YELLOW}⚪ Detenido${NC}"
    fi

    if pgrep -f "streamlit.*8502" > /dev/null; then
        echo -e "Frontend B:   ${GREEN}✅ Puerto 8502${NC}"
    else
        echo -e "Frontend B:   ${YELLOW}⚪ Detenido${NC}"
    fi

    if pgrep -f "streamlit.*8503" > /dev/null; then
        echo -e "Frontend C:   ${GREEN}✅ Puerto 8503${NC}"
    else
        echo -e "Frontend C:   ${YELLOW}⚪ Detenido${NC}"
    fi

    echo "=================================================="
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================

case "${1:-status}" in
    A|a)
        check_api
        launch_frontend_a
        ;;
    B|b)
        check_api
        launch_frontend_b
        ;;
    C|c)
        check_api
        launch_frontend_c
        ;;
    all)
        check_api
        launch_frontend_a
        sleep 2
        launch_frontend_b
        sleep 2
        launch_frontend_c
        log_success "¡Todos los frontends lanzados!"
        echo ""
        echo "Accesos:"
        echo "  Frontend A (básico):     http://localhost:8501"
        echo "  Frontend B (producto):   http://localhost:8502"
        echo "  Frontend C (LLM demo):   http://localhost:8503"
        echo ""
        ;;
    stop)
        stop_all
        ;;
    status)
        show_status
        ;;
    *)
        echo "Uso: $0 [A|B|C|all|stop|status]"
        echo ""
        echo "Opciones:"
        echo "  A      - Lanzar Frontend A (básico)"
        echo "  B      - Lanzar Frontend B (producto principal)"
        echo "  C      - Lanzar Frontend C (avanzado con LLM)"
        echo "  all    - Lanzar los 3 frontends"
        echo "  stop   - Detener todos los frontends"
        echo "  status - Mostrar estado actual"
        exit 1
        ;;
esac
