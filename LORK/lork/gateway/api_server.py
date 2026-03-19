"""
LORK API Server
===============

Control plane interface for LORK.

This is equivalent to the Kubernetes API server.
All external systems interact with LORK through this service.

Endpoints:
  POST /agents
  POST /tasks
  GET  /tasks/{task_id}
  GET  /agents/{agent_id}
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any

from lork.sdk.client import LorkClient

app = FastAPI(title="LORK Control Plane")

lork: LorkClient | None = None


class AgentCreate(BaseModel):
    tenant_id: str
    name: str
    description: str = ""


class TaskCreate(BaseModel):
    tenant_id: str
    agent_id: str
    task_type: str
    payload: dict[str, Any] = {}


@app.on_event("startup")
async def startup():
    global lork
    lork = await LorkClient.embedded().__aenter__()


@app.post("/agents")
async def create_agent(req: AgentCreate):
    agent = await lork.agents.register(
        tenant_id=req.tenant_id,
        name=req.name,
        description=req.description,
    )
    return agent


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    return await lork.agents.get(agent_id)


@app.post("/tasks")
async def submit_task(req: TaskCreate):
    task = await lork.tasks.submit(
        tenant_id=req.tenant_id,
        agent_id=req.agent_id,
        task_type=req.task_type,
        payload=req.payload,
    )
    return task


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    return await lork.tasks.get(task_id)

@app.post("/agents/{agent_id}/activate")
async def activate_agent(agent_id: str):
    return await lork.agents.activate(agent_id)

