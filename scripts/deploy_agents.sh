#!/bin/bash
# Deploy de todos los agentes como servicios en la VM core

HOST="constructor@192.168.2.112"
REMOTE_DIR="/home/constructor/astrik-agents"

echo "=== Desplegando agentes NATS en $HOST ==="

# Crear directorio remoto
ssh "$HOST" "mkdir -p $REMOTE_DIR"

# Copiar agentes y shared
rsync -avz --delete \
  agents/skills-agent/ \
  "$HOST:$REMOTE_DIR/skills-agent/"

rsync -avz --delete \
  agents/infra-agent/ \
  "$HOST:$REMOTE_DIR/infra-agent/"

rsync -avz --delete \
  agents/agent-factory/ \
  "$HOST:$REMOTE_DIR/agent-factory/"

# Copiar version-agent si existe
if [ -d "agents/version-agent" ]; then
  rsync -avz --delete \
    agents/version-agent/ \
    "$HOST:$REMOTE_DIR/version-agent/"
fi

# Copiar shared/
rsync -avz --delete \
  shared/ \
  "$HOST:$REMOTE_DIR/shared/"

# Instalar dependencias
ssh "$HOST" "cd $REMOTE_DIR && pip install -r skills-agent/requirements.txt 2>/dev/null; true"
ssh "$HOST" "cd $REMOTE_DIR && pip install nats-py 2>/dev/null; true"

# Iniciar servicios con systemd
for agent in skills-agent infra-agent agent-factory version-agent; do
  if [ -d "$REMOTE_DIR/$agent" ]; then
    ssh "$HOST" "cat > /etc/systemd/system/astrik-$agent.service << EOF
[Unit]
Description=Astrik $agent NATS Service
After=network.target nats.service

[Service]
Type=simple
User=constructor
WorkingDirectory=$REMOTE_DIR/$agent
ExecStart=/usr/bin/python3 $REMOTE_DIR/$agent/service.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"
    ssh "$HOST" "systemctl daemon-reload && systemctl enable astrik-$agent.service && systemctl restart astrik-$agent.service"
    echo "  [+] $agent iniciado"
  fi
done

echo "=== Deploy completado ==="
