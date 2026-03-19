# Architecture

LORK is designed as a control plane for autonomous AI systems.

The architecture separates orchestration, execution, and observability into distinct subsystems. This separation allows the system to scale independently across workloads and infrastructure environments.

---

## System Overview


Applications
│
▼
LORK Control Plane
│
├ Workflow Specifications
├ Controller Loop
├ Scheduler
├ Agent Graph
├ Policy Engine
├ Event Store
└ Observability
│
▼
Runtime Workers
│
▼
Tools / APIs / LLMs


---

## Control Plane

The control plane is responsible for orchestration and system state.

Primary responsibilities:

- workflow lifecycle management
- run scheduling
- state reconciliation
- execution coordination
- observability

Components:

**Workflow Specification Engine**

Parses and validates workflow definitions.

**Controller Loop**

Continuously reconciles desired state with actual execution state.

**Scheduler**

Determines which agent actions should execute next.

**Agent Graph**

Represents multi-agent workflows as execution graphs.

**Policy Engine**

Applies governance rules to agent actions and tool invocations.

**Event Store**

Records execution events for observability and replay.

---

## Runtime Plane

The runtime plane executes agent actions.

Components:

**Runtime Workers**

Execute workflow steps and interact with external tools or LLMs.

**Tool Gateway**

Controls and validates tool execution requests.

**Execution Engine**

Coordinates step execution and records events.

---

## Observability

LORK provides deep introspection into agent execution.

Capabilities include:

- timeline inspection
- execution tracing
- deterministic replay
- run forking

These features enable engineers to debug AI systems using techniques similar to those used in distributed systems.

---

## Scalability Model

The architecture allows horizontal scaling across several layers:

- multiple runtime workers
- distributed scheduling
- replicated event storage
- independent control plane instances

This model allows LORK to support high-volume agent workloads while maintaining deterministic execution behavior.

