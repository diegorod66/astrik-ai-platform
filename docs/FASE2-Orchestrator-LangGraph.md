# FASE 2: Orchestrator con LangGraph

## Objetivo

Este archivo es autocontenido y esta pensado para darselo a otra IA para implementar la Fase 2 completa del proyecto Astrik.

La meta es construir un `orchestrator/` en Python sobre LangGraph que:

1. Reciba un objetivo del usuario.
2. Lo divida en tareas.
3. Ejecute tareas usando agentes ya existentes del repo.
4. Valide resultados.
5. Versione el resultado final.
6. Persista estado con checkpoints en PostgreSQL.
7. Publique eventos de ciclo de vida por NATS.

## Contexto del Proyecto

Astrik AI Platform ya tiene una base funcional. Este repo ya incluye:

- `agents/agent-factory/`: crea agentes estandarizados con `agent.yaml`, estructura base y validacion.
- `agents/skills-agent/`: busca en GitHub, evalua, instala, prueba y documenta herramientas.
- `agents/infra-agent/`: genera `infrastructure/docker-compose.yml`, `.env`, monitoreo y runtime de `llama.cpp`.
- `scripts/release.py`: crea snapshots versionados, actualiza `CHANGELOG.md`, `VERSIONS.md` y genera tags.
- `infrastructure/docker-compose.yml`: ya define PostgreSQL, Redis, Qdrant y NATS.

Estado actual importante:

- El stack objetivo ya esta definido: Python 3.12+, FastAPI, PostgreSQL, Redis, Qdrant, NATS, llama.cpp.
- Los agentes actuales existen, pero funcionan como CLI o librerias locales; todavia no hay orquestacion autonoma.
- `scripts/release.py` ya acepta `python scripts/release.py snapshot orchestrator v1.0.0` siempre que exista una carpeta raiz `orchestrator/`.

## Arquitectura Objetivo

```mermaid
flowchart TD
    A[Usuario o API Client] --> B[FastAPI /workflows]
    B --> C[LangGraph StateGraph]
    C --> D[Planner Node]
    D --> E[Executor Node]
    E --> F[Validator Node]
    F -->|ok| G[Deployer Node]
    F -->|retry| E
    G --> H[Respuesta final]

    C --> I[(PostgreSQL Checkpoints)]
    D --> J[NATS Publisher]
    E --> J
    F --> J
    G --> J

    E --> K[Skills Agent Tools]
    E --> L[Infra Agent Tools]
    E --> M[Agent Factory Tools]
    G --> N[release.py]
    D --> O[llama.cpp OpenAI-compatible API]
```

## Flujo Funcional

1. FastAPI recibe un `objective`.
2. Se crea un `thread_id` para LangGraph.
3. `planner` convierte el objetivo en una lista de tareas.
4. `executor` toma la siguiente tarea pendiente y decide que herramienta usar.
5. `validator` revisa el resultado y decide `retry`, `continue` o `completed`.
6. `deployer` ejecuta snapshot/versionado cuando el flujo termino bien.
7. Cada transicion publica eventos en NATS.
8. Todo el estado queda persistido en PostgreSQL mediante checkpoints.

## Estructura de Directorios a Crear

```text
orchestrator/
  __init__.py
  requirements.txt
  .env.example
  config.py
  state.py
  db.py
  graph.py
  models.py
  server.py
  events.py
  llm.py
  nodes/
    __init__.py
    planner.py
    executor.py
    validator.py
    deployer.py
  tools/
    __init__.py
    registry.py
    existing_agents.py
  tests/
    test_smoke.py
```

## Reglas de Implementacion

1. Mantener `orchestrator/` como componente raiz independiente.
2. Reusar codigo real de `agents/skills-agent/src/tools.py`, `agents/infra-agent/src/tools.py` y `scripts/release.py`.
3. No duplicar logica si puede envolverse como tool.
4. Usar nombres de estado y eventos estables para que luego se puedan integrar mas agentes.
5. Asumir que llama.cpp expone una API compatible con OpenAI en `http://localhost:8080/v1`.

## Paso 1: Instalar dependencias

Crear `orchestrator/requirements.txt`:

```txt
fastapi==0.115.12
uvicorn[standard]==0.34.2
langgraph==0.4.7
langchain==0.3.25
langchain-openai==0.3.17
langchain-core==0.3.60
langgraph-checkpoint-postgres==2.0.21
psycopg[binary,pool]==3.2.7
nats-py==2.9.0
python-dotenv==1.0.1
pydantic==2.11.4
httpx==0.28.1
PyYAML==6.0.2
```

Instalacion:

```bash
pip install -r orchestrator/requirements.txt
```

Verificacion:

```bash
python -c "import fastapi, langgraph, nats, psycopg, yaml; print('deps ok')"
```

## Paso 2: State definition con TypedDict

Crear `orchestrator/state.py`:

```python
from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


WorkflowStatus = Literal["pending", "running", "retrying", "completed", "failed"]


class TaskItem(TypedDict):
    id: str
    title: str
    kind: str
    status: Literal["pending", "running", "completed", "failed"]
    tool: str


class OrchestratorState(TypedDict, total=False):
    objective: str
    messages: Annotated[list[Any], add_messages]
    plan: list[TaskItem]
    current_task_id: str | None
    current_task_index: int
    last_result: dict[str, Any]
    task_results: dict[str, dict[str, Any]]
    artifacts: dict[str, str]
    retries: int
    max_retries: int
    status: WorkflowStatus
    validation_notes: list[str]
    errors: list[str]
    version: str | None
```

Estado minimo al iniciar:

```python
initial_state: OrchestratorState = {
    "objective": "Crear infraestructura base con PostgreSQL y NATS",
    "messages": [],
    "plan": [],
    "current_task_id": None,
    "current_task_index": 0,
    "last_result": {},
    "task_results": {},
    "artifacts": {},
    "retries": 0,
    "max_retries": 2,
    "status": "pending",
    "validation_notes": [],
    "errors": [],
    "version": None,
}
```

## Paso 3: Config desde `.env`

Crear `orchestrator/.env.example`:

```env
DATABASE_URL=postgresql://astrik:astrik_secret@localhost:5432/astrik
NATS_URL=nats://localhost:4222
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
LLAMA_API_URL=http://localhost:8080/v1
LLAMA_MODEL=hermes3
ORCHESTRATOR_COMPONENT=orchestrator
ORCHESTRATOR_VERSION=v1.0.0
LOG_LEVEL=INFO
```

Crear `orchestrator/config.py`:

```python
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
    llama_api_url: str = os.getenv("LLAMA_API_URL", "http://localhost:8080/v1")
    llama_model: str = os.getenv("LLAMA_MODEL", "hermes3")
    orchestrator_component: str = os.getenv("ORCHESTRATOR_COMPONENT", "orchestrator")
    orchestrator_version: str = os.getenv("ORCHESTRATOR_VERSION", "v1.0.0")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
```

## Paso 4: LangGraph Checkpointer con PostgreSQL

Crear `orchestrator/db.py`:

```python
from __future__ import annotations

from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from .config import settings


pool = AsyncConnectionPool(
    conninfo=settings.database_url,
    max_size=20,
    kwargs={"autocommit": True},
    open=False,
)


@asynccontextmanager
async def lifespan_checkpointer():
    await pool.open()
    saver = AsyncPostgresSaver(pool)
    await saver.setup()
    try:
        yield saver
    finally:
        await pool.close()
```

Notas:

- Este paso permite que cada `thread_id` tenga checkpoints recuperables.
- Usar `postgresql://...`, no `postgresql+asyncpg://...`, porque aqui la conexion la maneja `psycopg`.

Verificacion:

```bash
docker compose -f infrastructure/docker-compose.yml up -d postgres
```

## Paso 5: Graph definition con `StateGraph`

Crear `orchestrator/graph.py`:

```python
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes.deployer import deployer_node
from .nodes.executor import executor_node
from .nodes.planner import planner_node
from .nodes.validator import validator_node
from .state import OrchestratorState


def route_after_planner(state: OrchestratorState) -> str:
    return "executor" if state.get("plan") else "failed"


def route_after_validator(state: OrchestratorState) -> str:
    status = state.get("status")
    if status == "completed":
        return "deployer"
    if status == "retrying":
        return "executor"
    if status == "failed":
        return "failed"
    return "executor"


def build_graph(checkpointer):
    builder = StateGraph(OrchestratorState)

    builder.add_node("planner", planner_node)
    builder.add_node("executor", executor_node)
    builder.add_node("validator", validator_node)
    builder.add_node("deployer", deployer_node)

    builder.add_edge(START, "planner")
    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "executor": "executor",
            "failed": END,
        },
    )
    builder.add_edge("executor", "validator")
    builder.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "executor": "executor",
            "deployer": "deployer",
            "failed": END,
        },
    )
    builder.add_edge("deployer", END)

    return builder.compile(checkpointer=checkpointer)
```

## Paso 6: Nodo Planner

Crear `orchestrator/llm.py`:

```python
from __future__ import annotations

import json

from langchain_openai import ChatOpenAI

from .config import settings


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llama_model,
        api_key="not-needed",
        base_url=settings.llama_api_url,
        temperature=0,
    )


async def plan_objective(objective: str) -> list[dict]:
    llm = get_llm()
    prompt = f"""
Divide el siguiente objetivo en tareas ejecutables.

Objetivo:
{objective}

Devuelve SOLO JSON con esta forma:
[
  {{"id": "task-1", "title": "...", "kind": "research|install|infra|factory|release", "tool": "..."}}
]
""".strip()
    response = await llm.ainvoke(prompt)
    content = response.content if isinstance(response.content, str) else str(response.content)
    data = json.loads(content)
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "kind": item["kind"],
            "status": "pending",
            "tool": item["tool"],
        }
        for item in data
    ]
```

Crear `orchestrator/nodes/planner.py`:

```python
from __future__ import annotations

from langchain_core.messages import AIMessage

from ..events import publish_event
from ..llm import plan_objective
from ..state import OrchestratorState


async def planner_node(state: OrchestratorState) -> dict:
    objective = state["objective"]
    plan = await plan_objective(objective)

    await publish_event(
        "workflow.started",
        {
            "objective": objective,
            "task_count": len(plan),
        },
    )

    return {
        "plan": plan,
        "status": "running",
        "messages": [AIMessage(content=f"Plan generado con {len(plan)} tareas")],
        "current_task_index": 0,
    }
```

Responsabilidad del planner:

- Convertir un objetivo libre en tareas cortas y ejecutables.
- Asignar `tool` sugerida desde el principio para reducir heuristicas luego.

## Paso 7: Nodo Executor

Este nodo debe tomar la tarea actual, resolver que tool usar y ejecutar codigo real del repo.

Crear `orchestrator/tools/existing_agents.py`:

```python
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar modulo desde {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


skills_tools = _load_module(
    "skills_agent_tools",
    ROOT / "agents" / "skills-agent" / "src" / "tools.py",
)

infra_tools = _load_module(
    "infra_agent_tools",
    ROOT / "agents" / "infra-agent" / "src" / "tools.py",
)


def search_github_tool(query: str, max_results: int = 5) -> list[dict]:
    return skills_tools.search_github(query, max_results)


def install_tool(name: str, install_type: str = "pip", source: str = "") -> dict:
    return skills_tools.install_tool(name, install_type, source)


def run_skill_pipeline(tool_name: str, github_query: str = "", install_type: str = "pip") -> dict:
    return skills_tools.run_full_pipeline(tool_name, github_query, install_type)


def generate_compose_tool(services: list[str] | None = None) -> str:
    return infra_tools.generate_compose(services)


def generate_env_tool(services: list[str] | None = None) -> str:
    return infra_tools.generate_env(services)
```

Crear `orchestrator/tools/registry.py`:

```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .existing_agents import (
    generate_compose_tool,
    generate_env_tool,
    install_tool,
    run_skill_pipeline,
    search_github_tool,
)


ROOT = Path(__file__).resolve().parents[2]


def create_agent_tool(name: str, description: str) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "agents" / "agent-factory" / "main.py"),
        "create",
        "--name",
        name,
        "--desc",
        description,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    return {
        "status": "completed" if proc.returncode == 0 else "failed",
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def snapshot_tool(component: str, version: str) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "release.py"),
        "snapshot",
        component,
        version,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    return {
        "status": "completed" if proc.returncode == 0 else "failed",
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


TOOL_REGISTRY = {
    "search_github": search_github_tool,
    "install_tool": install_tool,
    "skills_pipeline": run_skill_pipeline,
    "generate_compose": generate_compose_tool,
    "generate_env": generate_env_tool,
    "create_agent": create_agent_tool,
    "snapshot": snapshot_tool,
}
```

Crear `orchestrator/nodes/executor.py`:

```python
from __future__ import annotations

from langchain_core.messages import AIMessage

from ..events import publish_event
from ..state import OrchestratorState
from ..tools.registry import TOOL_REGISTRY


def _pick_tool(task: dict) -> str:
    if task.get("tool"):
        return task["tool"]

    kind = task.get("kind", "")
    mapping = {
        "research": "search_github",
        "install": "skills_pipeline",
        "infra": "generate_compose",
        "factory": "create_agent",
        "release": "snapshot",
    }
    return mapping.get(kind, "search_github")


def _build_tool_args(task: dict) -> dict:
    title = task["title"].lower()

    if task["tool"] == "search_github":
        return {"query": task["title"], "max_results": 5}
    if task["tool"] == "skills_pipeline":
        return {"tool_name": task["title"].split()[-1], "github_query": task["title"]}
    if task["tool"] == "generate_compose":
        return {"services": ["postgres", "redis", "qdrant", "nats"]}
    if task["tool"] == "create_agent":
        return {"name": "new-agent", "description": task["title"]}
    if task["tool"] == "snapshot":
        return {"component": "orchestrator", "version": "v1.0.0"}

    if "docker" in title or "infra" in title:
        return {"services": ["postgres", "redis", "qdrant", "nats"]}

    return {"query": task["title"], "max_results": 5}


async def executor_node(state: OrchestratorState) -> dict:
    plan = list(state.get("plan", []))
    index = state.get("current_task_index", 0)

    if index >= len(plan):
        return {"status": "completed"}

    task = dict(plan[index])
    tool_name = _pick_tool(task)
    task["tool"] = tool_name
    task["status"] = "running"
    args = _build_tool_args(task)

    await publish_event(
        "task.started",
        {
            "task_id": task["id"],
            "title": task["title"],
            "tool": tool_name,
        },
    )

    result = TOOL_REGISTRY[tool_name](**args)

    task["status"] = "completed" if result else "failed"
    plan[index] = task
    task_results = dict(state.get("task_results", {}))
    task_results[task["id"]] = result

    return {
        "plan": plan,
        "current_task_id": task["id"],
        "last_result": result,
        "task_results": task_results,
        "messages": [AIMessage(content=f"Ejecutada tarea {task['id']} con tool {tool_name}")],
    }
```

Routing esperado de tareas:

- `research` o texto con "buscar" -> `search_github`
- `install` o texto con "instalar" -> `skills_pipeline`
- `infra` o texto con "docker/compose" -> `generate_compose`
- `factory` o texto con "crear agente" -> `create_agent`
- `release` o texto con "versionar" -> `snapshot`

## Paso 8: Nodo Validator

Crear `orchestrator/nodes/validator.py`:

```python
from __future__ import annotations

from langchain_core.messages import AIMessage

from ..events import publish_event
from ..state import OrchestratorState


def _result_ok(result: dict) -> bool:
    if not result:
        return False
    status = result.get("status")
    if status in {"completed", "installed", "working"}:
        return True
    if isinstance(result, str) and result:
        return True
    if result.get("error") or result.get("stderr"):
        return False
    return True


async def validator_node(state: OrchestratorState) -> dict:
    plan = list(state.get("plan", []))
    index = state.get("current_task_index", 0)
    current_task_id = state.get("current_task_id")
    result = dict(state.get("last_result", {}))
    retries = state.get("retries", 0)
    max_retries = state.get("max_retries", 2)
    notes = list(state.get("validation_notes", []))
    errors = list(state.get("errors", []))

    if _result_ok(result):
        if index < len(plan):
            plan[index]["status"] = "completed"
        next_index = index + 1
        done = next_index >= len(plan)

        await publish_event(
            "task.completed",
            {"task_id": current_task_id, "next_index": next_index},
        )

        return {
            "plan": plan,
            "current_task_index": next_index,
            "status": "completed" if done else "running",
            "retries": 0,
            "validation_notes": notes + [f"Tarea {current_task_id} validada"],
            "messages": [AIMessage(content=f"Validator aprobo {current_task_id}")],
        }

    if retries < max_retries:
        await publish_event(
            "task.retry",
            {"task_id": current_task_id, "retry": retries + 1},
        )
        return {
            "status": "retrying",
            "retries": retries + 1,
            "validation_notes": notes + [f"Retry {retries + 1} para {current_task_id}"],
            "messages": [AIMessage(content=f"Validator pide retry para {current_task_id}")],
        }

    errors.append(f"La tarea {current_task_id} fallo tras {max_retries} reintentos")

    await publish_event(
        "task.failed",
        {"task_id": current_task_id, "errors": errors[-1]},
    )

    return {
        "status": "failed",
        "errors": errors,
        "messages": [AIMessage(content=f"Validator marco fallo definitivo en {current_task_id}")],
    }
```

Responsabilidad del validator:

- Aceptar resultados buenos.
- Pedir reintento si hay fallo recuperable.
- Cortar workflow si ya se agotaron los reintentos.

## Paso 9: Nodo Deployer

Crear `orchestrator/nodes/deployer.py`:

```python
from __future__ import annotations

from langchain_core.messages import AIMessage

from ..config import settings
from ..events import publish_event
from ..state import OrchestratorState
from ..tools.registry import snapshot_tool


async def deployer_node(state: OrchestratorState) -> dict:
    result = snapshot_tool(
        component=settings.orchestrator_component,
        version=settings.orchestrator_version,
    )

    status = "completed" if result.get("status") == "completed" else "failed"

    await publish_event(
        "workflow.finished",
        {
            "component": settings.orchestrator_component,
            "version": settings.orchestrator_version,
            "status": status,
        },
    )

    return {
        "version": settings.orchestrator_version,
        "status": status,
        "last_result": result,
        "messages": [AIMessage(content=f"Snapshot {settings.orchestrator_version} ejecutado")],
    }
```

Efecto esperado del deployer:

- Crear `releases/orchestrator-v1.0.0/`
- Actualizar `CHANGELOG.md`
- Actualizar `VERSIONS.md`
- Crear tag `orchestrator-v1.0.0`

## Paso 10: FastAPI Server

Crear `orchestrator/models.py`:

```python
from pydantic import BaseModel, Field


class WorkflowCreateRequest(BaseModel):
    objective: str = Field(min_length=5)


class WorkflowCreateResponse(BaseModel):
    thread_id: str
    status: str
```

Crear `orchestrator/server.py`:

```python
from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from .db import lifespan_checkpointer
from .graph import build_graph
from .models import WorkflowCreateRequest, WorkflowCreateResponse
from .state import OrchestratorState


graph = None


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    global graph
    async with lifespan_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)
        yield


app = FastAPI(title="Astrik Orchestrator", lifespan=app_lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}


@app.post("/workflows", response_model=WorkflowCreateResponse)
async def create_workflow(payload: WorkflowCreateRequest):
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    initial_state: OrchestratorState = {
        "objective": payload.objective,
        "messages": [],
        "plan": [],
        "current_task_id": None,
        "current_task_index": 0,
        "last_result": {},
        "task_results": {},
        "artifacts": {},
        "retries": 0,
        "max_retries": 2,
        "status": "pending",
        "validation_notes": [],
        "errors": [],
        "version": None,
    }
    result = await graph.ainvoke(initial_state, config=config)
    return WorkflowCreateResponse(thread_id=thread_id, status=result["status"])


@app.get("/workflows/{thread_id}")
async def get_workflow(thread_id: str):
    snapshot = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    if snapshot is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    return snapshot.values
```

Arranque local:

```bash
uvicorn orchestrator.server:app --host 0.0.0.0 --port 8000 --reload
```

## Paso 11: Eventos NATS

Crear `orchestrator/events.py`:

```python
from __future__ import annotations

import json

from nats.aio.client import Client as NATS

from .config import settings


async def publish_event(subject: str, payload: dict):
    nc = NATS()
    await nc.connect(settings.nats_url)
    try:
        await nc.publish(subject, json.dumps(payload).encode("utf-8"))
        await nc.flush()
    finally:
        await nc.close()
```

Sujetos recomendados:

- `workflow.started`
- `task.started`
- `task.completed`
- `task.retry`
- `task.failed`
- `workflow.finished`

Consumidor de prueba opcional:

```bash
docker exec -it astrik-nats nats sub 'workflow.*'
docker exec -it astrik-nats nats sub 'task.*'
```

## Paso 12: Integracion con agentes existentes como LangGraph tools

La integracion debe reusar codigo real ya presente en el repo.

### Skills Agent

Funciones reales disponibles hoy en `agents/skills-agent/src/tools.py`:

- `search_github(query, max_results=10)`
- `evaluate_tool(tool)`
- `install_tool(name, install_type="pip", source="")`
- `test_tool(name, test_command="")`
- `run_full_pipeline(tool_name, github_query="", install_type="pip", source="")`

### Infra Agent

Funciones reales disponibles hoy en `agents/infra-agent/src/tools.py`:

- `generate_env(services=None)`
- `generate_compose(services=None)`
- `add_service(name, custom_config=None)`
- `check_health(service="")`
- `run_full_build(services=None)`

### Agent Factory

El wrapper puede invocar el CLI real:

```bash
python agents/agent-factory/main.py create --name demo-agent --desc "Agente demo"
```

### Versionado

El wrapper debe invocar el script real:

```bash
python scripts/release.py snapshot orchestrator v1.0.0
```

### Observacion importante sobre imports

Los directorios `skills-agent` e `infra-agent` tienen guiones, por lo que no conviene hacer imports Python normales tipo `from agents.skills-agent...`. Por eso en esta fase se usa `importlib.util.spec_from_file_location` para cargar los modulos desde ruta absoluta.

## Como probar paso a paso

### 1. Infra minima

Levantar servicios base:

```bash
docker compose -f infrastructure/docker-compose.yml up -d postgres nats redis qdrant
```

Verificar:

```bash
docker ps
```

### 2. Variables de entorno

Crear `orchestrator/.env` a partir de `orchestrator/.env.example`.

### 3. Health del servidor

```bash
uvicorn orchestrator.server:app --host 0.0.0.0 --port 8000 --reload
curl http://localhost:8000/health
```

Respuesta esperada:

```json
{"status":"ok","service":"orchestrator"}
```

### 4. Crear workflow de prueba

```bash
curl -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"objective":"Buscar una herramienta de documentacion en Python y preparar infraestructura base"}'
```

Respuesta esperada:

```json
{"thread_id":"...","status":"completed"}
```

### 5. Consultar estado persistido

```bash
curl http://localhost:8000/workflows/TU_THREAD_ID
```

Debe devolver:

- `objective`
- `plan`
- `task_results`
- `validation_notes`
- `version`

### 6. Ver eventos NATS

En otra terminal:

```bash
docker exec -it astrik-nats nats sub '>'
```

Luego volver a lanzar un workflow. Deben verse eventos como:

```text
[workflow.started]
[task.started]
[task.completed]
[workflow.finished]
```

### 7. Verificar snapshot final

Tras un workflow exitoso, comprobar:

```bash
dir releases
type CHANGELOG.md
type VERSIONS.md
git tag
```

Debe existir algo como:

- `releases/orchestrator-v1.0.0/`
- entrada nueva en `CHANGELOG.md`
- entrada nueva en `VERSIONS.md`
- tag `orchestrator-v1.0.0`

## Prueba minima automatizada

Crear `orchestrator/tests/test_smoke.py`:

```python
from orchestrator.tools.registry import TOOL_REGISTRY


def test_registry_has_core_tools():
    assert "search_github" in TOOL_REGISTRY
    assert "generate_compose" in TOOL_REGISTRY
    assert "create_agent" in TOOL_REGISTRY
    assert "snapshot" in TOOL_REGISTRY
```

Ejecutar:

```bash
pytest orchestrator/tests/test_smoke.py
```

## Definicion de Heuristicas de Tareas

Para que otra IA implemente con criterio consistente, usar esta tabla:

| Caso | kind | tool |
|---|---|---|
| Buscar libreria o herramienta | `research` | `search_github` |
| Instalar herramienta | `install` | `skills_pipeline` |
| Crear compose, env o servicios | `infra` | `generate_compose` |
| Crear agente nuevo | `factory` | `create_agent` |
| Snapshot y release | `release` | `snapshot` |

## Criterios de Aceptacion

La Fase 2 se considera terminada si se cumple todo esto:

1. Existe `orchestrator/` con los archivos descritos arriba.
2. FastAPI expone `POST /workflows`, `GET /workflows/{thread_id}` y `GET /health`.
3. LangGraph persiste checkpoints en PostgreSQL.
4. El planner genera una lista de tareas valida.
5. El executor llama codigo real de agentes existentes.
6. El validator puede aprobar, reintentar o fallar.
7. El deployer ejecuta `scripts/release.py snapshot orchestrator v1.0.0`.
8. Se publican eventos por NATS durante el workflow.
9. Un workflow de prueba deja evidencia en `releases/`, `CHANGELOG.md` y `VERSIONS.md`.

## Ticket de Versionado al Finalizar

Usar este ticket textual al cerrar la fase:

````md
# Ticket: Release Fase 2 Orchestrator

## Componente
- `orchestrator`

## Objetivo
- Publicar la primera version funcional del Orchestrator basado en LangGraph.

## Checklist
- [ ] Dependencias instaladas
- [ ] `orchestrator/.env` configurado
- [ ] PostgreSQL operativo para checkpoints
- [ ] NATS operativo para eventos
- [ ] FastAPI levantando en puerto 8000
- [ ] Workflow de prueba ejecutado de punta a punta
- [ ] Snapshot generado en `releases/orchestrator-v1.0.0`
- [ ] `CHANGELOG.md` actualizado
- [ ] `VERSIONS.md` actualizado
- [ ] Tag git `orchestrator-v1.0.0` creado

## Comando final
```bash
python scripts/release.py snapshot orchestrator v1.0.0
```

## Evidencias esperadas
- `releases/orchestrator-v1.0.0/.release.json`
- nueva entrada en `CHANGELOG.md`
- nueva fila en `VERSIONS.md`
- `git tag` contiene `orchestrator-v1.0.0`
````

## Siguiente fase sugerida

Despues de esta Fase 2, la fase natural es agregar:

1. Memoria semantica en Qdrant.
2. Ejecucion desacoplada con workers NATS.
3. Human-in-the-loop para tareas de alto riesgo.
4. Observabilidad real con trazas y metricas por nodo.
