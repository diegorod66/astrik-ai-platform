from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_module(module_name: str, file_path: Path):
    parent = str(file_path.parent)
    cleanup = False
    if parent not in sys.path:
        sys.path.insert(0, parent)
        cleanup = True

    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"No se pudo cargar modulo desde {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if cleanup and parent in sys.path:
            sys.path.remove(parent)


skills_tools = _load_module(
    "skills_agent_tools",
    ROOT / "agents" / "skills-agent" / "src" / "tools.py",
)

infra_tools = _load_module(
    "infra_agent_tools",
    ROOT / "agents" / "infra-agent" / "src" / "tools.py",
)


def search_github_tool(query: str, max_results: int = 5) -> list[dict]:
    return skills_tools.search_github(query, max_results)


def install_tool(name: str, install_type: str = "pip", source: str = "") -> dict:
    return skills_tools.install_tool(name, install_type, source)


def run_skill_pipeline(tool_name: str, github_query: str = "", install_type: str = "pip") -> dict:
    return skills_tools.run_full_pipeline(tool_name, github_query, install_type)


def generate_compose_tool(services: list[str] | None = None) -> str:
    return infra_tools.generate_compose(services)


def generate_env_tool(services: list[str] | None = None) -> str:
    return infra_tools.generate_env(services)
