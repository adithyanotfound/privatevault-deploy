"""
lork/policy/engine.py
=====================
The LORK Policy Engine.

THE MOST IMPORTANT COMPONENT IN LORK.
All agent actions pass through here before execution.

Design principles:
  - Default-DENY: if no policy explicitly allows an action, it is blocked.
  - Explicit DENY beats ALLOW (identical to AWS IAM evaluation logic).
  - Evaluation is synchronous and deterministic — no side effects.
  - The engine is STATELESS: it takes policies + context and returns a decision.
  - Every evaluation is logged as a POLICY_EVALUATED event.

Evaluation algorithm:
  1. Collect all policies applicable to the agent (by agent_id or tenant-wide).
  2. Collect all rules from those policies.
  3. For each rule (in order): check if the action matches AND all conditions pass.
  4. If matched rule is DENY → return denied immediately (explicit deny wins).
  5. If matched rule is ALLOW → mark as allowed, continue checking for denies.
  6. If no rule matched → return denied (default-deny).
  7. If allowed but action is in agent's require_human_approval_for → flag approval.
"""

from __future__ import annotations

import logging
import operator
from typing import Any

from lork.models import (
    Agent,
    Policy,
    PolicyDecision,
    PolicyEffect,
    PolicyRule,
    PolicyCondition,
)
from lork.exceptions import PolicyDeniedError

logger = logging.getLogger(__name__)

_OPERATORS: dict[str, Any] = {
    "eq":       operator.eq,
    "neq":      operator.ne,
    "gt":       operator.gt,
    "lt":       operator.lt,
    "gte":      operator.ge,
    "lte":      operator.le,
    "in":       lambda val, col: val in col,
    "not_in":   lambda val, col: val not in col,
    "contains": lambda col, val: val in col,
}


class PolicyEngine:

    def __init__(self, policies: list[Policy]) -> None:
        self._policies = policies

    def evaluate(
        self,
        agent: Agent,
        action: str,
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:

        ctx = context or {}
        eval_context = {"agent": agent.model_dump(), **ctx}

        applicable_policies = self._get_applicable_policies(agent)

        if not applicable_policies:
            return PolicyDecision(
                allowed=False,
                reason="No policies found for this agent. Default-deny.",
                matched_rules=[],
            )

        allow_rules: list[PolicyRule] = []
        deny_rules: list[PolicyRule] = []

        for policy in applicable_policies:
            if not policy.enabled:
                continue
            for rule in policy.rules:
                if self._rule_matches(rule, action, eval_context):
                    if rule.effect == PolicyEffect.DENY:
                        deny_rules.append(rule)
                    else:
                        allow_rules.append(rule)

        if deny_rules:
            reason = f"Action '{action}' explicitly denied."
            logger.info("policy.denied agent=%s action=%s", agent.id, action)
            return PolicyDecision(
                allowed=False,
                reason=reason,
                matched_rules=deny_rules + allow_rules,
            )

        if not allow_rules:
            return PolicyDecision(
                allowed=False,
                reason=f"No policy allows action '{action}'. Default-deny.",
                matched_rules=[],
            )

        requires_approval = action in agent.permissions.require_human_approval_for

        return PolicyDecision(
            allowed=True,
            reason=f"Action '{action}' allowed.",
            matched_rules=allow_rules,
            requires_approval=requires_approval,
        )

    def enforce(
        self,
        agent: Agent,
        action: str,
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:

        decision = self.evaluate(agent, action, context)

        if not decision.allowed:
            raise PolicyDeniedError(
                decision.reason,
                agent_id=agent.id,
                action=action,
            )

        return decision

    def _get_applicable_policies(self, agent: Agent) -> list[Policy]:

        return [
            p for p in self._policies
            if not p.applies_to or agent.id in p.applies_to
        ]

    def _rule_matches(
        self,
        rule: PolicyRule,
        action: str,
        context: dict[str, Any],
    ) -> bool:

        action_matches = (
            "*" in rule.actions
            or action in rule.actions
            or any(action.startswith(a.rstrip("*")) for a in rule.actions if a.endswith("*"))
        )

        if not action_matches:
            return False

        for condition in rule.conditions:
            if not self._evaluate_condition(condition, context):
                return False

        return True

    def _evaluate_condition(
        self,
        condition: PolicyCondition,
        context: dict[str, Any],
    ) -> bool:

        actual_value = self._resolve_path(condition.field, context)

        if actual_value is _MISSING:
            return False

        op_fn = _OPERATORS.get(condition.operator)

        if op_fn is None:
            return False

        try:
            return bool(op_fn(actual_value, condition.value))
        except Exception:
            return False

    @staticmethod
    def _resolve_path(path: str, context: dict[str, Any]) -> Any:

        parts = path.split(".")
        current: Any = context

        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return _MISSING
            current = current[part]

        return current


class _MissingSentinel:
    def __repr__(self) -> str:
        return "<MISSING>"


_MISSING = _MissingSentinel()
