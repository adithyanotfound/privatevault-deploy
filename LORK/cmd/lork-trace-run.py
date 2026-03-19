import asyncio
import sys

from lork.storage.db import get_session
from lork.state.event_store import EventStore


async def main():

    if len(sys.argv) < 2:
        print("Usage: python cmd/lork-trace-run.py <run_id>")
        return

    run_id = sys.argv[1]

    session = await get_session()

    try:

        store = EventStore(session)
        events = await store.get_run_events(run_id)

        if not events:
            print("No events found for run:", run_id)
            return

        agents = {}

        for e in events:
            action = e.payload.get("action")
            agents.setdefault(e.agent_id, []).append(action)

        for agent, actions in agents.items():
            print(agent)
            for a in actions:
                print(f" └ {a}")

    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
