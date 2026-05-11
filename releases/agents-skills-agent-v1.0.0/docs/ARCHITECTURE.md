# Arquitectura del Agente: skills-agent

## Identidad
- **Nombre:** skills-agent
- **Versión:** 1.0.0
- **Modelo:** hermes3
- **Runtime:** llamacpp

## Propósito
Agente especializado en buscar, evaluar, instalar, probar y documentar herramientas externas y librerias para el proyecto

## Estructura de Directorios

```
agents/skills-agent/
├── agent.yaml           # Metadatos
├── main.py              # Entry point
├── prompts/
│   ├── system.md        # Prompt de sistema
│   └── tasks/           # Prompts específicos
├── src/
│   ├── __init__.py
│   ├── tools.py         # Herramientas
│   └── handlers.py      # Eventos
├── docs/
│   ├── ARCHITECTURE.md  # Este archivo
│   └── README.md        # Documentación
├── tests/
│   └── test_main.py
└── requirements.txt
```

## Comunicación
- **Consume:** SKILL_REQUESTED
- **Publica:** SKILL_INSTALLED, SKILL_FAILED

## Permisos
- filesystem:write
- filesystem:read
- network:http
