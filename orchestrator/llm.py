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
        plan.append(
            {
                "id": "task-1",
                "title": objective,
                "kind": "research",
                "status": "pending",
                "tool": "search_github",
            }
        )

    if any(word in objective_lower for word in ["instalar", "instala", "install", "configurar", "setup"]):
        plan.append(
            {
                "id": f"task-{len(plan) + 1}",
                "title": objective,
                "kind": "install",
                "status": "pending",
                "tool": "skills_pipeline",
            }
        )

    if any(word in objective_lower for word in ["infra", "docker", "compose", "postgres", "redis", "nats", "qdrant"]):
        plan.append(
            {
                "id": f"task-{len(plan) + 1}",
                "title": "Preparar infraestructura base",
                "kind": "infra",
                "status": "pending",
                "tool": "generate_compose",
            }
        )

    if any(word in objective_lower for word in ["crear agente", "nuevo agente", "agent"]):
        plan.append(
            {
                "id": f"task-{len(plan) + 1}",
                "title": f"Crear agente para {_slug(objective)}",
                "kind": "factory",
                "status": "pending",
                "tool": "create_agent",
            }
        )

    if not plan:
        plan = [
            {
                "id": "task-1",
                "title": objective,
                "kind": "research",
                "status": "pending",
                "tool": "search_github",
            },
            {
                "id": "task-2",
                "title": "Preparar infraestructura base",
                "kind": "infra",
                "status": "pending",
                "tool": "generate_compose",
            },
        ]

    return plan


async def plan_objective(objective: str) -> list[dict]:
    llm = get_llm()
    prompt = f"""
Divide el siguiente objetivo en tareas ejecutables y cortas.

Objetivo:
{objective}

Devuelve SOLO JSON con esta forma:
[
  {{"id": "task-1", "title": "...", "kind": "research|install|infra|factory|release", "tool": "..."}}
]
""".strip()
    try:
        response = await llm.ainvoke(prompt)
        content = response.content if isinstance(response.content, str) else str(response.content)
        data = json.loads(_strip_code_fences(content))
        return [
            {
                "id": item["id"],
                "title": item["title"],
                "kind": item["kind"],
                "status": "pending",
                "tool": item.get("tool", ""),
            }
            for item in data
        ]
    except Exception:
        return _fallback_plan(objective)
