# Arquitectura del Agente: agent-factory

## Identidad
- **Nombre:** agent-factory
- **Versión:** 1.0.0
- **Modelo:** Hermes 3
- **Runtime:** llama.cpp

## Propósito
Meta-agente constructor. Genera nuevos agentes con estructura estandarizada,
schema validado y boilerplate funcional. Es el primer agente del sistema
y la base para escalar la plataforma.

## Diagrama de Flujo

```
Usuario / OpenCode
        │
        ▼
┌───────────────────┐
│   Agent Factory   │
│     (main.py)     │
└───────┬───────────┘
        │
        ├── create ──────────► Genera estructura de directorios
        │                          │
        │                          ├── agent.yaml (metadatos)
        │                          ├── main.py (entry point)
        │                          ├── prompts/system.md
        │                          ├── src/tools.py
        │                          ├── src/handlers.py
        │                          ├── docs/ARCHITECTURE.md
        │                          ├── docs/README.md
        │                          ├── tests/test_main.py
        │                          └── requirements.txt
        │
        ├── list ───────────► Escanea agents/ y lista agentes válidos
        │
        └── validate ───────► Verifica estructura completa del agente
```

## Estructura de Directorios

```
agents/agent-factory/
├── agent.yaml              # Metadatos del factory
├── main.py                 # CLI: create | list | validate
├── prompts/
│   ├── system.md           # Prompt de sistema
│   └── tasks/              # (futuro) Prompts específicos
├── src/
│   ├── __init__.py
│   ├── schema.py           # Pydantic: AgentSchema, AgentEvents
│   └── generator.py        # Generación de estructura de agentes
├── docs/
│   ├── ARCHITECTURE.md     # Este archivo
│   └── README.md           # Documentación de uso
├── tests/
│   └── test_main.py
└── requirements.txt
```

## Schema de Agente (agent.yaml)

```yaml
name: string              # Obligatorio. Nombre único del agente
version: semver           # Obligatorio. Versión semántica
description: string       # Obligatorio. Propósito del agente
model: string             # Obligatorio. Modelo de IA
runtime: string           # Obligatorio. Motor de inferencia
permissions: [string]     # Permisos: filesystem, network, etc.
events:
  consumes: [string]      # Eventos que escucha
  publishes: [string]     # Eventos que emite
tools: [string]           # Herramientas disponibles
dependencies: [string]    # Paquetes Python requeridos
```

## Archivos Requeridos en Cada Agente

| Archivo | Obligatorio | Propósito |
|---------|-------------|-----------|
| `agent.yaml` | Sí | Metadatos y configuración |
| `main.py` | Sí | Entry point CLI |
| `prompts/system.md` | Sí | Prompt de sistema del agente |
| `src/__init__.py` | Sí | Paquete Python |
| `src/tools.py` | Sí | Implementación de herramientas |
| `src/handlers.py` | Sí | Manejadores de eventos |
| `docs/ARCHITECTURE.md` | Sí | Documentación arquitectural |
| `docs/README.md` | Sí | Documentación de uso |
| `tests/test_main.py` | Sí | Tests unitarios |
| `requirements.txt` | Sí | Dependencias |

## Comunicación
- **Consume:** AGENT_CREATE_REQUESTED
- **Publica:** AGENT_CREATED, AGENT_CREATE_FAILED

## Permisos
- filesystem:write
- filesystem:read
