from datetime import datetime
from lork.state.event_store import RunEvent


class RuntimeEngine:

    def __init__(self, gateway, event_store):
        self.gateway = gateway
        self.event_store = event_store

    async def execute(self, run_id, graph, start_agent):

        order = graph.execution_order(start_agent)

        sequence = 0

        for agent in order:

            sequence += 1

            await self.event_store.append(
                RunEvent(
                    run_id=run_id,
                    sequence=sequence,
                    timestamp=datetime.utcnow(),
                    type="agent_start",
                    agent_id=agent,
                    payload={}
                )
            )

            sequence += 1

            await self.event_store.append(
                RunEvent(
                    run_id=run_id,
                    sequence=sequence,
                    timestamp=datetime.utcnow(),
                    type="agent_end",
                    agent_id=agent,
                    payload={}
                )
            )
