class Marketplace:

    def __init__(self):
        self.listings = []

    def publish(self, agent, capability, price):

        listing = {
            "agent": agent,
            "capability": capability,
            "price": price
        }

        self.listings.append(listing)

        return listing

    def list(self):
        return self.listings

marketplace = Marketplace()
