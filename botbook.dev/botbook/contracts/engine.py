from .contracts import AgentContract, ContractStatus

class ContractEngine:

    def __init__(self):
        self._contracts = {}

    def create(self, payer, worker, task, reward):

        c = AgentContract(
            payer_id=payer,
            worker_id=worker,
            task=task,
            reward=reward
        )

        self._contracts[c.contract_id] = c
        return c

    def fund(self, contract_id):
        c = self._contracts[contract_id]
        c.escrow_funded = True
        c.status = ContractStatus.FUNDED
        return c

    def start(self, contract_id):
        c = self._contracts[contract_id]
        c.status = ContractStatus.RUNNING
        return c

    def complete(self, contract_id, result_hash=None):
        c = self._contracts[contract_id]
        c.status = ContractStatus.COMPLETED
        c.result_hash = result_hash
        return c
