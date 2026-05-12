"""Pagina de workflows: historial y aprobacion humana."""

import asyncio
import streamlit as st

st.set_page_config(page_title="Workflows", page_icon="+", layout="wide")
st.title("+ Workflows")
st.markdown("Historial de workflows y aprobacion humana.")

from src.orchestrator_client import OrchestratorClient

orch = OrchestratorClient()

if st.button("Recargar historial"):
    loop = asyncio.new_event_loop()
    history = loop.run_until_complete(orch.get_workflows_history())
    st.session_state.workflow_history = history

if "workflow_history" not in st.session_state:
    st.session_state.workflow_history = []

if st.session_state.workflow_history:
    for wf in st.session_state.workflow_history:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(f"**{wf.get('objective', '?')[:60]}...**")
            col2.write(f"`{wf.get('thread_id', '?')[:8]}`")
            col3.write(f"`{wf.get('status', '?')}`")
            st.divider()
else:
    st.info("No hay workflows en el historial.")
