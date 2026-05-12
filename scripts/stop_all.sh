#!/bin/bash
# Detener todos los servicios del Constructor Astrik

echo "=== Deteniendo Constructor Astrik ==="

# Detener Dashboard
if pgrep -f "streamlit run app.py" > /dev/null 2>&1; then
    pkill -f "streamlit run app.py"
    echo "[OK] Dashboard detenido"
fi

# Detener Orchestrator
if pgrep -f "uvicorn server:app" > /dev/null 2>&1; then
    pkill -f "uvicorn server:app"
    echo "[OK] Orchestrator detenido"
fi

# Detener agentes NATS
for agent in skills-agent infra-agent agent-factory version-agent; do
    if pgrep -f "$agent/service.py" > /dev/null 2>&1; then
        pkill -f "$agent/service.py"
        echo "[OK] $agent detenido"
    fi
done

echo "=== Sistema detenido ==="
