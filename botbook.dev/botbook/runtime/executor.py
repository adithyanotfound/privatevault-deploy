import importlib
from botbook.runtime.llm import generate
from botbook.runtime.registry import create_run, complete_run

def run(agent_name, context):

    run_id = create_run(agent_name, context["task"])

    module = importlib.import_module(f"agents.{agent_name}")
    agent = module.Agent()

    print(f"\n⚡ Running agent: {agent.name}")
    print("Run ID:", run_id)

    prompt = f"""
Role: {agent.role}

Task:
{context["task"]}

Previous context:
{context["data"]}
"""

    result = generate(prompt)

    complete_run(run_id, result)

    return result
