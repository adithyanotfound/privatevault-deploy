import importlib
import os

from plugins.base import BotBookPlugin

class PluginManager:

    def __init__(self):
        self.plugins = []

    def load_plugins(self):

        for file in os.listdir("plugins"):

            if file.endswith(".py") and file not in ["base.py","manager.py"]:

                module_name = f"plugins.{file[:-3]}"
                module = importlib.import_module(module_name)

                for attr in dir(module):

                    obj = getattr(module, attr)

                    if isinstance(obj, type) and issubclass(obj, BotBookPlugin) and obj is not BotBookPlugin:
                        self.plugins.append(obj())

    def trigger_register(self, agent):

        for plugin in self.plugins:
            plugin.on_agent_register(agent)

    def trigger_collaboration(self, agent_a, agent_b, task):

        for plugin in self.plugins:
            plugin.on_collaboration(agent_a, agent_b, task)


plugin_manager = PluginManager()
plugin_manager.load_plugins()
