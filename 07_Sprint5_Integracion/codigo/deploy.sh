#!/bin/bash
###############################################################################
# Script de Despliegue Automático - Buscador Semántico V2.2
###############################################################################
# Uso: ./deploy.sh [comando]
# Comandos: start, stop, restart, status, logs, test
###############################################################################

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorio base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="${SCRIPT_DIR}/docker"
API_URL="http://localhost:8000"

###############################################################################
# FUNCIONES AUXILIARES
###############################################################################

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

check_docker() {
    if ! command -v docker > /dev/null 2>&1; then
        log_error "Docker no está instalado"
        exit 1
    fi
    
    if ! command -v docker compose > /dev/null 2>&1; then
        log_error "Docker Compose no está instalado"
        exit 1
    fi
}

check_ports() {
    local ports=("8000" "8501" "5432")
    for port in "${ports[@]}"; do
        if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_warn "Puerto $port está ocupado"
        fi
    done
}

###############################################################################
# COMANDOS
###############################################################################

cmd_start() {
    log_step "Iniciando despliegue..."
    
    check_docker
    check_ports
    
    cd "$DOCKER_DIR"
    
    # Verificar .env
    if [ ! -f .env ]; then
        log_warn "Archivo .env no encontrado, creando con valores por defecto"
        cat > .env <<EOF
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=buscador
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
API_PORT=8000
STREAMLIT_PORT=8501
EOF
        log_info "Archivo .env creado"
    fi
    
    # Iniciar servicios
    log_step "Iniciando contenedores Docker..."
    docker compose up -d
    
    # Esperar a que PostgreSQL esté listo
    log_step "Esperando PostgreSQL..."
    for i in {1..30}; do
        if docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
            log_info "PostgreSQL listo"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            log_error "PostgreSQL no respondió a tiempo"
            exit 1
        fi
    done
    
    # Esperar a que API esté lista
    log_step "Esperando API..."
    for i in {1..30}; do
        if curl -s "$API_URL/health" > /dev/null 2>&1; then
            log_info "API lista"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            log_error "API no respondió a tiempo"
            exit 1
        fi
    done
    
    # Verificar estado
    cmd_status
    
    log_info "Despliegue completado exitosamente"
    echo ""
    echo "URLs de acceso:"
    echo "  API:      http://localhost:8000"
    echo "  Docs:     http://localhost:8000/docs"
    echo "  Frontend: http://localhost:8501"
}

cmd_stop() {
    log_step "Deteniendo servicios..."
    cd "$DOCKER_DIR"
    docker compose down
    log_info "Servicios detenidos"
}

cmd_restart() {
    cmd_stop
    cmd_start
}

cmd_status() {
    echo "========================================"
    echo "Estado de los Servicios"
    echo "========================================"
    
    cd "$DOCKER_DIR"
    docker compose ps
    
    echo ""
    echo "========================================"
    echo "Health Check"
    echo "========================================"
    
    if curl -s "$API_URL/health" | jq . 2>/dev/null; then
        log_info "API responde correctamente"
    else
        log_error "API no responde"
    fi
}

cmd_logs() {
    local service="${1:-}"
    cd "$DOCKER_DIR"
    
    if [ -n "$service" ]; then
        docker compose logs -f "$service"
    else
        docker compose logs -f
    fi
}

cmd_test() {
    log_step "Ejecutando tests de verificación..."
    
    # Test 1: Health
    echo ""
    echo "Test 1: Health Check"
    echo "-------------------"
    response=$(curl -s "$API_URL/health")
    if echo "$response" | jq -e '.status == "ok"' > /dev/null 2>&1; then
        log_info "✅ Health check OK"
        echo "$response" | jq .
    else
        log_error "❌ Health check falló"
    fi
    
    # Test 2: Búsqueda simple
    echo ""
    echo "Test 2: Búsqueda 'educación'"
    echo "---------------------------"
    response=$(curl -s -X POST "$API_URL/search" \
        -H "Content-Type: application/json" \
        -d '{"query": "educación", "top_k": 3}')
    
    count=$(echo "$response" | jq '.returned_results')
    if [ "$count" -gt 0 ]; then
        log_info "✅ Búsqueda OK ($count resultados)"
    else
        log_warn "⚠️ No hay resultados (base de datos vacía?)"
    fi
    
    # Test 3: Palabra ambigua
    echo ""
    echo "Test 3: Palabra ambigua 'paro'"
    echo "-----------------------------"
    response=$(curl -s -X POST "$API_URL/search" \
        -H "Content-Type: application/json" \
        -d '{"query": "paro", "top_k": 3}')
    
    echo "$response" | jq '.results[] | {title: .title, score: .score}'
    
    log_info "Tests completados"
}

cmd_backup() {
    local backup_file="backup_$(date +%Y%m%d_%H%M%S).sql"
    log_step "Creando backup: $backup_file"
    
    cd "$DOCKER_DIR"
    docker compose exec -T postgres pg_dump -U postgres buscador > "$backup_file"
    
    log_info "Backup guardado en: $DOCKER_DIR/$backup_file"
}

cmd_restore() {
    local backup_file="$1"
    if [ -z "$backup_file" ]; then
        log_error "Uso: $0 restore <archivo_backup.sql>"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        log_error "Archivo no encontrado: $backup_file"
        exit 1
    fi
    
    log_step "Restaurando backup desde: $backup_file"
    
    cd "$DOCKER_DIR"
    cat "$backup_file" | docker compose exec -T postgres psql -U postgres -d buscador
    
    log_info "Backup restaurado"
}

###############################################################################
# HELP
###############################################################################

cmd_help() {
    cat <<EOF
Uso: ./deploy.sh [comando] [opciones]

Comandos:
  start      Iniciar todos los servicios
  stop       Detener todos los servicios
  restart    Reiniciar todos los servicios
  status     Ver estado de los servicios
  logs       Ver logs (opcional: nombre del servicio)
  test       Ejecutar tests de verificación
  backup     Crear backup de PostgreSQL
  restore    Restaurar backup de PostgreSQL
  help       Mostrar esta ayuda

Ejemplos:
  ./deploy.sh start
  ./deploy.sh status
  ./deploy.sh logs api
  ./deploy.sh test
  ./deploy.sh backup
  ./deploy.sh restore backup_20260525.sql
EOF
}

###############################################################################
# MAIN
###############################################################################

case "${1:-help}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs "$2"
        ;;
    test)
        cmd_test
        ;;
    backup)
        cmd_backup
        ;;
    restore)
        cmd_restore "$2"
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        log_error "Comando desconocido: $1"
        cmd_help
        exit 1
        ;;
esac
