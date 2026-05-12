from shared.agent_service import AgentService
from .src.tools import run_full_build, add_service, check_health, generate_env


class InfraAgentService(AgentService):
    @property
    def agent_name(self): return "infra-agent"

    @property
    def agent_version(self): return "1.0.0"

    @property
    def model(self): return "deepseek-coder"

    @property
    def tools(self): return ["build", "add_service", "health", "gen_env"]

    async def execute_task(self, task_type: str, payload: dict) -> dict:
        try:
            if task_type == "build":
                result = run_full_build(payload.get("services"))
                return {"data": result, "error": None}

            elif task_type == "add_service":
                result = add_service(
                    payload.get("name", ""),
                    payload.get("config")
                )
                return {"data": result, "error": None}

            elif task_type == "health":
                result = check_health(payload.get("service", ""))
                return {"data": result, "error": None}

            elif task_type == "gen_env":
                env = generate_env(payload.get("services"))
                return {"data": {"env": env}, "error": None}

            else:
                return {"data": None, "error": f"Tipo de tarea no soportado: {task_type}"}

        except Exception as e:
            return {"data": None, "error": str(e)}


if __name__ == "__main__":
    import asyncio
    service = InfraAgentService()
    asyncio.run(service.start())
