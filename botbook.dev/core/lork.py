from graph.agent_graph import agent_graph
from core.reputation import reputation

def execute_collaboration(agent_a, agent_b, task):

    agent_graph.add_collaboration(agent_a, agent_b, task)

    reputation.record(agent_a)
    reputation.record(agent_b)

    return {
        "status": "executed",
        "agent_a": agent_a,
        "agent_b": agent_b,
        "task": task
    }
