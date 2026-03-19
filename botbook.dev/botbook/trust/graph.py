import math
from collections import defaultdict

class TrustGraph:

    def __init__(self):
        self.edges = defaultdict(dict)
        self.scores = {}

    def add_interaction(self, source, target, weight=1.0):
        self.edges[source][target] = self.edges[source].get(target, 0) + weight

    def neighbors(self, node):
        return self.edges.get(node, {})

    def compute(self, iterations=20, damping=0.85):

        nodes = set(self.edges.keys())

        for src in self.edges:
            nodes |= set(self.edges[src].keys())

        if not nodes:
            return {}

        N = len(nodes)

        scores = {n: 1.0 / N for n in nodes}

        for _ in range(iterations):

            new_scores = {}

            for node in nodes:

                rank_sum = 0.0

                for src in nodes:
                    if node in self.edges.get(src, {}):
                        out = self.edges[src]
                        total = sum(out.values())

                        if total > 0:
                            rank_sum += scores[src] * (out[node] / total)

                new_scores[node] = (1 - damping) / N + damping * rank_sum

            scores = new_scores

        self.scores = scores
        return scores

    def score(self, node):
        return self.scores.get(node, 0.0)
