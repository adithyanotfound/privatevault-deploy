# Run Replay

Replay allows engineers to re-execute a workflow run using its historical event log.

This capability enables deterministic debugging of complex AI systems.

---

## Why Replay Matters

AI systems often interact with external APIs, tools, and models.

When failures occur, engineers need a way to reconstruct exactly what happened.

Replay provides that capability.

---

## Replay Workflow


historical run
│
▼
event log
│
▼
replay engine
│
▼
step-by-step re-execution


---

## Replay Process

1. Retrieve the event log for a run.
2. Iterate through the events in sequence.
3. Reconstruct the execution timeline.
4. Re-execute steps deterministically.

---

## Deterministic Execution

For replay to be reliable, certain conditions must be met:

- identical workflow specification
- identical inputs
- deterministic model configuration
- deterministic tool behavior

LORK enforces deterministic replay by relying on the event log as the authoritative execution record.

---

## Use Cases

Replay enables several important operational workflows.

**Debugging**

Reproduce failures without rerunning the entire system.

**Testing**

Validate workflow changes against historical runs.

**Incident Analysis**

Investigate unexpected agent behavior.

