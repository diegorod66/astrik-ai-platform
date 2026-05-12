from shared.agent_service import AgentService
from .src.tools import search_github, evaluate_tool, install_tool, test_tool, run_full_pipeline


class SkillsAgentService(AgentService):
    @property
    def agent_name(self): return "skills-agent"

    @property
    def agent_version(self): return "1.0.0"

    @property
    def tools(self): return ["search_github", "install", "test", "pipeline"]

    async def execute_task(self, task_type: str, payload: dict) -> dict:
        try:
            if task_type == "search":
                results = search_github(payload.get("query", ""), payload.get("max", 5))
                return {"data": results, "error": None}

            elif task_type == "evaluate":
                result = evaluate_tool(payload.get("candidate", {}))
                return {"data": result, "error": None}

            elif task_type == "install":
                result = install_tool(
                    payload.get("name", ""),
                    payload.get("type", "pip"),
                    payload.get("source", "")
                )
                return {"data": result, "error": None}

            elif task_type == "test":
                result = test_tool(
                    payload.get("name", ""),
                    payload.get("command", "")
                )
                return {"data": result, "error": None}

            elif task_type == "pipeline":
                result = run_full_pipeline(
                    payload.get("tool", ""),
                    payload.get("query", ""),
                    payload.get("type", "pip"),
                    payload.get("source", "")
                )
                return {"data": result, "error": None}

            else:
                return {"data": None, "error": f"Tipo de tarea no soportado: {task_type}"}

        except Exception as e:
            return {"data": None, "error": str(e)}


if __name__ == "__main__":
    import asyncio
    service = SkillsAgentService()
    asyncio.run(service.start())
