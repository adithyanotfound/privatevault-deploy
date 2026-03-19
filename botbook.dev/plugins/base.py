class BotBookPlugin:
    """
    Base class for BotBook plugins.
    Plugins can hook into agent registration,
    collaboration events, or discovery.
    """

    def on_agent_register(self, agent):
        pass

    def on_collaboration(self, agent_a, agent_b, task):
        pass
