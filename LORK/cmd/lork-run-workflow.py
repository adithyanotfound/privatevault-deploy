import asyncio
import uuid
import sys
from datetime import datetime, UTC

from lork.storage.db import get_session
from lork.state.event_store import RunEvent, EventStore
from lork.spec.workflow import load_workflow


async def main():

    if len(sys.argv) < 2:
        print("Usage: python cmd/lork-run-workflow.py <workflow.yaml>")
        return

    workflow_path = sys.argv[1]
    workflow = load_workflow(workflow_path)

    run_id = str(uuid.uuid4())

    session = await get_session()
    store = EventStore(session)

    sequence = 0

    print("Starting run:", run_id)

    for step in workflow.steps:

        sequence += 1

        event = RunEvent(
            run_id=run_id,
            sequence=sequence,
            timestamp=datetime.now(UTC),
            type="agent_step",
            agent_id=step.agent,
            payload={"action": step.action}
        )

        await store.append(event)

        print(f"[{sequence}] {step.agent} -> {step.action}")

    await session.close()

    print("Run complete:", run_id)


if __name__ == "__main__":
    asyncio.run(main())
