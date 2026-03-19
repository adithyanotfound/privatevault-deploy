from typing import List
from lork.state.event_store import EventStore, RunEvent


class TimeTravelDebugger:

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    async def inspect(self, run_id: str) -> List[RunEvent]:
        """
        Return full event timeline of a run.
        """
        return await self.event_store.get_run_events(run_id)

    async def replay(self, run_id: str, step_executor):
        """
        Deterministically replay a run.
        """
        events = await self.event_store.get_run_events(run_id)

        for event in events:

            if event.type in ("tool_call", "llm_prompt"):
                await step_executor(event)

    async def fork(self, run_id: str, step: int, new_run_id: str):
        """
        Fork a run into a new timeline.
        """
        events = await self.event_store.get_run_events(run_id)

        forked = []

        for event in events:

            if event.sequence <= step:
                forked.append(
                    RunEvent(
                        run_id=new_run_id,
                        sequence=event.sequence,
                        timestamp=event.timestamp,
                        type=event.type,
                        agent_id=event.agent_id,
                        payload=event.payload
                    )
                )

        return forked
