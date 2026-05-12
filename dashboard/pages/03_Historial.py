"""Pagina de logs historicos con filtros."""

import streamlit as st

st.set_page_config(page_title="Historial", page_icon="+", layout="wide")
st.title("+ Historial de Logs")
st.markdown("Logs del sistema con filtros por servicio y nivel.")

col1, col2 = st.columns(2)
with col1:
    st.selectbox("Servicio", ["Todos", "skills-agent", "infra-agent", "agent-factory", "version-agent", "orchestrator"])
with col2:
    st.selectbox("Nivel", ["Todos", "INFO", "WARN", "ERROR", "DEBUG"])

st.caption("Conectando a Redis para logs en vivo...")
st.code("redis-cli subscribe astrik:logs")
