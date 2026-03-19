# Contributing to LORK

Welcome. This guide explains how to work on LORK effectively.

LORK is **infrastructure software**. Changes must prioritize:
- reliability
- correctness
- safety
- backward compatibility

Read this document fully before opening a pull request.

---

# The Prime Directive

**LORK is infrastructure.**

A bug in LORK can affect thousands of AI agents running in production.

Every change must be:

- Tested (unit + integration tests required)
- Reviewed (no self-merge)
- Documented (docstrings + ADR if architectural)
- Backwards compatible unless explicitly marked breaking

---

# Design Philosophy

LORK is built around several principles:

**1. Default-deny security**

Agents should never be able to perform actions unless explicitly allowed.

**2. Deterministic systems**

Policy evaluation and task scheduling must behave predictably.

**3. Stateless execution**

Runtime workers must remain stateless to enable horizontal scaling.

**4. Observability-first**

Every action must produce traceable events and audit records.

---

# Repository Map


lork/
├── lork/
│ ├── models.py
│ ├── exceptions.py
│
│ ├── control_plane/
│ │ ├── agent_registry.py
│ │ └── scheduler.py
│
│ ├── policy/
│ │ └── engine.py
│
│ ├── runtime/
│ │ └── worker.py
│
│ ├── storage/
│ │ └── memory.py
│
│ ├── sdk/
│ │ └── client.py
│
│ ├── gateway/ # Phase 2
│ ├── observability/ # Phase 2
│ ├── security/ # Phase 2
│ └── config/ # Phase 2
│
├── tests/
│ ├── unit/
│ ├── integration/
│ └── e2e/
│
├── docs/
│ ├── adr/
│ ├── api/
│ └── guides/
│
└── examples/
└── demo_agent.py


---

# Where Does a Bug Belong?


Agent permissions wrong?
→ lork/policy/engine.py

Agent lookup issues?
→ lork/control_plane/agent_registry.py

Task dispatch problems?
→ lork/control_plane/scheduler.py

Runtime execution issues?
→ lork/runtime/worker.py

Data persistence errors?
→ lork/storage/<backend>.py


---

# Development Setup

```bash
git clone https://github.com/LOLA0786/LORK.git
cd LORK

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"

Run demo:

python examples/demo_agent.py

Run tests:

pytest

Run coverage:

pytest --cov=lork --cov-report=term-missing
Code Style

We enforce strict formatting.

Tools used:

black
ruff
mypy

Run locally:

black .
ruff check .
mypy lork

CI will fail if formatting is incorrect.

Architecture Rules

LORK follows Hexagonal Architecture.

Layer dependencies are strictly enforced.

Layer	May import from	Must NOT import
models	stdlib	any lork modules
exceptions	stdlib	any lork modules
policy	models, exceptions	runtime, storage
control_plane	models, exceptions, policy	storage, sdk
runtime	models, policy	control_plane
storage	models	control_plane
sdk	everything above	gateway
gateway	sdk	runtime

Violating these rules will block PR approval.

Testing Requirements

Every change must include tests.

Rules:

Unit tests for logic

Integration tests for component interactions

Deterministic tests only

No arbitrary sleeps

No flaky tests

Test naming:

test_<what>_<condition>_<expected_result>

Example:

test_policy_deny_large_transfer
Adding a Storage Backend

Create lork/storage/<backend>.py

Implement required store protocols

Add integration tests

Document usage

Domain code must remain unchanged.

Commit Message Format
<type>(scope): summary

body explaining why

footer references

Types:

feat
fix
test
docs
refactor
perf
chore

Example:

fix(policy): enforce explicit deny precedence

Explicit DENY rules now override wildcard ALLOW rules,
matching AWS IAM evaluation semantics.

Closes #42
Pull Request Checklist

Before submitting:

 Tests added or updated

 All tests pass locally

 Code formatted with black

 Lint passes (ruff)

 Type checks pass (mypy)

 Layer rules respected

 Documentation updated

 CHANGELOG entry added

Security Issues

Do not open public issues for security vulnerabilities.

Report privately to:

security@lork.dev
Issue Labels

We use the following labels:

Label	Meaning
good first issue	beginner-friendly tasks
bug	confirmed bug
enhancement	new feature
docs	documentation
performance	performance improvements
security	security issues
Thank You

LORK aims to become the control plane for AI agents.

Contributions help make agent systems safer, more reliable, and production-ready.

Thank you for helping build that future.
