"""Constructor Astrik Dashboard — Streamlit principal."""

import asyncio
from datetime import datetime

import streamlit as st

st.set_page_config(
    page_title="Constructor Astrik",
    page_icon="+",
    layout="wide",
    initial_sidebar_state="expanded",
)

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


nats_client = get_nats_client()
orch_client = get_orch_client()

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

st.title("+ Constructor Astrik Dashboard")
st.caption(f"Ultima actualizacion: {datetime.now().strftime('%H:%M:%S')}")

col1, col2, col3, col4 = st.columns(4)
agents = nats_client.get_agents_status()
online = sum(1 for a in agents if a["status"] == "online")
warning = sum(1 for a in agents if a["status"] == "warning")
col1.metric("Agentes", len(agents), f"{online} online")
col2.metric("Workflows", 0)
col3.metric("LLM", "Online")
col4.metric("Version", "v0.1.X")

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

st.subheader("Logs del Sistema")
st.caption("Los logs apareceran aqui en tiempo real cuando los agentes esten activos.")
