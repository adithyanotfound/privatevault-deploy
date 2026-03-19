# Control Plane

The LORK control plane is responsible for orchestrating agent workflows.

It manages workflow execution, coordinates runtime workers, and maintains system state.

---

## Control Loop

At the core of the system is a reconciliation loop.

The control loop continuously compares desired state with actual state and schedules the necessary actions to achieve convergence.

Conceptually:


desired state
│
▼
controller loop
│
▼
actual state
│
▼
reconciliation


---

## Controller Responsibilities

The controller performs several tasks.

**Run Monitoring**

Tracks the progress of workflow runs.

**State Reconciliation**

Determines whether additional steps must be scheduled.

**Execution Scheduling**

Dispatches tasks to runtime workers.

**Failure Recovery**

Ensures incomplete runs can resume execution.

---

## Scheduler

The scheduler determines which steps should execute next.

It evaluates:

- workflow structure
- current run state
- dependency completion

The scheduler produces the next executable step for each active run.

---

## Execution Flow


workflow spec
│
▼
controller
│
▼
scheduler
│
▼
runtime worker
│
▼
event recorded


---

## Operational Guarantees

The control plane provides several important guarantees:

- consistent execution ordering
- recoverable workflow runs
- complete execution history
- reproducible debugging

These guarantees are essential when operating autonomous AI systems at scale.

