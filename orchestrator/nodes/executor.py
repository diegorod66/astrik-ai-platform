from __future__ import annotations

from langchain_core.messages import AIMessage

from ..events import publish_event
from ..state import OrchestratorState
from ..tools.registry import TOOL_REGISTRY


def _pick_tool(task: dict) -> str:
    if task.get("tool"):
        return task["tool"]

    kind = task.get("kind", "")
    mapping = {
        "research": "search_github",
        "install": "skills_pipeline",
        "infra": "generate_compose",
        "factory": "create_agent",
        "release": "snapshot",
    }
    return mapping.get(kind, "search_github")


def _build_tool_args(task: dict) -> dict:
    tool_name = task["tool"]
    title = task["title"].lower()

    if tool_name == "search_github":
        return {"query": task["title"], "max_results": 5}
    if tool_name == "skills_pipeline":
        return {"tool_name": task["title"].split()[-1], "github_query": task["title"]}
    if tool_name == "generate_compose":
        return {"services": ["postgres", "redis", "qdrant", "nats"]}
    if tool_name == "create_agent":
        slug = task["title"].lower().replace(" ", "-")
        return {"name": f"{slug[:40]}-agent", "description": task["title"]}
    if tool_name == "snapshot":
        return {"component": "orchestrator", "version": "v1.0.0"}

    if "docker" in title or "infra" in title:
        return {"services": ["postgres", "redis", "qdrant", "nats"]}

    return {"query": task["title"], "max_results": 5}


def _normalize_result(result) -> dict:
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        return {"status": "completed", "output": result}
    if isinstance(result, list):
        return {"status": "completed", "items": result}
    return {"status": "completed", "output": result}


async def executor_node(state: OrchestratorState) -> dict:
    plan = list(state.get("plan", []))
    index = state.get("current_task_index", 0)

    if index >= len(plan):
        return {"status": "completed"}

    task = dict(plan[index])
    tool_name = _pick_tool(task)
    task["tool"] = tool_name
    task["status"] = "running"
    args = _build_tool_args(task)

    await publish_event(
        "task.started",
        {
            "task_id": task["id"],
            "title": task["title"],
            "tool": tool_name,
        },
    )

    raw_result = TOOL_REGISTRY[tool_name](**args)
    result = _normalize_result(raw_result)

    task["status"] = "completed" if result.get("status") != "failed" else "failed"
    plan[index] = task
    task_results = dict(state.get("task_results", {}))
    task_results[task["id"]] = result

    return {
        "plan": plan,
        "current_task_id": task["id"],
        "last_result": result,
        "task_results": task_results,
        "messages": [AIMessage(content=f"Ejecutada tarea {task['id']} con tool {tool_name}")],
    }
