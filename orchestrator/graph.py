from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes.deployer import deployer_node
from .nodes.executor import executor_node
from .nodes.planner import planner_node
from .nodes.validator import validator_node
from .state import OrchestratorState


def route_after_planner(state: OrchestratorState) -> str:
    return "executor" if state.get("plan") else "failed"


def route_after_validator(state: OrchestratorState) -> str:
    status = state.get("status")
    if status == "completed":
        return "deployer"
    if status == "retrying":
        return "executor"
    if status == "failed":
        return "failed"
    return "executor"


def build_graph(checkpointer):
    builder = StateGraph(OrchestratorState)
    builder.add_node("planner", planner_node)
    builder.add_node("executor", executor_node)
    builder.add_node("validator", validator_node)
    builder.add_node("deployer", deployer_node)

    builder.add_edge(START, "planner")
    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "executor": "executor",
            "failed": END,
        },
    )
    builder.add_edge("executor", "validator")
    builder.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "executor": "executor",
            "deployer": "deployer",
            "failed": END,
        },
    )
    builder.add_edge("deployer", END)

    return builder.compile(checkpointer=checkpointer)
