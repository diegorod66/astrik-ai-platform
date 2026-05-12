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
