class Agent:

    def __init__(self):
        self.name = "research_agent"
        self.role = "Research companies and gather market insights"

    def run(self, task):

        print("Researching:", task)

        return "Research results for: " + task
