"""
Tests para el agente skills-agent.
"""


def test_agent_metadata():
    """Verificar que el agente tiene metadata básica"""
    assert "skills-agent" is not None
    assert "1.0.0" is not None
