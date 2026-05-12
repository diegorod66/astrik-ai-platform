from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .existing_agents import (
    generate_compose_tool,
    generate_env_tool,
    install_tool,
    run_skill_pipeline,
    search_github_tool,
)


ROOT = Path(__file__).resolve().parents[2]


def create_agent_tool(name: str, description: str) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "agents" / "agent-factory" / "main.py"),
        "create",
        "--name",
        name,
        "--desc",
        description,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    return {
        "status": "completed" if proc.returncode == 0 else "failed",
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def snapshot_tool(component: str, version: str) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "release.py"),
        "snapshot",
        component,
        version,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    return {
        "status": "completed" if proc.returncode == 0 else "failed",
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


TOOL_REGISTRY = {
    "search_github": search_github_tool,
    "install_tool": install_tool,
    "skills_pipeline": run_skill_pipeline,
    "generate_compose": generate_compose_tool,
    "generate_env": generate_env_tool,
    "create_agent": create_agent_tool,
    "snapshot": snapshot_tool,
}
