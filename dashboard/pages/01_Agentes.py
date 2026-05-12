"""Pagina de detalle de agentes."""

import streamlit as st

st.set_page_config(page_title="Agentes", page_icon="+", layout="wide")
st.title("+ Agentes del Sistema")
st.markdown("Detalle de cada agente: herramientas, estado, eventos.")

agents = [
    {"name": "skills-agent", "status": "online", "tools": ["search", "install", "test", "pipeline"]},
    {"name": "infra-agent", "status": "online", "tools": ["build", "add_service", "health", "generate_compose", "generate_env"]},
    {"name": "agent-factory", "status": "online", "tools": ["create", "list", "validate"]},
    {"name": "version-agent", "status": "online", "tools": ["snapshot", "bump", "current"]},
]

for agent in agents:
    with st.expander(f"{agent['name']} — :green[{agent['status']}]"):
        st.write("**Herramientas disponibles:**")
        for tool in agent["tools"]:
            st.code(f"  * {tool}")
        st.button(f"Invocar {agent['name']}", key=f"invoke_{agent['name']}")
