"""Cliente HTTP para la API del Orchestrator."""

import httpx

ORCHESTRATOR_URL = "http://192.168.2.112:8010"


class OrchestratorClient:
    def __init__(self, base_url: str = ORCHESTRATOR_URL):
        self.base_url = base_url

    async def health(self) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/health", timeout=5)
            return resp.json()

    async def create_workflow(self, objective: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/workflows",
                json={"objective": objective},
                timeout=30,
            )
            return resp.json()

    async def get_workflow(self, thread_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/workflows/{thread_id}", timeout=5)
            return resp.json()

    async def submit_decision(self, thread_id: str, decision: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/workflows/{thread_id}/decision",
                json={"decision": decision},
                timeout=5,
            )
            return resp.json()

    async def get_workflows_history(self, limit: int = 20) -> list:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/workflows?limit={limit}", timeout=5)
            return resp.json()
