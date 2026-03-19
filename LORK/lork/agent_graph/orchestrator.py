from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AgentNode:
    agent_id: str
    tools: List[str]
    next_nodes: List[str]


class AgentGraph:

    def __init__(self):
        self.nodes: Dict[str, AgentNode] = {}

    def add_node(self, agent_id: str, tools: List[str], next_nodes: List[str] | None = None):

        self.nodes[agent_id] = AgentNode(
            agent_id=agent_id,
            tools=tools,
            next_nodes=next_nodes or []
        )

    def execution_order(self, start_agent: str):

        visited = set()
        order = []

        def dfs(node):

            if node in visited:
                return

            visited.add(node)

            for nxt in self.nodes[node].next_nodes:
                dfs(nxt)

            order.append(node)

        dfs(start_agent)

        order.reverse()

        return order
