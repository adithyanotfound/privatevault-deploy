import os
import json
from datetime import datetime

MEMORY_DIR = "memory"

def ensure():
    os.makedirs(MEMORY_DIR, exist_ok=True)

def write(agent, task, result):

    ensure()

    record = {
        "agent": agent,
        "task": task,
        "result": result,
        "time": datetime.utcnow().isoformat()
    }

    path = os.path.join(MEMORY_DIR, "runs.json")

    data = []

    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)

    data.append(record)

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def history():

    path = os.path.join(MEMORY_DIR, "runs.json")

    if not os.path.exists(path):
        return []

    with open(path) as f:
        return json.load(f)
