from pydantic import BaseModel, Field
from typing import Optional


class AgentEvents(BaseModel):
    consumes: list[str] = []
    publishes: list[str] = []


class AgentSchema(BaseModel):
    name: str = Field(..., description="Nombre único del agente")
    version: str = Field(default="1.0.0", description="Versión semántica")
    description: str = Field(..., description="Descripción funcional")
    model: str = Field(..., description="Modelo de IA asignado")
    runtime: str = Field(default="llamacpp", description="Runtime de inferencia")
    permissions: list[str] = Field(default=[], description="Permisos del agente")
    events: Optional[AgentEvents] = None
    tools: list[str] = Field(default=[], description="Herramientas disponibles")
    dependencies: list[str] = Field(default=[], description="Dependencias Python")

    def dict(self):
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "model": self.model,
            "runtime": self.runtime,
            "permissions": self.permissions,
            "events": {
                "consumes": self.events.consumes if self.events else [],
                "publishes": self.events.publishes if self.events else [],
            } if self.events else {},
            "tools": self.tools,
            "dependencies": self.dependencies,
        }
