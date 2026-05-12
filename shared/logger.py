"""Logger centralizado con Redis pub/sub.
Cada servicio publica logs estructurados en Redis.
El dashboard los consume en vivo."""

import json
from datetime import datetime, timezone

import redis.asyncio as aioredis

REDIS_URL = "redis://192.168.2.112:6379/0"
LOG_CHANNEL = "astrik:logs"


class CentralizedLogger:
    """Logger que publica en Redis pub/sub.
    Usar: logger = CentralizedLogger("skills-agent")
          await logger.info("Servicio iniciado")
          await logger.error("Algo fallo", task_id="xxx")
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self._redis = None

    async def _connect(self):
        if self._redis is None:
            self._redis = aioredis.from_url(REDIS_URL, decode_responses=True)

    async def _publish(self, level: str, message: str, **extra):
        await self._connect()
        entry = {
            "service": self.service_name,
            "level": level,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
        try:
            await self._redis.publish(LOG_CHANNEL, json.dumps(entry))
        except Exception:
            pass

    async def info(self, message: str, **extra):
        await self._publish("INFO", message, **extra)

    async def error(self, message: str, **extra):
        await self._publish("ERROR", message, **extra)

    async def warn(self, message: str, **extra):
        await self._publish("WARN", message, **extra)

    async def debug(self, message: str, **extra):
        await self._publish("DEBUG", message, **extra)

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None
