"""
lork/models.py
==============
Core domain models for LORK.

These are the canonical data structures that flow through every layer of the system.
Every engineer on this project should read this file first.

Design rules:
  - Models are IMMUTABLE (frozen dataclasses or Pydantic with frozen=True).
  - Models carry NO business logic. Logic lives in the relevant domain package.
  - Every public field has a type annotation and docstring.
  - All IDs are UUIDs v4 strings (not ints) for global uniqueness across tenants.
  - Timestamps are always UTC ISO-8601 strings for portability.

Glossary (understand these terms before touching anything else):
  Agent     - An AI worker with an identity, permissions, and a lifecycle.
  Task      - A unit of work assigned to an agent.
  Policy    - A rule that governs what an agent is allowed to do.
  Run       - One execution of a Task by an Agent (the runtime trace).
  Tenant    - An isolated organizational account (multi-tenancy root).
  Event     - An immutable record of something that happened in the system.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def new_id() -> str:
    """Generate a new globally-unique ID."""
    return str(uuid.uuid4())


def utc_now() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    """Lifecycle states an Agent can be in."""
    PENDING   = "pending"
    ACTIVE    = "active"
    SUSPENDED = "suspended"
    RETIRED   = "retired"


class TaskStatus(str, Enum):
    """States a Task moves through from creation to completion."""
    QUEUED    = "queued"
    ASSIGNED  = "assigned"
    RUNNING   = "running"
    SUCCEEDED = "succeeded"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    TIMEOUT   = "timeout"


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY  = "deny"


class PolicyAction(str, Enum):

    DATA_READ   = "data.read"
    DATA_WRITE  = "data.write"
    DATA_DELETE = "data.delete"

    FINANCE_READ            = "finance.read"
    FINANCE_TRANSFER        = "finance.transfer"
    FINANCE_APPROVE_PAYMENT = "finance.approve_payment"

    EMAIL_SEND   = "email.send"
    SLACK_POST   = "slack.post"
    WEBHOOK_CALL = "webhook.call"

    AGENT_SPAWN   = "agent.spawn"
    AGENT_SUSPEND = "agent.suspend"

    CODE_EXECUTE = "code.execute"

    API_CALL = "api.call"

    ALL = "*"


class RunOutcome(str, Enum):
    SUCCESS           = "success"
    FAILURE           = "failure"
    POLICY_BLOCKED    = "policy_blocked"
    TIMEOUT           = "timeout"
    RUNTIME_ERROR     = "runtime_error"
    AGENT_ERROR       = "agent_error"


# ---------------------------------------------------------------------------
# Core Domain Models
# ---------------------------------------------------------------------------

class Tenant(BaseModel, frozen=True):

    id:         str = Field(default_factory=new_id)
    name:       str = Field(...)
    slug:       str = Field(...)
    created_at: str = Field(default_factory=utc_now)
    metadata:   dict[str, Any] = Field(default_factory=dict)


class AgentPermissions(BaseModel, frozen=True):

    allowed_actions:  list[str] = Field(default_factory=list)
    allowed_tools:    list[str] = Field(default_factory=list)
    max_llm_calls_per_run: int  = Field(default=50)
    require_human_approval_for: list[str] = Field(default_factory=list)


class Agent(BaseModel, frozen=True):

    id:          str = Field(default_factory=new_id)
    tenant_id:   str = Field(...)
    name:        str = Field(...)
    description: str = Field(default="")
    status:      AgentStatus = Field(default=AgentStatus.PENDING)
    permissions: AgentPermissions = Field(default_factory=AgentPermissions)
    tags:        dict[str, str] = Field(default_factory=dict)
    created_at:  str = Field(default_factory=utc_now)
    updated_at:  str = Field(default_factory=utc_now)


class TaskInput(BaseModel, frozen=True):

    type:    str = Field(...)
    payload: dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel, frozen=True):

    id:           str = Field(default_factory=new_id)
    tenant_id:    str = Field(...)
    agent_id:     str = Field(...)
    input:        TaskInput = Field(...)
    status:       TaskStatus = Field(default=TaskStatus.QUEUED)
    priority:     int = Field(default=5, ge=1, le=10)
    deadline_at:  str | None = Field(default=None)
    created_at:   str = Field(default_factory=utc_now)
    updated_at:   str = Field(default_factory=utc_now)
    metadata:     dict[str, Any] = Field(default_factory=dict)


class PolicyCondition(BaseModel, frozen=True):

    field:    str = Field(...)
    operator: str = Field(...)
    value:    Any = Field(...)


class PolicyRule(BaseModel, frozen=True):

    effect:      PolicyEffect = Field(...)
    actions:     list[str] = Field(...)
    conditions:  list[PolicyCondition] = Field(default_factory=list)
    description: str = Field(default="")


class Policy(BaseModel, frozen=True):

    id:          str = Field(default_factory=new_id)
    tenant_id:   str = Field(...)
    name:        str = Field(...)
    description: str = Field(default="")
    rules:       list[PolicyRule] = Field(default_factory=list)
    applies_to:  list[str] = Field(default_factory=list)
    enabled:     bool = Field(default=True)
    created_at:  str = Field(default_factory=utc_now)
    updated_at:  str = Field(default_factory=utc_now)


class RunStep(BaseModel, frozen=True):

    id:          str = Field(default_factory=new_id)
    type:        str = Field(...)
    started_at:  str = Field(default_factory=utc_now)
    finished_at: str | None = Field(default=None)
    input:       dict[str, Any] = Field(default_factory=dict)
    output:      dict[str, Any] = Field(default_factory=dict)
    error:       str | None = Field(default=None)
    metadata:    dict[str, Any] = Field(default_factory=dict)


class Run(BaseModel, frozen=True):

    id:          str = Field(default_factory=new_id)
    tenant_id:   str = Field(...)
    task_id:     str = Field(...)
    agent_id:    str = Field(...)
    outcome:     RunOutcome | None = Field(default=None)
    steps:       list[RunStep] = Field(default_factory=list)
    started_at:  str = Field(default_factory=utc_now)
    finished_at: str | None = Field(default=None)
    error:       str | None = Field(default=None)
    token_usage: dict[str, int] = Field(default_factory=dict)
    metadata:    dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel, frozen=True):

    allowed: bool = Field(...)
    reason: str = Field(...)
    matched_rules: list[PolicyRule] = Field(default_factory=list)
    requires_approval: bool = Field(default=False)


class EventType(str, Enum):

    AGENT_REGISTERED   = "agent.registered"
    AGENT_ACTIVATED    = "agent.activated"
    AGENT_SUSPENDED    = "agent.suspended"
    AGENT_RETIRED      = "agent.retired"

    TASK_CREATED       = "task.created"
    TASK_ASSIGNED      = "task.assigned"
    TASK_COMPLETED     = "task.completed"
    TASK_FAILED        = "task.failed"
    TASK_CANCELLED     = "task.cancelled"

    RUN_STARTED        = "run.started"
    RUN_STEP_COMPLETED = "run.step_completed"
    RUN_FINISHED       = "run.finished"

    POLICY_EVALUATED   = "policy.evaluated"
    POLICY_VIOLATION   = "policy.violation"

    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED   = "approval.granted"
    APPROVAL_DENIED    = "approval.denied"


class LorkEvent(BaseModel, frozen=True):

    id:         str = Field(default_factory=new_id)
    type:       EventType = Field(...)
    tenant_id:  str = Field(...)
    source:     str = Field(...)
    payload:    dict[str, Any] = Field(default_factory=dict)
    occurred_at: str = Field(default_factory=utc_now)

