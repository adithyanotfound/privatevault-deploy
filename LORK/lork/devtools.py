import json
import time
from pathlib import Path
from collections import defaultdict

RUN_DIR = Path(".lork/runs")


def _load(run_id):
    path = RUN_DIR / f"{run_id}.json"
    if not path.exists():
        print("Run not found:", run_id)
        return None
    with open(path) as f:
        return json.load(f)


def list_runs():
    if not RUN_DIR.exists():
        print("No runs found")
        return

    print("\nLORk Runs\n")
    for f in sorted(RUN_DIR.glob("*.json")):
        print(f.stem)


def inspect_run(run_id):
    data = _load(run_id)
    if not data:
        return

    events = data.get("events", [])

    print("\nRun Timeline\n")

    for i, e in enumerate(events, 1):
        etype = e.get("type","unknown")
        agent = e.get("agent","-")

        line = f"{i:02d} | {etype:15} | {agent}"

        if "latency_ms" in e:
            line += f" | {e['latency_ms']}ms"

        if "tokens" in e:
            line += f" | tokens:{e['tokens']}"

        print(line)

        if etype == "tool_call":
            tool = e.get("tool","unknown")
            payload = e.get("input","")
            print(f"     tool: {tool}")
            if payload:
                print(f"     input: {payload}")


def replay_run(run_id):
    data = _load(run_id)
    if not data:
        return

    events = data.get("events", [])

    print("\nReplay\n")

    for e in events:
        print(json.dumps(e, indent=2))
        time.sleep(0.2)


def trace_run(run_id):
    data = _load(run_id)
    if not data:
        return

    print(json.dumps(data, indent=2))


def graph_run(run_id):
    data = _load(run_id)
    if not data:
        return

    events = data.get("events", [])

    print("\nExecution Graph\n")

    last_agent = None

    for e in events:
        agent = e.get("agent")
        etype = e.get("type")

        if not agent:
            continue

        if last_agent and agent != last_agent:
            print(f"{last_agent} → {agent}")

        if etype == "tool_call":
            tool = e.get("tool","tool")
            print(f"{agent} → tool:{tool}")

        last_agent = agent


def stats_run(run_id):
    data = _load(run_id)
    if not data:
        return

    events = data.get("events", [])

    latency = defaultdict(int)
    tokens = defaultdict(int)

    for e in events:
        agent = e.get("agent","-")

        latency[agent] += e.get("latency_ms",0)
        tokens[agent] += e.get("tokens",0)

    print("\nAgent Stats\n")

    for agent in latency:
        print(f"{agent:12} latency:{latency[agent]}ms tokens:{tokens[agent]}")
