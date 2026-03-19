from dataclasses import dataclass, field
import uuid
import time
from enum import Enum

class ContractStatus(str, Enum):
    CREATED = "created"
    FUNDED = "funded"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

def _cid():
    return "ctr_" + uuid.uuid4().hex[:10]

@dataclass
class AgentContract:
    payer_id: str
    worker_id: str
    task: str
    reward: float

    contract_id: str = field(default_factory=_cid)
    created_at: float = field(default_factory=time.time)
    status: ContractStatus = ContractStatus.CREATED
    escrow_funded: bool = False
    result_hash: str | None = None
