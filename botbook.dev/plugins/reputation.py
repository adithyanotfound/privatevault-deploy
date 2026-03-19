from plugins.base import BotBookPlugin

class ReputationPlugin(BotBookPlugin):

    def on_agent_register(self, agent):
        print(f"[Reputation] new agent registered: {agent.name}")

    def on_collaboration(self, agent_a, agent_b, task):
        print(f"[Reputation] collaboration {agent_a} -> {agent_b} task={task}")
