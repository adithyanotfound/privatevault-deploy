import asyncio
import sys

from lork.storage.db import get_session
from lork.state.event_store import EventStore
from lork.debugger.time_travel import TimeTravelDebugger


async def print_header(run_id):
    print()
    print("RUN INSPECTION")
    print("--------------")
    print("run_id:", run_id)
    print()


async def print_timeline(events):
    print("EXECUTION TIMELINE")
    print("------------------")

    for e in events:
        print(f"[{e.sequence}] {e.type} | agent={e.agent_id} | payload={e.payload}")

    print()


async def print_graph(events):
    print("EXECUTION GRAPH")
    print("---------------")

    agents = {}

    for e in events:
        if e.agent_id not in agents:
            agents[e.agent_id] = []

        action = None
        if isinstance(e.payload, dict):
            action = e.payload.get("action")

        if action:
            agents[e.agent_id].append(action)

    for agent, actions in agents.items():
        print(agent)
        for act in actions:
            print(f"  └ {act}")

    print()


async def main():

    if len(sys.argv) < 2:
        print("usage: python cmd/lork-inspect-run.py <run_id>")
        sys.exit(1)

    run_id = sys.argv[1]

    session = await get_session()

    try:

        store = EventStore(session)
        debugger = TimeTravelDebugger(store)

        events = await debugger.inspect(run_id)

        if not events:
            print("No events found for run:", run_id)
            return

        await print_header(run_id)
        await print_timeline(events)
        await print_graph(events)

    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
