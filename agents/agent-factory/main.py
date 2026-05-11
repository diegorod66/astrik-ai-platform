"""
AGENT FACTORY — Meta-agente constructor de agentes.

Uso:
  python main.py create --name skills-agent --desc "Busca e instala herramientas" --model hermes3
  python main.py list
  python main.py validate --name skills-agent
"""

import sys
import argparse
import yaml
from pathlib import Path

from src.schema import AgentSchema, AgentEvents
from src.generator import create_agent_structure, AGENTS_DIR


def cmd_create(args):
    schema = AgentSchema(
        name=args.name,
        version=args.version,
        description=args.desc,
        model=args.model,
        runtime=args.runtime,
        permissions=args.permissions or [],
        events=AgentEvents(
            consumes=args.consumes or [],
            publishes=args.publishes or [],
        ),
        tools=args.tools or [],
        dependencies=args.deps or [],
    )

    try:
        path = create_agent_structure(schema)
        print(f"OK - Agente '{schema.name}' creado en: {path}")
        print(f"  Versión: {schema.version}")
        print(f"  Modelo: {schema.model}")
        print(f"  Runtime: {schema.runtime}")
    except FileExistsError as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def cmd_list(args):
    agent_dirs = [d for d in AGENTS_DIR.iterdir() if d.is_dir() and (d / "agent.yaml").exists()]
    if not agent_dirs:
        print("No hay agentes creados aún.")
        return

    print(f"Agentes en {AGENTS_DIR}:")
    print("-" * 50)
    for d in sorted(agent_dirs):
        yaml_path = d / "agent.yaml"
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            print(f"  {data['name']:25s} v{data.get('version', '?')}  [{data.get('model', '?')}]")
        except Exception:
            print(f"  {d.name:25s}  [error leyendo agent.yaml]")


def cmd_validate(args):
    agent_path = AGENTS_DIR / args.name
    if not agent_path.exists():
        print(f"ERROR: Agente '{args.name}' no encontrado en {agent_path}")
        sys.exit(1)

    yaml_path = agent_path / "agent.yaml"
    if not yaml_path.exists():
        print(f"ERROR: Falta agent.yaml en {agent_path}")
        sys.exit(1)

    required_files = [
        "agent.yaml", "main.py", "prompts/system.md",
        "src/__init__.py", "src/tools.py", "src/handlers.py",
        "docs/ARCHITECTURE.md", "docs/README.md",
        "tests/test_main.py", "requirements.txt",
    ]

    missing = []
    for f in required_files:
        if not (agent_path / f).exists():
            missing.append(f)

    if missing:
        print(f"ERROR: Archivos faltantes en '{args.name}':")
        for f in missing:
            print(f"  - {f}")
        sys.exit(1)

    print(f"OK - Agente '{args.name}' válido. Todos los archivos requeridos existen.")


def main():
    parser = argparse.ArgumentParser(description="Agent Factory — Constructor de Agentes")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # create
    p_create = subparsers.add_parser("create", help="Crear un nuevo agente")
    p_create.add_argument("--name", required=True, help="Nombre del agente")
    p_create.add_argument("--desc", required=True, help="Descripción funcional")
    p_create.add_argument("--version", default="1.0.0", help="Versión semántica")
    p_create.add_argument("--model", default="hermes3", help="Modelo de IA")
    p_create.add_argument("--runtime", default="llamacpp", help="Runtime de inferencia")
    p_create.add_argument("--permissions", nargs="*", help="Permisos del agente")
    p_create.add_argument("--consumes", nargs="*", help="Eventos que consume")
    p_create.add_argument("--publishes", nargs="*", help="Eventos que publica")
    p_create.add_argument("--tools", nargs="*", help="Herramientas disponibles")
    p_create.add_argument("--deps", nargs="*", help="Dependencias Python")

    # list
    p_list = subparsers.add_parser("list", help="Listar agentes existentes")

    # validate
    p_validate = subparsers.add_parser("validate", help="Validar estructura de un agente")
    p_validate.add_argument("--name", required=True, help="Nombre del agente a validar")

    args = parser.parse_args()

    if args.command == "create":
        cmd_create(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "validate":
        cmd_validate(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
