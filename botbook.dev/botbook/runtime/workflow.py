import yaml
from botbook.runtime.executor import run

def run_workflow(file_path, task):

    with open(file_path) as f:
        config = yaml.safe_load(f)

    steps = config.get("steps", [])

    context = {
        "task": task,
        "data": {}
    }

    for agent in steps:

        print("\n====================")
        print("Running agent:", agent)
        print("====================")

        result = run(agent, context)

        context["data"][agent] = result

        print("Output summary:", str(result)[:200])

    print("\nWorkflow complete")

    return context
