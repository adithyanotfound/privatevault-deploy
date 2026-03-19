"""
LORK Time Travel Debugger
=========================

Allows rewinding an agent run to a previous step and re-executing from there.

Use cases:
- Debug incorrect agent decisions
- Test new prompts or models on existing runs
- Investigate failures
- Evaluate alternative tool outputs
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from lork.runtime.replay_engine import RunLedger, RunStep, ReplayEngine

logger = logging.getLogger(__name__)


class TimeTravelSession:
    """
    Represents a debugging session for an agent run.
    """

    def __init__(self, ledger: RunLedger):
        self.original_ledger = ledger
        self.current_steps: List[RunStep] = list(ledger.steps)
        self.pointer = len(self.current_steps)

    def rewind_to(self, step_index: int):
        """
        Rewind execution pointer to a specific step.
        """
        if step_index < 0 or step_index >= len(self.current_steps):
            raise ValueError("Invalid step index")

        logger.info("Rewinding run to step %s", step_index)

        self.pointer = step_index + 1
        self.current_steps = self.current_steps[: self.pointer]

    def inspect_step(self, step_index: int) -> Dict[str, Any]:
        """
        Inspect a step in the run.
        """
        step = self.original_ledger.steps[step_index]
        return step.to_dict()

    def override_step_output(self, step_index: int, new_output: Dict[str, Any]):
        """
        Replace the output of a step to test alternate outcomes.
        """
        logger.info("Overriding output of step %s", step_index)

        step = self.current_steps[step_index]
        step.output = new_output

    def append_step(self, step: RunStep):
        """
        Add a new step after rewinding.
        """
        self.current_steps.append(step)
        self.pointer = len(self.current_steps)

    def snapshot(self) -> RunLedger:
        """
        Create a new ledger snapshot representing the modified run.
        """
        ledger = RunLedger(run_id=self.original_ledger.run_id + "_branch")
        ledger.steps = list(self.current_steps)
        return ledger


class TimeTravelDebugger:
    """
    Main interface for time-travel debugging.
    """

    def __init__(self, replay_engine: ReplayEngine):
        self.replay_engine = replay_engine

    async def replay_until(self, ledger: RunLedger, step_index: int):
        """
        Replay run until a certain step.
        """
        logger.info("Replaying run until step %s", step_index)

        partial = RunLedger(ledger.run_id)

        for i, step in enumerate(ledger.steps):
            partial.record_step(step)

            if i == step_index:
                break

        return await self.replay_engine.replay(partial)

    def start_session(self, ledger: RunLedger) -> TimeTravelSession:
        """
        Start a debugging session.
        """
        logger.info("Starting time travel session for run %s", ledger.run_id)
        return TimeTravelSession(ledger)


# Example usage

async def example():
    from lork.runtime.replay_engine import create_default_replay_engine

    engine = create_default_replay_engine()

    ledger = RunLedger("run-demo")

    ledger.record_step(
        RunStep(
            "llm_call",
            {"prompt": "Should we transfer $50k?"},
            {"response": "Yes"},
        )
    )

    ledger.record_step(
        RunStep(
            "tool_call",
            {"tool": "transfer_funds", "amount": 50000},
            {"result": "Transfer complete"},
        )
    )

    debugger = TimeTravelDebugger(engine)

    session = debugger.start_session(ledger)

    # Inspect step
    print(session.inspect_step(0))

    # Rewind to step 0
    session.rewind_to(0)

    # Change model decision
    session.override_step_output(
        0,
        {"response": "No, requires approval"},
    )

    new_ledger = session.snapshot()

    print("Modified run steps:")
    for s in new_ledger.steps:
        print(s.to_dict())
