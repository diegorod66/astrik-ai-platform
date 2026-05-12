"""
VERSION-AGENT — Agente de versionado continuo: snapshot, bump, tag, changelog
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Agente de versionado continuo: snapshot, bump, tag, changelog")
    parser.add_argument("--task", type=str, help="Tarea a ejecutar")
    parser.add_argument("--input", type=str, help="Entrada JSON para la tarea")
    args = parser.parse_args()

    if not args.task:
        parser.print_help()
        sys.exit(1)

    print(f"{{agent}}: version-agent ejecutando tarea: {args.task}")


if __name__ == "__main__":
    main()
