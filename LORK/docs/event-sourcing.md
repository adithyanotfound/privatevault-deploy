# Event Sourcing

LORK uses an event-sourced execution model.

Instead of storing only the final state of a workflow run, the system records every step as an immutable event.

This design provides complete visibility into agent behavior.

---

## Event Model

Each event represents a single step in the execution timeline.

Example structure:


run_id
sequence
timestamp
type
agent_id
payload


Example events:


agent_start
agent_step
tool_call
agent_end


---

## Benefits

Event sourcing provides several advantages for AI systems.

**Full Execution History**

Every decision and action taken by an agent is recorded.

**Deterministic Replay**

Historical runs can be replayed by re-executing events.

**Auditability**

Engineers can reconstruct the complete state of a system at any point in time.

**Debugging**

Execution timelines allow detailed inspection of agent behavior.

---

## Event Flow


workflow execution
│
▼
agent action
│
▼
event recorded
│
▼
event store
│
▼
debug / replay / trace


---

## Storage

Events are stored in an append-only table.

This ensures that historical execution data is never mutated.

Append-only storage guarantees that the system maintains a verifiable execution history.

