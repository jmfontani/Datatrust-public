#!/bin/bash
# ═════════════════════════════════════════════════════════════════════════════
# LANZAR_SISTEMA.SH - Script unificado de inicio/parada del Buscador Semántico
# ═════════════════════════════════════════════════════════════════════════════
#
# Uso:
#   ./lanzar_sistema.sh           # Inicia API + Frontend (por defecto)
#   ./lanzar_sistema.sh api       # Solo API
#   ./lanzar_sistema.sh frontend  # Solo Frontend
#   ./lanzar_sistema.sh stop      # Detiene todo
#   ./lanzar_sistema.sh status    # Muestra estado
#   ./lanzar_sistema.sh logs      # Muestra logs en tiempo real
#
# ═════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── CONFIGURACIÓN ───────────────────────────────────────────────────────────
API_PORT=${API_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-8501}
PROJECT_DIR="${PROJECT_DIR:-$HOME/datos/PFM/Datatrust}"
VENV_PATH="$PROJECT_DIR/venv/bin/activate"
LOG_DIR="${LOG_DIR:-/tmp/pfm_logs}"
API_LOG="$LOG_DIR/api.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
API_DIR="$PROJECT_DIR/05_Sprint3_Busqueda/codigo/api"
FRONTEND_DIR="$PROJECT_DIR/05_Sprint3_Busqueda/codigo/frontend"

# ─── COLORES ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── FUNCIONES DE UTILIDAD ─────────────────────────────────────────────────

print_header() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${BOLD}$1${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
}

print_ok()   { echo -e "${GREEN}✅${NC} $1"; }
print_ko()   { echo -e "${RED}❌${NC} $1"; }
print_warn() { echo -e "${YELLOW}⚠️${NC}  $1"; }
print_info() { echo -e "${CYAN}ℹ️${NC}  $1"; }
print_cmd()  { echo -e "${BOLD}▶${NC}  ${YELLOW}$1${NC}"; }

log() {
    local level=$1; shift
    case $level in
        ok)   print_ok "$@" ;;
        ko)   print_ko "$@" ;;
        warn) print_warn "$@" ;;
        info) print_info "$@" ;;
        cmd)  print_cmd "$@" ;;
    esac
}

# Detecta si estamos en el entorno del asistente (Docker) o en el servidor del usuario
detect_env() {
    if [ -f "$VENV_PATH" ]; then
        echo "venv"
    elif [ -d "$PROJECT_DIR" ]; then
        echo "project"
    elif [ -d "$(dirname "$0")/codigo/api" ]; then
        echo "local"
    else
        echo "none"
    fi
}

# Activa el entorno adecuado
activate_env() {
    local env_type=$(detect_env)
    
    case $env_type in
        venv)
            source "$VENV_PATH"
            log info "Virtualenv activado ($PROJECT_DIR/venv)"
            ;;
        project)
            log info "Proyecto detectado sin venv. Usando python3 del sistema..."
            # Actualizamos las rutas para apuntar al proyecto
            API_DIR="$PROJECT_DIR/05_Sprint3_Busqueda/codigo/api"
            FRONTEND_DIR="$PROJECT_DIR/05_Sprint3_Busqueda/codigo/frontend"
            ;;
        local)
            log info "Modo local: usando directorio actual"
            local BASE_DIR="$(dirname "$0")"
            API_DIR="$BASE_DIR/codigo/api"
            FRONTEND_DIR="$BASE_DIR/codigo/frontend"
            PROJECT_DIR="$BASE_DIR"
            ;;
        *)
            log warn "No se encontró el proyecto. Intentando modo portable..."
            ;;
    esac
}

# Verifica que existan los directorios necesarios
check_dirs() {
    local missing=0
    
    if [ ! -d "$API_DIR" ]; then
        log ko "No existe directorio API: $API_DIR"
        missing=1
    fi
    
    if [ ! -f "$API_DIR/main.py" ]; then
        log ko "No existe $API_DIR/main.py"
        missing=1
    fi
    
    if [ ! -d "$FRONTEND_DIR" ]; then
        log ko "No existe directorio Frontend: $FRONTEND_DIR"
        missing=1
    fi
    
    if [ ! -f "$FRONTEND_DIR/app.py" ]; then
        log ko "No existe $FRONTEND_DIR/app.py"
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        echo ""
        log info "Estructura esperada:"
        echo "  $PROJECT_DIR/05_Sprint3_Busqueda/codigo/api/main.py"
        echo "  $PROJECT_DIR/05_Sprint3_Busqueda/codigo/frontend/app.py"
        echo ""
        log info "Puedes definir la ruta con: export PROJECT_DIR=/ruta/al/proyecto"
        exit 1
    fi
    
    log ok "Directorios verificados"
}

# Verifica dependencias críticas
check_deps() {
    local missing_deps=()
    
    python3 -c "import fastapi" 2>/dev/null || missing_deps+=("fastapi")
    python3 -c "import uvicorn" 2>/dev/null || missing_deps+=("uvicorn")
    python3 -c "import streamlit" 2>/dev/null || missing_deps+=("streamlit")
    python3 -c "import requests" 2>/dev/null || missing_deps+=("requests")
    python3 -c "import sentence_transformers" 2>/dev/null || missing_deps+=("sentence-transformers")
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log warn "Faltan dependencias: ${missing_deps[*]}"
        log info "Instalando..."
        
        # Intentamos con pip del venv primero, si no con pip3 global
        if command -v pip &>/dev/null && [ "$(detect_env)" = "venv" ]; then
            pip install "${missing_deps[@]}" -q
        else
            pip3 install "${missing_deps[@]}" --break-system-packages -q 2>/dev/null || \
            pip3 install "${missing_deps[@]}" -q
        fi
        
        log ok "Dependencias instaladas"
    else
        log ok "Dependencias OK"
    fi
}

# ─── GESTIÓN DE PUERTOS ──────────────────────────────────────────────────────

port_pids() {
    lsof -ti :"$1" 2>/dev/null || true
}

is_port_free() {
    [ -z "$(port_pids "$1")" ]
}

free_port() {
    local port=$1
    local pids=$(port_pids "$port")
    
    if [ -n "$pids" ]; then
        log warn "Puerto $port ocupado. Liberando procesos: $pids"
        kill $pids 2>/dev/null || true
        sleep 1
        
        # Si siguen vivos, matar con -9
        pids=$(port_pids "$port")
        if [ -n "$pids" ]; then
            kill -9 $pids 2>/dev/null || true
            sleep 1
        fi
        
        if is_port_free "$port"; then
            log ok "Puerto $port liberado"
        else
            log ko "No se pudo liberar el puerto $port. PIDs: $(port_pids "$port")"
            return 1
        fi
    fi
}

# ─── INICIO DE SERVICIOS ───────────────────────────────────────────────────

start_api() {
    print_header "🚀 INICIANDO BACKEND (FastAPI)"
    
    free_port "$API_PORT" || return 1
    
    mkdir -p "$LOG_DIR"
    cd "$API_DIR"
    
    log info "Iniciando API en puerto $API_PORT..."
    log cmd "uvicorn main:app --host 0.0.0.0 --port $API_PORT"
    
    nohup python3 -m uvicorn main:app \
        --host 0.0.0.0 \
        --port "$API_PORT" \
        > "$API_LOG" 2>&1 &
    
    API_PID=$!
    echo "$API_PID" > /tmp/pfm_api.pid
    log info "API iniciada (PID: $API_PID)"
    
    # Esperar a que esté lista
    log info "Esperando que la API esté lista (máx 90s)..."
    local ready=false
    
    for i in $(seq 1 90); do
        if curl -s "http://localhost:$API_PORT/health" > /dev/null 2>&1; then
            ready=true
            break
        fi
        
        # Mostrar progreso cada 10s
        if [ $((i % 10)) -eq 0 ]; then
            log info "Esperando... (${i}s/90s)"
            # Mostrar últimas líneas del log para diagnóstico
            if [ -f "$API_LOG" ]; then
                tail -n 2 "$API_LOG" 2>/dev/null | sed 's/^/     /'
            fi
        fi
        
        sleep 1
    done
    
    if [ "$ready" = false ]; then
        log ko "La API no respondió en 90 segundos"
        log info "Últimas líneas del log:"
        tail -n 20 "$API_LOG" 2>/dev/null | sed 's/^/     /'
        log info "Puedes revisar el log completo: tail -f $API_LOG"
        return 1
    fi
    
    # Verificar datos cargados
    local health_json
    health_json=$(curl -s "http://localhost:$API_PORT/health" 2>/dev/null || echo '{"datasets_count":0}')
    local datasets_count
    datasets_count=$(echo "$health_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('datasets_count', 0))" 2>/dev/null || echo "0")
    
    log ok "API lista en http://localhost:$API_PORT"
    log info "Datasets cargados: $datasets_count"
    
    return 0
}

start_frontend() {
    print_header "🎨 INICIANDO FRONTEND (Streamlit)"
    
    free_port "$FRONTEND_PORT" || return 1
    
    cd "$FRONTEND_DIR"
    
    log info "Iniciando Streamlit en puerto $FRONTEND_PORT..."
    
    # Detectar cómo ejecutar streamlit
    local streamlit_cmd
    if command -v streamlit &>/dev/null && [ "$(detect_env)" = "venv" ]; then
        streamlit_cmd="streamlit"
    else
        streamlit_cmd="python3 -m streamlit"
    fi
    
    log cmd "$streamlit_cmd run app.py --server.port $FRONTEND_PORT --server.address 0.0.0.0"
    
    nohup $streamlit_cmd run app.py \
        --server.port "$FRONTEND_PORT" \
        --server.address 0.0.0.0 \
        > "$FRONTEND_LOG" 2>&1 &
    
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" > /tmp/pfm_frontend.pid
    log info "Frontend iniciado (PID: $FRONTEND_PID)"
    
    # Esperar a que esté listo
    log info "Esperando que el Frontend esté listo (máx 30s)..."
    local ready=false
    
    for i in $(seq 1 30); do
        if curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
            ready=true
            break
        fi
        sleep 1
    done
    
    if [ "$ready" = false ]; then
        log warn "El Frontend no respondió HTTP en 30s (puede ser normal)"
        log info "Verificando que el proceso exista..."
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            log ok "Proceso Streamlit activo (PID: $FRONTEND_PID)"
            log info "Espera ~10s más y accede a: http://localhost:$FRONTEND_PORT"
        else
            log ko "El proceso Streamlit no está corriendo"
            log info "Últimas líneas del log:"
            tail -n 20 "$FRONTEND_LOG" 2>/dev/null | sed 's/^/     /'
            return 1
        fi
    else
        log ok "Frontend listo en http://localhost:$FRONTEND_PORT"
    fi
    
    return 0
}

# ─── PARADA DE SERVICIOS ───────────────────────────────────────────────────

stop_all() {
    print_header "🛑 DETENIENDO SERVICIOS"
    
    local killed=0
    
    # Detener por PID guardados
    if [ -f /tmp/pfm_api.pid ]; then
        local pid=$(cat /tmp/pfm_api.pid)
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
            log ok "API detenida (PID: $pid)"
            killed=$((killed + 1))
        fi
        rm -f /tmp/pfm_api.pid
    fi
    
    if [ -f /tmp/pfm_frontend.pid ]; then
        local pid=$(cat /tmp/pfm_frontend.pid)
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
            log ok "Frontend detenido (PID: $pid)"
            killed=$((killed + 1))
        fi
        rm -f /tmp/pfm_frontend.pid
    fi
    
    # Detener por puertos (por si quedó algo huérfano)
    for port in "$API_PORT" "$FRONTEND_PORT"; do
        local pids=$(port_pids "$port")
        if [ -n "$pids" ]; then
            log info "Limpiando procesos en puerto $port: $pids"
            kill -9 $pids 2>/dev/null || true
            killed=$((killed + 1))
        fi
    done
    
    # Detener procesos por nombre (fallback)
    pkill -f "uvicorn main:app" 2>/dev/null || true
    pkill -f "streamlit run" 2>/dev/null || true
    
    if [ $killed -gt 0 ]; then
        log ok "Servicios detenidos"
    else
        log info "No había servicios activos"
    fi
}

# ─── ESTADO ──────────────────────────────────────────────────────────────────

show_status() {
    print_header "📊 ESTADO DEL SISTEMA"
    
    local api_pid=""
    local frontend_pid=""
    local api_running=false
    local frontend_running=false
    
    # Verificar por puertos
    local api_pids=$(port_pids "$API_PORT")
    local frontend_pids=$(port_pids "$FRONTEND_PORT")
    
    if [ -n "$api_pids" ]; then
        api_running=true
        api_pid="$api_pids"
    fi
    
    if [ -n "$frontend_pids" ]; then
        frontend_running=true
        frontend_pid="$frontend_pids"
    fi
    
    echo ""
    echo -e "  ${BOLD}API Backend${NC}    (puerto $API_PORT)"
    if $api_running; then
        local health="$(curl -s http://localhost:$API_PORT/health 2>/dev/null || echo '{}')"
        local datasets="$(echo "$health" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("datasets_count","?"))' 2>/dev/null || echo "?")"
        echo -e "     ${GREEN}●${NC} Corriendo (PID: $api_pid)"
        echo -e "     ${GREEN}●${NC} Health: http://localhost:$API_PORT/health"
        echo -e "     ${GREEN}●${NC} Datasets: $datasets"
    else
        echo -e "     ${RED}●${NC} Detenida"
    fi
    
    echo ""
    echo -e "  ${BOLD}Frontend${NC}       (puerto $FRONTEND_PORT)"
    if $frontend_running; then
        echo -e "     ${GREEN}●${NC} Corriendo (PID: $frontend_pid)"
        echo -e "     ${GREEN}●${NC} URL: http://localhost:$FRONTEND_PORT"
    else
        echo -e "     ${RED}●${NC} Detenido"
    fi
    
    echo ""
    echo -e "  ${BOLD}Configuración${NC}"
    echo -e "     Directorio: $PROJECT_DIR"
    echo -e "     Entorno: $(detect_env)"
    echo -e "     Logs: $LOG_DIR"
    
    if $api_running && $frontend_running; then
        echo ""
        log ok "Sistema completamente operativo"
    fi
}

# ─── LOGS ────────────────────────────────────────────────────────────────────

show_logs() {
    print_header "📋 LOGS EN TIEMPO REAL"
    log info "Mostrando logs (Ctrl+C para salir)..."
    echo ""
    
    if [ -f "$API_LOG" ] && [ -f "$FRONTEND_LOG" ]; then
        echo -e "${CYAN}─── API ──────────────────────────────────────────────────────────────────────${NC}"
        tail -n 5 "$API_LOG"
        echo ""
        echo -e "${CYAN}─── FRONTEND ─────────────────────────────────────────────────────────────────${NC}"
        tail -n 5 "$FRONTEND_LOG"
        echo ""
        echo -e "${YELLOW}Sigue los logs con:${NC}"
        echo "  tail -f $API_LOG"
        echo "  tail -f $FRONTEND_LOG"
    elif [ -f "$API_LOG" ]; then
        tail -n 20 "$API_LOG"
    elif [ -f "$FRONTEND_LOG" ]; then
        tail -n 20 "$FRONTEND_LOG"
    else
        log warn "No hay logs disponibles aún"
    fi
}

# ─── HELP ───────────────────────────────────────────────────────────────────

show_help() {
    print_header "🔍 Buscador Semántico de Datasets - Ayuda"
    
    echo ""
    echo -e "${BOLD}USO:${NC}"
    echo "  ./lanzar_sistema.sh [comando] [opciones]"
    echo ""
    echo -e "${BOLD}COMANDOS:${NC}"
    echo "  (vacío)         Inicia API + Frontend (por defecto)"
    echo "  api             Solo inicia el Backend API"
    echo "  frontend        Solo inicia el Frontend Streamlit"
    echo "  stop            Detiene todos los servicios"
    echo "  status          Muestra el estado del sistema"
    echo "  logs            Muestra los logs"
    echo "  help            Muestra esta ayuda"
    echo ""
    echo -e "${BOLD}VARIABLES DE ENTORNO:${NC}"
    echo "  PROJECT_DIR         Ruta al proyecto (default: ~/datos/PFM/Datatrust)"
    echo "  API_PORT            Puerto del backend (default: 8000)"
    echo "  FRONTEND_PORT       Puerto del frontend (default: 8501)"
    echo "  LOG_DIR             Directorio de logs (default: /tmp/pfm_logs)"
    echo ""
    echo -e "${BOLD}EJEMPLOS:${NC}"
    echo "  # Iniciar todo con puertos por defecto"
    echo "  ./lanzar_sistema.sh"
    echo ""
    echo "  # Iniciar solo la API"
    echo "  ./lanzar_sistema.sh api"
    echo ""
    echo "  # Usar puertos personalizados"
    echo "  API_PORT=9000 FRONTEND_PORT=9001 ./lanzar_sistema.sh"
    echo ""
    echo "  # Proyecto en ruta alternativa"
    echo "  PROJECT_DIR=/opt/pfm ./lanzar_sistema.sh"
    echo ""
    echo -e "${BOLD}ARCHIVOS:${NC}"
    echo "  Backend:   $API_DIR/main.py"
    echo "  Frontend:  $FRONTEND_DIR/app.py"
    echo "  Logs:      $LOG_DIR/"
    echo ""
}

# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

main() {
    local cmd="${1:-}"
    
    case "$cmd" in
        help|--help|-h)
            show_help
            exit 0
            ;;
        status)
            show_status
            exit 0
            ;;
        stop)
            stop_all
            exit 0
            ;;
        logs)
            show_logs
            exit 0
            ;;
    esac
    
    # Para los comandos de inicio, verificamos entorno
    print_header "🔍 Buscador Semántico de Datasets"
    log info "Modo: ${cmd:-todo (API + Frontend)}"
    log info "Entorno: $(detect_env)"
    echo ""
    
    activate_env
    check_dirs
    check_deps
    
    local success=0
    
    case "$cmd" in
        api)
            start_api && success=1
            ;;
        frontend)
            start_frontend && success=1
            ;;
        ""|todo|all)
            if start_api; then
                echo ""
                if start_frontend; then
                    success=1
                fi
            fi
            ;;
        *)
            log ko "Comando desconocido: '$cmd'"
            log info "Usa 'help' para ver los comandos disponibles"
            exit 1
            ;;
    esac
    
    if [ $success -eq 1 ]; then
        echo ""
        print_header "✅ SISTEMA LISTO"
        echo ""
        echo -e "  ${GREEN}●${NC} Backend:    ${BOLD}http://localhost:$API_PORT${NC}"
        echo -e "  ${GREEN}●${NC} Frontend:   ${BOLD}http://localhost:$FRONTEND_PORT${NC}"
        echo -e "  ${GREEN}●${NC} Health:     ${BOLD}http://localhost:$API_PORT/health${NC}"
        echo ""
        echo -e "  ${CYAN}Logs:${NC}"
        echo "    tail -f $API_LOG"
        echo "    tail -f $FRONTEND_LOG"
        echo ""
        echo -e "  ${CYAN}Gestión:${NC}"
        echo "    ./lanzar_sistema.sh status   # Ver estado"
        echo "    ./lanzar_sistema.sh logs     # Ver logs"
        echo "    ./lanzar_sistema.sh stop     # Detener todo"
        echo ""
        
        # Guardar estado
        cat > /tmp/pfm_status.json <<EOF
{
    "status": "running",
    "api_port": $API_PORT,
    "frontend_port": $FRONTEND_PORT,
    "api_pid": $(cat /tmp/pfm_api.pid 2>/dev/null || echo "null"),
    "frontend_pid": $(cat /tmp/pfm_frontend.pid 2>/dev/null || echo "null"),
    "started_at": "$(date -Iseconds)"
}
EOF
        
        log info "Estado guardado en /tmp/pfm_status.json"
        
        # Si se inició en foreground, mostrar logs
        if [ -z "$cmd" ] || [ "$cmd" = "todo" ] || [ "$cmd" = "all" ]; then
            echo ""
            log info "Pulsa Ctrl+C para salir de este script (los servicios seguirán en background)"
            echo ""
            # Solo mostramos un resumen de logs iniciales, no bloqueamos con tail -f
            sleep 2
            show_logs
        fi
    fi
}

main "$@"
