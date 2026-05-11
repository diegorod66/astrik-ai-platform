"""
Manejadores de eventos para el Skills Agent.

Eventos que consume:
- SKILL_REQUESTED: solicitud de buscar/instalar una herramienta
- SKILL_LIST: listar skills instalados
- SKILL_INFO: info detallada de un skill

Eventos que publica:
- SKILL_INSTALLED: skill instalado exitosamente
- SKILL_FAILED: error en instalacion
"""

import json
from .tools import run_full_pipeline


def handle_skill_requested(event: dict) -> dict:
    """Buscar, evaluar, instalar, probar y documentar una herramienta.

    Event payload:
        tool_name (str): Nombre de la herramienta
        github_query (str, opcional): Query personalizada para GitHub
        install_type (str, opcional): pip|npm|git|binary
        source (str, opcional): Fuente personalizada
    """
    tool = event.get("tool_name", "")
    if not tool:
        return {
            "event": "SKILL_REQUESTED",
            "status": "failed",
            "error": "Falta 'tool_name' en el evento",
        }

    result = run_full_pipeline(
        tool_name=tool,
        github_query=event.get("github_query", ""),
        install_type=event.get("install_type", "pip"),
        source=event.get("source", ""),
    )

    if result.get("status") == "completed":
        return {"event": "SKILL_INSTALLED", "status": "ok", "result": result}
    else:
        return {"event": "SKILL_FAILED", "status": "error", "result": result}


def handle_skill_list(event: dict) -> dict:
    """Listar todas las herramientas instaladas como skills."""
    from pathlib import Path
    skills_dir = Path(__file__).resolve().parent.parent.parent.parent / "skills"
    if not skills_dir.exists():
        return {"event": "SKILL_LIST", "status": "ok", "skills": []}

    installed = []
    for d in skills_dir.iterdir():
        if d.is_dir():
            skill_file = d / "SKILL.md"
            if skill_file.exists():
                installed.append({
                    "name": d.name,
                    "doc": str(skill_file),
                })
    return {"event": "SKILL_LIST", "status": "ok", "skills": installed}


def handle_skill_info(event: dict) -> dict:
    """Obtener info detallada de un skill instalado."""
    name = event.get("name", "")
    from pathlib import Path
    skill_file = Path(__file__).resolve().parent.parent.parent.parent / "skills" / name / "SKILL.md"
    if skill_file.exists():
        return {
            "event": "SKILL_INFO",
            "status": "ok",
            "name": name,
            "doc": skill_file.read_text(encoding="utf-8"),
        }
    return {"event": "SKILL_INFO", "status": "error", "error": f"Skill '{name}' no encontrado"}
