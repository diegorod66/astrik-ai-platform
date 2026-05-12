"""Nodo Deployer: invoca Version Agent via NATS para snapshot y bump."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from ..events import publish_event
from ..state import OrchestratorState
from ..tools.nats_agent import NATSAgentTool


async def deployer_node(state: OrchestratorState) -> dict:
    task_details = state.get("plan", [])
    components_versionados = set()

    for task in task_details:
        agent = task.get("agent", "")
        if agent == "skills-agent":
            components_versionados.add("agents/skills-agent")
        elif agent == "infra-agent":
            components_versionados.add("agents/infra-agent")
        elif agent == "agent-factory":
            components_versionados.add("agents/agent-factory")

    version_tool = NATSAgentTool("version-agent")
    results = []

    await publish_event("deploy.started", {
        "components": list(components_versionados),
    })

    for component in components_versionados:
        response = await version_tool.invoke("snapshot", {
            "componente": component,
            "version": "",
        })
        results.append({"component": component, "response": response})

        if response.get("status") == "completed":
            await publish_event("deploy.component_done", {
                "component": component,
                "version": response.get("version", "?"),
            })

    bump_response = await version_tool.invoke("bump", {"part": "patch"})
    results.append({"component": "proyecto", "response": bump_response})

    await publish_event("deploy.completed", {
        "components": list(components_versionados),
        "bump": bump_response.get("version", "?"),
    })

    return {
        "status": "completed",
        "version": bump_response.get("version", "v0.1.X"),
        "components_versionados": list(components_versionados),
        "deploy_results": results,
        "messages": [AIMessage(content=f"Deploy completado: {len(components_versionados)} componentes versionados")],
    }
