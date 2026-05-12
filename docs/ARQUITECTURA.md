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
