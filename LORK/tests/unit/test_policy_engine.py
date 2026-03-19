"""
tests/unit/test_policy_engine.py
=================================
Unit tests for the LORK Policy Engine.
"""

import pytest

from lork.models import (
    Agent,
    AgentPermissions,
    AgentStatus,
    Policy,
    PolicyCondition,
    PolicyEffect,
    PolicyRule,
)

from lork.policy.engine import PolicyEngine
from lork.exceptions import PolicyDeniedError


def make_agent(
    allowed_actions=None,
    require_human_approval_for=None,
) -> Agent:

    return Agent(
        id="agent-test-001",
        tenant_id="tenant-001",
        name="test_agent",
        status=AgentStatus.ACTIVE,
        permissions=AgentPermissions(
            allowed_actions=allowed_actions or [],
            require_human_approval_for=require_human_approval_for or [],
        ),
    )


def make_allow_policy(
    actions,
    conditions=None,
    applies_to=None,
) -> Policy:

    return Policy(
        id="policy-allow-001",
        tenant_id="tenant-001",
        name="test_allow_policy",
        rules=[
            PolicyRule(
                effect=PolicyEffect.ALLOW,
                actions=actions,
                conditions=conditions or [],
            )
        ],
        applies_to=applies_to or [],
    )


def make_deny_policy(actions, conditions=None) -> Policy:

    return Policy(
        id="policy-deny-001",
        tenant_id="tenant-001",
        name="test_deny_policy",
        rules=[
            PolicyRule(
                effect=PolicyEffect.DENY,
                actions=actions,
                conditions=conditions or [],
            )
        ],
    )


class TestDefaultDeny:

    def test_no_policies_denies(self):

        agent = make_agent()

        engine = PolicyEngine(policies=[])

        result = engine.evaluate(agent, "data.read")

        assert result.allowed is False
        assert "No policies" in result.reason


    def test_no_matching_action_denies(self):

        agent = make_agent()

        policy = make_allow_policy(actions=["email.send"])

        engine = PolicyEngine(policies=[policy])

        result = engine.evaluate(agent, "data.delete")

        assert result.allowed is False


    def test_disabled_policy_denies(self):

        agent = make_agent()

        policy = make_allow_policy(actions=["data.read"])

        disabled = policy.model_copy(update={"enabled": False})

        engine = PolicyEngine(policies=[disabled])

        result = engine.evaluate(agent, "data.read")

        assert result.allowed is False


class TestAllow:

    def test_matching_allow_policy_allows(self):

        agent = make_agent()

        policy = make_allow_policy(actions=["data.read"])

        engine = PolicyEngine(policies=[policy])

        result = engine.evaluate(agent, "data.read")

        assert result.allowed is True


    def test_wildcard_action_allows(self):

        agent = make_agent()

        policy = make_allow_policy(actions=["*"])

        engine = PolicyEngine(policies=[policy])

        result = engine.evaluate(agent, "finance.transfer")

        assert result.allowed is True


    def test_multiple_actions_in_rule(self):

        agent = make_agent()

        policy = make_allow_policy(actions=["data.read", "data.write"])

        engine = PolicyEngine(policies=[policy])

        assert engine.evaluate(agent, "data.read").allowed is True
        assert engine.evaluate(agent, "data.write").allowed is True


class TestDenyOverridesAllow:

    def test_explicit_deny_beats_allow(self):

        agent = make_agent()

        allow_policy = make_allow_policy(actions=["*"])

        deny_policy = make_deny_policy(actions=["finance.transfer"])

        engine = PolicyEngine(policies=[allow_policy, deny_policy])

        result = engine.evaluate(agent, "finance.transfer")

        assert result.allowed is False


    def test_deny_only_for_specific_action(self):

        agent = make_agent()

        allow_policy = make_allow_policy(actions=["*"])

        deny_policy = make_deny_policy(actions=["data.delete"])

        engine = PolicyEngine(policies=[allow_policy, deny_policy])

        assert engine.evaluate(agent, "data.read").allowed is True
        assert engine.evaluate(agent, "data.delete").allowed is False


class TestConditions:

    def test_condition_eq_passes(self):

        agent = make_agent()

        policy = make_allow_policy(
            actions=["finance.transfer"],
            conditions=[
                PolicyCondition(field="amount", operator="eq", value=100),
            ],
        )

        engine = PolicyEngine(policies=[policy])

        result = engine.evaluate(agent, "finance.transfer", context={"amount": 100})

        assert result.allowed is True


    def test_condition_eq_fails_wrong_value(self):

        agent = make_agent()

        policy = make_allow_policy(
            actions=["finance.transfer"],
            conditions=[
                PolicyCondition(field="amount", operator="eq", value=100),
            ],
        )

        engine = PolicyEngine(policies=[policy])

        result = engine.evaluate(agent, "finance.transfer", context={"amount": 9999})

        assert result.allowed is False


    def test_condition_in_operator(self):

        agent = make_agent()

        policy = make_allow_policy(
            actions=["data.read"],
            conditions=[
                PolicyCondition(field="env", operator="in", value=["staging", "dev"]),
            ],
        )

        engine = PolicyEngine(policies=[policy])

        assert engine.evaluate(agent, "data.read", {"env": "staging"}).allowed is True
        assert engine.evaluate(agent, "data.read", {"env": "production"}).allowed is False


class TestApproval:

    def test_action_requiring_approval_is_flagged(self):

        agent = make_agent(
            allowed_actions=["finance.transfer"],
            require_human_approval_for=["finance.transfer"],
        )

        policy = make_allow_policy(actions=["finance.transfer"])

        engine = PolicyEngine(policies=[policy])

        result = engine.evaluate(agent, "finance.transfer")

        assert result.allowed is True
        assert result.requires_approval is True


class TestEnforce:

    def test_enforce_raises_on_deny(self):

        agent = make_agent()

        engine = PolicyEngine(policies=[])

        with pytest.raises(PolicyDeniedError):
            engine.enforce(agent, "data.read")


    def test_enforce_returns_decision_on_allow(self):

        agent = make_agent()

        policy = make_allow_policy(actions=["data.read"])

        engine = PolicyEngine(policies=[policy])

        decision = engine.enforce(agent, "data.read")

        assert decision.allowed is True
