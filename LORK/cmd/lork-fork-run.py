import asyncio
import sys
import uuid

from lork.storage.db import get_session
from lork.state.event_store import EventStore, RunEvent


async def main():

    if len(sys.argv) < 2:
        print("Usage: python cmd/lork-fork-run.py <run_id>")
        return

    original_run = sys.argv[1]
    new_run = str(uuid.uuid4())

    session = await get_session()

    try:

        store = EventStore(session)
        events = await store.get_run_events(original_run)

        if not events:
            print("No events found for run:", original_run)
            return

        print("Forking run:", original_run)
        print("New run id:", new_run)

        for e in events:

            new_event = RunEvent(
                run_id=new_run,
                sequence=e.sequence,
                timestamp=e.timestamp,
                type=e.type,
                agent_id=e.agent_id,
                payload=e.payload
            )

            await store.append(new_event)

        print("Fork complete")

    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
