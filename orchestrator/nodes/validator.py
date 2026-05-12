"""Nodo Validator con human-in-loop.
Usa interrupt() de LangGraph para pausar y esperar decision humana antes del deploy."""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

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
        all_done = next_index >= len(plan)

        await publish_event("task.completed", {
            "task_id": current_task_id,
            "next_index": next_index,
        })

        if all_done:
            await publish_event("workflow.pending_approval", {
                "objective": state.get("objective", ""),
                "task_count": len(plan),
                "task_results": {
                    tid: str(res)[:200]
                    for tid, res in state.get("task_results", {}).items()
                },
            })

            decision = interrupt({
                "query": "Aprobar deploy y versionado?",
                "summary": f"""
=== RESUMEN DEL WORKFLOW ===
Objetivo: {state.get('objective', '')}
Tareas completadas: {len(state.get('task_results', {}))}
Errores: {len(errors)}
""",
                "options": ["approve", "reject", "modify"],
            })

            if decision == "approve":
                return {
                    "plan": plan,
                    "current_task_index": next_index,
                    "status": "completed",
                    "retries": 0,
                    "validation_notes": notes + ["Workflow aprobado por humano"],
                    "messages": [AIMessage(content="Workflow aprobado para deploy")],
                }
            elif decision == "reject":
                await publish_event("workflow.rejected", {
                    "objective": state.get("objective"),
                })
                return {
                    "status": "failed",
                    "errors": errors + ["Workflow rechazado por el usuario"],
                    "messages": [AIMessage(content="Workflow rechazado por el usuario")],
                }
            elif decision == "modify":
                return {
                    "status": "waiting_modification",
                    "messages": [AIMessage(content="Esperando modificaciones del usuario")],
                }

        return {
            "plan": plan,
            "current_task_index": next_index,
            "status": "running",
            "retries": 0,
            "validation_notes": notes + [f"Tarea {current_task_id} validada"],
            "messages": [AIMessage(content=f"Validator aprobo {current_task_id}")],
        }

    if retries < max_retries:
        await publish_event("task.retry", {
            "task_id": current_task_id,
            "retry": retries + 1,
        })
        return {
            "status": "retrying",
            "retries": retries + 1,
            "validation_notes": notes + [f"Retry {retries + 1} para {current_task_id}"],
            "messages": [AIMessage(content=f"Validator pide retry para {current_task_id}")],
        }

    errors.append(f"La tarea {current_task_id} fallo tras {max_retries} reintentos")
    await publish_event("task.failed", {
        "task_id": current_task_id,
        "error": errors[-1],
    })
    return {
        "status": "failed",
        "errors": errors,
        "messages": [AIMessage(content=f"Validator marco fallo definitivo en {current_task_id}")],
    }
