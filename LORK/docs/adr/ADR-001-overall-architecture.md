# ADR-001: LORK Overall Architecture

Date: 2024-01-01  
Status: Accepted  
Author: LORK Core Team

---

## Context

LORK is a **control plane for AI agents**.

Agents will:

- run autonomous workflows
- access external APIs
- interact with company data
- execute tasks at scale

Because LORK sits in the middle of these systems, architectural mistakes would
be extremely costly to fix later.

The architecture must support:

- strict security boundaries
- high testability
- replaceable infrastructure
- long-term maintainability
- safe scaling to large teams

The core question:

**Which architectural pattern should structure LORK?**

---

## Decision

LORK adopts **Hexagonal Architecture (Ports & Adapters)**.

This architecture separates:

- business logic
- delivery interfaces
- infrastructure

### High-Level Structure


┌───────────────────────────────────────────────┐
│ Delivery Layer │
│ │
│ SDK • CLI • HTTP Gateway │
│ │
└───────────────▲───────────────────────────────┘
│ calls
│
┌───────────────┴───────────────────────────────┐
│ Domain Layer │
│ │
│ Agent Registry │
│ Task Scheduler │
│ Policy Engine │
│ Runtime Worker │
│ │
└───────────────▲───────────────────────────────┘
│ interfaces (Protocols)
│
┌───────────────┴───────────────────────────────┐
│ Infrastructure Layer │
│ │
│ Storage • Event Bus • LLM Clients • Metrics │
│ │
└───────────────────────────────────────────────┘


---

## Core Rules

1. **Domain code must never depend on infrastructure.**

2. Infrastructure implements interfaces defined in the domain.

3. Delivery layers (API, CLI, SDK) call domain services but never infrastructure directly.

4. Domain models are pure data structures.

---

## Package Map

| Package | Layer | Responsibility | Must NOT contain |
|------|------|------|------|
| `lork/models.py` | Shared | Domain models | Logic or I/O |
| `lork/exceptions.py` | Shared | Error types | Framework code |
| `lork/policy/` | Domain | Policy evaluation | HTTP / DB calls |
| `lork/control_plane/` | Domain | Agent registry & scheduler | HTTP / DB |
| `lork/runtime/` | Domain | Agent execution loop | Framework code |
| `lork/storage/` | Infrastructure | Storage backends | Business rules |
| `lork/events/` | Infrastructure | Event streaming | Business rules |
| `lork/gateway/` | Delivery | HTTP API | Business rules |
| `lork/sdk/` | Delivery | Developer SDK | Domain logic |
| `lork/observability/` | Infrastructure | Metrics & tracing | Domain logic |
| `lork/security/` | Infrastructure | Authentication | Domain logic |
| `lork/config/` | Infrastructure | Settings | Domain logic |

---

## Consequences

### Advantages

- Infrastructure can be replaced without touching business logic.
- Domain logic is easy to unit test.
- New APIs (gRPC, GraphQL) can be added without refactoring core systems.
- Clear mental model for contributors.

### Tradeoffs

- More files and layers.
- Requires discipline in imports.
- Developers unfamiliar with Ports & Adapters may need time to learn the pattern.

---

## Enforcement

Architecture rules are enforced through:

- `ruff` linting rules
- CI checks
- code review guidelines

Future improvement:

Introduce **import-linter** in CI to automatically verify layer boundaries.

---

## Alternatives Considered

### MVC (Model–View–Controller)

Rejected.

MVC mixes framework concerns with business logic and becomes difficult to test
without a running web server.

---

### Microservices from Day 1

Rejected.

Premature complexity.

LORK starts as a **modular monolith**, allowing us to extract services later
once boundaries are proven.

---

### Full Domain-Driven Design Aggregates

Partially adopted.

LORK uses immutable models (`frozen=True`) which provide many DDD benefits
without introducing excessive abstraction layers.

---

## Long-Term Vision

LORK should eventually operate as a distributed control plane capable of managing:

- thousands of agents
- millions of tasks
- multi-region deployments
- enterprise governance policies

Choosing Hexagonal Architecture ensures the system remains adaptable as it evolves.

