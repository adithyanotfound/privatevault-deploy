import asyncio
import sys

from lork.storage.db import get_session
from lork.state.event_store import EventStore


async def main():

    if len(sys.argv) < 2:
        print("Usage: python cmd/lork-replay-run.py <run_id>")
        return

    run_id = sys.argv[1]

    session = await get_session()

    try:

        store = EventStore(session)
        events = await store.get_run_events(run_id)

        if not events:
            print("No events found for run:", run_id)
            return

        print("Replaying run:", run_id)

        for e in events:
            action = e.payload.get("action")
            print(f"[{e.sequence}] {e.agent_id} -> {action}")

        print("Replay finished")

    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
