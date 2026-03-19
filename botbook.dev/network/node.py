import requests

class BotBookNode:

    def __init__(self):
        self.peers = []

    def add_peer(self, url):
        self.peers.append(url)

    def broadcast_agent(self, agent):

        for peer in self.peers:
            try:
                requests.post(
                    f"{peer}/agents/publish",
                    json=agent
                )
            except:
                pass

node = BotBookNode()
