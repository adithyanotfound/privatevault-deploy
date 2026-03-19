import networkx as nx

class AgentGraph:

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_agent(self, name):
        if name not in self.graph:
            self.graph.add_node(name)

    def add_collaboration(self, agent_a, agent_b, task):
        self.add_agent(agent_a)
        self.add_agent(agent_b)

        self.graph.add_edge(agent_a, agent_b, task=task)

    def export(self):
        nodes = list(self.graph.nodes())
        edges = [
            {
                "source": u,
                "target": v,
                "task": d.get("task")
            }
            for u, v, d in self.graph.edges(data=True)
        ]

        return {
            "nodes": nodes,
            "edges": edges
        }

agent_graph = AgentGraph()
