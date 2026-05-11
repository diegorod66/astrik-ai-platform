# skills-agent

## Descripción
Agente especializado en buscar, evaluar, instalar, probar y documentar herramientas externas y librerias para el proyecto

## Versión
1.0.0

## Modelo
hermes3 — llamacpp

## Herramientas
filesystem, network, git

## Dependencias
pyyaml, requests, beautifulsoup4

## Uso
```bash
python main.py --task <tarea> --input '<json>'
```

## Eventos
- Consume: SKILL_REQUESTED
- Publica: SKILL_INSTALLED, SKILL_FAILED
