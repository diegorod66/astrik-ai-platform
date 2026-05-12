from __future__ import annotations

from langchain_core.messages import AIMessage

from ..config import settings
from ..events import publish_event
from ..state import OrchestratorState
from ..tools.registry import snapshot_tool


async def deployer_node(state: OrchestratorState) -> dict:
    result = snapshot_tool(
        component=settings.orchestrator_component,
        version=settings.orchestrator_version,
    )
    status = "completed" if result.get("status") == "completed" else "failed"

    await publish_event(
        "workflow.finished",
        {
            "component": settings.orchestrator_component,
            "version": settings.orchestrator_version,
            "status": status,
        },
    )

    return {
        "version": settings.orchestrator_version,
        "status": status,
        "last_result": result,
        "messages": [AIMessage(content=f"Snapshot {settings.orchestrator_version} ejecutado")],
    }
