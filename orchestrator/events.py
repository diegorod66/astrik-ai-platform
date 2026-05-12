from __future__ import annotations

import json
import logging

from nats.aio.client import Client as NATS

from .config import settings


logger = logging.getLogger(__name__)


async def publish_event(subject: str, payload: dict) -> bool:
    nc = NATS()
    try:
        await nc.connect(settings.nats_url)
        await nc.publish(subject, json.dumps(payload).encode("utf-8"))
        await nc.flush()
        return True
    except Exception as exc:
        logger.warning("NATS publish failed for %s: %s", subject, exc)
        return False
    finally:
        try:
            await nc.close()
        except Exception:
            pass
