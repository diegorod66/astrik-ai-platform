#!/bin/bash
# Mostrar estado de todos los servicios

echo "=== Estado de Constructor Astrik ==="
echo ""

# Orchestrator
if curl -sf http://192.168.2.112:8010/health > /dev/null 2>&1; then
    echo "[OK] Orchestrator :8010"
else
    echo "[--] Orchestrator :8010 (offline)"
fi

# Agentes NATS
for agent in skills-agent infra-agent agent-factory version-agent; do
    if pgrep -f "$agent/service.py" > /dev/null 2>&1; then
        echo "[OK] $agent"
    else
        echo "[--] $agent (offline)"
    fi
done

# Dashboard
if pgrep -f "streamlit run app.py" > /dev/null 2>&1; then
    echo "[OK] Dashboard :8501"
else
    echo "[--] Dashboard :8501 (offline)"
fi

# Servicios Docker
echo ""
echo "--- Servicios Docker ---"
docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "Docker no disponible"
