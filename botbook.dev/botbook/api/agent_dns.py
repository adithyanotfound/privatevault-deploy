from fastapi import APIRouter
from botbook.network.agent_dns import dns

router = APIRouter(prefix="/v1/dns", tags=["dns"])

@router.post("/register")
def register(payload: dict):

    name = payload["name"]
    agent_id = payload["agent_id"]

    dns.register(name, agent_id)

    return {
        "status": "registered",
        "address": f"agent://{name}",
        "agent_id": agent_id
    }


@router.post("/resolve")
def resolve(payload: dict):

    address = payload["address"]

    agent_id = dns.resolve(address)

    if not agent_id:
        return {"error": "agent_not_found"}

    return {
        "address": address,
        "agent_id": agent_id
    }
