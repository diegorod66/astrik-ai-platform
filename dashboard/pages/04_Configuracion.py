"""Pagina de configuracion del sistema."""

import asyncio
import streamlit as st

st.set_page_config(page_title="Configuracion", page_icon="+", layout="wide")
st.title("+ Configuracion del Sistema")

from src.orchestrator_client import OrchestratorClient

orch = OrchestratorClient()

st.subheader("Modelo por Agente")
st.caption("Selecciona el modelo LLM para cada agente. Los cambios se aplican via Redis y el agente los recarga automaticamente.")

col1, col2, col3 = st.columns([2, 2, 1])
col1.markdown("**Agente**")
col2.markdown("**Modelo**")
col3.markdown("")

loop = asyncio.new_event_loop()
config = loop.run_until_complete(orch.get_agent_config())
current_models = config.get("agents", {})
available = config.get("available_models", ["hermes3", "deepseek-coder", "phi4"])

AGENTS = ["skills-agent", "infra-agent", "agent-factory", "version-agent"]

for agent in AGENTS:
    col1, col2, col3 = st.columns([2, 2, 1])
    col1.write(f"**{agent}**")
    current = current_models.get(agent, "hermes3")
    idx = available.index(current) if current in available else 0
    new_model = col2.selectbox(
        f"modelo_{agent}",
        available,
        index=idx,
        label_visibility="collapsed",
        key=f"model_select_{agent}",
    )
    if col3.button("Aplicar", key=f"apply_{agent}"):
        try:
            result = loop.run_until_complete(orch.update_agent_model(agent, new_model))
            st.success(f"{agent}: modelo cambiado a {new_model}")
        except Exception as e:
            st.error(f"Error al actualizar {agent}: {e}")

st.divider()
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
