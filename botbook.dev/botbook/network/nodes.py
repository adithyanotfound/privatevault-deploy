"""
BotBook Federated Node Registry
"""

from typing import Dict

class NodeRegistry:

    def __init__(self):
        self.nodes: Dict[str, str] = {}

    def register(self, node_id: str, endpoint: str):
        self.nodes[node_id] = endpoint

    def list_nodes(self):
        return self.nodes


nodes = NodeRegistry()
