from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from .db import lifespan_checkpointer
from .graph import build_graph
from .models import WorkflowCreateRequest, WorkflowCreateResponse
from .state import build_initial_state


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


graph = None


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    global graph
    async with lifespan_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)
        yield


app = FastAPI(title="Astrik Orchestrator", lifespan=app_lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}


@app.post("/workflows", response_model=WorkflowCreateResponse)
async def create_workflow(payload: WorkflowCreateRequest):
    if graph is None:
        raise HTTPException(status_code=503, detail="graph not initialized")

    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(build_initial_state(payload.objective), config=config)
    return WorkflowCreateResponse(thread_id=thread_id, status=result["status"])


@app.get("/workflows/{thread_id}")
async def get_workflow(thread_id: str):
    if graph is None:
        raise HTTPException(status_code=503, detail="graph not initialized")

    snapshot = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    if snapshot is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    return snapshot.values
