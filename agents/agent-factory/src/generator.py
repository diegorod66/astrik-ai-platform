import os
import shutil
from pathlib import Path

from .schema import AgentSchema

AGENTS_DIR = Path(__file__).parent.parent.parent


def create_agent_structure(schema: AgentSchema) -> Path:
    agent_dir = AGENTS_DIR / schema.name
    if agent_dir.exists():
        raise FileExistsError(f"El agente '{schema.name}' ya existe en {agent_dir}")

    dirs = [
        agent_dir,
        agent_dir / "prompts" / "tasks",
        agent_dir / "src",
        agent_dir / "docs",
        agent_dir / "tests",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    _write_file(agent_dir / "agent.yaml", _render_agent_yaml(schema))
    _write_file(agent_dir / "main.py", _render_main(schema))
    _write_file(agent_dir / "prompts" / "system.md", _render_system_prompt(schema))
    _write_file(agent_dir / "src" / "__init__.py", "")
    _write_file(agent_dir / "src" / "tools.py", _render_tools(schema))
    _write_file(agent_dir / "src" / "handlers.py", _render_handlers(schema))
    _write_file(agent_dir / "docs" / "ARCHITECTURE.md", _render_architecture(schema))
    _write_file(agent_dir / "docs" / "README.md", _render_readme(schema))
    _write_file(agent_dir / "tests" / "test_main.py", _render_tests(schema))
    _write_file(agent_dir / "requirements.txt", _render_requirements(schema))

    return agent_dir


def _write_file(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def _render_agent_yaml(schema: AgentSchema) -> str:
    events = schema.dict().get("events", {})
    consumes = "\n    - " + "\n    - ".join(events.get("consumes", [])) if events.get("consumes") else ""
    publishes = "\n    - " + "\n    - ".join(events.get("publishes", [])) if events.get("publishes") else ""
    permissions = "\n  - " + "\n  - ".join(schema.permissions) if schema.permissions else ""
    tools = "\n  - " + "\n  - ".join(schema.tools) if schema.tools else ""
    deps = "\n  - " + "\n  - ".join(schema.dependencies) if schema.dependencies else ""

    return f"""name: {schema.name}
version: {schema.version}
description: >
  {schema.description}
model: {schema.model}
runtime: {schema.runtime}
permissions:{permissions}
events:
  consumes:{consumes}
  publishes:{publishes}
tools:{tools}
dependencies:{deps}
"""


def _render_main(schema: AgentSchema) -> str:
    return f'''"""
{schema.name.upper()} — {schema.description}
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="{schema.description}")
    parser.add_argument("--task", type=str, help="Tarea a ejecutar")
    parser.add_argument("--input", type=str, help="Entrada JSON para la tarea")
    args = parser.parse_args()

    if not args.task:
        parser.print_help()
        sys.exit(1)

    print(f"{{{{{{agent}}}}}}: {schema.name} ejecutando tarea: {{args.task}}")


if __name__ == "__main__":
    main()
'''


def _render_system_prompt(schema: AgentSchema) -> str:
    tools_desc = "\n".join(f"- {t}" for t in schema.tools) if schema.tools else "- Ninguna"
    return f"""Eres {schema.name}, un agente especializado del sistema Astrik AI Platform.

DESCRIPCIÓN:
{schema.description}

MODELO ASIGNADO: {schema.model}
RUNTIME: {schema.runtime}

HERAMIENTAS DISPONIBLES:
{tools_desc}

INSTRUCCIONES:
- Responde siempre en español
- Usa type hints en tu código
- Documenta todo lo que generes
- Sigue los estándares del proyecto
"""


def _render_tools(schema: AgentSchema) -> str:
    tools_code = []
    for tool in schema.tools:
        func_name = tool.replace("-", "_")
        tools_code.append(f'''
def tool_{func_name}(params: dict) -> dict:
    """Herramienta: {tool}"""
    return {{"tool": "{tool}", "status": "pending", "result": None}}
''')
    return f'''"""
Herramientas disponibles para el agente {schema.name}.
"""

{"".join(tools_code)}
'''


def _render_handlers(schema: AgentSchema) -> str:
    events = schema.dict().get("events", {})
    consumes = events.get("consumes", [])
    handlers = "\n\n".join(
        f'def handle_{e.lower()}(event: dict) -> dict:\n    """Manejador para evento {e}"""\n    return {{"event": "{e}", "status": "ack"}}'
        for e in consumes
    ) if consumes else "    pass"
    return f'''"""
Manejadores de eventos para el agente {schema.name}.
"""

{handlers}
'''


def _render_architecture(schema: AgentSchema) -> str:
    sd = schema.dict()
    ev = sd.get("events", {})
    consumes = ", ".join(ev.get("consumes", [])) or "Ninguno"
    publishes = ", ".join(ev.get("publishes", [])) or "Ninguno"
    perms = "\n".join(f"- {p}" for p in schema.permissions) if schema.permissions else "- Ninguno"
    return f"""# Arquitectura del Agente: {schema.name}

## Identidad
- **Nombre:** {schema.name}
- **Versión:** {schema.version}
- **Modelo:** {schema.model}
- **Runtime:** {schema.runtime}

## Propósito
{schema.description}

## Estructura de Directorios

```
agents/{schema.name}/
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
- **Consume:** {consumes}
- **Publica:** {publishes}

## Permisos
{perms}
"""


def _render_readme(schema: AgentSchema) -> str:
    sd = schema.dict()
    ev = sd.get("events", {})
    consumes = ", ".join(ev.get("consumes", [])) or "Ninguno"
    publishes = ", ".join(ev.get("publishes", [])) or "Ninguno"
    tools_desc = ", ".join(schema.tools) if schema.tools else "Ninguna"
    deps_desc = ", ".join(schema.dependencies) if schema.dependencies else "Ninguna"
    return f"""# {schema.name}

## Descripción
{schema.description}

## Versión
{schema.version}

## Modelo
{schema.model} — {schema.runtime}

## Herramientas
{tools_desc}

## Dependencias
{deps_desc}

## Uso
```bash
python main.py --task <tarea> --input '<json>'
```

## Eventos
- Consume: {consumes}
- Publica: {publishes}
"""


def _render_tests(schema: AgentSchema) -> str:
    return f'''"""
Tests para el agente {schema.name}.
"""


def test_agent_metadata():
    """Verificar que el agente tiene metadata básica"""
    assert "{schema.name}" is not None
    assert "{schema.version}" is not None
'''



def _render_requirements(schema: AgentSchema) -> str:
    return "\n".join(schema.dependencies) if schema.dependencies else "# Sin dependencias externas"
