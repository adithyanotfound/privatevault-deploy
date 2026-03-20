
class Agent:

    def __init__(self):
        self.name = "finance_agent"
        self.role = "Financial analysis and reporting"

    def run(self, task):
        print(f"Agent: {self.name}")
        print(f"Role: {self.role}")
        print("Task:", task)

        return "completed"
