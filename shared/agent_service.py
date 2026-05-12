import asyncio
import json
import uuid
import signal
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from .logger import CentralizedLogger
from .agent_config import get_agent_model

NATS_URL = "nats://192.168.2.112:4222"
HEARTBEAT_INTERVAL = 30


class AgentService(ABC):

    def __init__(self):
        self.nc = NATS()
        self.subscriptions = []
        self._running = False
        self._start_time = None
        self._current_task = None
        self.logger = CentralizedLogger(self.agent_name)

    @property
    @abstractmethod
    def agent_name(self) -> str: ...

    @property
    @abstractmethod
    def agent_version(self) -> str: ...

    @property
    def model(self) -> str:
        return get_agent_model(self.agent_name)

    @property
    def tools(self) -> list[str]:
        return []

    @property
    def events_consumes(self) -> list[str]:
        return [f"agent.{self.agent_name}.request", "agent.config.updated"]

    @property
    def events_publishes(self) -> list[str]:
        return [
            f"agent.{self.agent_name}.response",
            f"agent.{self.agent_name}.heartbeat",
            f"agent.{self.agent_name}.online",
            f"agent.{self.agent_name}.offline",
        ]

    async def start(self):
        self._start_time = datetime.now(timezone.utc)
        self._running = True

        await self.nc.connect(NATS_URL)
        await self.logger.info(f"Conectado a NATS en {NATS_URL}")

        await self._publish_online()

        for subject in self.events_consumes:
            sub = await self.nc.subscribe(subject, cb=self._on_message)
            self.subscriptions.append(sub)
            await self.logger.info(f"Escuchando en: {subject}")

        asyncio.create_task(self._heartbeat_loop())

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            except NotImplementedError:
                pass

        await self.logger.info("Servicio iniciado. Esperando eventos...")
        self._shutdown_event = asyncio.Event()
        await self._shutdown_event.wait()

    async def stop(self):
        self._running = False
        if hasattr(self, '_shutdown_event'):
            self._shutdown_event.set()
        await self._publish_offline()
        for sub in self.subscriptions:
            try:
                await sub.unsubscribe()
            except Exception:
                pass
        await self.nc.drain()
        await self.logger.info("Servicio detenido.")

    async def _on_message(self, msg: Msg):
        try:
            data = json.loads(msg.data.decode())

            # Handle config updates
            if msg.subject == "agent.config.updated":
                target = data.get("agent", "")
                if target == self.agent_name or target == "*":
                    await self.logger.info(f"Configuracion actualizada, recargando...")
                    await self._publish_online()
                return

            task_id = data.get("id", str(uuid.uuid4()))
            task_type = data.get("type", "unknown")
            payload = data.get("payload", {})
            reply_to = data.get("reply_to", f"agent.{self.agent_name}.response")

            await self.logger.info(f"Tarea recibida: {task_type}", task_id=task_id, task_type=task_type)
            self._current_task = task_id

            await self.nc.publish(reply_to, json.dumps({
                "id": task_id, "status": "running",
                "result": None, "error": None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }).encode())

            result = await self.execute_task(task_type, payload)
            self._current_task = None

            status = "completed" if result.get("error") is None else "failed"

            await self.nc.publish(reply_to, json.dumps({
                "id": task_id, "status": status,
                "result": result.get("data"),
                "error": result.get("error"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }).encode())

            await self.logger.info(f"Tarea {task_id}: {status}", task_id=task_id, status=status)

        except Exception as e:
            await self.logger.error(f"Error procesando mensaje: {e}", error=str(e))
            try:
                await self.nc.publish(msg.reply, json.dumps({
                    "id": "unknown", "status": "failed",
                    "result": None, "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }).encode())
            except Exception:
                pass

    @abstractmethod
    async def execute_task(self, task_type: str, payload: dict) -> dict:
        ...

    async def _publish_online(self):
        await self.nc.publish(f"agent.{self.agent_name}.online", json.dumps({
            "agent": self.agent_name, "version": self.agent_version,
            "model": self.model, "runtime": "llamacpp",
            "tools": self.tools,
            "events_consumes": self.events_consumes,
            "events_publishes": self.events_publishes,
            "status": "online"
        }).encode())

    async def _publish_offline(self):
        try:
            await self.nc.publish(f"agent.{self.agent_name}.offline", json.dumps({
                "agent": self.agent_name, "status": "offline"
            }).encode())
        except Exception:
            pass

    async def _heartbeat_loop(self):
        while self._running:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                await self.nc.publish(f"agent.{self.agent_name}.heartbeat", json.dumps({
                    "agent": self.agent_name, "version": self.agent_version,
                    "status": "busy" if self._current_task else "idle",
                    "uptime": (datetime.now(timezone.utc) - self._start_time).total_seconds(),
                    "current_task": self._current_task,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }).encode())
            except Exception:
                pass
