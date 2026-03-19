
class Agent:

    def __init__(self):
        self.name = "sales_agent"
        self.role = "Sales automation and lead qualification"

    def run(self, task):
        print(f"Agent: {self.name}")
        print(f"Role: {self.role}")
        print("Task:", task)

        return "completed"
