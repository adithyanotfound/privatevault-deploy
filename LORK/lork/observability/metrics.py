"""
LORK Prometheus metrics definitions.
Import and use these throughout the codebase for consistent metric names.
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Summary

# ── Agent metrics ──────────────────────────────────────────────────────────────

AGENT_ACTIVE_TOTAL = Gauge(
    "lork_agents_active_total",
    "Number of currently active agents",
    ["organization_id"],
)

AGENT_STATUS_CHANGES = Counter(
    "lork_agent_status_changes_total",
    "Total agent status transitions",
    ["from_status", "to_status", "organization_id"],
)

# ── Task metrics ───────────────────────────────────────────────────────────────

TASK_SUBMITTED_TOTAL = Counter(
    "lork_tasks_submitted_total",
    "Total tasks submitted",
    ["task_type", "organization_id"],
)

TASK_COMPLETED_TOTAL = Counter(
    "lork_tasks_completed_total",
    "Total tasks completed successfully",
    ["task_type", "organization_id"],
)

TASK_FAILED_TOTAL = Counter(
    "lork_tasks_failed_total",
    "Total tasks that failed",
    ["task_type", "organization_id", "reason"],
)

TASK_DURATION_SECONDS = Histogram(
    "lork_task_duration_seconds",
    "Task execution duration in seconds",
    ["task_type"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

TASK_QUEUE_DEPTH = Gauge(
    "lork_task_queue_depth",
    "Current number of queued tasks",
    ["organization_id"],
)

# ── LLM metrics ────────────────────────────────────────────────────────────────

LLM_TOKENS_USED = Counter(
    "lork_llm_tokens_total",
    "Total LLM tokens consumed",
    ["provider", "model", "organization_id"],
)

LLM_CALL_DURATION = Histogram(
    "lork_llm_call_duration_seconds",
    "LLM API call duration",
    ["provider", "model"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60],
)

LLM_CALL_ERRORS = Counter(
    "lork_llm_call_errors_total",
    "Total LLM API call errors",
    ["provider", "model", "error_type"],
)

# ── Policy metrics ─────────────────────────────────────────────────────────────

POLICY_CHECKS_TOTAL = Counter(
    "lork_policy_checks_total",
    "Total policy evaluations",
    ["outcome", "organization_id"],
)

POLICY_VIOLATIONS_TOTAL = Counter(
    "lork_policy_violations_total",
    "Total policy violations (denials)",
    ["action", "organization_id"],
)

# ── Tool metrics ───────────────────────────────────────────────────────────────

TOOL_CALLS_TOTAL = Counter(
    "lork_tool_calls_total",
    "Total tool calls made by agents",
    ["tool_name", "outcome"],
)

TOOL_CALL_DURATION = Histogram(
    "lork_tool_call_duration_seconds",
    "Tool execution duration",
    ["tool_name"],
    buckets=[0.01, 0.1, 0.5, 1, 5, 30],
)

# ── Audit metrics ──────────────────────────────────────────────────────────────

AUDIT_EVENTS_TOTAL = Counter(
    "lork_audit_events_total",
    "Total audit log events",
    ["event_type", "severity", "organization_id"],
)
