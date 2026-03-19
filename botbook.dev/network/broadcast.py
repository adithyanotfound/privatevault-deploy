import requests

class NetworkBroadcaster:

    def __init__(self):
        self.peers = []

    def add_peer(self, url):
        if url not in self.peers:
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


broadcaster = NetworkBroadcaster()
