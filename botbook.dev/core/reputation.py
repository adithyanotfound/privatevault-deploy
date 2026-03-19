class ReputationSystem:

    def __init__(self):
        self.scores = {}

    def record(self, agent):

        if agent not in self.scores:
            self.scores[agent] = 0

        self.scores[agent] += 1

    def get(self, agent):
        return self.scores.get(agent, 0)

reputation = ReputationSystem()
