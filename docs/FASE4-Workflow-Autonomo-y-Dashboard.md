# FASE 4: Workflow Autonomo Completo + Dashboard

> **IMPORTANTE**: Este documento es autocontenido. Una IA puede implementar toda la Fase 4 siguiendo estos pasos sin necesidad de preguntar nada.

---

## Contexto del Proyecto

### Estado actual post-Fase 3 (✅ CONFIRMADO — Deploy completado en VM core 192.168.2.112):

| Componente | Estado | Notas |
|---|---|---|
| **Infraestructura** | Docker, PostgreSQL, Redis, Qdrant, NATS corriendo | 192.168.2.112 |
| **LLM** | Qwen2.5-32B-Instruct-Q4_K_M.gguf via llama.cpp | 192.168.2.111:11434 |
| **Orchestrator LangGraph** | FastAPI + StateGraph en puerto 8010 | 192.168.2.112:8010 |
| **Skills Agent** | ✅ systemd ACTIVO — conectado a NATS | `agent.skills-agent.request` |
| **Infra Agent** | ✅ systemd ACTIVO — conectado a NATS | `agent.infra-agent.request` |
| **Agent Factory** | ✅ systemd ACTIVO — conectado a NATS | `agent.agent-factory.request` |
| **Version Agent** | ✅ systemd ACTIVO — conectado a NATS | `agent.version-agent.request` |
| **NATS** | URL confirmada | `nats://192.168.2.112:4222` |
| **Tests integracion** | 5/5 PASS | test_skills_agent_online, test_infra_agent_online, test_skills_agent_search, test_infra_agent_health, test_version_agent_current |
| **shared/agent_service.py** | Clase base AgentService (usa `print()` — se migra a CentralizedLogger en Fase 4) | Pendiente migracion |
| **Version proyecto** | v0.1.1 | |
| **Versiones componente** | agents-v1.0.0 (tag GitHub), orchestrator v1.0.0 | |

### Lecciones aprendidas del deploy de Fase 3 (importantes para Fase 4):

| Issue | Solucion |
|---|---|
| VM usa `python3`, no `python` | Usar `#!/usr/bin/env python3` en shebang |
| PEP 668 bloquea `pip install` | Agregar `--break-system-packages` |
| Imports relativos `from .src.tools` fallan al ejecutar directo | Usar imports absolutos con `sys.path.insert(0, ...)` |
| `asyncio.run(service.start())` retorna inmediatamente | Agregar `await asyncio.Event().wait()` en loop principal |
| Git push requiere autenticacion | Usar token personal, limpiar URL remota |

### Stack tecnologico:
- Python 3.12+, LangGraph 0.4.7, FastAPI, nats-py
- PostgreSQL (psycopg + AsyncPostgresSaver), Redis, Qdrant
- Streamlit (para dashboard)
- LLM: OpenAI-compatible API en `http://192.168.2.111:11434/v1`
- Sistema de archivos: repo en `~/astrik-platform`

### Archivos que ya existen y NO se tocan:
- `shared/agent_service.py` — solo se modifica para usar logger
- `orchestrator/state.py` — NO se modifica (ya tiene OrchestratorState completo)
- `orchestrator/config.py` — NO se modifica (ya tiene Settings completo)
- `orchestrator/db.py` — NO se modifica (ya tiene AsyncPostgresSaver)
- `orchestrator/models.py` — NO se modifica (ya tiene WorkflowCreateRequest/Response)
- `orchestrator/events.py` — NO se modifica (ya tiene publish_event)
- `orchestrator/graph.py` — se modifica para agregar human-in-loop route
- `orchestrator/tools/nats_agent.py` — NO se modifica (ya tiene NATSAgentTool)
- `orchestrator/tools/existing_agents.py` — NO se modifica (ya carga skills e infra tools)
- `orchestrator/tools/registry.py` — se agregan tools de invocacion NATS
- `orchestrator/llm.py` — se modifica para que el planner asigne agentes
- `orchestrator/nodes/executor.py` — NO se modifica (ya ejecuta tools locales)
- `orchestrator/nodes/executor_nats.py` — se modifica para ser usado como executor virtual

### Archivos existentes que se modifican:
| Archivo | Cambio |
|---|---|
| `shared/agent_service.py` | Agregar CentralizedLogger en vez de print() |
| `shared/logger.py` | CREAR: logger centralizado con Redis pub/sub |
| `orchestrator/graph.py` | Ruta "human" para human-in-loop |
| `orchestrator/nodes/planner.py` | Usar LLM real con asignacion de agente NATS |
| `orchestrator/nodes/executor_nats.py` | Convertir en nodo que invoca agentes via NATS |
| `orchestrator/nodes/validator.py` | Agregar human-in-loop con interrupt() |
| `orchestrator/nodes/deployer.py` | Llamar Version Agent via NATS |
| `orchestrator/server.py` | Agregar endpoint decision + historial workflows |
| `orchestrator/tools/registry.py` | Agregar TOOL_REGISTRY_NATS |
| `orchestrator/llm.py` | Prompt que asigna agente NATS a cada tarea |

### Archivos nuevos a crear:
| Archivo | Descripcion |
|---|---|
| `dashboard/app.py` | Streamlit principal |
| `dashboard/pages/01_Agentes.py` | Pagina de detalle de agentes |
| `dashboard/pages/02_Workflows.py` | Pagina de historial y aprobacion |
| `dashboard/pages/03_Historial.py` | Logs historicos con filtros |
| `dashboard/pages/04_Configuracion.py` | Config del sistema |
| `dashboard/src/nats_client.py` | Cliente NATS en tiempo real |
| `dashboard/src/orchestrator_client.py` | Cliente HTTP del Orchestrator |
| `dashboard/src/db_client.py` | Cliente PostgreSQL para historial |
| `dashboard/requirements.txt` | Dependencias del dashboard |
| `dashboard/Dockerfile` | Contenedor del dashboard |
| `scripts/astrik.sh` | CLI unificada |
| `scripts/start_all.sh` | Iniciar todos los servicios |
| `scripts/stop_all.sh` | Detener todos los servicios |
| `scripts/status.sh` | Estado de todos los servicios |
| `docs/README.md` | Documentacion completa |
| `docs/ARQUITECTURA.md` | Diagrama final de arquitectura |

---

## Arquitectura Objetivo (Fase 4)

```mermaid
flowchart TD
    subgraph "Usuario"
        CLI[astrik CLI]
        WEB[Dashboard Streamlit :8501]
    end

    subgraph "Orquestacion"
        API[FastAPI /workflows :8010]
        ORCH[LangGraph StateGraph]
        PG[(PostgreSQL Checkpoints)]
        NATS{NATS Event Bus :4222}
    end

    subgraph "Workflow Nodes"
        PLAN[Planner Node<br/>LLM -> tareas + agente]
        EXEC[Executor NATS Node<br/>Invoca agentes via NATS]
        VAL[Validator Node<br/>interrupt() human-in-loop]
        DEP[Deployer Node<br/>Version Agent snapshot]
    end

    subgraph "Agentes NATS"
        SA[Skills Agent<br/>search/install/test]
        IA[Infra Agent<br/>compose/env/build]
        AF[Agent Factory<br/>create/list/validate]
        VA[Version Agent<br/>snapshot/bump/tag]
    end

    subgraph "Infraestructura"
        LLM[llama.cpp GPU :11434]
        REDIS[(Redis :6379<br/>Logs pub/sub)]
        QDRANT[(Qdrant :6333<br/>Memoria)]
    end

    CLI --> API
    WEB --> API
    API --> ORCH
    ORCH --> PG
    ORCH --> NATS

    ORCH --> PLAN
    PLAN --> EXEC
    EXEC --> VAL
    VAL -->|approve| DEP
    VAL -->|retry| EXEC
    VAL -->|human| WEB

    EXEC -.-> NATS
    NATS -.-> SA
    NATS -.-> IA
    NATS -.-> AF
    NATS -.-> VA

    PLAN -.-> LLM
    SA -.-> LLM
    SA -.-> REDIS
    IA -.-> REDIS
    AF -.-> REDIS
    VA -.-> REDIS
    ORCH -.-> REDIS
```

---

## Reglas de Implementacion

1. **No duplicar logica existente**: Usar `NATSAgentTool` para invocar agentes. No crear nuevos clientes NATS.
2. **Logger es obligatorio**: Todo servicio DEBE usar `CentralizedLogger` en vez de `print()`.
3. **Human-in-loop obligatorio**: El nodo validator DEBE usar `interrupt()` de LangGraph antes del deploy.
4. **NATS es el unico canal de comunicacion**: Orchestrator no importa codigo de agentes directamente.
5. **Dashboard es Streamlit**: No usar Next.js ni otras tecnologias web.
6. **Config via .env**: Todas las URLs y puertos desde variables de entorno.
7. **Errores manejados con retry**: Maximo 2 reintentos antes de escalar a humano.

---

## Plan de Implementacion

### Paso 0: Verificar prerequisitos

Antes de empezar, confirmar que existe:

```bash
# 1. Infraestructura base funcionando
docker ps
# Debe mostrar: postgres, redis, qdrant, nats

# 2. LLM endpoint accesible
curl http://192.168.2.111:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-32b-instruct","messages":[{"role":"user","content":"hola"}],"max_tokens":10}'

# 3. Agentes NATS desplegados (o al menos codigo presente)
ls agents/*/service.py

# 4. Orchestrator existente
ls orchestrator/server.py orchestrator/graph.py orchestrator/state.py
```

Si todo esta OK, continuar.

---

### Paso 1: Crear Logger Centralizado `shared/logger.py`

**Archivo: `shared/logger.py`**

```python
"""Logger centralizado con Redis pub/sub.
Cada servicio publica logs estructurados en Redis.
El dashboard los consume en vivo."""

import json
from datetime import datetime, timezone

import redis.asyncio as aioredis

# Si redis.asyncio no existe, instalar: pip install "redis[hiredis]>=5.0"

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
            pass  # no romper el servicio si Redis falla

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
```

---

### Paso 2: Modificar `shared/agent_service.py` para usar CentralizedLogger

**Archivo: `shared/agent_service.py`**

Reemplazar todos los `print(...)` por llamadas a `self.logger.info/error/warn`.

Las lineas a modificar son:

```python
# Linea 1-3: Agregar import
import json
import asyncio
import uuid
import signal
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from .logger import CentralizedLogger  # <-- NUEVO


# En __init__, despues de self._current_task = None:
class AgentService(ABC):
    def __init__(self):
        self.nc = NATS()
        self.subscriptions = []
        self._running = False
        self._start_time = None
        self._current_task = None
        self.logger = CentralizedLogger(self.agent_name)  # <-- NUEVO
```

Luego reemplazar CADA `print(...)` por `await self.logger.info(...)`:

```python
# Linea ~57 (start): print(f"[{self.agent_name}] Conectado a NATS en {NATS_URL}")
# Reemplazar por:
        await self.logger.info(f"Conectado a NATS en {NATS_URL}")

# Linea ~64 (start): print(f"[{self.agent_name}] Escuchando en: {subject}")
# Reemplazar por:
        await self.logger.info(f"Escuchando en: {subject}")

# Linea ~75 (start): print(f"[{self.agent_name}] Servicio iniciado. Esperando eventos...")
# Reemplazar por:
        await self.logger.info("Servicio iniciado. Esperando eventos...")

# Linea ~86 (stop): print(f"[{self.agent_name}] Servicio detenido.")
# Reemplazar por:
        await self.logger.info("Servicio detenido.")

# Linea ~96 (_on_message): print(f"[{self.agent_name}] Tarea recibida: {task_type} (id: {task_id})")
# Reemplazar por:
        await self.logger.info(f"Tarea recibida: {task_type}", task_id=task_id, task_type=task_type)

# Linea ~117 (_on_message): print(f"[{self.agent_name}] Tarea {task_id}: {status}")
# Reemplazar por:
        await self.logger.info(f"Tarea {task_id}: {status}", task_id=task_id, status=status)

# Linea ~120 (_on_message exception handler):
# Reemplazar:
        await self.logger.error(f"Error procesando mensaje: {e}", error=str(e))
```

---

### Paso 3: Modificar `orchestrator/llm.py` - Prompt con asignacion de agente NATS

**Archivo: `orchestrator/llm.py`** — modificar el prompt de `plan_objective` para que el LLM asigne un agente NATS a cada tarea.

Reemplazar la funcion `plan_objective` completa:

```python
async def plan_objective(objective: str) -> list[dict]:
    llm = get_llm()
    prompt = f"""
Eres un planificador de sistemas multi-agente.
Dado un objetivo, dividelo en tareas especificas y asignale a cada una un agente y una herramienta.

AGENTES DISPONIBLES:
  - "skills-agent": tools = ["search", "install", "test", "pipeline"]
  - "infra-agent": tools = ["build", "add_service", "health", "generate_compose", "generate_env"]
  - "agent-factory": tools = ["create", "list", "validate"]
  - "version-agent": tools = ["snapshot", "bump", "current"]

Objetivo:
{objective}

Devuelve SOLO JSON con esta forma exacta:
[
  {{"id": "task-1", "title": "descripcion corta", "agent": "skills-agent", "tool": "search", "kind": "research"}},
  {{"id": "task-2", "title": "descripcion corta", "agent": "infra-agent", "tool": "build", "kind": "infra"}}
]

kind debe ser uno de: research, install, infra, factory, release.
No agregues explicaciones ni markdown. Solo JSON valido.""".strip()
    try:
        response = await llm.ainvoke(prompt)
        content = response.content if isinstance(response.content, str) else str(response.content)
        data = json.loads(_strip_code_fences(content))
        return [
            {
                "id": item["id"],
                "title": item["title"],
                "agent": item.get("agent", "skills-agent"),
                "tool": item.get("tool", "search"),
                "kind": item.get("kind", "research"),
                "status": "pending",
            }
            for item in data
        ]
    except Exception:
        return _fallback_plan(objective)
```

Tambien actualizar `_fallback_plan` para incluir el campo `agent`:

```python
def _fallback_plan(objective: str) -> list[dict]:
    objective_lower = objective.lower()
    plan: list[dict] = []

    if any(word in objective_lower for word in ["buscar", "herramienta", "github", "libreria"]):
        plan.append({
            "id": "task-1",
            "title": objective,
            "agent": "skills-agent",
            "tool": "search",
            "kind": "research",
            "status": "pending",
        })

    if any(word in objective_lower for word in ["instalar", "instala", "install", "configurar", "setup"]):
        plan.append({
            "id": f"task-{len(plan) + 1}",
            "title": objective,
            "agent": "skills-agent",
            "tool": "pipeline",
            "kind": "install",
            "status": "pending",
        })

    if any(word in objective_lower for word in ["infra", "docker", "compose", "postgres", "redis", "nats", "qdrant"]):
        plan.append({
            "id": f"task-{len(plan) + 1}",
            "title": "Preparar infraestructura base",
            "agent": "infra-agent",
            "tool": "build",
            "kind": "infra",
            "status": "pending",
        })

    if any(word in objective_lower for word in ["crear agente", "nuevo agente", "agent"]):
        plan.append({
            "id": f"task-{len(plan) + 1}",
            "title": f"Crear agente para {_slug(objective)}",
            "agent": "agent-factory",
            "tool": "create",
            "kind": "factory",
            "status": "pending",
        })

    if not plan:
        plan = [
            {
                "id": "task-1",
                "title": objective,
                "agent": "skills-agent",
                "tool": "search",
                "kind": "research",
                "status": "pending",
            },
            {
                "id": "task-2",
                "title": "Preparar infraestructura base",
                "agent": "infra-agent",
                "tool": "build",
                "kind": "infra",
                "status": "pending",
            },
        ]

    return plan
```

Tambien actualizar `TaskItem` hint en el docstring — aunque state.py no se toca, el plan ahora incluye "agent".

---

### Paso 4: Modificar `orchestrator/nodes/planner.py` para pasar agent/tool en plan

**Archivo: `orchestrator/nodes/planner.py`**

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
            "plan": [{"id": t["id"], "title": t["title"], "agent": t["agent"], "tool": t["tool"]} for t in plan],
        },
    )

    return {
        "plan": plan,
        "status": "running",
        "messages": [AIMessage(content=f"Plan generado con {len(plan)} tareas")],
        "current_task_index": 0,
    }
```

---

### Paso 5: Reescribir `orchestrator/nodes/executor_nats.py` — Nodo que invoca agentes via NATS

Este es el nodo clave de Fase 4. Reemplaza la logica local del executor por invocacion a agentes NATS.

**Archivo: `orchestrator/nodes/executor_nats.py`**

```python
"""Nodo Executor que invoca agentes via NATS en vez de usar tools locales."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from ..events import publish_event
from ..state import OrchestratorState
from ..tools.nats_agent import NATSAgentTool

# Mapa de agente -> sujetos NATS
AGENT_MAP = {
    "skills-agent": {
        "subject": "agent.skills-agent.request",
        "tools": ["search", "install", "test", "pipeline"],
    },
    "infra-agent": {
        "subject": "agent.infra-agent.request",
        "tools": ["build", "add_service", "health", "generate_compose", "generate_env"],
    },
    "agent-factory": {
        "subject": "agent.agent-factory.request",
        "tools": ["create", "list", "validate"],
    },
    "version-agent": {
        "subject": "agent.version-agent.request",
        "tools": ["snapshot", "bump", "current"],
    },
}


async def executor_nats_node(state: OrchestratorState) -> dict:
    """Toma la tarea actual del plan e invoca el agente correspondiente via NATS."""
    plan = list(state.get("plan", []))
    index = state.get("current_task_index", 0)

    if index >= len(plan):
        return {"status": "completed"}

    task = dict(plan[index])
    agent_name = task.get("agent", "skills-agent")
    tool_name = task.get("tool", "search")
    title = task.get("title", "")

    # Verificar que el agente existe en el mapa
    if agent_name not in AGENT_MAP:
        await publish_event("task.failed", {
            "task_id": task["id"],
            "error": f"Agente desconocido: {agent_name}",
        })
        return {
            "status": "failed",
            "errors": [f"Agente desconocido: {agent_name}"],
            "messages": [AIMessage(content=f"Error: agente {agent_name} no configurado")],
        }

    await publish_event("task.started", {
        "task_id": task["id"],
        "title": title,
        "agent": agent_name,
        "tool": tool_name,
    })

    # Invocar agente via NATS
    nats_tool = NATSAgentTool(agent_name)
    response = await nats_tool.invoke(tool_name, {
        "query": title,
        "description": title,
    })

    task["status"] = "completed" if response.get("status") == "completed" else "failed"
    plan[index] = task
    task_results = dict(state.get("task_results", {}))
    task_results[task["id"]] = response

    return {
        "plan": plan,
        "current_task_id": task["id"],
        "last_result": response,
        "task_results": task_results,
        "messages": [AIMessage(content=f"Ejecutada tarea {task['id']} via {agent_name}/{tool_name}")],
    }
```

---

### Paso 6: Modificar `orchestrator/nodes/validator.py` — Agregar human-in-loop con interrupt()

**Archivo: `orchestrator/nodes/validator.py`**

```python
"""Nodo Validator con human-in-loop.
Usa interrupt() de LangGraph para pausar y esperar decision humana antes del deploy."""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from ..events import publish_event
from ..state import OrchestratorState


def _result_ok(result: dict) -> bool:
    if not result:
        return False
    status = result.get("status")
    if status in {"completed", "installed", "working", "already_exists"}:
        return True
    if result.get("error") or result.get("stderr"):
        return False
    return status != "failed"


async def validator_node(state: OrchestratorState) -> dict:
    plan = list(state.get("plan", []))
    index = state.get("current_task_index", 0)
    current_task_id = state.get("current_task_id")
    result = dict(state.get("last_result", {}))
    retries = state.get("retries", 0)
    max_retries = state.get("max_retries", 2)
    notes = list(state.get("validation_notes", []))
    errors = list(state.get("errors", []))

    # ---- Resultado OK: avanzar a la siguiente tarea ----
    if _result_ok(result):
        if index < len(plan):
            plan[index]["status"] = "completed"
        next_index = index + 1
        all_done = next_index >= len(plan)

        await publish_event("task.completed", {
            "task_id": current_task_id,
            "next_index": next_index,
        })

        # Si todas las tareas estan completas, pedir aprobacion humana
        if all_done:
            await publish_event("workflow.pending_approval", {
                "objective": state.get("objective", ""),
                "task_count": len(plan),
                "task_results": {
                    tid: str(res)[:200]
                    for tid, res in state.get("task_results", {}).items()
                },
            })

            decision = interrupt({
                "query": "Aprobar deploy y versionado?",
                "summary": f"""
=== RESUMEN DEL WORKFLOW ===
Objetivo: {state.get('objective', '')}
Tareas completadas: {len(state.get('task_results', {}))}
Errores: {len(errors)}
""",
                "options": ["approve", "reject", "modify"],
            })

            if decision == "approve":
                return {
                    "plan": plan,
                    "current_task_index": next_index,
                    "status": "completed",
                    "retries": 0,
                    "validation_notes": notes + ["Workflow aprobado por humano"],
                    "messages": [AIMessage(content="Workflow aprobado para deploy")],
                }
            elif decision == "reject":
                await publish_event("workflow.rejected", {
                    "objective": state.get("objective"),
                })
                return {
                    "status": "failed",
                    "errors": errors + ["Workflow rechazado por el usuario"],
                    "messages": [AIMessage(content="Workflow rechazado por el usuario")],
                }
            elif decision == "modify":
                return {
                    "status": "waiting_modification",
                    "messages": [AIMessage(content="Esperando modificaciones del usuario")],
                }

        # Sin aprobacion humana (menos de todas las tareas)
        return {
            "plan": plan,
            "current_task_index": next_index,
            "status": "running",
            "retries": 0,
            "validation_notes": notes + [f"Tarea {current_task_id} validada"],
            "messages": [AIMessage(content=f"Validator aprobo {current_task_id}")],
        }

    # ---- Resultado fallido: reintentar ----
    if retries < max_retries:
        await publish_event("task.retry", {
            "task_id": current_task_id,
            "retry": retries + 1,
        })
        return {
            "status": "retrying",
            "retries": retries + 1,
            "validation_notes": notes + [f"Retry {retries + 1} para {current_task_id}"],
            "messages": [AIMessage(content=f"Validator pide retry para {current_task_id}")],
        }

    # ---- Fallo definitivo ----
    errors.append(f"La tarea {current_task_id} fallo tras {max_retries} reintentos")
    await publish_event("task.failed", {
        "task_id": current_task_id,
        "error": errors[-1],
    })
    return {
        "status": "failed",
        "errors": errors,
        "messages": [AIMessage(content=f"Validator marco fallo definitivo en {current_task_id}")],
    }
```

---

### Paso 7: Modificar `orchestrator/nodes/deployer.py` — Llamar Version Agent via NATS

**Archivo: `orchestrator/nodes/deployer.py`**

```python
"""Nodo Deployer: invoca Version Agent via NATS para snapshot y bump."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from ..events import publish_event
from ..state import OrchestratorState
from ..tools.nats_agent import NATSAgentTool


async def deployer_node(state: OrchestratorState) -> dict:
    task_details = state.get("plan", [])
    components_versionados = set()

    for task in task_details:
        agent = task.get("agent", "")
        if agent == "skills-agent":
            components_versionados.add("agents/skills-agent")
        elif agent == "infra-agent":
            components_versionados.add("agents/infra-agent")
        elif agent == "agent-factory":
            components_versionados.add("agents/agent-factory")

    # Invocar Version Agent via NATS para cada componente
    version_tool = NATSAgentTool("version-agent")
    results = []

    await publish_event("deploy.started", {
        "components": list(components_versionados),
    })

    for component in components_versionados:
        response = await version_tool.invoke("snapshot", {
            "componente": component,
            "version": "",  # usa la version actual del proyecto
        })
        results.append({"component": component, "response": response})

        if response.get("status") == "completed":
            await publish_event("deploy.component_done", {
                "component": component,
                "version": response.get("version", "?"),
            })

    # Bump version del proyecto
    bump_response = await version_tool.invoke("bump", {"part": "patch"})
    results.append({"component": "proyecto", "response": bump_response})

    await publish_event("deploy.completed", {
        "components": list(components_versionados),
        "bump": bump_response.get("version", "?"),
    })

    return {
        "status": "completed",
        "version": bump_response.get("version", "v0.1.X"),
        "components_versionados": list(components_versionados),
        "deploy_results": results,
        "messages": [AIMessage(content=f"Deploy completado: {len(components_versionados)} componentes versionados")],
    }
```

---

### Paso 8: Modificar `orchestrator/graph.py` — Agregar ruta human-in-loop + nodo executor_nats

**Archivo: `orchestrator/graph.py`**

```python
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes.deployer import deployer_node
from .nodes.executor_nats import executor_nats_node  # <-- cambiar a executor_nats
from .nodes.planner import planner_node
from .nodes.validator import validator_node
from .state import OrchestratorState


def route_after_planner(state: OrchestratorState) -> str:
    return "executor_nats" if state.get("plan") else "failed"


def route_after_validator(state: OrchestratorState) -> str:
    status = state.get("status")
    if status == "completed":
        return "deployer"
    if status == "retrying":
        return "executor_nats"
    if status == "failed":
        return "failed"
    if status == "waiting_modification":
        return "human"  # nodo virtual para esperar
    return "executor_nats"


def build_graph(checkpointer):
    builder = StateGraph(OrchestratorState)
    builder.add_node("planner", planner_node)
    builder.add_node("executor_nats", executor_nats_node)
    builder.add_node("validator", validator_node)
    builder.add_node("deployer", deployer_node)

    builder.add_edge(START, "planner")
    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "executor_nats": "executor_nats",
            "failed": END,
        },
    )
    builder.add_edge("executor_nats", "validator")
    builder.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "executor_nats": "executor_nats",
            "deployer": "deployer",
            "failed": END,
            "human": END,  # workflow pausado, espera decision externa
        },
    )
    builder.add_edge("deployer", END)

    return builder.compile(checkpointer=checkpointer)
```

---

### Paso 9: Modificar `orchestrator/server.py` — Agregar endpoint decision humana + historial

**Archivo: `orchestrator/server.py`**

```python
from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .db import lifespan_checkpointer
from .graph import build_graph
from .models import WorkflowCreateRequest, WorkflowCreateResponse
from .state import build_initial_state


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


graph = None


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    global graph
    async with lifespan_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)
        yield


app = FastAPI(title="Astrik Orchestrator", lifespan=app_lifespan)


class DecisionRequest(BaseModel):
    decision: str  # "approve" | "reject" | "modify"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}


@app.post("/workflows", response_model=WorkflowCreateResponse)
async def create_workflow(payload: WorkflowCreateRequest):
    if graph is None:
        raise HTTPException(status_code=503, detail="graph not initialized")

    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(build_initial_state(payload.objective), config=config)
    return WorkflowCreateResponse(thread_id=thread_id, status=result["status"])


@app.get("/workflows/{thread_id}")
async def get_workflow(thread_id: str):
    if graph is None:
        raise HTTPException(status_code=503, detail="graph not initialized")

    snapshot = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    if snapshot is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    return snapshot.values


@app.post("/workflows/{thread_id}/decision")
async def submit_decision(thread_id: str, payload: DecisionRequest):
    """Enviar decision humana al workflow pausado (human-in-loop).
    Resumes el grafo con la decision del usuario."""
    if graph is None:
        raise HTTPException(status_code=503, detail="graph not initialized")

    if payload.decision not in ("approve", "reject", "modify"):
        raise HTTPException(status_code=422, detail="decision must be 'approve', 'reject' or 'modify'")

    await graph.aconn.update_state(
        {"configurable": {"thread_id": thread_id}},
        {"decision": payload.decision},
        as_node="validator",
    )
    return {"status": "decision_received", "decision": payload.decision}


@app.get("/workflows")
async def list_workflows(limit: int = 20):
    """Listar historial de workflows (threads) desde PostgreSQL."""
    if graph is None:
        raise HTTPException(status_code=503, detail="graph not initialized")

    # Obtener threads del checkpointer
    threads = []
    async for thread in graph.aget_state_history({"configurable": {"thread_id": ""}}, limit=limit):
        threads.append({
            "thread_id": thread.config["configurable"]["thread_id"],
            "status": thread.values.get("status", "unknown"),
            "objective": thread.values.get("objective", ""),
            "updated_at": str(thread.checkpoint["ts"]) if thread.checkpoint else None,
        })
    return threads
```

---

### Paso 10: Modificar `orchestrator/tools/registry.py` — Agregar TOOL_REGISTRY_NATS

**Archivo: `orchestrator/tools/registry.py`**

Agregar al final del archivo:

```python
import json
from .nats_agent import NATSAgentTool


def nats_invoke_skills(task_type: str, payload: dict) -> dict:
    """Invoca Skills Agent via NATS"""
    import asyncio
    t = NATSAgentTool("skills-agent")
    return asyncio.run(t.invoke(task_type, payload))


def nats_invoke_infra(task_type: str, payload: dict) -> dict:
    """Invoca Infra Agent via NATS"""
    import asyncio
    t = NATSAgentTool("infra-agent")
    return asyncio.run(t.invoke(task_type, payload))


def nats_invoke_factory(task_type: str, payload: dict) -> dict:
    """Invoca Agent Factory via NATS"""
    import asyncio
    t = NATSAgentTool("agent-factory")
    return asyncio.run(t.invoke(task_type, payload))


def nats_invoke_version(task_type: str, payload: dict) -> dict:
    """Invoca Version Agent via NATS"""
    import asyncio
    t = NATSAgentTool("version-agent")
    return asyncio.run(t.invoke(task_type, payload))


TOOL_REGISTRY_NATS = {
    "skills-agent": nats_invoke_skills,
    "infra-agent": nats_invoke_infra,
    "agent-factory": nats_invoke_factory,
    "version-agent": nats_invoke_version,
}
```

---

### Paso 11: Crear Dashboard — Cliente NATS en tiempo real

**Archivo: `dashboard/src/nats_client.py`**

```python
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
        """Inicia la conexion NATS en un thread background."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def runner():
            await self.connect()
            while True:
                await asyncio.sleep(1)

        thread = threading.Thread(target=loop.run_until_complete, args=(runner(),), daemon=True)
        thread.start()
        return thread
```

---

### Paso 12: Crear Dashboard — Cliente Orchestrator

**Archivo: `dashboard/src/orchestrator_client.py`**

```python
"""Cliente HTTP para la API del Orchestrator."""

import httpx

ORCHESTRATOR_URL = "http://192.168.2.112:8010"


class OrchestratorClient:
    def __init__(self, base_url: str = ORCHESTRATOR_URL):
        self.base_url = base_url

    async def health(self) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/health", timeout=5)
            return resp.json()

    async def create_workflow(self, objective: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/workflows",
                json={"objective": objective},
                timeout=30,
            )
            return resp.json()

    async def get_workflow(self, thread_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/workflows/{thread_id}", timeout=5)
            return resp.json()

    async def submit_decision(self, thread_id: str, decision: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/workflows/{thread_id}/decision",
                json={"decision": decision},
                timeout=5,
            )
            return resp.json()

    async def get_workflows_history(self, limit: int = 20) -> list:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/workflows?limit={limit}", timeout=5)
            return resp.json()
```

---

### Paso 13: Crear Dashboard — Cliente DB

**Archivo: `dashboard/src/db_client.py`**

```python
"""Cliente PostgreSQL para leer historial de workflows."""

import asyncpg

DATABASE_URL = "postgresql://astrik:astrik_secret@192.168.2.112:5432/astrik"


class DBClient:
    def __init__(self, dsn: str = DATABASE_URL):
        self.dsn = dsn
        self._pool = None

    async def connect(self):
        self._pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=5)

    async def close(self):
        if self._pool:
            await self._pool.close()

    async def get_checkpoints(self, limit: int = 50) -> list[dict]:
        if not self._pool:
            await self.connect()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT thread_id, checkpoint, parent_checkpoint_id, metadata "
                "FROM checkpoints ORDER BY checkpoint DESC LIMIT $1",
                limit,
            )
            return [dict(r) for r in rows]

    async def get_workflow_by_thread(self, thread_id: str) -> dict | None:
        if not self._pool:
            await self.connect()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT thread_id, checkpoint, parent_checkpoint_id, metadata "
                "FROM checkpoints WHERE thread_id = $1 ORDER BY checkpoint DESC LIMIT 1",
                thread_id,
            )
            return dict(row) if row else None
```

---

### Paso 14: Crear Dashboard — Streamlit Principal

**Archivo: `dashboard/app.py`**

```python
"""Constructor Astrik Dashboard — Streamlit principal."""

import asyncio
import threading
from datetime import datetime

import streamlit as st

st.set_page_config(
    page_title="Constructor Astrik",
    page_icon="+",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Importar clientes
from src.nats_client import DashboardNATSClient
from src.orchestrator_client import OrchestratorClient


@st.cache_resource
def get_nats_client():
    client = DashboardNATSClient()
    client.start_background()
    return client


@st.cache_resource
def get_orch_client():
    return OrchestratorClient()


# Inicializar
nats_client = get_nats_client()
orch_client = get_orch_client()

# ---- Sidebar ----
st.sidebar.title("+ Constructor Astrik")
st.sidebar.caption("Sistema Multi-Agente Autonomo")
st.sidebar.divider()
st.sidebar.subheader("Enviar Objetivo")

with st.sidebar.form("objective_form"):
    objective = st.text_area(
        "Describe el objetivo:",
        height=100,
        placeholder="Ej: Buscar e instalar una herramienta de linting para Python",
    )
    submitted = st.form_submit_button("Ejecutar", type="primary", use_container_width=True)
    if submitted and objective:
        with st.spinner("Enviando al Orchestrator..."):
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(orch_client.create_workflow(objective))
            st.success(f"Workflow creado: {result.get('thread_id', '?')}")
            st.session_state.last_workflow = result.get("thread_id")

st.sidebar.divider()
st.sidebar.subheader("Estado del Sistema")

try:
    loop = asyncio.new_event_loop()
    health = loop.run_until_complete(orch_client.health())
    status_color = "green" if health.get("status") == "ok" else "red"
    st.sidebar.markdown(f"Orchestrator: :{status_color}[{health.get('status', '?')}]")
except Exception:
    st.sidebar.markdown("Orchestrator: :red[offline]")

st.sidebar.markdown("LLM: 192.168.2.111:11434")
st.sidebar.markdown("NATS: 192.168.2.112:4222")

# ---- Pagina principal ----
st.title("+ Constructor Astrik Dashboard")
st.caption(f"Ultima actualizacion: {datetime.now().strftime('%H:%M:%S')}")

# Metricas
col1, col2, col3, col4 = st.columns(4)
agents = nats_client.get_agents_status()
online = sum(1 for a in agents if a["status"] == "online")
warning = sum(1 for a in agents if a["status"] == "warning")
col1.metric("Agentes", len(agents), f"{online} online")
col2.metric("Workflows", 0)
col3.metric("LLM", "Online")
col4.metric("Version", "v0.1.X")

# Tabla de agentes
st.subheader("Agentes")
if agents:
    agent_data = []
    for a in agents:
        status_emoji = {
            "online": ":green[Online]",
            "warning": ":orange[Warning]",
            "offline": ":red[Offline]",
            "busy": ":blue[Busy]",
        }.get(a["status"], ":gray[Unknown]")
        agent_data.append({
            "Nombre": a["name"],
            "Estado": status_emoji,
            "Version": a["version"],
            "Modelo": a["model"],
            "Tarea Actual": a["current_task"] or "-",
        })
    st.dataframe(agent_data, use_container_width=True)
else:
    st.info("Esperando heartbeats de agentes...")

# Workflow rapido
st.subheader("Workflow Rapido")
col_w1, col_w2 = st.columns([3, 1])
with col_w1:
    st.text_input(
        "Objetivo rapido:",
        key="quick_objective",
        placeholder="Escribe un objetivo y presiona Enter...",
    )
with col_w2:
    if st.button("Ejecutar", use_container_width=True):
        if st.session_state.quick_objective:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                orch_client.create_workflow(st.session_state.quick_objective)
            )
            st.success(f"Enviado! ID: {result.get('thread_id', '?')}")

# Logs en vivo (placeholder — se conecta via Redis en version completa)
st.subheader("Logs del Sistema")
st.caption("Los logs apareceran aqui en tiempo real cuando los agentes esten activos.")

# Auto-refresh cada 5s
st.empty()
```

---

### Paso 15: Crear Dashboard — Paginas

**Archivo: `dashboard/pages/01_Agentes.py`**

```python
"""Pagina de detalle de agentes."""

import streamlit as st

st.set_page_config(page_title="Agentes", page_icon="+", layout="wide")
st.title("+ Agentes del Sistema")
st.markdown("Detalle de cada agente: herramientas, estado, eventos.")

# Datos simulados
agents = [
    {"name": "skills-agent", "status": "online", "tools": ["search", "install", "test", "pipeline"]},
    {"name": "infra-agent", "status": "online", "tools": ["build", "add_service", "health", "generate_compose", "generate_env"]},
    {"name": "agent-factory", "status": "online", "tools": ["create", "list", "validate"]},
    {"name": "version-agent", "status": "online", "tools": ["snapshot", "bump", "current"]},
]

for agent in agents:
    with st.expander(f"{agent['name']} — :green[{agent['status']}]"):
        st.write("**Herramientas disponibles:**")
        for tool in agent["tools"]:
            st.code(f"  • {tool}")
        st.button(f"Invocar {agent['name']}", key=f"invoke_{agent['name']}")
```

**Archivo: `dashboard/pages/02_Workflows.py`**

```python
"""Pagina de workflows: historial y aprobacion humana."""

import asyncio
import streamlit as st

st.set_page_config(page_title="Workflows", page_icon="+", layout="wide")
st.title("+ Workflows")
st.markdown("Historial de workflows y aprobacion humana.")

from src.orchestrator_client import OrchestratorClient

orch = OrchestratorClient()

# Boton para recargar
if st.button("Recargar historial"):
    loop = asyncio.new_event_loop()
    history = loop.run_until_complete(orch.get_workflows_history())
    st.session_state.workflow_history = history

if "workflow_history" not in st.session_state:
    st.session_state.workflow_history = []

if st.session_state.workflow_history:
    for wf in st.session_state.workflow_history:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(f"**{wf.get('objective', '?')[:60]}...**")
            col2.write(f"`{wf.get('thread_id', '?')[:8]}`")
            col3.write(f"`{wf.get('status', '?')}`")
            st.divider()
else:
    st.info("No hay workflows en el historial.")
```

**Archivo: `dashboard/pages/03_Historial.py`**

```python
"""Pagina de logs historicos con filtros."""

import streamlit as st

st.set_page_config(page_title="Historial", page_icon="+", layout="wide")
st.title("+ Historial de Logs")
st.markdown("Logs del sistema con filtros por servicio y nivel.")

col1, col2 = st.columns(2)
with col1:
    st.selectbox("Servicio", ["Todos", "skills-agent", "infra-agent", "agent-factory", "version-agent", "orchestrator"])
with col2:
    st.selectbox("Nivel", ["Todos", "INFO", "WARN", "ERROR", "DEBUG"])

st.caption("Conectando a Redis para logs en vivo...")
st.code("redis-cli subscribe astrik:logs")
```

**Archivo: `dashboard/pages/04_Configuracion.py`**

```python
"""Pagina de configuracion del sistema."""

import streamlit as st

st.set_page_config(page_title="Configuracion", page_icon="+", layout="wide")
st.title("+ Configuracion del Sistema")

st.subheader("Modo Auto-pilot")
auto_pilot = st.toggle("Saltar aprobacion humana y auto-aprobar workflows", value=False)
if auto_pilot:
    st.warning("ATENCION: Todos los workflows se auto-aprobaran sin intervencion humana.")

st.divider()
st.subheader("Conexiones")

connections = {
    "Orchestrator API": "http://192.168.2.112:8010",
    "NATS": "nats://192.168.2.112:4222",
    "LLM API": "http://192.168.2.111:11434/v1",
    "PostgreSQL": "192.168.2.112:5432",
    "Redis": "192.168.2.112:6379",
    "Qdrant": "192.168.2.112:6333",
}

for name, url in connections.items():
    st.text_input(name, value=url, disabled=True)

st.divider()
if st.button("Versionar y Release", type="primary", use_container_width=True):
    st.success("Proceso de versionado iniciado!")
```

---

### Paso 16: Crear Dashboard — Requirements y Dockerfile

**Archivo: `dashboard/requirements.txt`**

```
streamlit==1.43.2
nats-py==2.9.0
httpx==0.28.1
asyncpg==0.30.0
redis[hiredis]==5.2.1
pandas==2.2.3
```

**Archivo: `dashboard/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

### Paso 17: Crear Scripts de Sistema

**Archivo: `scripts/start_all.sh`**

```bash
#!/bin/bash
# Iniciar todos los servicios del Constructor Astrik

set -e

ORCHESTRATOR_DIR="$HOME/astrik-platform"
LOG_DIR="$HOME/logs"
mkdir -p "$LOG_DIR"

echo "=== Iniciando Constructor Astrik ==="

# 1. Verificar Docker
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker no esta corriendo"
    exit 1
fi

# 2. Iniciar infraestructura
cd "$ORCHESTRATOR_DIR/infrastructure"
docker compose up -d 2>/dev/null || echo "Infra ya estaba corriendo"

# 3. Esperar a que los servicios esten listos
echo "Esperando servicios..."
sleep 5

# 4. Iniciar Orchestrator
cd "$ORCHESTRATOR_DIR/orchestrator"
nohup uvicorn server:app --host 0.0.0.0 --port 8010 > "$LOG_DIR/orchestrator.log" 2>&1 &
echo "[OK] Orchestrator en puerto 8010 (PID $!)"

# 5. Iniciar agentes NATS
cd "$ORCHESTRATOR_DIR/agents"
for agent in skills-agent infra-agent agent-factory version-agent; do
    if [ -f "$agent/service.py" ]; then
        nohup python "$agent/service.py" > "$LOG_DIR/$agent.log" 2>&1 &
        echo "[OK] $agent iniciado (PID $!)"
    else
        echo "[WARN] $agent/service.py no encontrado"
    fi
done

# 6. Iniciar Dashboard
if [ -d "$ORCHESTRATOR_DIR/dashboard" ]; then
    cd "$ORCHESTRATOR_DIR/dashboard"
    nohup streamlit run app.py --server.port 8501 > "$LOG_DIR/dashboard.log" 2>&1 &
    echo "[OK] Dashboard en http://192.168.2.112:8501 (PID $!)"
fi

echo ""
echo "=== Sistema iniciado ==="
echo "Logs en: $LOG_DIR"
```

**Archivo: `scripts/stop_all.sh`**

```bash
#!/bin/bash
# Detener todos los servicios del Constructor Astrik

echo "=== Deteniendo Constructor Astrik ==="

# Detener Dashboard
if pgrep -f "streamlit run app.py" > /dev/null 2>&1; then
    pkill -f "streamlit run app.py"
    echo "[OK] Dashboard detenido"
fi

# Detener Orchestrator
if pgrep -f "uvicorn server:app" > /dev/null 2>&1; then
    pkill -f "uvicorn server:app"
    echo "[OK] Orchestrator detenido"
fi

# Detener agentes NATS
for agent in skills-agent infra-agent agent-factory version-agent; do
    if pgrep -f "$agent/service.py" > /dev/null 2>&1; then
        pkill -f "$agent/service.py"
        echo "[OK] $agent detenido"
    fi
done

echo "=== Sistema detenido ==="
```

**Archivo: `scripts/status.sh`**

```bash
#!/bin/bash
# Mostrar estado de todos los servicios

echo "=== Estado de Constructor Astrik ==="
echo ""

# Orchestrator
if curl -sf http://192.168.2.112:8010/health > /dev/null 2>&1; then
    echo "[OK] Orchestrator :8010"
else
    echo "[--] Orchestrator :8010 (offline)"
fi

# Agentes NATS
for agent in skills-agent infra-agent agent-factory version-agent; do
    if pgrep -f "$agent/service.py" > /dev/null 2>&1; then
        echo "[OK] $agent"
    else
        echo "[--] $agent (offline)"
    fi
done

# Dashboard
if pgrep -f "streamlit run app.py" > /dev/null 2>&1; then
    echo "[OK] Dashboard :8501"
else
    echo "[--] Dashboard :8501 (offline)"
fi

# Servicios Docker
echo ""
echo "--- Servicios Docker ---"
docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "Docker no disponible"
```

**Archivo: `scripts/astrik.sh`**

```bash
#!/bin/bash
# CLI unificada para interactuar con Constructor Astrik

ORCHESTRATOR_URL="http://192.168.2.112:8010"

case "${1:-help}" in
    "run")
        if [ -z "$2" ]; then
            echo "Uso: astrik run <objetivo>"
            exit 1
        fi
        echo "Enviando objetivo al Orchestrator..."
        curl -s -X POST "$ORCHESTRATOR_URL/workflows" \
            -H "Content-Type: application/json" \
            -d "{\"objective\": \"$2\"}" | python3 -m json.tool
        ;;
    "decision")
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Uso: astrik decision <thread_id> <approve|reject|modify>"
            exit 1
        fi
        echo "Enviando decision '$3' para workflow $2..."
        curl -s -X POST "$ORCHESTRATOR_URL/workflows/$2/decision" \
            -H "Content-Type: application/json" \
            -d "{\"decision\": \"$3\"}" | python3 -m json.tool
        ;;
    "status")
        curl -s "$ORCHESTRATOR_URL/health" | python3 -m json.tool
        ;;
    "workflow")
        if [ -z "$2" ]; then
            curl -s "$ORCHESTRATOR_URL/workflows" | python3 -m json.tool
        else
            curl -s "$ORCHESTRATOR_URL/workflows/$2" | python3 -m json.tool
        fi
        ;;
    "dashboard")
        echo "Dashboard: http://192.168.2.112:8501"
        ;;
    "start")
        bash "$(dirname "$0")/start_all.sh"
        ;;
    "stop")
        bash "$(dirname "$0")/stop_all.sh"
        ;;
    "help"|*)
        echo "Constructor Astrik CLI"
        echo ""
        echo "Uso: astrik <comando> [argumentos]"
        echo ""
        echo "Comandos:"
        echo "  run <objetivo>          Enviar objetivo al sistema"
        echo "  decision <id> <d>       Aprobar/rechazar workflow (approve|reject|modify)"
        echo "  status                  Estado del Orchestrator"
        echo "  workflow [id]           Listar o ver detalle de workflow"
        echo "  dashboard               Abrir URL del Dashboard"
        echo "  start                   Iniciar todos los servicios"
        echo "  stop                    Detener todos los servicios"
        echo "  help                    Mostrar esta ayuda"
        ;;
esac
```

```bash
# Instalacion:
# sudo ln -s ~/astrik-platform/scripts/astrik.sh /usr/local/bin/astrik
# sudo chmod +x /usr/local/bin/astrik
```

---

### Paso 18: Crear Documentacion

**Archivo: `docs/README.md`**

```markdown
# Constructor Astrik

Sistema Multi-Agente Autonomo para construir la plataforma Astrik AI.

## Arquitectura

Ver `docs/ARQUITECTURA.md` para el diagrama completo.

## Stack Tecnologico

- **Orquestacion**: LangGraph 0.4.7 + FastAPI
- **Mensajeria**: NATS (nats-py 2.9.0)
- **Base de datos**: PostgreSQL 16 (checkpoints), Redis 7 (logs/pub-sub), Qdrant (memoria semantica)
- **LLM**: llama.cpp GPU con Qwen2.5-32B-Instruct-Q4_K_M.gguf
- **Agentes**: Skills Agent, Infra Agent, Agent Factory, Version Agent
- **Dashboard**: Streamlit 1.43
- **Dashboard**: servicios como systemd en VM core (192.168.2.112)

## Requisitos

- Python 3.12+
- Docker + Docker Compose
- NATS Server (via Docker)
- PostgreSQL 16 (via Docker)
- Redis 7 (via Docker)
- llama.cpp con GPU (en LXC aparte)

## Instalacion Rapida

```bash
# 1. Clonar repositorio
git clone https://github.com/diegorod66/astrik-ai-platform.git ~/astrik-platform
cd ~/astrik-platform

# 2. Instalar dependencias del Orchestrator
pip install -r orchestrator/requirements.txt

# 3. Instalar dependencias del Dashboard
pip install -r dashboard/requirements.txt

# 4. Configurar .env
cp orchestrator/.env.example orchestrator/.env
# Editar orchestrator/.env con las URLs correctas

# 5. Iniciar infraestructura
cd infrastructure && docker compose up -d && cd ..

# 6. Iniciar todo
bash scripts/start_all.sh
```

## Uso

### CLI

```bash
# Enviar objetivo
astrik run "Buscar e instalar una herramienta de linting para Python"

# Ver estado
astrik status

# Listar workflows
astrik workflow

# Aprobar workflow pausado
astrik decision <thread_id> approve

# Iniciar/detener sistema
astrik start
astrik stop
```

### Dashboard

Abrir `http://192.168.2.112:8501`

### API

```bash
# Crear workflow
curl -X POST http://192.168.2.112:8010/workflows \
  -H "Content-Type: application/json" \
  -d '{"objective": "Buscar herramienta de linting"}'

# Ver workflow
curl http://192.168.2.112:8010/workflows/<thread_id>

# Aprobar workflow
curl -X POST http://192.168.2.112:8010/workflows/<thread_id>/decision \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve"}'

# Healthcheck
curl http://192.168.2.112:8010/health
```

## Estructura del Repositorio

```
astrik-platform/
  agents/              # Agentes NATS (skills, infra, factory, version)
  dashboard/           # Streamlit dashboard
  docs/                # Documentacion y planes
  infrastructure/      # Docker Compose, .env
  orchestrator/        # LangGraph StateGraph + FastAPI
  scripts/             # CLI, start/stop, deploy
  shared/              # Clase base AgentService, Logger
  tests/               # Tests de integracion
```

## Versionado

```bash
python scripts/release.py snapshot <componente> <version>
```

## Licencia

MIT
```

**Archivo: `docs/ARQUITECTURA.md`**

```markdown
# Arquitectura de Constructor Astrik

## Diagrama de Componentes

Ver el diagrama interactivo en `constructor-astrik-diagram.html`.

## Flujo de un Workflow Completo

1. **Usuario** envia objetivo via CLI, Dashboard o API
2. **FastAPI** recibe `POST /workflows` y crea un `thread_id`
3. **Planner Node** consulta LLM para dividir el objetivo en tareas con agente asignado
4. **Executor NATS Node** toma cada tarea e invoca el agente correspondiente via NATS
5. **Validator Node** verifica el resultado:
   - Si OK: avanza a siguiente tarea
   - Si falla: reintenta hasta 2 veces
   - Si todas completas: PAUSA con `interrupt()` para aprobacion humana
6. **Humano** aprueba via Dashboard o API `POST /workflows/{id}/decision`
7. **Deployer Node** invoca Version Agent via NATS para snapshot y bump
8. **Respuesta final** devuelta al usuario

## Protocolo de Eventos NATS

### Sujetos de Agentes

| Subject | Direccion | Descripcion |
|---|---|---|
| `agent.<name>.request` | Orchestrator -> Agente | Solicitud de tarea |
| `agent.<name>.response` | Agente -> Orchestrator | Respuesta de tarea |
| `agent.<name>.heartbeat` | Agente -> NATS | Heartbeat cada 30s |
| `agent.<name>.online` | Agente -> NATS | Al iniciar |
| `agent.<name>.offline` | Agente -> NATS | Al detener |

### Sujetos de Workflow

| Subject | Direccion | Descripcion |
|---|---|---|
| `workflow.started` | Orchestrator -> NATS | Workflow iniciado |
| `task.started` | Orchestrator -> NATS | Tarea iniciada |
| `task.completed` | Orchestrator -> NATS | Tarea completada |
| `task.retry` | Orchestrator -> NATS | Reintentando tarea |
| `task.failed` | Orchestrator -> NATS | Tarea fallida |
| `workflow.pending_approval` | Orchestrator -> NATS | Esperando humano |
| `workflow.finished` | Orchestrator -> NATS | Workflow terminado |
| `deploy.started` | Orchestrator -> NATS | Deploy iniciado |
| `deploy.component_done` | Orchestrator -> NATS | Componente versionado |
| `deploy.completed` | Orchestrator -> NATS | Deploy completado |

### Logs (Redis Pub/Sub)

| Channel | Formato | Descripcion |
|---|---|---|
| `astrik:logs` | `{"service","level","message","timestamp"}` | Logs de todos los servicios |

## Esquema de Base de Datos

### PostgreSQL (Checkpoints de LangGraph)

Tabla `checkpoints` (creada automaticamente por AsyncPostgresSaver):
- `thread_id` TEXT
- `checkpoint_ns` TEXT
- `parent_checkpoint_id` TEXT
- `checkpoint` JSONB
- `metadata` JSONB

### Redis

- Pub/Sub channel `astrik:logs` para logs en tiempo real
- Pub/Sub channel `astrik:events` para eventos de sistema

### Qdrant

- Colecciones para memoria semantica de agentes (uso futuro)

## Puertos

| Servicio | Puerto | Host |
|---|---|---|
| Orchestrator API | 8010 | 192.168.2.112 |
| Dashboard | 8501 | 192.168.2.112 |
| PostgreSQL | 5432 | 192.168.2.112 |
| Redis | 6379 | 192.168.2.112 |
| Qdrant | 6333 | 192.168.2.112 |
| NATS | 4222 | 192.168.2.112 |
| LLM API | 11434 | 192.168.2.111 |
```

---

## Orden de Implementacion

| Paso | Archivo(s) | Accion |
|---|---|---|
| 1 | `shared/logger.py` | CREAR |
| 2 | `shared/agent_service.py` | MODIFICAR (usar CentralizedLogger) |
| 3 | `orchestrator/llm.py` | MODIFICAR (prompt con agent NATS) |
| 4 | `orchestrator/nodes/planner.py` | MODIFICAR (plan con agent/tool) |
| 5 | `orchestrator/nodes/executor_nats.py` | REESCRIBIR (invocar agentes via NATS) |
| 6 | `orchestrator/nodes/validator.py` | MODIFICAR (human-in-loop con interrupt) |
| 7 | `orchestrator/nodes/deployer.py` | MODIFICAR (Version Agent via NATS) |
| 8 | `orchestrator/graph.py` | MODIFICAR (executor_nats + rutas) |
| 9 | `orchestrator/server.py` | MODIFICAR (decision + historial) |
| 10 | `orchestrator/tools/registry.py` | MODIFICAR (agregar TOOL_REGISTRY_NATS) |
| 11 | `dashboard/src/nats_client.py` | CREAR |
| 12 | `dashboard/src/orchestrator_client.py` | CREAR |
| 13 | `dashboard/src/db_client.py` | CREAR |
| 14 | `dashboard/app.py` | CREAR |
| 15 | `dashboard/pages/01_Agentes.py` | CREAR |
| 15 | `dashboard/pages/02_Workflows.py` | CREAR |
| 15 | `dashboard/pages/03_Historial.py` | CREAR |
| 15 | `dashboard/pages/04_Configuracion.py` | CREAR |
| 16 | `dashboard/requirements.txt` | CREAR |
| 16 | `dashboard/Dockerfile` | CREAR |
| 17 | `scripts/start_all.sh` | CREAR |
| 17 | `scripts/stop_all.sh` | CREAR |
| 17 | `scripts/status.sh` | CREAR |
| 17 | `scripts/astrik.sh` | CREAR |
| 18 | `docs/README.md` | CREAR |
| 18 | `docs/ARQUITECTURA.md` | CREAR |

---

## Verificacion por Paso

Cada paso debe verificarse antes de continuar:

### Verificacion Paso 1-2 (Logger)
```bash
python -c "from shared.logger import CentralizedLogger; print('logger ok')"
```

### Verificacion Paso 3-4 (Planner con agentes)
```bash
python -c "
import asyncio
from orchestrator.llm import plan_objective
plan = asyncio.run(plan_objective('Buscar herramienta de linting'))
print(plan)
# Cada tarea debe tener 'agent' y 'tool'
assert all('agent' in t for t in plan), 'Falta agent en plan'
print('plan_objective OK')
"
```

### Verificacion Paso 5-9 (Workflow completo sin agentes reales)
```bash
# Iniciar orchestrator en modo test
uvicorn orchestrator.server:app --host 0.0.0.0 --port 8010 &

# Enviar workflow
curl -X POST http://localhost:8010/workflows \
  -H "Content-Type: application/json" \
  -d '{"objective": "Prueba de sistema"}'

# Ver estado
curl http://localhost:8010/workflows/<thread_id>

# Endpoint decision
curl -X POST http://localhost:8010/workflows/<thread_id>/decision \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve"}'

# Health
curl http://localhost:8010/health
```

### Verificacion Paso 11-16 (Dashboard)
```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py --server.port 8501
# Abrir http://localhost:8501
```

### Verificacion Paso 17 (Scripts)
```bash
bash scripts/astrik.sh help
bash scripts/status.sh
```

---

## Prueba Integrada Final

```python
"""
test_fase4_workflow.py - Prueba de integracion del workflow completo.
Ejecutar CON agentes NATS y infraestructura corriendo.
"""

import asyncio
import httpx

ORCHESTRATOR_URL = "http://192.168.2.112:8010"


async def test_health():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{ORCHESTRATOR_URL}/health", timeout=5)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
    print("[OK] Health endpoint")


async def test_create_workflow():
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{ORCHESTRATOR_URL}/workflows",
            json={"objective": "Buscar herramienta de documentacion Python"},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        assert "thread_id" in data
        assert data["status"] in ("completed", "running", "failed")
    print(f"[OK] Workflow creado: {data['thread_id']} -> {data['status']}")
    return data["thread_id"]


async def test_get_workflow(thread_id: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{ORCHESTRATOR_URL}/workflows/{thread_id}", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "objective" in data
        assert "plan" in data
    print(f"[OK] Workflow recuperado: {len(data.get('plan', []))} tareas")


async def test_decision(thread_id: str):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{ORCHESTRATOR_URL}/workflows/{thread_id}/decision",
            json={"decision": "approve"},
            timeout=5,
        )
        assert r.status_code == 200
    print("[OK] Decision enviada")


async def main():
    await test_health()
    thread_id = await test_create_workflow()
    await test_get_workflow(thread_id)
    await test_decision(thread_id)
    print("\n=== Todas las pruebas pasaron ===")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Ticket de Versionado al Finalizar

```markdown
# Ticket: Release Fase 4 — Workflow Autonomo + Dashboard

## Componente
- `orchestrator` (modificado)
- `dashboard` (nuevo)
- `scripts/` (nuevo)
- `shared/logger.py` (nuevo)
- `shared/agent_service.py` (modificado)
- `docs/` (nuevo)

## Objetivo
Completar el sistema multi-agente autonomo con workflow completo, human-in-loop, dashboard Streamlit y CLI.

## Checklist
- [ ] Logger centralizado funcionando (Redis pub/sub)
- [ ] Agentes usan CentralizedLogger (sin print())
- [ ] Planner asigna agente NATS a cada tarea via LLM
- [ ] Executor invoca agentes reales via NATS
- [ ] Validator pausa con interrupt() antes del deploy
- [ ] Deployer invoca Version Agent via NATS
- [ ] Endpoint POST /workflows/{id}/decision funcional
- [ ] Endpoint GET /workflows (historial) funcional
- [ ] Dashboard muestra agentes en vivo
- [ ] Dashboard permite enviar objetivos
- [ ] Dashboard tiene pagina de aprobacion humana
- [ ] CLI astrik.sh funcional (run, decision, status, workflow)
- [ ] Scripts start/stop/status.sh funcionales
- [ ] docs/README.md y docs/ARQUITECTURA.md completos
- [ ] Prueba integrada final pasa

## Comando final
```bash
python scripts/release.py snapshot . v1.0.0
git add -A
git commit -m "feat: Fase 4 completa - workflow autonomo + dashboard"
git push origin master --tags
```
```

---

## Criterios de Exito (Checklist Final)

- [ ] Workflow completo: objetivo -> LLM planifica con agente -> ejecutor invoca via NATS -> validator valida -> human-in-loop -> deployer versiona
- [ ] Human-in-loop: el workflow pausa con `interrupt()` y espera decision antes del deploy
- [ ] Dashboard Streamlit muestra agentes en vivo con estado y heartbeats
- [ ] Dashboard permite enviar objetivos y ver resultados
- [ ] Dashboard tiene pagina de aprobacion humana (workflows pausados)
- [ ] CLI `astrik` funciona: `astrik run`, `astrik decision`, `astrik status`, `astrik workflow`
- [ ] Scripts `start_all.sh` / `stop_all.sh` / `status.sh` funcionales
- [ ] Logger centralizado: `shared/logger.py` implementado, agentes lo usan
- [ ] Errores: si un agente NATS falla, reintenta 2 veces, si persiste escala al humano
- [ ] Documentacion completa: `docs/README.md` y `docs/ARQUITECTURA.md`
- [ ] Prueba integrada `test_fase4_workflow.py` pasa
- [ ] Release v1.0.0 versionado en GitHub
