import yaml
from botbook.runtime.executor import run

def execute_dag(file_path, task):

    with open(file_path) as f:
        config = yaml.safe_load(f)

    agents = config["agents"]

    completed = {}
    context = {}

    while len(completed) < len(agents):

        for agent, meta in agents.items():

            if agent in completed:
                continue

            deps = meta.get("depends_on", [])

            if all(d in completed for d in deps):

                print("\nRunning:", agent)

                result = run(agent, {
                    "task": task,
                    "data": context
                })

                context[agent] = result
                completed[agent] = True

    print("\nDAG workflow complete")

    return context
