import asyncio
import sys

from sqlalchemy import text

from lork.debugger.time_travel import TimeTravelDebugger
from lork.storage.db import get_session
from lork.state.event_store import EventStore


async def list_runs(session):

    result = await session.execute(
        text("SELECT DISTINCT run_id FROM run_events")
    )

    rows = result.fetchall()

    if not rows:
        print("No runs found.")
        return

    print("Available runs:")
    for r in rows:
        print("-", r[0])


async def main():

    session = await get_session()

    try:

        if len(sys.argv) < 2:
            print("Usage:")
            print("  python cmd/lork-debug-run.py <run_id>")
            print("  python cmd/lork-debug-run.py --list")
            return

        if sys.argv[1] == "--list":
            await list_runs(session)
            return

        run_id = sys.argv[1]

        store = EventStore(session)
        debugger = TimeTravelDebugger(store)

        events = await debugger.inspect(run_id)

        if not events:
            print("No events found for run:", run_id)
            return

        for e in events:
            print(
                f"[{e.sequence}] {e.type} | agent={e.agent_id} | payload={e.payload}"
            )

    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
