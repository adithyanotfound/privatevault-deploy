import json
import time
from pathlib import Path

RUN_DIR = Path.home() / ".lork" / "runs"
RUN_DIR.mkdir(parents=True, exist_ok=True)


def append_event(run_id, event_type, agent=None):
    file = RUN_DIR / f"{run_id}.events"

    event = {
        "ts": time.time(),
        "type": event_type,
        "agent": agent
    }

    with open(file, "a") as f:
        f.write(json.dumps(event) + "\n")


def read_events(run_id):
    file = RUN_DIR / f"{run_id}.events"

    if not file.exists():
        return []

    events = []
    with open(file) as f:
        for line in f:
            events.append(json.loads(line))

    return events
