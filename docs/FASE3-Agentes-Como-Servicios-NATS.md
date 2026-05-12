# FASE 3: Agentes como Servicios NATS

## Contexto del Proyecto (Actualizado)

Constructor Astrik es un sistema multi-agente que actualmente tiene:

### Infraestructura corriendo (deployada)

| Componente | URL/Datos |
|------------|-----------|
| Orchestrator API | http://192.168.2.112:8010 (health: /health) |
| PostgreSQL | 192.168.2.112:5432 / user: astrik / pass: astrik_secret / db: astrik |
| Redis | 192.168.2.112:6379 |
| Qdrant | http://192.168.2.112:6333 (gRPC: 6334) |
| NATS | 192.168.2.112:4222 (monitor: http://192.168.2.112:8222) |
| LLM endpoint | http://192.168.2.111:11434/v1/chat/completions (modelo: Qwen2.5-32B-Instruct-Q4_K_M.gguf) |

### Agentes existentes (scripts CLI, NO servicios)

Todos en el repositorio bajo `agents/`:

| Agente | Path | Funcion |
|--------|------|---------|
| Agent Factory | `agents/agent-factory/` | Crear y validar agentes estandarizados |
| Skills Agent | `agents/skills-agent/` | Buscar, instalar y documentar herramientas |
| Infra Agent | `agents/infra-agent/` | Generar infraestructura Docker |

### Orchestrator existente (con LangGraph)

El Orchestrator ya esta corriendo y expone API REST en puerto 8010.
Tiene nodos: planner, executor, validator, deployer.
Usa LangGraph con checkpoints en PostgreSQL.
Tiene event bus NATS.

### Estructura del repositorio

```
astrik-ai-platform/
+-- agents/              # Agentes (scripts CLI actualmente)
+-- orchestrator/        # LangGraph + FastAPI (ya deployado)
+-- infrastructure/      # Docker compose files
+-- scripts/             # release.py, etc.
+-- docs/                # Documentacion
+-- runtimes/            # Config de runtimes (llamacpp)
+-- skills/              # Skills instalados
+-- releases/            # Snapshots versionados
+-- shared/              # Codigo compartido (a crear)
```

### Stack tecnologico

- Python 3.12+
- LangGraph / LangChain
- FastAPI / uvicorn
- nats-py (cliente NATS)
- llama.cpp via API OpenAI-compatible
- PostgreSQL (asyncpg), Redis (redis-py), Qdrant (qdrant-client)
- Los agentes actuales son scripts CLI que ejecutan y terminan

---

## Objetivo de la Fase 3

Convertir cada agente de **script CLI** a **servicio vivo** que:

1. Conecta a NATS al iniciar
2. Escucha eventos (subscribe) en subjects especificos
3. Procesa tareas cuando llegan
4. Publica resultados (publish)
5. Envia heartbeat periodico
6. Responde a graceful shutdown

---

## Arquitectura de la Fase 3

```
                     NATS (192.168.2.112:4222)
                            |
         +------------------+-------------------+
         |                  |                   |
    skills.service     infra.service      factory.service
    (skills-agent)     (infra-agent)      (agent-factory)
         |                  |                   |
    version.service    orchestrator        [futuros agentes]
    (version-agent)    (ya corriendo)
```

Cada servicio es un proceso Python independiente que:
- Corre como daemon (systemd o docker)
- Se conecta a NATS al arrancar
- Publica un evento AGENT_ONLINE con su metadata (nombre, version, tools, modelo)
- Escucha events en `agent.<nombre>.request`
- Publica respuestas en `agent.<nombre>.response`
- Envia heartbeat cada 30s en `heartbeat.<nombre>`

---

## Protocolo de Eventos NATS

### Subjects

| Subject | Direction | Descripcion |
|---------|-----------|-------------|
| `agent.<name>.request` | Orchestrator -> Agente | Tarea a ejecutar |
| `agent.<name>.response` | Agente -> Orchestrator | Resultado de la tarea |
| `agent.<name>.heartbeat` | Agente -> Sistema | Heartbeat (cada 30s) |
| `agent.<name>.online` | Agente -> Sistema | Registro al iniciar |
| `agent.<name>.offline` | Agente -> Sistema | Notificacion al detenerse |
| `system.shutdown` | Sistema -> Todos | Señal de detencion global |

### Formato de eventos (JSON)

**REQUEST (Orchestrator -> Agente)**
```json
{
  "id": "uuid-de-la-tarea",
  "type": "search | install | generate_compose | create_agent | snapshot | etc",
  "payload": {
    // parametros especificos de la tarea
  },
  "timestamp": "2026-05-12T00:00:00Z",
  "reply_to": "agent.skills.response"  // subject para respuesta
}
```

**RESPONSE (Agente -> Orchestrator)**
```json
{
  "id": "uuid-de-la-tarea",
  "status": "completed | failed | running",
  "result": {
    // resultado especifico de la tarea
  },
  "error": null,
  "timestamp": "2026-05-12T00:00:01Z"
}
```

**HEARTBEAT (Agente -> Sistema)**
```json
{
  "agent": "skills-agent",
  "version": "1.0.0",
  "status": "idle | busy",
  "uptime": 3600,
  "current_task": null,
  "timestamp": "2026-05-12T00:00:30Z"
}
```

**ONLINE (Agente -> Sistema)**
```json
{
  "agent": "infra-agent",
  "version": "1.0.0",
  "model": "deepseek-coder",
  "runtime": "llamacpp",
  "tools": ["docker_compose", "check_health", "add_service"],
  "events_consumes": ["agent.infra.request"],
  "events_publishes": ["agent.infra.response", "agent.infra.heartbeat"],
  "status": "online"
}
```

---

## Tarea 1: Crear Clase Base AgentService en shared/

**Archivo a crear:** `shared/agent_service.py`

Debe ser una clase base abstracta que cualquier agente pueda heredar para convertirse en servicio NATS.

### Interfaz:

```python
class AgentService(ABC):
    # Configuracion
    agent_name: str                    # Nombre del agente
    agent_version: str                 # Version
    model: str                         # Modelo asignado
    tools: list[str]                   # Herramientas disponibles
    events_consumes: list[str]         # Subjects que escucha
    events_publishes: list[str]        # Subjects que publica

    # Ciclo de vida
    async def start(self):             # Conectar a NATS, publicar ONLINE, loop heartbeat
    async def stop(self):              # Publicar OFFLINE, desconectar NATS
    async def handle_request(self, msg): # Callback cuando llega un request

    # Hook para subclases
    @abstractmethod
    async def execute_task(self, task_type: str, payload: dict) -> dict:
        """Implementar en cada agente. Procesa la tarea y devuelve resultado."""
        pass
```

### Detalles de implementacion:

```python
import asyncio
import json
import uuid
import signal
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg

NATS_URL = "nats://192.168.2.112:4222"
HEARTBEAT_INTERVAL = 30  # segundos

class AgentService(ABC):

    def __init__(self):
        self.nc = NATS()
        self.subscriptions = []
        self._running = False
        self._start_time = None
        self._current_task = None

    @property
    @abstractmethod
    def agent_name(self) -> str: ...

    @property
    @abstractmethod
    def agent_version(self) -> str: ...

    @property
    def model(self) -> str:
        return "hermes3"

    @property
    def tools(self) -> list[str]:
        return []

    @property
    def events_consumes(self) -> list[str]:
        return [f"agent.{self.agent_name}.request"]

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

        # Conectar a NATS
        await self.nc.connect(NATS_URL)
        print(f"[{self.agent_name}] Conectado a NATS en {NATS_URL}")

        # Publicar ONLINE
        await self._publish_online()

        # Suscribirse a requests
        for subject in self.events_consumes:
            sub = await self.nc.subscribe(subject, cb=self._on_message)
            self.subscriptions.append(sub)
            print(f"[{self.agent_name}] Escuchando en: {subject}")

        # Heartbeat loop
        asyncio.create_task(self._heartbeat_loop())

        # Graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            except NotImplementedError:
                # Windows no soporta add_signal_handler
                pass

        print(f"[{self.agent_name}] Servicio iniciado. Esperando eventos...")

    async def stop(self):
        self._running = False
        await self._publish_offline()
        for sub in self.subscriptions:
            try:
                await sub.unsubscribe()
            except Exception:
                pass
        await self.nc.drain()
        print(f"[{self.agent_name}] Servicio detenido.")

    async def _on_message(self, msg: Msg):
        try:
            data = json.loads(msg.data.decode())
            task_id = data.get("id", str(uuid.uuid4()))
            task_type = data.get("type", "unknown")
            payload = data.get("payload", {})
            reply_to = data.get("reply_to", f"agent.{self.agent_name}.response")

            print(f"[{self.agent_name}] Tarea recibida: {task_type} (id: {task_id})")
            self._current_task = task_id

            # Publicar respuesta inmediata: running
            await self.nc.publish(reply_to, json.dumps({
                "id": task_id, "status": "running",
                "result": None, "error": None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }).encode())

            # Ejecutar la tarea (hook de la subclase)
            result = await self.execute_task(task_type, payload)
            self._current_task = None

            status = "completed" if result.get("error") is None else "failed"

            # Publicar respuesta final
            await self.nc.publish(reply_to, json.dumps({
                "id": task_id, "status": status,
                "result": result.get("data"),
                "error": result.get("error"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }).encode())

            print(f"[{self.agent_name}] Tarea {task_id}: {status}")

        except Exception as e:
            print(f"[{self.agent_name}] Error procesando mensaje: {e}")
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
        """Implementar en la subclase.

        Returns:
            dict con formato: {"data": ..., "error": null} o {"data": null, "error": "mensaje"}
        """
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
```

### Tests de la clase base (shared/tests/test_agent_service.py)

Verificar:
- Conexion a NATS
- Publicacion de ONLINE al iniciar
- Recepcion de mensajes
- Publicacion de respuesta
- Heartbeat periodico
- Publicacion de OFFLINE al detener
- Graceful shutdown

---

## Tarea 2: Refactorizar Skills Agent como Servicio NATS

**Archivo a crear/refactorizar:** `agents/skills-agent/service.py`

Hereda de AgentService e implementa execute_task() mapeando los tipos de tarea a las herramientas existentes en `src/tools.py`.

### Mapeo de tareas:

| task_type | payload | tool a llamar |
|-----------|---------|---------------|
| `search` | `{"query": "..."}` | `search_github(query)` |
| `evaluate` | `{"candidate": {...}}` | `evaluate_tool(candidate)` |
| `install` | `{"name": "...", "type": "pip", "source": ""}` | `install_tool(name, type, source)` |
| `test` | `{"name": "...", "command": ""}` | `test_tool(name, command)` |
| `pipeline` | `{"tool": "...", "query": "", "type": "pip", "source": ""}` | `run_full_pipeline(tool, query, type, source)` |

### Implementacion:

```python
from shared.agent_service import AgentService
from .src.tools import search_github, evaluate_tool, install_tool, test_tool, run_full_pipeline

class SkillsAgentService(AgentService):
    @property
    def agent_name(self): return "skills-agent"

    @property
    def agent_version(self): return "1.0.0"

    @property
    def tools(self): return ["search_github", "install", "test", "pipeline"]

    async def execute_task(self, task_type: str, payload: dict) -> dict:
        try:
            if task_type == "search":
                results = search_github(payload.get("query", ""), payload.get("max", 5))
                return {"data": results, "error": None}

            elif task_type == "evaluate":
                result = evaluate_tool(payload.get("candidate", {}))
                return {"data": result, "error": None}

            elif task_type == "install":
                result = install_tool(
                    payload.get("name", ""),
                    payload.get("type", "pip"),
                    payload.get("source", "")
                )
                return {"data": result, "error": None}

            elif task_type == "test":
                result = test_tool(
                    payload.get("name", ""),
                    payload.get("command", "")
                )
                return {"data": result, "error": None}

            elif task_type == "pipeline":
                result = run_full_pipeline(
                    payload.get("tool", ""),
                    payload.get("query", ""),
                    payload.get("type", "pip"),
                    payload.get("source", "")
                )
                return {"data": result, "error": None}

            else:
                return {"data": None, "error": f"Tipo de tarea no soportado: {task_type}"}

        except Exception as e:
            return {"data": None, "error": str(e)}


if __name__ == "__main__":
    import asyncio
    service = SkillsAgentService()
    asyncio.run(service.start())
```

---

## Tarea 3: Refactorizar Infra Agent como Servicio NATS

**Archivo a crear:** `agents/infra-agent/service.py`

### Mapeo de tareas:

| task_type | payload | tool a llamar |
|-----------|---------|---------------|
| `build` | `{"services": ["postgres","redis","qdrant","nats"]}` | `run_full_build(services)` |
| `add_service` | `{"name": "monitoring", "config": {...}}` | `add_service(name, config)` |
| `health` | `{"service": "postgres"}` | `check_health(service)` |
| `status` | `{}` | Resumen de infraestructura |
| `gen_env` | `{"services": [...]}` | `generate_env(services)` |

```python
from shared.agent_service import AgentService
from .src.tools import run_full_build, add_service, check_health, generate_env

class InfraAgentService(AgentService):
    @property
    def agent_name(self): return "infra-agent"

    @property
    def agent_version(self): return "1.0.0"

    @property
    def model(self): return "deepseek-coder"

    @property
    def tools(self): return ["build", "add_service", "health", "gen_env"]

    async def execute_task(self, task_type: str, payload: dict) -> dict:
        try:
            if task_type == "build":
                result = run_full_build(payload.get("services"))
                return {"data": result, "error": None}

            elif task_type == "add_service":
                result = add_service(
                    payload.get("name", ""),
                    payload.get("config")
                )
                return {"data": result, "error": None}

            elif task_type == "health":
                result = check_health(payload.get("service", ""))
                return {"data": result, "error": None}

            elif task_type == "gen_env":
                env = generate_env(payload.get("services"))
                return {"data": {"env": env}, "error": None}

            else:
                return {"data": None, "error": f"Tipo de tarea no soportado: {task_type}"}

        except Exception as e:
            return {"data": None, "error": str(e)}


if __name__ == "__main__":
    import asyncio
    service = InfraAgentService()
    asyncio.run(service.start())
```

---

## Tarea 4: Refactorizar Agent Factory como Servicio NATS

**Archivo a crear:** `agents/agent-factory/service.py`

### Mapeo de tareas:

| task_type | payload | tool/accion |
|-----------|---------|-------------|
| `create` | `{"name": "...", "desc": "...", "model": "hermes3", ...}` | `create_agent_structure(schema)` |
| `list` | `{}` | Listar agentes existentes |
| `validate` | `{"name": "..."}` | Validar estructura de un agente |

```python
from shared.agent_service import AgentService
from .src.schema import AgentSchema, AgentEvents
from .src.generator import create_agent_structure, AGENTS_DIR

class FactoryAgentService(AgentService):
    @property
    def agent_name(self): return "agent-factory"

    @property
    def agent_version(self): return "1.0.0"

    @property
    def tools(self): return ["create_agent", "list_agents", "validate_agent"]

    async def execute_task(self, task_type: str, payload: dict) -> dict:
        try:
            if task_type == "create":
                schema = AgentSchema(
                    name=payload["name"],
                    description=payload.get("desc", ""),
                    version=payload.get("version", "1.0.0"),
                    model=payload.get("model", "hermes3"),
                    runtime=payload.get("runtime", "llamacpp"),
                    permissions=payload.get("permissions", []),
                    events=AgentEvents(
                        consumes=payload.get("consumes", []),
                        publishes=payload.get("publishes", []),
                    ),
                    tools=payload.get("tools", []),
                    dependencies=payload.get("dependencies", []),
                )
                path = create_agent_structure(schema)
                return {"data": {"path": str(path), "name": schema.name}, "error": None}

            elif task_type == "list":
                agents = []
                for d in AGENTS_DIR.iterdir():
                    if d.is_dir() and (d / "agent.yaml").exists():
                        agents.append(d.name)
                return {"data": {"agents": agents}, "error": None}

            elif task_type == "validate":
                name = payload.get("name", "")
                agent_path = AGENTS_DIR / name
                if not agent_path.exists():
                    return {"data": None, "error": f"Agente '{name}' no encontrado"}
                required = ["agent.yaml", "main.py", "prompts/system.md",
                           "src/tools.py", "src/handlers.py",
                           "docs/ARCHITECTURE.md", "docs/README.md",
                           "tests/test_main.py", "requirements.txt"]
                missing = [f for f in required if not (agent_path / f).exists()]
                return {"data": {"valid": len(missing) == 0, "missing": missing}, "error": None}

            else:
                return {"data": None, "error": f"Tipo de tarea no soportado: {task_type}"}

        except Exception as e:
            return {"data": None, "error": str(e)}


if __name__ == "__main__":
    import asyncio
    service = FactoryAgentService()
    asyncio.run(service.start())
```

---

## Tarea 5: Crear Version Agent como Servicio NATS (NUEVO)

**Objetivo:** Crear un agente nuevo que exponga las capacidades de `scripts/release.py` como servicio NATS.
Usar el Agent Factory (su CLI) para crearlo, y luego implementar el service.py.

**Creacion via Agent Factory:**
```bash
cd agents/agent-factory
python main.py create \
  --name version-agent \
  --desc "Agente de versionado continuo: snapshot, bump, tag, changelog" \
  --version 1.0.0 \
  --model phi4 \
  --runtime llamacpp \
  --permissions filesystem:write filesystem:read \
  --consumes agent.version.request \
  --publishes agent.version.response agent.version.heartbeat \
  --tools filesystem git \
  --deps pyyaml
```

**Luego implementar service.py en el agent creado:**
`agents/version-agent/service.py`

### Mapeo de tareas:

| task_type | payload | accion |
|-----------|---------|--------|
| `snapshot` | `{"componente": "agents/skills-agent", "version": "v1.1.0"}` | Ejecuta scripts/release.py snapshot |
| `bump` | `{"part": "patch"}` | Sube version del proyecto |
| `list` | `{"componente": ""}` | Lista releases |
| `current` | `{}` | Version actual |
| `changelog` | `{}` | Ultimas entradas del changelog |

```python
from shared.agent_service import AgentService
import subprocess
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RELEASE_SCRIPT = ROOT / "scripts" / "release.py"

class VersionAgentService(AgentService):
    @property
    def agent_name(self): return "version-agent"

    @property
    def agent_version(self): return "1.0.0"

    @property
    def model(self): return "phi4"

    @property
    def tools(self): return ["snapshot", "bump", "list", "current"]

    def _run_release(self, *args) -> dict:
        try:
            result = subprocess.run(
                ["python", str(RELEASE_SCRIPT)] + list(args),
                capture_output=True, text=True, timeout=60
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"returncode": -1, "stdout": "", "stderr": "Timeout"}
        except Exception as e:
            return {"returncode": -1, "stdout": "", "stderr": str(e)}

    async def execute_task(self, task_type: str, payload: dict) -> dict:
        try:
            if task_type == "snapshot":
                componente = payload.get("componente", "")
                version = payload.get("version", "")
                args = ["snapshot", componente]
                if version:
                    args.append(version)
                result = self._run_release(*args)
                return {"data": result, "error": None if result["returncode"] == 0 else result["stderr"]}

            elif task_type == "bump":
                part = payload.get("part", "patch")
                result = self._run_release("bump", part)
                return {"data": result, "error": None if result["returncode"] == 0 else result["stderr"]}

            elif task_type == "list":
                componente = payload.get("componente", "")
                args = ["list"]
                if componente:
                    args.append(componente)
                result = self._run_release(*args)
                return {"data": result, "error": None}

            elif task_type == "current":
                result = self._run_release("current")
                return {"data": result, "error": None}

            else:
                return {"data": None, "error": f"Tipo de tarea no soportado: {task_type}"}

        except Exception as e:
            return {"data": None, "error": str(e)}


if __name__ == "__main__":
    import asyncio
    service = VersionAgentService()
    asyncio.run(service.start())
```

---

## Tarea 6: Integrar Servicios con Orchestrator LangGraph

El Orchestrator ya existente debe ser capaz de invocar agentes via NATS en vez de llamar scripts CLI.

### Crear/modificar en orchestrator:

**`orchestrator/tools/nats_agent.py`** - Tool generica para invocar cualquier agente via NATS:

```python
import asyncio
import json
import uuid
from nats.aio.client import Client as NATS
from datetime import datetime, timezone

NATS_URL = "nats://192.168.2.112:4222"
REQUEST_TIMEOUT = 120  # segundos

class NATSAgentTool:
    """Tool para invocar un agente via NATS y esperar su respuesta."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.request_subject = f"agent.{agent_name}.request"
        self.response_subject = f"agent.{agent_name}.response"

    async def invoke(self, task_type: str, payload: dict, timeout: int = REQUEST_TIMEOUT) -> dict:
        nc = NATS()
        await nc.connect(NATS_URL)

        task_id = str(uuid.uuid4())
        response_future = asyncio.get_event_loop().create_future()

        async def on_response(msg):
            try:
                data = json.loads(msg.data.decode())
                if data.get("id") == task_id:
                    response_future.set_result(data)
            except Exception as e:
                if not response_future.done():
                    response_future.set_exception(e)

        sub = await nc.subscribe(self.response_subject, cb=on_response)

        # Publicar request
        await nc.publish(self.request_subject, json.dumps({
            "id": task_id,
            "type": task_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reply_to": self.response_subject,
        }).encode())

        try:
            result = await asyncio.wait_for(response_future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return {"status": "timeout", "error": f"Agente {self.agent_name} no respondio en {timeout}s"}
        finally:
            await sub.unsubscribe()
            await nc.drain()
```

**`orchestrator/nodes/executor_nats.py`** - Version del executor que usa NATS en vez de CLI:

```python
from langgraph_core import tool
from ..tools.nats_agent import NATSAgentTool

@tool
def invoke_skills_agent(task_type: str, payload: dict) -> dict:
    """Invocar Skills Agent via NATS"""
    import asyncio
    tool = NATSAgentTool("skills-agent")
    return asyncio.run(tool.invoke(task_type, payload))

@tool
def invoke_infra_agent(task_type: str, payload: dict) -> dict:
    """Invocar Infra Agent via NATS"""
    import asyncio
    tool = NATSAgentTool("infra-agent")
    return asyncio.run(tool.invoke(task_type, payload))

@tool
def invoke_factory_agent(task_type: str, payload: dict) -> dict:
    """Invocar Agent Factory via NATS"""
    import asyncio
    tool = NATSAgentTool("agent-factory")
    return asyncio.run(tool.invoke(task_type, payload))

@tool
def invoke_version_agent(task_type: str, payload: dict) -> dict:
    """Invocar Version Agent via NATS"""
    import asyncio
    tool = NATSAgentTool("version-agent")
    return asyncio.run(tool.invoke(task_type, payload))
```

---

## Tarea 7: Script de Deploy de Servicios

**Archivo a crear:** `scripts/deploy_agents.sh`

```bash
#!/bin/bash
# Deploy de todos los agentes como servicios en la VM core

HOST="constructor@192.168.2.112"
REMOTE_DIR="/home/constructor/astrik-agents"

echo "=== Desplegando agentes NATS en $HOST ==="

# Crear directorio remoto
ssh "$HOST" "mkdir -p $REMOTE_DIR"

# Copiar agentes y shared
rsync -avz --delete \
  agents/skills-agent/ \
  "$HOST:$REMOTE_DIR/skills-agent/"

rsync -avz --delete \
  agents/infra-agent/ \
  "$HOST:$REMOTE_DIR/infra-agent/"

rsync -avz --delete \
  agents/agent-factory/ \
  "$HOST:$REMOTE_DIR/agent-factory/"

# Copiar version-agent si existe
if [ -d "agents/version-agent" ]; then
  rsync -avz --delete \
    agents/version-agent/ \
    "$HOST:$REMOTE_DIR/version-agent/"
fi

# Copiar shared/
rsync -avz --delete \
  shared/ \
  "$HOST:$REMOTE_DIR/shared/"

# Instalar dependencias
ssh "$HOST" "cd $REMOTE_DIR && pip install -r skills-agent/requirements.txt 2>/dev/null; true"
ssh "$HOST" "cd $REMOTE_DIR && pip install nats-py 2>/dev/null; true"

# Iniciar servicios con systemd
for agent in skills-agent infra-agent agent-factory version-agent; do
  if [ -d "$REMOTE_DIR/$agent" ]; then
    ssh "$HOST" "cat > /etc/systemd/system/astrik-$agent.service << EOF
[Unit]
Description=Astrik $agent NATS Service
After=network.target nats.service

[Service]
Type=simple
User=constructor
WorkingDirectory=$REMOTE_DIR/$agent
ExecStart=/usr/bin/python3 $REMOTE_DIR/$agent/service.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"
    ssh "$HOST" "systemctl daemon-reload && systemctl enable astrik-$agent.service && systemctl restart astrik-$agent.service"
    echo "  [+] $agent iniciado"
  fi
done

echo "=== Deploy completado ==="
```

---

## Tarea 8: Tests de Integracion

**Archivo a crear:** `tests/test_agents_nats.py`

Pruebas automatizadas:

```python
"""Tests de integracion para agentes como servicios NATS."""

import asyncio
import json
import pytest
from nats.aio.client import Client as NATS

NATS_URL = "nats://192.168.2.112:4222"

@pytest.fixture
async def nats_conn():
    nc = NATS()
    await nc.connect(NATS_URL)
    yield nc
    await nc.drain()

@pytest.mark.asyncio
async def test_skills_agent_online(nats_conn):
    """Verificar que Skills Agent publica ONLINE al iniciar"""
    nc = nats_conn
    future = asyncio.get_event_loop().create_future()

    async def cb(msg):
        data = json.loads(msg.data.decode())
        if data.get("agent") == "skills-agent":
            future.set_result(data)

    await nc.subscribe("agent.skills-agent.online", cb=cb)
    result = await asyncio.wait_for(future, timeout=10)
    assert result["status"] == "online"

@pytest.mark.asyncio
async def test_infra_agent_online(nats_conn):
    """Verificar que Infra Agent publica ONLINE al iniciar"""
    nc = nats_conn
    future = asyncio.get_event_loop().create_future()

    async def cb(msg):
        data = json.loads(msg.data.decode())
        if data.get("agent") == "infra-agent":
            future.set_result(data)

    await nc.subscribe("agent.infra-agent.online", cb=cb)
    result = await asyncio.wait_for(future, timeout=10)
    assert result["status"] == "online"

@pytest.mark.asyncio
async def test_skills_agent_request_response(nats_conn):
    """Skills Agent: enviar request y recibir response"""
    nc = nats_conn
    future = asyncio.get_event_loop().create_future()

    async def cb(msg):
        future.set_result(json.loads(msg.data.decode()))

    await nc.subscribe("agent.skills-agent.response", cb=cb)
    await nc.publish("agent.skills-agent.request", json.dumps({
        "id": "test-001",
        "type": "search",
        "payload": {"query": "python linting", "max": 3},
        "reply_to": "agent.skills-agent.response"
    }).encode())

    result = await asyncio.wait_for(future, timeout=30)
    assert result["status"] in ("completed", "running")

@pytest.mark.asyncio
async def test_infra_agent_health(nats_conn):
    """Infra Agent: verificar health check"""
    nc = nats_conn
    future = asyncio.get_event_loop().create_future()

    async def cb(msg):
        future.set_result(json.loads(msg.data.decode()))

    await nc.subscribe("agent.infra-agent.response", cb=cb)
    await nc.publish("agent.infra-agent.request", json.dumps({
        "id": "test-002",
        "type": "health",
        "payload": {"service": ""},
        "reply_to": "agent.infra-agent.response"
    }).encode())

    result = await asyncio.wait_for(future, timeout=30)
    assert result["status"] in ("completed", "running")

@pytest.mark.asyncio
async def test_version_agent_current(nats_conn):
    """Version Agent: obtener version actual"""
    nc = nats_conn
    future = asyncio.get_event_loop().create_future()

    async def cb(msg):
        future.set_result(json.loads(msg.data.decode()))

    await nc.subscribe("agent.version-agent.response", cb=cb)
    await nc.publish("agent.version-agent.request", json.dumps({
        "id": "test-003",
        "type": "current",
        "payload": {},
        "reply_to": "agent.version-agent.response"
    }).encode())

    result = await asyncio.wait_for(future, timeout=30)
    assert result["status"] in ("completed", "running")
```

---

## Resumen de Archivos a Crear/Modificar

| Archivo | Accion |
|---------|--------|
| `shared/agent_service.py` | CREAR - Clase base AgentService |
| `shared/__init__.py` | CREAR - Package init |
| `agents/skills-agent/service.py` | CREAR - Skills Agent como servicio NATS |
| `agents/infra-agent/service.py` | CREAR - Infra Agent como servicio NATS |
| `agents/agent-factory/service.py` | CREAR - Agent Factory como servicio NATS |
| `agents/version-agent/service.py` | CREAR - Version Agent como servicio NATS |
| `orchestrator/tools/nats_agent.py` | CREAR - Tool NATS para invocar agentes |
| `orchestrator/nodes/executor_nats.py` | CREAR - Executor node que usa NATS |
| `scripts/deploy_agents.sh` | CREAR - Script de deploy |
| `tests/test_agents_nats.py` | CREAR - Tests de integracion |
| `shared/tests/test_agent_service.py` | CREAR - Tests de la clase base |

---

## Orden de Implementacion

1. `shared/agent_service.py` + tests
2. `agents/skills-agent/service.py` (el mas simple, ya tiene tools implementadas)
3. Probar skills-agent manualmente
4. `agents/infra-agent/service.py`
5. Probar infra-agent manualmente
6. `agents/agent-factory/service.py`
7. Probar factory-agent manualmente
8. Crear `agents/version-agent/` via Agent Factory + implementar service.py
9. Probar version-agent manualmente
10. `orchestrator/tools/nats_agent.py` + `executor_nats.py`
11. Tests de integracion
12. Deploy en VM core
13. Versionar release: `python scripts/release.py snapshot agents v1.0.0`

---

## Criterio de Exito de la Fase 3

- [ ] Cada agente inicia, se conecta a NATS y publica AGENT_ONLINE
- [ ] Orchestrator puede invocar Skills Agent via NATS y recibe respuesta
- [ ] Orchestrator puede invocar Infra Agent via NATS y recibe respuesta
- [ ] Orchestrator puede invocar Agent Factory via NATS y recibe respuesta
- [ ] Orchestrator puede invocar Version Agent via NATS y recibe respuesta
- [ ] Heartbeats periodicos de cada agente visibles en NATS
- [ ] Graceful shutdown publica AGENT_OFFLINE
- [ ] Tests de integracion pasan
- [ ] Agentes deployados en VM core como servicios systemd
- [ ] Versionado del release completo
