from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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


class DecisionRequest(BaseModel):
    decision: str


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


@app.post("/workflows/{thread_id}/decision")
async def submit_decision(thread_id: str, payload: DecisionRequest):
    if graph is None:
        raise HTTPException(status_code=503, detail="graph not initialized")

    if payload.decision not in ("approve", "reject", "modify"):
        raise HTTPException(
            status_code=422,
            detail="decision must be 'approve', 'reject' or 'modify'",
        )

    await graph.aupdate_state(
        {"configurable": {"thread_id": thread_id}},
        {"decision": payload.decision},
        as_node="validator",
    )
    return {"status": "decision_received", "decision": payload.decision}


@app.get("/workflows")
async def list_workflows(limit: int = 20):
    if graph is None:
        raise HTTPException(status_code=503, detail="graph not initialized")

    threads = {}
    async for thread in graph.checkpointer.alist(config=None, limit=limit):
        conf = thread.config if isinstance(thread.config, dict) else {}
        cv = (
            thread.checkpoint.get("channel_values", {})
            if isinstance(thread.checkpoint, dict)
            else {}
        )
        ts = thread.checkpoint.get("ts") if isinstance(thread.checkpoint, dict) else None
        tid = conf.get("configurable", {}).get("thread_id", "")
        if not tid:
            continue
        existing = threads.get(tid)
        if existing is None or (ts and existing.get("updated_at") is not None and ts > existing["updated_at"]):
            threads[tid] = {
                "thread_id": tid,
                "status": cv.get("status", "unknown"),
                "objective": cv.get("objective", ""),
                "updated_at": str(ts) if ts else None,
            }

    result = sorted(threads.values(), key=lambda x: x.get("updated_at") or "", reverse=True)
    return result
