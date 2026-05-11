"""
SKILLS AGENT — Busca, evalúa, instala, prueba y documenta herramientas.

Uso:
  python main.py search --query "documentation versioning python"
  python main.py install --name mkdocs --type pip
  python main.py pipeline --tool mkdocs --query "mkdocs python documentation"
  python main.py test --name mkdocs
  python main.py list
  python main.py info --name mkdocs
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.tools import search_github, evaluate_tool, install_tool, test_tool, document_tool, run_full_pipeline
from src.handlers import handle_skill_list, handle_skill_info


def cmd_search(args):
    results = search_github(args.query, args.max)
    errors = [r for r in results if "error" in r]
    if errors:
        print(f"ERROR: {errors[0]['error']}")
        sys.exit(1)

    print(f"\nResultados para: '{args.query}'\n")
    for r in results[:args.max]:
        ev = evaluate_tool(r)
        stars = r.get("stars", 0)
        print(f"  [{ev['verdict'].upper():15s}] {r['name']:45s} * {stars:>6}")
        print(f"  {'':20s}{r.get('description', '')[:80]}")
        print(f"  {'':20s}{r.get('url', '')}")
        print()


def cmd_install(args):
    result = install_tool(args.name, args.type, args.source)
    print(f"\nInstalando {args.name}...")
    print(f"  Estado: {result['status']}")
    if result.get("path"):
        print(f"  Ruta: {result['path']}")
    if result.get("logs"):
        print("  Logs:")
        for line in result["logs"][-5:]:
            print(f"    {line}")

    if result["status"] == "installed":
        test_result = test_tool(args.name)
        doc_result = document_tool(
            args.name,
            {"score": "N/A", "verdict": "instalado manualmente", "url": args.source or "N/A"},
            result,
            test_result,
        )
        print(f"  Test: {test_result['status']}")
        print(f"  Documentacion: {doc_result}")


def cmd_pipeline(args):
    print(f"\nPipeline completo para: {args.tool}\n")
    result = run_full_pipeline(args.tool, args.query, args.type, args.source)

    if result.get("status") == "failed":
        print(f"ERROR: {result.get('error', 'desconocido')}")
        sys.exit(1)

    print(f"  Estado: {result['status']}")
    print(f"  Mejor candidato: {result.get('best_candidate', 'N/A')}")
    print(f"  Score: {result.get('best_score', 'N/A')}/10")
    print(f"  Veredicto: {result.get('verdict', 'N/A')}")
    print(f"  URL: {result.get('best_url', 'N/A')}")
    print(f"  Instalacion: {result.get('installation', {}).get('status', 'N/A')}")
    print(f"  Test: {result.get('test', {}).get('status', 'N/A')}")
    print(f"  Docs: {result.get('documentation', 'N/A')}")


def cmd_test(args):
    result = test_tool(args.name, args.command)
    print(f"\nTest: {args.name}")
    print(f"  Estado: {result['status']}")
    if result.get("output"):
        print(f"  Output:\n{result['output']}")


def cmd_list(args):
    result = handle_skill_list({"event": "SKILL_LIST"})
    if result["status"] != "ok":
        print(f"ERROR: {result.get('error', 'desconocido')}")
        sys.exit(1)

    skills = result.get("skills", [])
    if not skills:
        print("\nNo hay skills instalados aun.")
        return

    print(f"\nSkills instalados ({len(skills)}):\n")
    for s in skills:
        print(f"  - {s['name']}")


def cmd_info(args):
    result = handle_skill_info({"event": "SKILL_INFO", "name": args.name})
    if result["status"] != "ok":
        print(f"ERROR: {result.get('error', 'desconocido')}")
        sys.exit(1)
    print(f"\nSkill: {args.name}\n")
    print(result.get("doc", ""))


def main():
    parser = argparse.ArgumentParser(
        description="Skills Agent — Busca, evalua, instala, prueba y documenta herramientas"
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos")

    p_search = subparsers.add_parser("search", help="Buscar herramientas en GitHub")
    p_search.add_argument("--query", required=True, help="Query de busqueda")
    p_search.add_argument("--max", type=int, default=8, help="Max resultados")

    p_install = subparsers.add_parser("install", help="Instalar una herramienta")
    p_install.add_argument("--name", required=True, help="Nombre")
    p_install.add_argument("--type", default="pip", choices=["pip", "npm", "git", "binary", "system"], help="Tipo")
    p_install.add_argument("--source", default="", help="Fuente (URL o paquete)")

    p_pipeline = subparsers.add_parser("pipeline", help="Pipeline completo: buscar+instalar+testear+documentar")
    p_pipeline.add_argument("--tool", required=True, help="Herramienta a buscar")
    p_pipeline.add_argument("--query", default="", help="Query GitHub personalizada")
    p_pipeline.add_argument("--type", default="pip", choices=["pip", "npm", "git", "binary", "system"], help="Tipo")
    p_pipeline.add_argument("--source", default="", help="Fuente personalizada")

    p_test = subparsers.add_parser("test", help="Probar herramienta instalada")
    p_test.add_argument("--name", required=True, help="Nombre")
    p_test.add_argument("--command", default="", help="Comando de test personalizado")

    p_list = subparsers.add_parser("list", help="Listar skills instalados")
    p_info = subparsers.add_parser("info", help="Info detallada de skill")
    p_info.add_argument("--name", required=True, help="Nombre del skill")

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args)
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "pipeline":
        cmd_pipeline(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "info":
        cmd_info(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
