import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Contract:
    contract_id: str
    client: str
    worker: str
    task: str
    amount: float
    currency: str
    status: str
    created_at: float
    result_hash: Optional[str] = None


class ContractEngine:

    def __init__(self):
        self.contracts: Dict[str, Contract] = {}
        self.escrow: Dict[str, float] = {}

    def create_contract(self, client: str, worker: str, task: str, amount: float, currency="USD"):
        cid = "bbk_ct_" + uuid.uuid4().hex[:10]

        contract = Contract(
            contract_id=cid,
            client=client,
            worker=worker,
            task=task,
            amount=amount,
            currency=currency,
            status="ESCROW_LOCKED",
            created_at=time.time(),
        )

        self.contracts[cid] = contract
        self.escrow[cid] = amount

        return contract

    def release_payment(self, contract_id: str, result_hash: str):

        contract = self.contracts.get(contract_id)

        if not contract:
            raise Exception("contract_not_found")

        contract.status = "PAID"
        contract.result_hash = result_hash

        amount = self.escrow.pop(contract_id, 0)

        return {
            "contract_id": contract_id,
            "worker": contract.worker,
            "amount_paid": amount,
            "result_hash": result_hash,
        }


engine = ContractEngine()
