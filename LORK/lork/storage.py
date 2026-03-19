import json
import os
import uuid
from pathlib import Path

RUN_DIR = Path(".lork/runs")
RUN_DIR.mkdir(parents=True, exist_ok=True)

def save_run(events):
    run_id = str(uuid.uuid4())
    path = RUN_DIR / f"{run_id}.json"

    with open(path, "w") as f:
        json.dump({"events": events}, f, indent=2)

    print("Saved run:", run_id)
    return run_id
