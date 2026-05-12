"""
Herramientas del Infra Agent.

Capacidades:
- generate_compose: generar docker-compose.yml completo
- add_service: agregar un servicio al compose existente
- check_health: verificar estado de servicios
- generate_env: generar .env desde template
- generate_ollama: configurar llama.cpp runtime
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
INFRA_DIR = PROJECT_ROOT / "infrastructure"


# --- Servicios disponibles ---

def _has_nvidia() -> bool:
    try:
        subprocess.run(["nvidia-smi"], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


SERVICE_TEMPLATES = {
    "postgres": {
        "image": "postgres:16-alpine",
        "container_name": "astrik-postgres",
        "ports": ["5432:5432"],
        "env_file": [".env"],
        "volumes": ["postgres_data:/var/lib/postgresql/data"],
        "healthcheck": {
            "test": ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-astrik}"],
            "interval": "10s",
            "retries": 5,
        },
        "networks": ["astrik-net"],
    },
    "redis": {
        "image": "redis:7-alpine",
        "container_name": "astrik-redis",
        "ports": ["6379:6379"],
        "volumes": ["redis_data:/data"],
        "healthcheck": {
            "test": ["CMD", "redis-cli", "ping"],
            "interval": "10s",
            "retries": 5,
        },
        "networks": ["astrik-net"],
    },
    "qdrant": {
        "image": "qdrant/qdrant:v1.13.6",
        "container_name": "astrik-qdrant",
        "ports": ["6333:6333", "6334:6334"],
        "volumes": ["qdrant_data:/qdrant/storage"],
        "healthcheck": {
            "test": ["CMD-SHELL", "bash -lc \"exec 3<>/dev/tcp/127.0.0.1/6333; printf 'GET /healthz HTTP/1.1\\r\\nHost: localhost\\r\\nConnection: close\\r\\n\\r\\n' >&3; grep -q '200 OK' <&3\""],
            "interval": "15s",
            "retries": 5,
        },
        "networks": ["astrik-net"],
    },
    "nats": {
        "image": "nats:2.10-alpine",
        "container_name": "astrik-nats",
        "ports": ["4222:4222", "8222:8222"],
        "volumes": ["nats_data:/data"],
        "healthcheck": {
            "test": ["CMD-SHELL", "wget -qO- http://localhost:8222/healthz || exit 1"],
            "interval": "15s",
            "retries": 5,
        },
        "networks": ["astrik-net"],
    },
    "llamacpp": {
        "build": {
            "context": ".",
            "dockerfile": "runtimes/llamacpp/Dockerfile",
        },
        "container_name": "astrik-llamacpp",
        "ports": ["${LLAMA_PORT:-8081}:8080"],
        "volumes": [
            "llamacpp_models:/models",
            "./runtimes/llamacpp:/app",
        ],
        "deploy": {
            "resources": {
                "reservations": {"devices": [{"driver": "nvidia", "count": 1, "capabilities": ["gpu"]}]}
            }
        } if _has_nvidia() else {},
        "environment": {
            "LLAMA_MODEL": "${LLAMA_MODEL:-hermes3}",
            "LLAMA_N_GPU_LAYERS": "${LLAMA_N_GPU_LAYERS:-35}",
            "LLAMA_CTX_SIZE": "${LLAMA_CTX_SIZE:-8192}",
        },
        "healthcheck": {
            "test": ["CMD-SHELL", "curl -sf http://localhost:8080/health || exit 1"],
            "interval": "30s",
            "retries": 3,
        },
        "networks": ["astrik-net"],
    },
    "monitoring": {
        "services": {
            "prometheus": {
                "image": "prom/prometheus:latest",
                "container_name": "astrik-prometheus",
                "ports": ["9090:9090"],
                "volumes": ["./infrastructure/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml"],
                "networks": ["astrik-net"],
            },
            "grafana": {
                "image": "grafana/grafana:latest",
                "container_name": "astrik-grafana",
                "ports": ["3001:3000"],
                "volumes": ["grafana_data:/var/lib/grafana"],
                "networks": ["astrik-net"],
            },
        }
    },
}


# --- Generadores ---

def generate_env(services: list[str] | None = None) -> str:
    """Generar archivo .env con configuración base."""
    env = {
        "PROJECT_NAME": "astrik-ai-platform",
        "ENVIRONMENT": "development",

        # Postgres
        "POSTGRES_USER": "astrik",
        "POSTGRES_PASSWORD": "astrik_secret",
        "POSTGRES_DB": "astrik",
        "POSTGRES_PORT": "5433",

        # Redis
        "REDIS_PORT": "6379",

        # Qdrant
        "QDRANT_PORT": "6333",
        "QDRANT_GRPC_PORT": "6334",

        # NATS
        "NATS_PORT": "4222",
        "NATS_MONITOR_PORT": "8222",

        # llama.cpp
        "LLAMA_MODEL": "hermes3",
        "LLAMA_N_GPU_LAYERS": "35",
        "LLAMA_CTX_SIZE": "8192",
        "LLAMA_PORT": "8081",
    }
    return "\n".join(f"{k}={v}" for k, v in env.items()) + "\n"


def generate_compose(services: list[str] | None = None) -> str:
    """Generar docker-compose.yml completo."""
    INFRA_DIR.mkdir(parents=True, exist_ok=True)

    # .env
    env_path = INFRA_DIR / ".env"
    env_content = generate_env()
    if not env_path.exists():
        env_path.write_text(env_content, encoding="utf-8")
        # Also copy .env.example
        example_path = INFRA_DIR / ".env.example"
        example_path.write_text(env_content, encoding="utf-8")

    selected = services or ["postgres", "redis", "qdrant", "nats"]
    compose = {
        "version": "3.8",
        "name": "astrik-ai-platform",
        "networks": {
            "astrik-net": {
                "driver": "bridge",
                "ipam": {"config": [{"subnet": "172.20.0.0/16"}]},
            }
        },
        "volumes": {},
        "services": {},
    }

    for svc in selected:
        if svc not in SERVICE_TEMPLATES:
            continue
        tmpl = SERVICE_TEMPLATES[svc]
        if svc == "monitoring":
            for sub_name, sub_tmpl in tmpl["services"].items():
                compose["services"][sub_name] = sub_tmpl
            continue

        compose["services"][svc] = dict(tmpl)
        # Add volumes
        for vol_def in tmpl.get("volumes", []):
            vol_name = vol_def.split(":")[0]
            if vol_name not in ("/var/lib/postgresql/data", "/data", "/qdrant/storage", "/app", "/models"):
                compose["volumes"][vol_name] = {"driver": "local"}

    # Save compose
    compose_path = INFRA_DIR / "docker-compose.yml"
    import yaml
    with open(compose_path, "w", encoding="utf-8") as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Save also as JSON for reference
    meta_path = INFRA_DIR / ".compose-services.json"
    meta_path.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(),
        "services": selected,
        "compose_file": str(compose_path),
    }, indent=2), encoding="utf-8")

    return str(compose_path)


def add_service(name: str, custom_config: dict | None = None) -> dict:
    """Agregar un servicio al docker-compose existente."""
    compose_path = INFRA_DIR / "docker-compose.yml"
    if not compose_path.exists():
        return {"status": "error", "error": "No existe docker-compose.yml. Ejecuta generate primero."}

    import yaml
    with open(compose_path, encoding="utf-8") as f:
        compose = yaml.safe_load(f) or {}

    if name in compose.get("services", {}):
        return {"status": "exists", "service": name}

    tmpl = custom_config or SERVICE_TEMPLATES.get(name)
    if not tmpl:
        return {"status": "error", "error": f"Servicio '{name}' no definido en templates"}

    if "services" not in compose:
        compose["services"] = {}
    compose["services"][name] = tmpl

    # Add volumes
    for vol_def in tmpl.get("volumes", []):
        vol_name = vol_def.split(":")[0]
        if "volumes" not in compose:
            compose["volumes"] = {}
        compose["volumes"][vol_name] = {"driver": "local"}

    # Add networks
    if "networks" not in compose:
        compose["networks"] = {}
    if "astrik-net" not in compose.get("networks", {}):
        compose["networks"]["astrik-net"] = {"driver": "bridge"}

    with open(compose_path, "w", encoding="utf-8") as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False)

    return {"status": "added", "service": name, "path": str(compose_path)}


def check_health(service: str | None = None) -> dict:
    """Verificar estado de servicios via docker ps."""
    try:
        cmd = ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if proc.returncode != 0:
            return {"status": "error", "error": proc.stderr.strip(), "docker_installed": False}

        lines = proc.stdout.strip().split("\n")
        all_services = []
        for line in lines:
            parts = line.split("\t")
            if len(parts) >= 2:
                all_services.append({"name": parts[0], "status": parts[1], "ports": parts[2] if len(parts) > 2 else ""})

        if service:
            filtered = [s for s in all_services if service in s["name"]]
            return {"status": "ok", "services": filtered, "docker_installed": True}
        return {"status": "ok", "services": all_services, "docker_installed": True}

    except FileNotFoundError:
        return {"status": "error", "error": "Docker no instalado", "docker_installed": False}


def generate_monitoring() -> str:
    """Generar config de Prometheus."""
    monitor_dir = INFRA_DIR / "monitoring"
    monitor_dir.mkdir(parents=True, exist_ok=True)

    prom_config = """global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'orchestrator'
    static_configs:
      - targets: ['host.docker.internal:8000']

  - job_name: 'nats'
    static_configs:
      - targets: ['astrik-nats:8222']

  - job_name: 'qdrant'
    static_configs:
      - targets: ['astrik-qdrant:6333']
"""
    prom_path = monitor_dir / "prometheus.yml"
    prom_path.write_text(prom_config, encoding="utf-8")

    return str(prom_path)


def generate_llamacpp_dockerfile() -> str:
    """Generar Dockerfile para llama.cpp runtime."""
    runtime_dir = PROJECT_ROOT / "runtimes" / "llamacpp"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    dockerfile = """FROM nvidia/cuda:12.4-devel-ubuntu22.04

RUN apt-get update && apt-get install -y \\
    build-essential cmake git curl \\
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/ggerganov/llama.cpp /llama.cpp
WORKDIR /llama.cpp
RUN mkdir build && cd build && \\
    cmake .. -DLLAMA_CUDA=ON -DLLAMA_NATIVE=OFF && \\
    make -j$(nproc)

RUN ln -s /llama.cpp/build/bin/server /usr/local/bin/llama-server

VOLUME ["/models"]
EXPOSE 8080

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
"""
    (runtime_dir / "Dockerfile").write_text(dockerfile, encoding="utf-8")

    entrypoint = """#!/bin/bash
MODEL_PATH=${LLAMA_MODEL_PATH:-/models/${LLAMA_MODEL:-hermes3}.gguf}

if [ ! -f "$MODEL_PATH" ]; then
    echo "ERROR: Modelo no encontrado en $MODEL_PATH"
    echo "Descarga el modelo con: curl -L {url} -o $MODEL_PATH"
    exit 1
fi

exec /usr/local/bin/llama-server \\
    -m "$MODEL_PATH" \\
    --host 0.0.0.0 \\
    --port ${LLAMA_PORT:-8080} \\
    --n-gpu-layers ${LLAMA_N_GPU_LAYERS:-35} \\
    --ctx-size ${LLAMA_CTX_SIZE:-8192}
"""
    (runtime_dir / "entrypoint.sh").write_text(entrypoint, encoding="utf-8")

    return str(runtime_dir)


def run_full_build(services: list[str] | None = None) -> dict:
    """Pipeline completo: generar compose, env, monitoring, Dockerfile."""
    compose_path = generate_compose(services)
    env_path = str(INFRA_DIR / ".env")
    monitor_path = generate_monitoring()
    llamacpp_path = generate_llamacpp_dockerfile()

    return {
        "status": "completed",
        "compose_file": compose_path,
        "env_file": env_path,
        "monitoring": monitor_path,
        "llamacpp_runtime": llamacpp_path,
        "services": services or ["postgres", "redis", "qdrant", "nats"],
        "generated_at": datetime.now().isoformat(),
    }
