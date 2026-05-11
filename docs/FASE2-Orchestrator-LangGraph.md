# FASE 2: Orchestrator con LangGraph

## Contexto del Proyecto

Astrik AI Platform es un sistema multi-agente local autonomo.
Este repositorio ya tiene construido:

- **Agent Factory** (agents/agent-factory/) - Creador de agentes estandarizados
- **Skills Agent** (agents/skills-agent/) - Busca, instala y prueba herramientas externas
- **Infra Agent** (agents/infra-agent/) - Genera infraestructura Docker
- **Versionado** (scripts/release.py) - Snapshots versionados de componentes

Stack definido:
- Python 3.12+, llama.cpp (GPU), FastAPI, PostgreSQL, Redis, Qdrant, NATS
- Los agentes actuales son scripts CLI, NO son autonomos

## Objetivo de la Fase 2

Construir el **Orchestrator Core** usando LangGraph como base, que permita:

1. Recibir un objetivo del usuario
2. Descomponerlo en tareas via un nodo Planner
3. Ejecutar las tareas usando agentes existentes como LangGraph nodes
4. Validar resultados via un nodo QA
5. Versionar automaticamente via un nodo Deployer
6. Persistir estado en PostgreSQL (checkpoints LangGraph)
7. Publicar eventos via NATS

## Arquitectura

```
Usuario/FastAPI
      |
      v
LangGraph StateGraph
      |
      +--> Planner Node --> Skills Node --> Executor Node --> Validator Node --> Deployer Node
      |       |                |               |                |                |
      |       v                v               v                v                v
      |    Tools compartidas: github_search, docker_ops, filesystem, versioning, model_query
      |
      v
NATS Event Bus
      |
      v
PostgreSQL (checkpoints) | Redis (colas) | Qdrant (memoria)
```

## Estructura a Crear

```
orchestrator/
+-- graph.py              # LangGraph StateGraph definition
+-- state.py              # TypedDict del estado del workflow
+-- server.py             # FastAPI wrapper (uvicorn)
+-- config.py             # Configuracion desde .env
+-- db.py                 # SQLAlchemy async + LangGraph PostgresCheckpointer
+-- events.py             # NATS publisher/subscriber
+-- requirements.txt
+-- nodes/
|   +-- __init__.py
|   +-- planner.py        # Nodo: recibe objetivo, lo divide en tareas
|   +-- executor.py       # Nodo: ejecuta las tareas usando tools
|   +-- validator.py      # Nodo: QA y validacion
|   +-- deployer.py       # Nodo: deploy, release y versionado
+-- agents/
|   +-- __init__.py
|   +-- factory_agent.py  # LangGraph AgentNode: wrapper del Agent Factory
|   +-- skills_agent.py   # LangGraph AgentNode: wrapper del Skills Agent
|   +-- infra_agent.py    # LangGraph AgentNode: wrapper del Infra Agent
|   +-- version_agent.py  # LangGraph AgentNode: wrapper del versionado
+-- tools/
|   +-- __init__.py
|   +-- github_search.py  # Tool: buscar en GitHub (Skills Agent)
|   +-- docker_ops.py     # Tool: operaciones Docker (Infra Agent)
|   +-- filesystem.py     # Tool: operaciones de archivos
|   +-- versioning.py     # Tool: snapshot, bump, tag (scripts/release.py)
|   +-- model_query.py    # Tool: consultar llama.cpp
+-- events/
|   +-- __init__.py
|   +-- publisher.py      # Publicar eventos NATS
|   +-- subscriber.py     # Escuchar eventos NATS
+-- docs/
+-- tests/
```

## Plan de Implementacion

### Paso 1: Instalar dependencias

```bash
pip install langgraph langchain langchain-community fastapi uvicorn
pip install nats-py sqlalchemy asyncpg redis pydantic pyyaml httpx
```

### Paso 2: State definition (state.py)

```python
from typing import TypedDict, Optional, Annotated
from langgraph.graph import add_messages

class OrchestratorState(TypedDict):
    objective: str                    # Objetivo original del usuario
    messages: Annotated[list, add_messages]  # Historial de mensajes
    plan: list[str]                   # Lista de tareas planificadas
    current_task: Optional[str]       # Tarea actual en ejecucion
    task_results: dict                # Resultados por tarea
    errors: list[str]                 # Errores acumulados
    retries: int                      # Contador de reintentos
    status: str                       # running | completed | failed | waiting_human
    artifacts: dict                   # Archivos generados
    version: Optional[str]            # Version del release generado
```

### Paso 3: Config (config.py)

Leer desde variables de entorno con defaults:
- DATABASE_URL (postgresql+asyncpg://astrik:astrik_secret@localhost:5432/astrik)
- REDIS_URL (redis://localhost:6379/0)
- NATS_URL (nats://localhost:4222)
- LLAMA_API_URL (http://localhost:8080/v1)
- QDRANT_URL (http://localhost:6333)

### Paso 4: LangGraph Checkpointer (db.py)

Usar PostgresSaver de LangGraph para persistencia automatica:

```python
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.base import create_checkpoint

checkpointer = PostgresSaver.from_conn_string(
    "postgresql+asyncpg://astrik:astrik_secret@localhost:5432/astrik"
)
```

### Paso 5: Graph definition (graph.py)

```python
from langgraph.graph import StateGraph, START, END
from .nodes.planner import planner_node
from .nodes.executor import executor_node
from .nodes.validator import validator_node
from .nodes.deployer import deployer_node

builder = StateGraph(OrchestratorState)

builder.add_node("planner", planner_node)
builder.add_node("executor", executor_node)
builder.add_node("validator", validator_node)
builder.add_node("deployer", deployer_node)

builder.add_edge(START, "planner")
builder.add_conditional_edges(
    "planner",
    lambda state: "executor" if state["plan"] else "failed",
)
builder.add_edge("executor", "validator")
builder.add_conditional_edges(
    "validator",
    lambda state: "deployer" if state["status"] == "completed" else "executor",
    {"deployer": "deployer", "executor": "executor"}
)
builder.add_edge("deployer", END)

graph = builder.compile(checkpointer=checkpointer)
```

### Paso 6: Nodo Planner (nodes/planner.py)

Funcion:
1. Recibe el objetivo del usuario
2. Usa Hermes 3 via llama.cpp API para descomponer en tareas
3. Genera un plan (lista de pasos)
4. Actualiza el estado con el plan

```python
async def planner_node(state: OrchestratorState) -> dict:
    objective = state["objective"]
    # Consultar Hermes 3 via llama.cpp API
    plan = await query_llm(f"Divide este objetivo en tareas: {objective}")
    return {
        "plan": plan,
        "status": "running",
        "messages": [f"Plan generado: {len(plan)} tareas"]
    }
```

### Paso 7: Nodo Executor (nodes/executor.py)

Funcion:
1. Toma la tarea actual del plan
2. Determina que tool/agente usar
3. Ejecuta la tool correspondiente
4. Almacena el resultado

Routing de tareas a tools:
- "buscar herramienta" -> github_search_tool
- "instalar" -> install_tool
- "crear docker" -> docker_compose_tool
- "versionar" -> snapshot_tool
- "crear agente" -> agent_factory_tool

### Paso 8: Nodo Validator (nodes/validator.py)

Funcion:
1. Verifica que la tarea se completo correctamente
2. Corre tests si existen
3. Decide si continuar o reintentar

### Paso 9: Nodo Deployer (nodes/deployer.py)

Funcion:
1. Versiona el resultado via snapshot_tool
2. Publica el release
3. Actualiza CHANGELOG y VERSIONS.md
4. Crea git tag

### Paso 10: FastAPI Server (server.py)

```python
from fastapi import FastAPI
from .graph import graph
from .state import OrchestratorState

app = FastAPI(title="Astrik Orchestrator")

@app.post("/workflows")
async def create_workflow(objective: str):
    config = {"configurable": {"thread_id": str(uuid4())}}
    state = OrchestratorState(objective=objective)
    result = await graph.ainvoke(state, config)
    return {"thread_id": config["configurable"]["thread_id"], "status": result["status"]}

@app.get("/workflows/{thread_id}")
async def get_workflow(thread_id: str):
    state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    return state

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Paso 11: Eventos NATS (events/publisher.py)

```python
import asyncio
from nats.aio.client import Client as NATS

async def publish_event(subject: str, data: dict):
    nc = NATS()
    await nc.connect("nats://localhost:4222")
    await nc.publish(subject, json.dumps(data).encode())
    await nc.close()
```

Eventos a publicar:
- TASK_CREATED {task_id, objective, agent}
- TASK_COMPLETED {task_id, result}
- TASK_FAILED {task_id, error, retries}
- WORKFLOW_STARTED {workflow_id, objective}
- WORKFLOW_FINISHED {workflow_id, status, version}

### Paso 12: Integracion con Agentes Existentes

Cada agente existente debe exponer sus herramientas como LangGraph tools:

**Skills Agent -> tools/github_search.py**
```python
@tool
def search_github_tool(query: str) -> list[dict]:
    """Buscar herramientas en GitHub"""
    from agents.skills-agent.src.tools import search_github
    return search_github(query)
```

**Infra Agent -> tools/docker_ops.py**
```python
@tool
def docker_compose_tool(services: list[str]) -> str:
    """Generar docker-compose.yml"""
    from agents.infra-agent.src.tools import generate_compose
    return generate_compose(services)
```

**Versionado -> tools/versioning.py**
```python
@tool
def snapshot_tool(component: str, version: str) -> dict:
    """Crear snapshot versionado de un componente"""
    import subprocess
    result = subprocess.run(["python", "scripts/release.py", "snapshot", component, version])
    return {"status": "completed" if result.returncode == 0 else "failed"}
```

## Como Probar

```bash
# 1. Iniciar el servidor
cd orchestrator
uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# 2. Crear un workflow
curl -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"objective": "Buscar e instalar herramienta de linting para Python"}'

# 3. Ver estado
curl http://localhost:8000/workflows/{thread_id}

# 4. Healthcheck
curl http://localhost:8000/health
```

## Entregables

Cada paso debe producir codigo funcional y estar documentado en el agent.yaml
del Orchestrator Agent. Al finalizar, versionar con:

```bash
python scripts/release.py snapshot orchestrator v1.0.0
```
