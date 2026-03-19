class Agent:

    def __init__(self):
        self.name = "outreach_agent"
        self.role = "Create outreach campaigns"

    def run(self, task):

        print("Generating outreach based on:", task)

        return "Outreach email draft for: " + task
