import os

def init_project():

    folders = [
        "agents",
        "tools",
        "memory",
        "workflows"
    ]

    for f in folders:
        os.makedirs(f, exist_ok=True)

    print("Project initialized")

    print("""
Structure created:

agents/
tools/
memory/
workflows/

Next steps:

botbook make sales_agent
botbook run sales_agent "task"
""")
