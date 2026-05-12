# Constructor Astrik

Sistema Multi-Agente Autonomo para construir la plataforma Astrik AI.

## Arquitectura

Ver `docs/ARQUITECTURA.md` para el diagrama completo.

## Stack Tecnologico

- **Orquestacion**: LangGraph 0.4.7 + FastAPI
- **Mensajeria**: NATS (nats-py 2.9.0)
- **Base de datos**: PostgreSQL 16 (checkpoints), Redis 7 (logs/pub-sub), Qdrant (memoria semantica)
- **LLM**: llama.cpp GPU con Qwen2.5-32B-Instruct-Q4_K_M.gguf
- **Agentes**: Skills Agent, Infra Agent, Agent Factory, Version Agent
- **Dashboard**: Streamlit 1.43
- **Deploy**: servicios como systemd en VM core (192.168.2.112)

## Requisitos

- Python 3.12+
- Docker + Docker Compose
- NATS Server (via Docker)
- PostgreSQL 16 (via Docker)
- Redis 7 (via Docker)
- llama.cpp con GPU (en LXC aparte)

## Instalacion Rapida

```bash
# 1. Clonar repositorio
git clone https://github.com/diegorod66/astrik-ai-platform.git ~/astrik-platform
cd ~/astrik-platform

# 2. Instalar dependencias del Orchestrator
pip3 install --break-system-packages -r orchestrator/requirements.txt

# 3. Instalar dependencias del Dashboard
pip3 install --break-system-packages -r dashboard/requirements.txt

# 4. Configurar .env
cp orchestrator/.env.example orchestrator/.env
# Editar orchestrator/.env con las URLs correctas

# 5. Iniciar infraestructura
cd infrastructure && docker compose up -d && cd ..

# 6. Iniciar todo
bash scripts/start_all.sh
```

## Uso

### CLI

```bash
# Enviar objetivo
astrik run "Buscar e instalar una herramienta de linting para Python"

# Ver estado
astrik status

# Listar workflows
astrik workflow

# Aprobar workflow pausado
astrik decision <thread_id> approve

# Iniciar/detener sistema
astrik start
astrik stop
```

### Dashboard

Abrir `http://192.168.2.112:8501`

### API

```bash
# Crear workflow
curl -X POST http://192.168.2.112:8010/workflows \
  -H "Content-Type: application/json" \
  -d '{"objective": "Buscar herramienta de linting"}'

# Ver workflow
curl http://192.168.2.112:8010/workflows/<thread_id>

# Aprobar workflow
curl -X POST http://192.168.2.112:8010/workflows/<thread_id>/decision \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve"}'

# Healthcheck
curl http://192.168.2.112:8010/health
```

## Estructura del Repositorio

```
astrik-platform/
  agents/              # Agentes NATS (skills, infra, factory, version)
  dashboard/           # Streamlit dashboard
  docs/                # Documentacion y planes
  infrastructure/      # Docker Compose, .env
  orchestrator/        # LangGraph StateGraph + FastAPI
  scripts/             # CLI, start/stop, deploy
  shared/              # Clase base AgentService, Logger
  tests/               # Tests de integracion
```

## Versionado

```bash
python3 scripts/release.py snapshot <componente> <version>
```

## Licencia

MIT
