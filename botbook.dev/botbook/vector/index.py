class CapabilityIndex:

    def __init__(self):
        self.index = {}

    def add(self, member_id, capabilities):

        for cap in capabilities:
            self.index.setdefault(cap, set())
            self.index[cap].add(member_id)

    def search(self, caps):

        results = set()

        for c in caps:
            results |= self.index.get(c,set())

        return list(results)
