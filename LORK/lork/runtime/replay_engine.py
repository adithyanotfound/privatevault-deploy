from typing import Callable
from lork.state.event_store import EventStore


class ReplayEngine:

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    async def replay(self, run_id: str, step_executor: Callable):

        events = await self.event_store.get_run_events(run_id)

        for event in events:

            if event.type in ("tool_call", "llm_prompt"):
                await step_executor(event)

    async def fork(self, run_id: str, new_run_id: str):

        events = await self.event_store.get_run_events(run_id)

        forked = []

        for e in events:
            forked.append(
                dict(
                    run_id=new_run_id,
                    sequence=e.sequence,
                    timestamp=e.timestamp,
                    type=e.type,
                    agent_id=e.agent_id,
                    payload=e.payload
                )
            )

        return forked
