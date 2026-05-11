"""
Sistema de versionado interno de componentes.
Genera snapshots versionados en releases/, maneja git tags y changelog.

Uso:
  python scripts/release.py snapshot <componente>           # snapshot con version actual
  python scripts/release.py snapshot <componente> v1.2.3    # snapshot con version especifica
  python scripts/release.py bump <major|minor|patch>        # sube version del proyecto
  python scripts/release.py list                            # lista todos los releases
  python scripts/release.py list <componente>               # lista releases de un componente
  python scripts/release.py current                         # muestra version actual
"""

import sys
import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parent.parent
RELEASES_DIR = ROOT / "releases"
VERSION_FILE = ROOT / "VERSION"
CHANGELOG = ROOT / "CHANGELOG.md"
VERSIONS_DOC = ROOT / "VERSIONS.md"


# --- Utilidades de version ---

def read_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    return "0.1.0"


def write_version(version: str):
    VERSION_FILE.write_text(version.strip() + "\n", encoding="utf-8")


def parse_version(v: str) -> tuple:
    parts = v.lstrip("v").split(".")
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return major, minor, patch


def bump_version(current: str, part: str) -> str:
    major, minor, patch = parse_version(current)
    if part == "major":
        return f"v{major + 1}.0.0"
    elif part == "minor":
        return f"v{major}.{minor + 1}.0"
    elif part == "patch":
        return f"v{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Parte invalida: {part}. Usa major, minor o patch.")


def format_version(v: str) -> str:
    return v if v.startswith("v") else f"v{v}"


# --- Componentes del proyecto ---

def list_components() -> list[str]:
    """Devuelve componentes detectables del proyecto."""
    components = []
    # Agentes
    agents_dir = ROOT / "agents"
    if agents_dir.exists():
        for d in agents_dir.iterdir():
            if d.is_dir() and (d / "agent.yaml").exists():
                components.append(f"agents/{d.name}")
    # Modulos raiz con agent.yaml (el proyecto como componente)
    if (ROOT / "agent.yaml").exists():
        components.append(ROOT.name)
    return sorted(components)


def resolve_component(name: str) -> Path:
    """Resuelve nombre de componente a su path real."""
    # Nombre completo: agents/skills-agent
    path = ROOT / name
    if path.exists():
        return path

    # Solo nombre: skills-agent -> agents/skills-agent
    path = ROOT / "agents" / name
    if path.exists():
        return path

    raise FileNotFoundError(f"Componente '{name}' no encontrado en:\n  {ROOT / name}\n  {ROOT / 'agents' / name}")


# --- Comandos ---

def cmd_snapshot(args):
    componente = args.componente
    version = format_version(args.version) if args.version else format_version(read_version())

    try:
        src = resolve_component(componente)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Normalizar nombre del release
    safe_name = componente.replace("/", "-")
    release_name = f"{safe_name}-{version}"
    dest = RELEASES_DIR / release_name

    if dest.exists():
        print(f"ERROR: Ya existe {dest}")
        sys.exit(1)

    # Crear snapshot
    print(f"Creando release: {release_name}")
    shutil.copytree(src, dest, ignore=shutil.ignores("__pycache__", ".pytest_cache", "node_modules"))
    print(f"  Origen: {src}")
    print(f"  Destino: {dest}")

    # Generar metadatos del release
    meta = {
        "componente": componente,
        "version": version,
        "fecha": datetime.now().isoformat(),
        "origen": str(src),
        "archivos": sum(1 for _ in dest.rglob("*") if _.is_file()),
    }
    meta_path = dest / ".release.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Git tag
    tag = f"{safe_name}-{version}"
    try:
        subprocess.run(["git", "tag", tag, "-m", f"Release {release_name}"],
                       cwd=ROOT, capture_output=True, text=True, timeout=15)
        print(f"  Git tag: {tag}")
    except Exception as e:
        print(f"  Git tag fallo (no es un repo git?): {e}")

    # Changelog
    _append_changelog(componente, version)
    print(f"  CHANGELOG.md actualizado")

    # VERSIONS.md
    _update_versions_doc(componente, version)
    print(f"  VERSIONS.md actualizado")

    # Skopeo: si el Skills Agent esta instalado, registrar como skill
    _register_as_skill(release_name, meta)

    print(f"\nRelease completado: {dest}")


def cmd_bump(args):
    current = read_version()
    new_ver = bump_version(current, args.part)
    write_version(new_ver)
    print(f"Version: {current} -> {new_ver}")

    # Commit automatico si es git
    try:
        subprocess.run(["git", "add", str(VERSION_FILE)], cwd=ROOT, capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", f"chore: bump version to {new_ver}"],
                       cwd=ROOT, capture_output=True, timeout=10)
        print(f"  Git commit: version {new_ver}")
    except Exception:
        pass


def cmd_list(args):
    if not RELEASES_DIR.exists():
        print("No hay releases aun.")
        return

    releases = sorted(RELEASES_DIR.iterdir()) if RELEASES_DIR.exists() else []

    if args.componente:
        prefix = args.componente.replace("/", "-")
        releases = [r for r in releases if r.name.startswith(prefix + "-v") or r.name.startswith(prefix + "v")]

    if not releases:
        print(f"No se encontraron releases.")
        return

    print(f"\nReleases ({len(releases)}):\n")
    for r in releases:
        meta_file = r / ".release.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            fecha = meta.get("fecha", "?")[:10]
            archivos = meta.get("archivos", "?")
        else:
            fecha = "?"
            archivos = "?"
        print(f"  {r.name:50s}  [{fecha}]  {archivos} archivos")


def cmd_current(args):
    v = read_version()
    print(f"Version actual del proyecto: {v}")


# --- Documentación ---

def _append_changelog(componente: str, version: str):
    entry = f"\n## [{version}] - {datetime.now().strftime('%Y-%m-%d')}\n### {componente}\n- Release inicial del componente.\n"
    if CHANGELOG.exists():
        content = CHANGELOG.read_text(encoding="utf-8")
        # Insertar despues del header
        lines = content.split("\n")
        if len(lines) > 2:
            lines.insert(2, entry)
        else:
            lines.append(entry)
        CHANGELOG.write_text("\n".join(lines), encoding="utf-8")
    else:
        CHANGELOG.write_text(f"# Changelog\n\n{entry}", encoding="utf-8")


def _update_versions_doc(componente: str, version: str):
    entry = f"| {componente} | {version} | {datetime.now().strftime('%Y-%m-%d')} |\n"
    if VERSIONS_DOC.exists():
        content = VERSIONS_DOC.read_text(encoding="utf-8")
        # Buscar la linea de la tabla y agregar
        if "|---" in content:
            content += entry
        else:
            content += f"\n{entry}"
        VERSIONS_DOC.write_text(content, encoding="utf-8")
    else:
        VERSIONS_DOC.write_text(
            "# Versiones\n\n"
            "## Registro de versiones por componente\n\n"
            "| Componente | Version | Fecha |\n"
            "|---|---|---|\n"
            f"{entry}",
            encoding="utf-8"
        )


def _register_as_skill(release_name: str, meta: dict):
    """Registra el release como skill documentado (para el Skills Agent)."""
    skills_dir = ROOT / "skills"
    skills_dir.mkdir(exist_ok=True)
    skill_doc = skills_dir / release_name / "RELEASE.md"
    skill_doc.parent.mkdir(parents=True, exist_ok=True)
    skill_doc.write_text(
        f"# Release: {release_name}\n\n"
        f"- **Componente:** {meta['componente']}\n"
        f"- **Version:** {meta['version']}\n"
        f"- **Fecha:** {meta['fecha'][:10]}\n"
        f"- **Archivos:** {meta['archivos']}\n"
        f"- **Origen:** {meta['origen']}\n",
        encoding="utf-8"
    )


# --- CLI ---

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sistema de versionado interno de componentes")
    subparsers = parser.add_subparsers(dest="command", help="Comandos")

    p_snap = subparsers.add_parser("snapshot", help="Crear snapshot versionado de un componente")
    p_snap.add_argument("componente", help="Nombre del componente (agents/skills-agent, agents/agent-factory, etc.)")
    p_snap.add_argument("version", nargs="?", default="", help="Version especifica (opcional, usa VERSION por defecto)")

    p_bump = subparsers.add_parser("bump", help="Subir version del proyecto")
    p_bump.add_argument("part", choices=["major", "minor", "patch"], help="Que parte de la version subir")

    p_list = subparsers.add_parser("list", help="Listar releases")
    p_list.add_argument("componente", nargs="?", default="", help="Filtrar por componente (opcional)")

    p_current = subparsers.add_parser("current", help="Mostrar version actual")

    args = parser.parse_args()

    if args.command == "snapshot":
        cmd_snapshot(args)
    elif args.command == "bump":
        cmd_bump(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "current":
        cmd_current(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
