from fastapi import APIRouter
from botbook.integrations.illuu_adapter import IlluuAdapter

router = APIRouter()

illuu = IlluuAdapter()

@router.post("/v1/agent/run")
def run_agent(payload: dict):

    agent_id = payload.get("agent_id")
    task = payload.get("task")

    result = illuu.run(agent_id, task)

    return {
        "agent_id": agent_id,
        "task": task,
        "result": result
    }
