#!/usr/bin/env python3
from shared.agent_service import AgentService
import subprocess
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RELEASE_SCRIPT = ROOT / "scripts" / "release.py"


class VersionAgentService(AgentService):
    @property
    def agent_name(self): return "version-agent"

    @property
    def agent_version(self): return "1.0.0"

    @property
    def model(self): return "phi4"

    @property
    def tools(self): return ["snapshot", "bump", "list", "current"]

    def _run_release(self, *args) -> dict:
        try:
            result = subprocess.run(
                ["python", str(RELEASE_SCRIPT)] + list(args),
                capture_output=True, text=True, timeout=60
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"returncode": -1, "stdout": "", "stderr": "Timeout"}
        except Exception as e:
            return {"returncode": -1, "stdout": "", "stderr": str(e)}

    async def execute_task(self, task_type: str, payload: dict) -> dict:
        try:
            if task_type == "snapshot":
                componente = payload.get("componente", "")
                version = payload.get("version", "")
                args = ["snapshot", componente]
                if version:
                    args.append(version)
                result = self._run_release(*args)
                return {"data": result, "error": None if result["returncode"] == 0 else result["stderr"]}

            elif task_type == "bump":
                part = payload.get("part", "patch")
                result = self._run_release("bump", part)
                return {"data": result, "error": None if result["returncode"] == 0 else result["stderr"]}

            elif task_type == "list":
                componente = payload.get("componente", "")
                args = ["list"]
                if componente:
                    args.append(componente)
                result = self._run_release(*args)
                return {"data": result, "error": None}

            elif task_type == "current":
                result = self._run_release("current")
                return {"data": result, "error": None}

            else:
                return {"data": None, "error": f"Tipo de tarea no soportado: {task_type}"}

        except Exception as e:
            return {"data": None, "error": str(e)}


if __name__ == "__main__":
    import asyncio
    service = VersionAgentService()
    asyncio.run(service.start())
