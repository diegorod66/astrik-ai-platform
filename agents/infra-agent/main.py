"""
INFRA AGENT — Construye y gestiona la infraestructura Docker del proyecto.

Uso:
  python main.py build                        # Generar compose completo
  python main.py build --services postgres,redis   # Solo servicios seleccionados
  python main.py add --name qdrant            # Agregar servicio al compose
  python main.py health                       # Ver servicios corriendo
  python main.py health --service postgres    # Estado de un servicio
  python main.py status                       # Resumen de infraestructura
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.tools import run_full_build, add_service, check_health, generate_env, INFRA_DIR


def cmd_build(args):
    services = args.services.split(",") if args.services else None
    result = run_full_build(services)

    if result["status"] != "completed":
        print(f"ERROR: {result}")
        sys.exit(1)

    print(f"\nInfraestructura construida en: {INFRA_DIR}")
    print(f"  docker-compose: {result['compose_file']}")
    print(f"  .env:           {result['env_file']}")
    print(f"  monitoring:     {result['monitoring']}")
    print(f"  llama.cpp:      {result['llamacpp_runtime']}")
    print(f"\nServicios incluidos: {', '.join(result['services'])}")
    print(f"\nPara iniciar: docker compose -f {result['compose_file']} up -d")


def cmd_add(args):
    result = add_service(args.name)
    if result["status"] == "error":
        print(f"ERROR: {result['error']}")
        sys.exit(1)
    print(f"Servicio '{args.name}': {result['status']}")
    if result.get("path"):
        print(f"  Compose: {result['path']}")


def cmd_health(args):
    result = check_health(args.service)
    if not result.get("docker_installed"):
        print("Docker no esta instalado o no esta corriendo.")
        return

    services = result.get("services", [])
    if not services:
        print("No hay servicios de Astrik corriendo.")
        return

    print(f"\nServicios Docker ({len(services)}):\n")
    for s in services:
        print(f"  {s['name']:30s} {s['status']}")


def cmd_status(args):
    print(f"\nEstado de Infraestructura\n")
    print(f"  Directorio: {INFRA_DIR}")

    compose = INFRA_DIR / "docker-compose.yml"
    print(f"  docker-compose: {'EXISTE' if compose.exists() else 'NO CREADO'}")

    env = INFRA_DIR / ".env"
    print(f"  .env:           {'EXISTE' if env.exists() else 'NO CREADO'}")

    if compose.exists():
        import yaml
        with open(compose, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        services = list(data.get("services", {}).keys())
        print(f"  Servicios definidos: {', '.join(services)}")

    # Docker status
    health = check_health()
    if health.get("docker_installed"):
        running = [s for s in health.get("services", []) if "Up" in s.get("status", "")]
        print(f"  Contenedores corriendo: {len(running)}")


def main():
    parser = argparse.ArgumentParser(
        description="Infra Agent — Gestion de infraestructura Docker"
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos")

    p_build = subparsers.add_parser("build", help="Construir infraestructura completa")
    p_build.add_argument("--services", default="", help="Servicios separados por coma (ej: postgres,redis,qdrant,nats)")

    p_add = subparsers.add_parser("add", help="Agregar servicio al compose")
    p_add.add_argument("--name", required=True, help="Nombre del servicio")

    p_health = subparsers.add_parser("health", help="Ver estado de servicios")
    p_health.add_argument("--service", default="", help="Filtrar por servicio")

    p_status = subparsers.add_parser("status", help="Resumen de infraestructura")

    args = parser.parse_args()

    if args.command == "build":
        cmd_build(args)
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "health":
        cmd_health(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
