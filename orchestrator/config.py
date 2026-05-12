from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://astrik:astrik_secret@localhost:5432/astrik",
    )
    nats_url: str = os.getenv("NATS_URL", "nats://localhost:4222")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    llama_api_url: str = os.getenv("LLAMA_API_URL", "http://localhost:8081/v1")
    llama_model: str = os.getenv("LLAMA_MODEL", "hermes3")
    orchestrator_component: str = os.getenv("ORCHESTRATOR_COMPONENT", "orchestrator")
    orchestrator_version: str = os.getenv("ORCHESTRATOR_VERSION", "v1.0.0")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
