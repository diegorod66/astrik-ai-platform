# Agent Factory

## Descripción
Meta-agente constructor de agentes para Astrik AI Platform.
Crea, valida y gestiona la estructura estandarizada de nuevos agentes en el sistema.

## Versión
1.0.0

## Modelo
Hermes 3 — llama.cpp

## Herramientas
- filesystem
- template_engine

## Dependencias
- pyyaml
- pydantic

## Comandos

```bash
# Crear un nuevo agente
python main.py create --name skills-agent --desc "Busca e instala herramientas" --model hermes3

# Listar agentes existentes
python main.py list

# Validar estructura de un agente
python main.py validate --name skills-agent
```

## Ejemplo de creación completa

```bash
python main.py create \
  --name skills-agent \
  --desc "Agente especializado en buscar, evaluar, instalar y documentar herramientas externas" \
  --version 1.0.0 \
  --model hermes3 \
  --runtime llamacpp \
  --permissions filesystem:write filesystem:read network:http \
  --consumes SKILL_REQUESTED \
  --publishes SKILL_INSTALLED SKILL_FAILED \
  --tools filesystem network git \
  --deps pyyaml requests beautifulsoup4
```

## Eventos
- Consume: AGENT_CREATE_REQUESTED
- Publica: AGENT_CREATED, AGENT_CREATE_FAILED
