from orchestrator.tools.registry import TOOL_REGISTRY


def test_registry_has_core_tools():
    assert "search_github" in TOOL_REGISTRY
    assert "generate_compose" in TOOL_REGISTRY
    assert "create_agent" in TOOL_REGISTRY
    assert "snapshot" in TOOL_REGISTRY
