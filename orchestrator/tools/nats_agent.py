import asyncio
import json
import uuid
from nats.aio.client import Client as NATS
from datetime import datetime, timezone

NATS_URL = "nats://192.168.2.112:4222"
REQUEST_TIMEOUT = 120


class NATSAgentTool:
    """Tool para invocar un agente via NATS y esperar su respuesta."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.request_subject = f"agent.{agent_name}.request"
        self.response_subject = f"agent.{agent_name}.response"

    async def invoke(self, task_type: str, payload: dict, timeout: int = REQUEST_TIMEOUT) -> dict:
        nc = NATS()
        await nc.connect(NATS_URL)

        task_id = str(uuid.uuid4())
        response_future = asyncio.get_event_loop().create_future()

        async def on_response(msg):
            try:
                data = json.loads(msg.data.decode())
                if data.get("id") == task_id:
                    response_future.set_result(data)
            except Exception as e:
                if not response_future.done():
                    response_future.set_exception(e)

        sub = await nc.subscribe(self.response_subject, cb=on_response)

        await nc.publish(self.request_subject, json.dumps({
            "id": task_id,
            "type": task_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reply_to": self.response_subject,
        }).encode())

        try:
            result = await asyncio.wait_for(response_future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return {"status": "timeout", "error": f"Agente {self.agent_name} no respondio en {timeout}s"}
        finally:
            await sub.unsubscribe()
            await nc.drain()
