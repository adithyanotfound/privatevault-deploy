import os
import sys

TEMPLATES = {
"sales_agent": "Sales automation and lead qualification",
"finance_agent": "Financial analysis and reporting",
"executive_assistant": "Executive scheduling and meeting summaries",
"hr_head": "HR management and employee operations",
"operations_head": "Operations coordination and process automation",
"marketing_agent": "Marketing strategy and campaign generation",
"recruiter": "Hiring pipeline and candidate evaluation",
"compliance_agent": "Regulatory monitoring and compliance reports",
"risk_monitor": "Enterprise risk detection",
"customer_support": "Customer ticket triage and support"
}

TEMPLATE_CODE = '''
class Agent:

    def __init__(self):
        self.name = "{name}"
        self.role = "{role}"

    def run(self, task):
        print(f"Agent: {{self.name}}")
        print(f"Role: {{self.role}}")
        print("Task:", task)

        return "completed"
'''

def create_agent(agent_name):

    if agent_name not in TEMPLATES:
        print("Unknown agent. Available agents:")
        for a in TEMPLATES:
            print("-", a)
        return

    os.makedirs("agents", exist_ok=True)

    path = f"agents/{agent_name}.py"

    if os.path.exists(path):
        print("Agent already exists:", path)
        return

    role = TEMPLATES[agent_name]

    code = TEMPLATE_CODE.format(
        name=agent_name,
        role=role
    )

    with open(path, "w") as f:
        f.write(code)

    print("Created agent:", path)


def main():
    if len(sys.argv) < 2:
        print("Usage: botbook-make <agent>")
        return

    create_agent(sys.argv[1])
