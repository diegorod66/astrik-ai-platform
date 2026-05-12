"""Configuracion de agentes persistida en Redis.
Cada agente tiene clave: agent:config:<nombre>:model
"""

from __future__ import annotations

import json

REDIS_HOST = "192.168.2.112"
REDIS_PORT = 6379
REDIS_DB = 0

AVAILABLE_MODELS = ["hermes3", "deepseek-coder", "phi4", "llama3", "mistral"]
DEFAULT_MODEL = "hermes3"

_redis = None


def _get_redis():
    global _redis
    if _redis is None:
        import redis
        _redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    return _redis


def get_agent_model(agent_name: str) -> str:
    r = _get_redis()
    val = r.get(f"agent:config:{agent_name}:model")
    return val if val else DEFAULT_MODEL


def set_agent_model(agent_name: str, model: str) -> None:
    if model not in AVAILABLE_MODELS:
        raise ValueError(f"Modelo no valido: {model}. Opciones: {AVAILABLE_MODELS}")
    r = _get_redis()
    r.set(f"agent:config:{agent_name}:model", model)


def get_all_configs() -> dict[str, str]:
    r = _get_redis()
    keys = r.keys("agent:config:*:model")
    configs = {}
    for key in keys:
        agent = key.split(":")[2]
        configs[agent] = r.get(key) or DEFAULT_MODEL
    return configs


def export_config() -> dict:
    return {
        "agents": get_all_configs(),
        "available_models": AVAILABLE_MODELS,
        "default_model": DEFAULT_MODEL,
    }
