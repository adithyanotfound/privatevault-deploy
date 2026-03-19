from ..events.bus import EventBus
from .service import TrustService

bus = EventBus()
trust = TrustService()

async def contract_completed(event):

    payer = event.get("payer")
    worker = event.get("worker")
    success = event.get("success", True)

    if success:
        trust.record_success(payer, worker)
    else:
        trust.record_failure(payer, worker)

bus.subscribe(contract_completed)
