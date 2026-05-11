# infra-agent

## Descripción
Agente especializado en construir y gestionar toda la infraestructura Docker del proyecto: servicios, redes, volumenes, healthchecks, monitoreo. Gestiona PostgreSQL, Redis, Qdrant, NATS y llama.cpp

## Versión
1.0.0

## Modelo
deepseek-coder — llamacpp

## Herramientas
filesystem, docker, shell

## Dependencias
pyyaml

## Uso
```bash
python main.py --task <tarea> --input '<json>'
```

## Eventos
- Consume: INFRA_BUILD_REQUESTED, INFRA_SERVICE_ADD
- Publica: INFRA_READY, INFRA_SERVICE_RUNNING
