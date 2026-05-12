#!/bin/bash
# Iniciar todos los servicios del Constructor Astrik

set -e

ORCHESTRATOR_DIR="$HOME/astrik-platform"
LOG_DIR="$HOME/logs"
mkdir -p "$LOG_DIR"

echo "=== Iniciando Constructor Astrik ==="

# 1. Verificar Docker
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker no esta corriendo"
    exit 1
fi

# 2. Iniciar infraestructura
cd "$ORCHESTRATOR_DIR/infrastructure"
docker compose up -d 2>/dev/null || echo "Infra ya estaba corriendo"

# 3. Esperar a que los servicios esten listos
echo "Esperando servicios..."
sleep 5

# 4. Iniciar Orchestrator
cd "$ORCHESTRATOR_DIR/orchestrator"
nohup uvicorn server:app --host 0.0.0.0 --port 8010 > "$LOG_DIR/orchestrator.log" 2>&1 &
echo "[OK] Orchestrator en puerto 8010 (PID $!)"

# 5. Iniciar agentes NATS
cd "$ORCHESTRATOR_DIR/agents"
for agent in skills-agent infra-agent agent-factory version-agent; do
    if [ -f "$agent/service.py" ]; then
        nohup python3 "$agent/service.py" > "$LOG_DIR/$agent.log" 2>&1 &
        echo "[OK] $agent iniciado (PID $!)"
    else
        echo "[WARN] $agent/service.py no encontrado"
    fi
done

# 6. Iniciar Dashboard
if [ -d "$ORCHESTRATOR_DIR/dashboard" ]; then
    cd "$ORCHESTRATOR_DIR/dashboard"
    nohup streamlit run app.py --server.port 8501 > "$LOG_DIR/dashboard.log" 2>&1 &
    echo "[OK] Dashboard en http://192.168.2.112:8501 (PID $!)"
fi

echo ""
echo "=== Sistema iniciado ==="
echo "Logs en: $LOG_DIR"
