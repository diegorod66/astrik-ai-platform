# Arquitectura del Agente: infra-agent

## Identidad
- **Nombre:** infra-agent
- **Versión:** 1.0.0
- **Modelo:** DeepSeek-Coder
- **Runtime:** llama.cpp

## Propósito
Construir y gestionar toda la infraestructura Docker del proyecto Astrik AI Platform.
Genera docker-compose.yml, .env, monitoreo y runtime de modelos.

## Flujo de trabajo

```
Usuario / OpenCode
        |
        v
   Infra Agent (main.py)
        |
        +-- build ---------> Genera:
        |                       - infrastructure/docker-compose.yml
        |                       - infrastructure/.env
        |                       - infrastructure/monitoring/prometheus.yml
        |                       - runtimes/llamacpp/Dockerfile
        |
        +-- add ------------> Agrega servicio al compose existente
        |
        +-- health ---------> docker ps de servicios del proyecto
        |
        +-- status ---------> Resumen completo de infraestructura
```

## Servicios incluidos

| Servicio | Puerto | Proposito |
|----------|--------|-----------|
| PostgreSQL | 5432 | Persistencia principal |
| Redis | 6379 | Cache / short-term memory |
| Qdrant | 6333 | Memoria vectorial / RAG |
| NATS | 4222 | Event bus entre agentes |
| llama.cpp | 8080 | Inferencia GPU con CUDA |
| Prometheus | 9090 | Metricas |
| Grafana | 3001 | Dashboard de monitoreo |

## Comunicacion
- **Consume:** INFRA_BUILD_REQUESTED, INFRA_SERVICE_ADD
- **Publica:** INFRA_READY, INFRA_SERVICE_RUNNING
