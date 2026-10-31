#!/bin/bash
# Controla el clon de la API para la Fase F. Uso: gestionar_clon.sh <minilm|bge|estado|parar>
set -u
C=buscador_api
PATRON="uvicorn main_v2_bge_experimento"

pids() {
  docker exec $C sh -c "for p in /proc/[0-9]*; do c=\$(tr '\0' ' ' < \$p/cmdline 2>/dev/null); case \"\$c\" in *$PATRON*) echo \${p#/proc/};; esac; done"
}

estado() {
  echo "--- procesos del clon ---"
  for p in $(pids); do
    echo -n "  PID $p  env: "
    docker exec $C sh -c "tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep EXPERIMENTO | tr '\n' ' '"
    echo
  done
  [ -z "$(pids)" ] && echo "  (ninguno)"
}

parar() {
  for p in $(pids); do
    echo "  matando PID $p"
    docker exec $C kill -9 "$p" 2>/dev/null
  done
  sleep 3
  [ -z "$(pids)" ] && echo "  puerto 8002 libre" || echo "  AVISO: sigue vivo"
}

arrancar() {
  local motor="$1" col="$2"
  docker exec -d -e EXPERIMENTO_MOTOR="$motor" -e EXPERIMENTO_COLUMNA="$col" \
    $C python -m uvicorn main_v2_bge_experimento:app --app-dir api --host 0.0.0.0 --port 8002
  for i in $(seq 1 20); do
    sleep 5
    if docker exec $C sh -c "curl -s -m 5 http://localhost:8002/health >/dev/null 2>&1"; then
      echo "  arrancado tras $((i*5))s"
      return 0
    fi
  done
  echo "  ERROR: no respondio en 100s"
  return 1
}

case "${1:-estado}" in
  minilm) parar; arrancar minilm embedding ;;
  bge)    parar; arrancar bge embedding_bge ;;
  parar)  parar ;;
  estado) estado ;;
esac
