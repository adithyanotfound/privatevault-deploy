"""
update_after_decision.py — Post-Decision Trust Score Updates

After a mesh decision is finalized, update each participating agent's
trust based on whether they voted with or against the outcome.

Uses TrustEngine internally. This module is a convenience wrapper
that accepts the full agent_votes list format from the demo script.
"""

from coordination.trust.trust_engine import TrustEngine

# Module-level engine instance (shared across calls)
_engine = TrustEngine()


def get_engine() -> TrustEngine:
    """Get the module-level TrustEngine instance."""
    return _engine


def update_agents(agent_votes: list[dict], final_decision: str,
                  policy_pass: bool, tenant_id: str = None) -> list[dict]:
    """
    Update trust scores for all agents after a mesh decision.

    Args:
        agent_votes: [{"agent_id": "pricing_agent", "decision": "APPROVE"}, ...]
        final_decision: "APPROVE" or "REJECT" (the consensus outcome)
        policy_pass: whether the hard policy check passed
        tenant_id: optional enterprise tenant for weight lookup

    Returns:
        list of {"agent_id", "old_trust", "new_trust", "reason"}
    """
    updates = []
    for vote in agent_votes:
        agent_id = vote.get("agent_id", "")
        decision = vote.get("decision", "ABSTAIN")

        # Initialize if not tracked yet
        _engine.initialize_agent(agent_id, 0.5)

        result = _engine.record_outcome(
            agent_id=agent_id,
            voted=decision,
            final_decision=final_decision,
            policy_pass=policy_pass,
            tenant_id=tenant_id,
        )
        updates.append(result)

    return updates
