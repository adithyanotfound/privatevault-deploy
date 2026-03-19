class CapabilityIndex:

    def __init__(self):
        self.index = {}

    def register(self, agent):

        for capability in agent.capabilities:

            if capability not in self.index:
                self.index[capability] = []

            self.index[capability].append(agent.name)

    def search(self, capability):
        return self.index.get(capability, [])

capability_index = CapabilityIndex()
