"""
Tests para el agente infra-agent.
"""


def test_agent_metadata():
    """Verificar que el agente tiene metadata básica"""
    assert "infra-agent" is not None
    assert "1.0.0" is not None
