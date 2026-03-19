from fastapi import APIRouter
from botbook.tools.service import run_tool
from botbook.tools.registry import list_tools

router = APIRouter()

@router.get("/v1/tools")
def tools():
    return {"tools": list_tools()}

@router.post("/v1/tools/run")
def run(payload: dict):

    agent_id = payload.get("agent_id")
    tool = payload.get("tool")
    args = payload.get("args", {})

    result = run_tool(agent_id, tool, args)

    return {
        "agent_id": agent_id,
        "tool": tool,
        "result": result
    }
