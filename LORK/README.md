# LORK

Control Plane for AI Agents.

Containers → Kubernetes  
Functions → Serverless  
Agents → LORK

LORK provides infrastructure for running, observing, and debugging autonomous AI systems in production.  
The system introduces deterministic execution, event-sourced agent runs, and time-travel debugging for complex AI workflows.

---

# Why LORK Exists

AI agents behave like distributed systems.

They call tools, query models, access APIs, and make multi-step decisions.  
Traditional debugging tools are insufficient for this class of systems.

LORK introduces infrastructure primitives that make AI systems observable and reproducible.

Key ideas:

• event-sourced execution  
• deterministic replay  
• run forking  
• execution tracing  
• timeline inspection

---

# Quickstart

Run a workflow.


python cmd/lork-run-workflow.py workflows/support_ticket.yaml


Example output:


Starting run: e9268751...
[1] support_agent -> read_ticket
[2] support_agent -> search_docs
[3] support_agent -> draft_reply
Run complete: e9268751...


---

# List Runs


python cmd/lork-debug-run.py --list


Example:


Available runs:

e9268751...

317e26ee...

test-run


---

# Inspect Run Execution


python cmd/lork-inspect-run.py <run_id>


Example output:

RUN INSPECTION

run_id: e9268751...

EXECUTION TIMELINE

[1] agent_step | agent=support_agent | payload={'action': 'read_ticket'}
[2] agent_step | agent=support_agent | payload={'action': 'search_docs'}
[3] agent_step | agent=support_agent | payload={'action': 'draft_reply'}

EXECUTION GRAPH

support_agent
└ read_ticket
└ search_docs
└ draft_reply


This command displays both the execution timeline and the logical graph of the agent workflow.

---

# Trace Execution


python cmd/lork-trace-run.py <run_id>


Example:


support_agent
└ read_ticket
└ search_docs
└ draft_reply


---

# Replay Run


python cmd/lork-replay-run.py <run_id>


Replay re-executes a historical run using its event log.

This enables deterministic debugging and reproduction of failures.

---

# Fork Run


python cmd/lork-fork-run.py <run_id>


Forking creates a new run derived from an existing event history.

This allows engineers to explore alternate execution paths without modifying the original run.

---

# Architecture


Applications
│
▼
LORK Control Plane
│
├ Workflow Specifications
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


The architecture separates orchestration from execution.

The control plane manages workflow state, while runtime workers execute agent actions.

---

# Execution Model

LORK uses an event-sourced execution model.

Each step in a workflow generates an immutable event.

Example event structure:


run_id
sequence
timestamp
type
agent_id
payload


Events are appended to the event store and become the authoritative record of execution.

---

# Time-Travel Debugging

Because runs are event-sourced, engineers can inspect historical execution timelines.

Capabilities include:

• timeline inspection  
• execution tracing  
• deterministic replay  
• run forking

This model allows AI workflows to be debugged using techniques similar to distributed systems.

---

# Repository Structure


lork/
├ cmd/
├ lork/
├ workflows/
├ docs/
├ tests/
└ infra/


Key directories:

cmd/  
CLI tools for running and debugging workflows.

lork/  
Core platform implementation including runtime, scheduler, and state engine.

workflows/  
Example workflow specifications.

docs/  
Architecture and system design documentation.

---

# Example Workflow


workflows/support_ticket.yaml


Example:


name: support-ticket

steps:

agent: support_agent
action: read_ticket

agent: support_agent
action: search_docs

agent: support_agent
action: draft_reply


---

# Current Status

LORK is early-stage infrastructure under active development.

The goal is to build the operational foundation required to run autonomous AI systems safely and reliably.

---

# License

Apache 2.0

