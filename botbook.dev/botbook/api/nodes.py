from fastapi import APIRouter
from botbook.network.nodes import nodes

router = APIRouter(prefix="/v1/nodes", tags=["nodes"])


@router.post("/register")
def register(payload: dict):

    node_id = payload["node_id"]
    endpoint = payload["endpoint"]

    nodes.register(node_id, endpoint)

    return {
        "status": "registered",
        "node_id": node_id,
        "endpoint": endpoint
    }


@router.get("")
def list_nodes():

    return {
        "nodes": nodes.list_nodes()
    }
