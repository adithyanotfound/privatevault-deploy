import importlib
import sys

def run_agent(agent_name, task):

    try:
        module = importlib.import_module(f"agents.{agent_name}")
    except Exception as e:
        print("Failed to load agent:", e)
        return

    try:
        agent = module.Agent()
    except Exception as e:
        print("Agent class missing:", e)
        return

    result = agent.run(task)

    print("\nResult:", result)
