"""
LORK Agent State Engine
=======================

Core infrastructure for recording and replaying agent execution state.

This module implements an event-sourced state system for AI agents.

Capabilities
------------
- Start agent runs
- Record every execution step
- Store immutable event history
- Build state snapshots
- Replay runs deterministically
- Fork runs for simulation
- Query run history

Concept
-------
Every agent run becomes an append-only event log.

Run
 ├─ Step 1: LLM call
 ├─ Step 2: Tool call
 ├─ Step 3: Policy decision
 ├─ Step 4: Tool result
 └─ Step N: Final output

State is reconstructed by replaying events.

Similar to:
- Temporal workflow history
- Kubernetes desired state
- Git commit history
"""

from __future__ import annotations

import uuid
import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Event models
# ---------------------------------------------------------------------------

@dataclass
class StateEvent:
    """Single event in an agent run."""

    event_id: str
    run_id: str
    step: int
    type: str
    payload: Dict[str, Any]
    timestamp: datetime.datetime


@dataclass
class RunState:
    """Current reconstructed state of an agent run."""

    run_id: str
    agent_id: str
    tenant_id: str
    status: str
    steps: int
    data: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# In-memory event log (replace with Postgres later)
# ---------------------------------------------------------------------------

class InMemoryEventStore:

    def __init__(self):
        self._events: Dict[str, List[StateEvent]] = {}

    async def append(self, event: StateEvent):

        if event.run_id not in self._events:
            self._events[event.run_id] = []

        self._events[event.run_id].append(event)

    async def list_events(self, run_id: str) -> List[StateEvent]:
        return list(self._events.get(run_id, []))

    async def clear(self):
        self._events.clear()


# ---------------------------------------------------------------------------
# State engine
# ---------------------------------------------------------------------------

class StateEngine:
    """
    Core state manager for LORK agent runs.
    """

    def __init__(self, event_store: Optional[InMemoryEventStore] = None):

        self._events = event_store or InMemoryEventStore()

        self._runs: Dict[str, RunState] = {}

    # ---------------------------------------------------------------------
    # Run lifecycle
    # ---------------------------------------------------------------------

    async def start_run(self, tenant_id: str, agent_id: str) -> str:
        """Create a new agent run."""

        run_id = f"run_{uuid.uuid4().hex[:12]}"

        state = RunState(
            run_id=run_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            status="running",
            steps=0,
        )

        self._runs[run_id] = state

        await self._record_event(
            run_id,
            "run_started",
            {"agent_id": agent_id, "tenant_id": tenant_id},
        )

        return run_id

    async def finish_run(self, run_id: str):

        state = self._runs[run_id]
        state.status = "completed"

        await self._record_event(run_id, "run_completed", {})

    # ---------------------------------------------------------------------
    # Step recording
    # ---------------------------------------------------------------------

    async def record_step(
        self,
        run_id: str,
        type: str,
        payload: Dict[str, Any],
    ):
        """Record a single execution step."""

        state = self._runs[run_id]

        state.steps += 1

        await self._record_event(
            run_id,
            type,
            payload,
        )

    async def _record_event(
        self,
        run_id: str,
        type: str,
        payload: Dict[str, Any],
    ):

        events = await self._events.list_events(run_id)

        step = len(events) + 1

        event = StateEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            step=step,
            type=type,
            payload=payload,
            timestamp=datetime.datetime.utcnow(),
        )

        await self._events.append(event)

    # ---------------------------------------------------------------------
    # State reconstruction
    # ---------------------------------------------------------------------

    async def get_state(self, run_id: str) -> RunState:
        """Rebuild state from event log."""

        events = await self._events.list_events(run_id)

        if run_id not in self._runs:
            raise ValueError("Run not found")

        state = RunState(**self._runs[run_id].__dict__)

        for event in events:

            if event.type == "tool_call":
                state.data["last_tool"] = event.payload

            elif event.type == "llm_call":
                state.data["last_llm"] = event.payload

            elif event.type == "policy_check":
                state.data["policy"] = event.payload

        return state

    # ---------------------------------------------------------------------
    # Replay engine
    # ---------------------------------------------------------------------

    async def replay(self, run_id: str) -> List[StateEvent]:
        """
        Replay the full execution history of a run.
        """

        events = await self._events.list_events(run_id)

        ordered = sorted(events, key=lambda e: e.step)

        return ordered

    # ---------------------------------------------------------------------
    # Fork runs
    # ---------------------------------------------------------------------

    async def fork_run(self, run_id: str) -> str:
        """
        Create a new run starting from an existing run's state.
        """

        parent_events = await self._events.list_events(run_id)

        new_run = await self.start_run(
            tenant_id=self._runs[run_id].tenant_id,
            agent_id=self._runs[run_id].agent_id,
        )

        for event in parent_events:
            await self._record_event(
                new_run,
                event.type,
                event.payload,
            )

        return new_run

    # ---------------------------------------------------------------------
    # History
    # ---------------------------------------------------------------------

    async def run_history(self, run_id: str) -> List[Dict[str, Any]]:

        events = await self._events.list_events(run_id)

        return [
            {
                "step": e.step,
                "type": e.type,
                "payload": e.payload,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ]


# ---------------------------------------------------------------------------
# Global singleton (simple default)
# ---------------------------------------------------------------------------

_default_engine: Optional[StateEngine] = None


def get_state_engine() -> StateEngine:

    global _default_engine

    if _default_engine is None:
        _default_engine = StateEngine()

    return _default_engine
