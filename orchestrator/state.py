from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


WorkflowStatus = Literal["pending", "running", "retrying", "completed", "failed"]
TaskStatus = Literal["pending", "running", "completed", "failed"]


class TaskItem(TypedDict):
    id: str
    title: str
    kind: str
    status: TaskStatus
    tool: str


class OrchestratorState(TypedDict, total=False):
    objective: str
    messages: Annotated[list[Any], add_messages]
    plan: list[TaskItem]
    current_task_id: str | None
    current_task_index: int
    last_result: dict[str, Any]
    task_results: dict[str, dict[str, Any]]
    artifacts: dict[str, str]
    retries: int
    max_retries: int
    status: WorkflowStatus
    validation_notes: list[str]
    errors: list[str]
    version: str | None


def build_initial_state(objective: str) -> OrchestratorState:
    return {
        "objective": objective,
        "messages": [],
        "plan": [],
        "current_task_id": None,
        "current_task_index": 0,
        "last_result": {},
        "task_results": {},
        "artifacts": {},
        "retries": 0,
        "max_retries": 2,
        "status": "pending",
        "validation_notes": [],
        "errors": [],
        "version": None,
    }
