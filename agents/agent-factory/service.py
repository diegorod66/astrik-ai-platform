from shared.agent_service import AgentService
from .src.schema import AgentSchema, AgentEvents
from .src.generator import create_agent_structure, AGENTS_DIR


class FactoryAgentService(AgentService):
    @property
    def agent_name(self): return "agent-factory"

    @property
    def agent_version(self): return "1.0.0"

    @property
    def tools(self): return ["create_agent", "list_agents", "validate_agent"]

    async def execute_task(self, task_type: str, payload: dict) -> dict:
        try:
            if task_type == "create":
                schema = AgentSchema(
                    name=payload["name"],
                    description=payload.get("desc", ""),
                    version=payload.get("version", "1.0.0"),
                    model=payload.get("model", "hermes3"),
                    runtime=payload.get("runtime", "llamacpp"),
                    permissions=payload.get("permissions", []),
                    events=AgentEvents(
                        consumes=payload.get("consumes", []),
                        publishes=payload.get("publishes", []),
                    ),
                    tools=payload.get("tools", []),
                    dependencies=payload.get("dependencies", []),
                )
                path = create_agent_structure(schema)
                return {"data": {"path": str(path), "name": schema.name}, "error": None}

            elif task_type == "list":
                agents = []
                for d in AGENTS_DIR.iterdir():
                    if d.is_dir() and (d / "agent.yaml").exists():
                        agents.append(d.name)
                return {"data": {"agents": agents}, "error": None}

            elif task_type == "validate":
                name = payload.get("name", "")
                agent_path = AGENTS_DIR / name
                if not agent_path.exists():
                    return {"data": None, "error": f"Agente '{name}' no encontrado"}
                required = ["agent.yaml", "main.py", "prompts/system.md",
                           "src/tools.py", "src/handlers.py",
                           "docs/ARCHITECTURE.md", "docs/README.md",
                           "tests/test_main.py", "requirements.txt"]
                missing = [f for f in required if not (agent_path / f).exists()]
                return {"data": {"valid": len(missing) == 0, "missing": missing}, "error": None}

            else:
                return {"data": None, "error": f"Tipo de tarea no soportado: {task_type}"}

        except Exception as e:
            return {"data": None, "error": str(e)}


if __name__ == "__main__":
    import asyncio
    service = FactoryAgentService()
    asyncio.run(service.start())
