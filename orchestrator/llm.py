from __future__ import annotations

import json
import re

from langchain_openai import ChatOpenAI

from .config import settings


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llama_model,
        api_key="not-needed",
        base_url=settings.llama_api_url,
        temperature=0,
    )


def _strip_code_fences(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    return text


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value or "task"


def _fallback_plan(objective: str) -> list[dict]:
    objective_lower = objective.lower()
    plan: list[dict] = []

    if any(word in objective_lower for word in ["buscar", "herramienta", "github", "libreria"]):
        plan.append({
            "id": "task-1",
            "title": objective,
            "agent": "skills-agent",
            "tool": "search",
            "kind": "research",
            "status": "pending",
        })

    if any(word in objective_lower for word in ["instalar", "instala", "install", "configurar", "setup"]):
        plan.append({
            "id": f"task-{len(plan) + 1}",
            "title": objective,
            "agent": "skills-agent",
            "tool": "pipeline",
            "kind": "install",
            "status": "pending",
        })

    if any(word in objective_lower for word in ["infra", "docker", "compose", "postgres", "redis", "nats", "qdrant"]):
        plan.append({
            "id": f"task-{len(plan) + 1}",
            "title": "Preparar infraestructura base",
            "agent": "infra-agent",
            "tool": "build",
            "kind": "infra",
            "status": "pending",
        })

    if any(word in objective_lower for word in ["crear agente", "nuevo agente", "agent"]):
        plan.append({
            "id": f"task-{len(plan) + 1}",
            "title": f"Crear agente para {_slug(objective)}",
            "agent": "agent-factory",
            "tool": "create",
            "kind": "factory",
            "status": "pending",
        })

    if not plan:
        plan = [
            {
                "id": "task-1",
                "title": objective,
                "agent": "skills-agent",
                "tool": "search",
                "kind": "research",
                "status": "pending",
            },
            {
                "id": "task-2",
                "title": "Preparar infraestructura base",
                "agent": "infra-agent",
                "tool": "build",
                "kind": "infra",
                "status": "pending",
            },
        ]

    return plan


async def plan_objective(objective: str) -> list[dict]:
    llm = get_llm()
    prompt = f"""
Eres un planificador de sistemas multi-agente.
Dado un objetivo, dividelo en tareas especificas y asignale a cada una un agente y una herramienta.

AGENTES DISPONIBLES:
  - "skills-agent": tools = ["search", "install", "test", "pipeline"]
  - "infra-agent": tools = ["build", "add_service", "health", "generate_compose", "generate_env"]
  - "agent-factory": tools = ["create", "list", "validate"]
  - "version-agent": tools = ["snapshot", "bump", "current"]

Objetivo:
{objective}

Devuelve SOLO JSON con esta forma exacta:
[
  {{"id": "task-1", "title": "descripcion corta", "agent": "skills-agent", "tool": "search", "kind": "research"}},
  {{"id": "task-2", "title": "descripcion corta", "agent": "infra-agent", "tool": "build", "kind": "infra"}}
]

kind debe ser uno de: research, install, infra, factory, release.
No agregues explicaciones ni markdown. Solo JSON valido.""".strip()
    try:
        response = await llm.ainvoke(prompt)
        content = response.content if isinstance(response.content, str) else str(response.content)
        data = json.loads(_strip_code_fences(content))
        return [
            {
                "id": item["id"],
                "title": item["title"],
                "agent": item.get("agent", "skills-agent"),
                "tool": item.get("tool", "search"),
                "kind": item.get("kind", "research"),
                "status": "pending",
            }
            for item in data
        ]
    except Exception:
        return _fallback_plan(objective)
