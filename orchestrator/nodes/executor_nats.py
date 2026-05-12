"""Nodo Executor que invoca agentes via NATS en vez de usar tools locales."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from ..events import publish_event
from ..state import OrchestratorState
from ..tools.nats_agent import NATSAgentTool

AGENT_MAP = {
    "skills-agent": {
        "subject": "agent.skills-agent.request",
        "tools": ["search", "install", "test", "pipeline"],
    },
    "infra-agent": {
        "subject": "agent.infra-agent.request",
        "tools": ["build", "add_service", "health", "generate_compose", "generate_env"],
    },
    "agent-factory": {
        "subject": "agent.agent-factory.request",
        "tools": ["create", "list", "validate"],
    },
    "version-agent": {
        "subject": "agent.version-agent.request",
        "tools": ["snapshot", "bump", "current"],
    },
}


async def executor_nats_node(state: OrchestratorState) -> dict:
    """Toma la tarea actual del plan e invoca el agente correspondiente via NATS."""
    plan = list(state.get("plan", []))
    index = state.get("current_task_index", 0)

    if index >= len(plan):
        return {"status": "completed"}

    task = dict(plan[index])
    agent_name = task.get("agent", "skills-agent")
    tool_name = task.get("tool", "search")
    title = task.get("title", "")

    if agent_name not in AGENT_MAP:
        await publish_event("task.failed", {
            "task_id": task["id"],
            "error": f"Agente desconocido: {agent_name}",
        })
        return {
            "status": "failed",
            "errors": [f"Agente desconocido: {agent_name}"],
            "messages": [AIMessage(content=f"Error: agente {agent_name} no configurado")],
        }

    await publish_event("task.started", {
        "task_id": task["id"],
        "title": title,
        "agent": agent_name,
        "tool": tool_name,
    })

    nats_tool = NATSAgentTool(agent_name)
    response = await nats_tool.invoke(tool_name, {
        "query": title,
        "description": title,
    })

    task["status"] = "completed" if response.get("status") == "completed" else "failed"
    plan[index] = task
    task_results = dict(state.get("task_results", {}))
    task_results[task["id"]] = response

    return {
        "plan": plan,
        "current_task_id": task["id"],
        "last_result": response,
        "task_results": task_results,
        "messages": [AIMessage(content=f"Ejecutada tarea {task['id']} via {agent_name}/{tool_name}")],
    }
