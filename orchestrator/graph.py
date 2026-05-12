from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes.deployer import deployer_node
from .nodes.executor_nats import executor_nats_node
from .nodes.planner import planner_node
from .nodes.validator import validator_node
from .state import OrchestratorState


def route_after_planner(state: OrchestratorState) -> str:
    return "executor_nats" if state.get("plan") else "failed"


def route_after_validator(state: OrchestratorState) -> str:
    status = state.get("status")
    if status == "completed":
        return "deployer"
    if status == "retrying":
        return "executor_nats"
    if status == "failed":
        return "failed"
    if status == "waiting_modification":
        return "human"
    return "executor_nats"


def build_graph(checkpointer):
    builder = StateGraph(OrchestratorState)
    builder.add_node("planner", planner_node)
    builder.add_node("executor_nats", executor_nats_node)
    builder.add_node("validator", validator_node)
    builder.add_node("deployer", deployer_node)

    builder.add_edge(START, "planner")
    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "executor_nats": "executor_nats",
            "failed": END,
        },
    )
    builder.add_edge("executor_nats", "validator")
    builder.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "executor_nats": "executor_nats",
            "deployer": "deployer",
            "failed": END,
            "human": END,
        },
    )
    builder.add_edge("deployer", END)

    return builder.compile(checkpointer=checkpointer)
