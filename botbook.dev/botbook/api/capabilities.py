from fastapi import APIRouter
from botbook.network.capability_registry import registry

router = APIRouter(prefix="/v1/capabilities", tags=["capabilities"])


@router.post("/register")
def register(payload: dict):

    agent_id = payload["agent_id"]
    capabilities = payload["capabilities"]

    registry.register(agent_id, capabilities)

    return {
        "status": "registered",
        "agent_id": agent_id,
        "capabilities": capabilities
    }


@router.post("/search")
def search(payload: dict):

    capability = payload["capability"]

    agents = registry.search(capability)

    return {
        "capability": capability,
        "agents": agents,
        "count": len(agents)
    }
