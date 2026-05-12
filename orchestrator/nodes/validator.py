from __future__ import annotations

from langchain_core.messages import AIMessage

from ..events import publish_event
from ..state import OrchestratorState


def _result_ok(result: dict) -> bool:
    if not result:
        return False
    status = result.get("status")
    if status in {"completed", "installed", "working", "already_exists"}:
        return True
    if result.get("error") or result.get("stderr"):
        return False
    return status != "failed"


async def validator_node(state: OrchestratorState) -> dict:
    plan = list(state.get("plan", []))
    index = state.get("current_task_index", 0)
    current_task_id = state.get("current_task_id")
    result = dict(state.get("last_result", {}))
    retries = state.get("retries", 0)
    max_retries = state.get("max_retries", 2)
    notes = list(state.get("validation_notes", []))
    errors = list(state.get("errors", []))

    if _result_ok(result):
        if index < len(plan):
            plan[index]["status"] = "completed"
        next_index = index + 1
        done = next_index >= len(plan)

        await publish_event(
            "task.completed",
            {"task_id": current_task_id, "next_index": next_index},
        )

        return {
            "plan": plan,
            "current_task_index": next_index,
            "status": "completed" if done else "running",
            "retries": 0,
            "validation_notes": notes + [f"Tarea {current_task_id} validada"],
            "messages": [AIMessage(content=f"Validator aprobo {current_task_id}")],
        }

    if retries < max_retries:
        await publish_event(
            "task.retry",
            {"task_id": current_task_id, "retry": retries + 1},
        )
        return {
            "status": "retrying",
            "retries": retries + 1,
            "validation_notes": notes + [f"Retry {retries + 1} para {current_task_id}"],
            "messages": [AIMessage(content=f"Validator pide retry para {current_task_id}")],
        }

    errors.append(f"La tarea {current_task_id} fallo tras {max_retries} reintentos")

    await publish_event(
        "task.failed",
        {"task_id": current_task_id, "error": errors[-1]},
    )

    return {
        "status": "failed",
        "errors": errors,
        "messages": [AIMessage(content=f"Validator marco fallo definitivo en {current_task_id}")],
    }
