import uuid
import json
import os
from datetime import datetime

RUN_DIR = "runs"

os.makedirs(RUN_DIR, exist_ok=True)

def create_run(agent, task):

    run_id = str(uuid.uuid4())[:8]

    data = {
        "run_id": run_id,
        "agent": agent,
        "task": task,
        "status": "running",
        "created": datetime.utcnow().isoformat()
    }

    with open(f"{RUN_DIR}/{run_id}.json","w") as f:
        json.dump(data,f,indent=2)

    return run_id


def complete_run(run_id, result):

    path = f"runs/{run_id}.json"

    with open(path) as f:
        data=json.load(f)

    data["status"]="completed"
    data["result"]=result

    with open(path,"w") as f:
        json.dump(data,f,indent=2)
