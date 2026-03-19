from fastapi import APIRouter
from botbook.events.event_bus import event_bus

router = APIRouter(prefix="/v1/events", tags=["events"])


@router.post("/publish")
def publish(payload: dict):

    event = payload["event"]
    data = payload.get("data", {})

    event_bus.publish(event, data)

    return {
        "status": "published",
        "event": event
    }
