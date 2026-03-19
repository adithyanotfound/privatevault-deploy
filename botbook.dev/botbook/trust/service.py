from .graph import TrustGraph

class TrustService:

    def __init__(self):
        self.graph = TrustGraph()

    def record_success(self, payer, worker):
        self.graph.add_interaction(payer, worker, weight=2.0)

    def record_failure(self, payer, worker):
        self.graph.add_interaction(payer, worker, weight=0.2)

    def recompute(self):
        return self.graph.compute()

    def trust_score(self, member_id):
        return self.graph.score(member_id)
