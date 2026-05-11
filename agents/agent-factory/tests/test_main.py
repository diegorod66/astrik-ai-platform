"""
Tests para Agent Factory.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schema import AgentSchema, AgentEvents
from src.generator import create_agent_structure


def test_schema_valid():
    schema = AgentSchema(
        name="test-agent",
        description="Agente de prueba",
        model="hermes3",
        runtime="llamacpp",
    )
    assert schema.name == "test-agent"
    assert schema.version == "1.0.0"


def test_schema_with_events():
    schema = AgentSchema(
        name="test-agent",
        description="Agente de prueba",
        model="hermes3",
        runtime="llamacpp",
        events=AgentEvents(
            consumes=["TASK_ASSIGNED"],
            publishes=["TASK_COMPLETED"],
        ),
    )
    assert "TASK_ASSIGNED" in schema.events.consumes
    assert "TASK_COMPLETED" in schema.events.publishes


def test_generate_agent_structure():
    schema = AgentSchema(
        name="test-agent-gen",
        description="Agente generado en test",
        model="hermes3",
        runtime="llamacpp",
        tools=["filesystem"],
        dependencies=["pyyaml"],
        events=AgentEvents(
            consumes=["SKILL_REQUESTED"],
            publishes=["SKILL_INSTALLED"],
        ),
    )
    path = create_agent_structure(schema)
    assert path.exists()
    assert (path / "agent.yaml").exists()
    assert (path / "main.py").exists()
    assert (path / "prompts" / "system.md").exists()
    assert (path / "src" / "tools.py").exists()
    assert (path / "src" / "handlers.py").exists()
    assert (path / "docs" / "ARCHITECTURE.md").exists()
    assert (path / "docs" / "README.md").exists()
    assert (path / "tests" / "test_main.py").exists()
    assert (path / "requirements.txt").exists()

    import shutil
    shutil.rmtree(path)
