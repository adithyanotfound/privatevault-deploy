from dataclasses import dataclass
from datetime import datetime
from typing import Any, List
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class RunEvent:
    run_id: str
    sequence: int
    timestamp: datetime
    type: str
    agent_id: str
    payload: dict


class EventStore:

    def __init__(self, session: AsyncSession):
        self.session = session


    async def append(self, event: RunEvent):

        stmt = text("""
        INSERT INTO run_events (
            run_id,
            sequence,
            timestamp,
            type,
            agent_id,
            payload
        )
        VALUES (
            :run_id,
            :sequence,
            :timestamp,
            :type,
            :agent_id,
            :payload
        )
        """)

        await self.session.execute(stmt, {
            "run_id": event.run_id,
            "sequence": event.sequence,
            "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else event.timestamp,
            "type": event.type,
            "agent_id": event.agent_id,
            "payload": json.dumps(event.payload)
        })

        await self.session.commit()


    async def get_run_events(self, run_id: str):

        stmt = text("""
        SELECT run_id, sequence, timestamp, type, agent_id, payload
        FROM run_events
        WHERE run_id = :run_id
        ORDER BY sequence ASC
        """)

        result = await self.session.execute(stmt, {"run_id": run_id})

        rows = result.fetchall()

        events: List[RunEvent] = []

        for r in rows:
            events.append(
                RunEvent(
                    run_id=r[0],
                    sequence=r[1],
                    timestamp=r[2],
                    type=r[3],
                    agent_id=r[4],
                    payload=json.loads(r[5])
                )
            )

        return events
