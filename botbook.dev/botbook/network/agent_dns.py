"""
BotBook Agent DNS
Resolves human-readable agent addresses.
Example:
agent://risk-agent
agent://finance-agent
"""

from typing import Dict

class AgentDNS:

    def __init__(self):
        self.registry: Dict[str, str] = {}

    def register(self, name: str, agent_id: str):
        self.registry[name] = agent_id

    def resolve(self, address: str):
        if not address.startswith("agent://"):
            return None

        name = address.replace("agent://", "")
        return self.registry.get(name)


dns = AgentDNS()
