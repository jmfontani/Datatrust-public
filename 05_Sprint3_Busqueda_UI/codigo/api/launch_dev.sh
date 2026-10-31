#!/bin/bash
# Script para lanzar la API en el entorno de desarrollo

cd /home/node/.openclaw/workspace/PFM/Datatrust/05_Sprint3_Busqueda/codigo/api

# Exportar PYTHONPATH para encontrar dependencias
export PYTHONPATH=/home/node/.openclaw/workspace/PFM/Datatrust/venv/lib/python3.11/site-packages:$PYTHONPATH

# Lanzar API
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
