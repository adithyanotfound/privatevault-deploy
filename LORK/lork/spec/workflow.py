import yaml
from dataclasses import dataclass
from typing import List


@dataclass
class AgentStep:
    agent: str
    action: str


@dataclass
class WorkflowSpec:
    name: str
    steps: List[AgentStep]


def load_workflow(path: str) -> WorkflowSpec:

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    steps = [
        AgentStep(agent=s["agent"], action=s["action"])
        for s in data["steps"]
    ]

    return WorkflowSpec(
        name=data["name"],
        steps=steps
    )
