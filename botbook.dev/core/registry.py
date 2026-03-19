from typing import List
from agents.agent import Agent
from core.capability_index import capability_index
from network.broadcast import broadcaster

class AgentRegistry:

    def __init__(self):
        self.agents = []

    def register(self, agent: Agent, propagate=True):

        self.agents.append(agent)
        capability_index.register(agent)

        if propagate:
            broadcaster.broadcast_agent(agent.dict())

        return agent

    def list_agents(self) -> List[Agent]:
        return self.agents

registry = AgentRegistry()
