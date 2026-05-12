from __future__ import annotations

from langchain_core.messages import AIMessage

from ..events import publish_event
from ..llm import plan_objective
from ..state import OrchestratorState


async def planner_node(state: OrchestratorState) -> dict:
    objective = state["objective"]
    plan = await plan_objective(objective)

    await publish_event(
        "workflow.started",
        {
            "objective": objective,
            "task_count": len(plan),
        },
    )

    return {
        "plan": plan,
        "status": "running",
        "messages": [AIMessage(content=f"Plan generado con {len(plan)} tareas")],
        "current_task_index": 0,
    }
