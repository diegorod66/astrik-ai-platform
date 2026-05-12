"""Pagina de configuracion del sistema."""

import streamlit as st

st.set_page_config(page_title="Configuracion", page_icon="+", layout="wide")
st.title("+ Configuracion del Sistema")

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
