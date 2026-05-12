"""Cliente NATS para el Dashboard.
Escucha heartbeats, logs y eventos de workflow en tiempo real."""

import asyncio
import json
import threading
from datetime import datetime, timezone
from nats.aio.client import Client as NATS

NATS_URL = "nats://192.168.2.112:4222"


class DashboardNATSClient:
    def __init__(self):
        self.nc = NATS()
        self.agents = {}
        self.workflows = []
        self.logs = []
        self._callbacks = []
        self._connected = False

    def on_event(self, callback):
        self._callbacks.append(callback)

    def _emit(self, event_type: str, data: dict):
        for cb in self._callbacks:
            try:
                cb(event_type, data)
            except Exception:
                pass

    async def connect(self):
        await self.nc.connect(NATS_URL)
        self._connected = True

        await self.nc.subscribe("agent.*.heartbeat", cb=self._on_heartbeat)
        await self.nc.subscribe("agent.*.online", cb=self._on_online)
        await self.nc.subscribe("agent.*.offline", cb=self._on_offline)
        await self.nc.subscribe("workflow.*", cb=self._on_workflow_event)

    async def _on_heartbeat(self, msg):
        data = json.loads(msg.data.decode())
        agent = data.get("agent", "unknown")
        self.agents[agent] = {
            **data,
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }
        self._emit("heartbeat", data)

    async def _on_online(self, msg):
        data = json.loads(msg.data.decode())
        agent = data.get("agent", "unknown")
        self.agents[agent] = {**data, "last_seen": datetime.now(timezone.utc).isoformat()}
        self._emit("online", data)

    async def _on_offline(self, msg):
        data = json.loads(msg.data.decode())
        agent = data.get("agent", "unknown")
        if agent in self.agents:
            self.agents[agent]["status"] = "offline"
        self._emit("offline", data)

    async def _on_workflow_event(self, msg):
        data = json.loads(msg.data.decode())
        self.workflows.insert(0, data)
        self.workflows = self.workflows[:100]
        self._emit("workflow", data)

    def get_agents_status(self) -> list[dict]:
        result = []
        now = datetime.now(timezone.utc)
        for name, data in self.agents.items():
            last_str = data.get("last_seen", now.isoformat())
            try:
                last = datetime.fromisoformat(last_str)
            except Exception:
                last = now
            delta = (now - last).total_seconds()
            status = data.get("status", "unknown")
            if status == "online" and delta > 90:
                status = "warning"
            if status == "online" and delta > 180:
                status = "offline"
            result.append({
                "name": name,
                "status": status,
                "version": data.get("version", "?"),
                "model": data.get("model", "?"),
                "tools": data.get("tools", []),
                "current_task": data.get("current_task"),
                "uptime": data.get("uptime", 0),
                "last_seen": data.get("last_seen", ""),
            })
        return result

    def start_background(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def runner():
            await self.connect()
            while True:
                await asyncio.sleep(1)

        thread = threading.Thread(target=loop.run_until_complete, args=(runner(),), daemon=True)
        thread.start()
        return thread
