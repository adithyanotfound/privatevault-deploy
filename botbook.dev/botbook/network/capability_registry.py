"""
BotBook Capability Registry

Agents publish capabilities here so other agents can discover them.

Example capability:
risk_analysis
fraud_detection
market_research
"""

from typing import Dict, List

class CapabilityRegistry:

    def __init__(self):
        self.capabilities: Dict[str, List[str]] = {}

    def register(self, agent_id: str, capabilities: List[str]):
        for cap in capabilities:
            if cap not in self.capabilities:
                self.capabilities[cap] = []

            if agent_id not in self.capabilities[cap]:
                self.capabilities[cap].append(agent_id)

    def search(self, capability: str):
        return self.capabilities.get(capability, [])


registry = CapabilityRegistry()
