"""Tests de integracion para agentes como servicios NATS."""
import asyncio
import json
import pytest
from nats.aio.client import Client as NATS

NATS_URL = "nats://192.168.2.112:4222"


@pytest.fixture(scope="function")
async def nats_conn():
    nc = NATS()
    await nc.connect(NATS_URL)
    yield nc
    await nc.drain()


@pytest.mark.asyncio
async def test_skills_agent_online(nats_conn):
    """Verificar que Skills Agent responde a un request (prueba que esta vivo)"""
    nc = nats_conn
    future = asyncio.get_event_loop().create_future()

    async def cb(msg):
        future.set_result(json.loads(msg.data.decode()))

    await nc.subscribe("agent.skills-agent.response", cb=cb)
    await nc.publish("agent.skills-agent.request", json.dumps({
        "id": "test-online-skills",
        "type": "search",
        "payload": {"query": "python linting", "max": 1},
        "reply_to": "agent.skills-agent.response"
    }).encode())

    result = await asyncio.wait_for(future, timeout=15)
    assert result["status"] in ("completed", "running", "failed")


@pytest.mark.asyncio
async def test_infra_agent_online(nats_conn):
    """Verificar que Infra Agent responde a un request"""
    nc = nats_conn
    future = asyncio.get_event_loop().create_future()

    async def cb(msg):
        future.set_result(json.loads(msg.data.decode()))

    await nc.subscribe("agent.infra-agent.response", cb=cb)
    await nc.publish("agent.infra-agent.request", json.dumps({
        "id": "test-online-infra",
        "type": "health",
        "payload": {"service": ""},
        "reply_to": "agent.infra-agent.response"
    }).encode())

    result = await asyncio.wait_for(future, timeout=15)
    assert result["status"] in ("completed", "running", "failed")


@pytest.mark.asyncio
async def test_skills_agent_search(nats_conn):
    """Skills Agent: buscar herramienta"""
    nc = nats_conn
    future = asyncio.get_event_loop().create_future()

    async def cb(msg):
        future.set_result(json.loads(msg.data.decode()))

    await nc.subscribe("agent.skills-agent.response", cb=cb)
    await nc.publish("agent.skills-agent.request", json.dumps({
        "id": "test-search",
        "type": "search",
        "payload": {"query": "python linting", "max": 2},
        "reply_to": "agent.skills-agent.response"
    }).encode())

    result = await asyncio.wait_for(future, timeout=30)
    assert result["status"] in ("completed", "running")


@pytest.mark.asyncio
async def test_infra_agent_health(nats_conn):
    """Infra Agent: verificar health check"""
    nc = nats_conn
    future = asyncio.get_event_loop().create_future()

    async def cb(msg):
        future.set_result(json.loads(msg.data.decode()))

    await nc.subscribe("agent.infra-agent.response", cb=cb)
    await nc.publish("agent.infra-agent.request", json.dumps({
        "id": "test-health",
        "type": "health",
        "payload": {"service": ""},
        "reply_to": "agent.infra-agent.response"
    }).encode())

    result = await asyncio.wait_for(future, timeout=30)
    assert result["status"] in ("completed", "running", "failed")


@pytest.mark.asyncio
async def test_version_agent_current(nats_conn):
    """Version Agent: obtener version actual"""
    nc = nats_conn
    future = asyncio.get_event_loop().create_future()

    async def cb(msg):
        future.set_result(json.loads(msg.data.decode()))

    await nc.subscribe("agent.version-agent.response", cb=cb)
    await nc.publish("agent.version-agent.request", json.dumps({
        "id": "test-version",
        "type": "current",
        "payload": {},
        "reply_to": "agent.version-agent.response"
    }).encode())

    result = await asyncio.wait_for(future, timeout=30)
    assert result["status"] in ("completed", "running", "failed")
