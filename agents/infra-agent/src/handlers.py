"""
Manejadores de eventos para Infra Agent.

Eventos que consume:
- INFRA_BUILD_REQUESTED: construir infraestructura completa
- INFRA_SERVICE_ADD: agregar un servicio al compose
"""

import json
from .tools import run_full_build, add_service, check_health


def handle_infra_build_requested(event: dict) -> dict:
    """Construir infraestructura completa.

    Event payload:
        services (list, opcional): Servicios a incluir
            default: [postgres, redis, qdrant, nats]
    """
    services = event.get("services")
    result = run_full_build(services)

    if result["status"] == "completed":
        return {"event": "INFRA_READY", "status": "ok", "result": result}
    return {"event": "INFRA_READY", "status": "error", "error": str(result)}


def handle_infra_service_add(event: dict) -> dict:
    """Agregar servicio al docker-compose.

    Event payload:
        name (str): Nombre del servicio
        config (dict, opcional): Configuracion personalizada
    """
    name = event.get("name", "")
    if not name:
        return {"event": "INFRA_SERVICE_ADD", "status": "error", "error": "Falta 'name'"}

    result = add_service(name, event.get("config"))
    return {"event": "INFRA_SERVICE_RUNNING", "status": result["status"], "result": result}


def handle_infra_health_check(event: dict) -> dict:
    """Verificar estado de servicios Docker."""
    service = event.get("service")
    result = check_health(service)
    return {"event": "INFRA_HEALTH", "status": "ok", "result": result}
