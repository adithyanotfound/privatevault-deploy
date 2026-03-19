from fastapi import APIRouter
from pydantic import BaseModel

from botbook.economy.contracts import engine

router = APIRouter(prefix="/v1/contracts")


class ContractRequest(BaseModel):
    client: str
    worker: str
    task: str
    amount: float


@router.post("/create")
async def create_contract(req: ContractRequest):
    c = engine.create_contract(req.client, req.worker, req.task, req.amount)

    return {
        "contract_id": c.contract_id,
        "status": c.status,
        "escrow_locked": c.amount,
        "worker": c.worker,
        "task": c.task,
    }


class ReleaseRequest(BaseModel):
    contract_id: str
    result_hash: str


@router.post("/release")
async def release(req: ReleaseRequest):
    return engine.release_payment(req.contract_id, req.result_hash)
