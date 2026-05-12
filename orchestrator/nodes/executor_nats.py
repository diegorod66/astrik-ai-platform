from langchain_core.tools import tool
from ..tools.nats_agent import NATSAgentTool


@tool
def invoke_skills_agent(task_type: str, payload: dict) -> dict:
    """Invocar Skills Agent via NATS"""
    import asyncio
    t = NATSAgentTool("skills-agent")
    return asyncio.run(t.invoke(task_type, payload))


@tool
def invoke_infra_agent(task_type: str, payload: dict) -> dict:
    """Invocar Infra Agent via NATS"""
    import asyncio
    t = NATSAgentTool("infra-agent")
    return asyncio.run(t.invoke(task_type, payload))


@tool
def invoke_factory_agent(task_type: str, payload: dict) -> dict:
    """Invocar Agent Factory via NATS"""
    import asyncio
    t = NATSAgentTool("agent-factory")
    return asyncio.run(t.invoke(task_type, payload))


@tool
def invoke_version_agent(task_type: str, payload: dict) -> dict:
    """Invocar Version Agent via NATS"""
    import asyncio
    t = NATSAgentTool("version-agent")
    return asyncio.run(t.invoke(task_type, payload))
