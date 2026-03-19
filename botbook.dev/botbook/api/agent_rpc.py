from fastapi import APIRouter
from botbook.network.agent_rpc import call_agent

router = APIRouter()

@router.post("/v1/agents/call")
def agent_call(payload: dict):

    caller = payload.get("caller")
    target = payload.get("target")
    task = payload.get("task")

    result = call_agent(caller, target, task)

    return result
