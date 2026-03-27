"""
trust_engine.py — Dynamic Trust Weights

Unlike the static TrustRegistry, this tracks recent agent behavior
in mesh decisions and adjusts weights dynamically.

Combined score = α × static + (1-α) × dynamic
where α comes from weight_config.py → dynamic_trust.static_dynamic_blend
"""

import time
from typing import Optional
from coordination.trust.weight_config import get_weights


class TrustEngine:
    """Dynamic trust weighting based on recent mesh decision history."""

    def __init__(self):
        self._dynamic_scores: dict[str, float] = {}
        self._history: dict[str, list[dict]] = {}   # agent_id → list of outcomes
        self._last_update: dict[str, float] = {}

    def get_weight(self, agent_id: str, tenant_id: Optional[str] = None) -> float:
        """Get the current dynamic trust weight for an agent."""
        return self._dynamic_scores.get(agent_id, 0.5)

    def get_combined_score(self, agent_id: str, static_score: float,
                           tenant_id: Optional[str] = None) -> float:
        """
        Blend static trust (from TrustRegistry / BotBook) with dynamic weight.
        Formula: α × static + (1 - α) × dynamic
        """
        w = get_weights(tenant_id)
        dt = w["dynamic_trust"]
        alpha = dt["static_dynamic_blend"]
        dynamic = self.get_weight(agent_id, tenant_id)

        combined = (alpha * static_score) + ((1.0 - alpha) * dynamic)

        # Clamp to [min_trust, max_trust]
        combined = max(dt["min_trust"], min(dt["max_trust"], combined))
        return round(combined, 4)

    def record_outcome(self, agent_id: str, voted: str, final_decision: str,
                       policy_pass: bool, tenant_id: Optional[str] = None) -> dict:
        """
        Record a mesh decision outcome and update dynamic trust.

        Rules:
        - Agent voted WITH final decision AND policy passed → boost
        - Agent voted AGAINST final decision → slight penalty
        - Agent voted APPROVE but policy blocked → extra penalty (missed violation)
        """
        w = get_weights(tenant_id)
        dt = w["dynamic_trust"]

        current = self._dynamic_scores.get(agent_id, 0.5)
        old_score = current

        voted_upper = voted.upper()
        final_upper = final_decision.upper()

        # Determine alignment
        agent_aligned = (
            (voted_upper == "APPROVE" and final_upper in ("ALLOW", "APPROVE")) or
            (voted_upper == "REJECT" and final_upper in ("BLOCK", "REJECT"))
        )

        if agent_aligned and policy_pass:
            # Correctly predicted outcome — reward
            current += dt["alignment_boost"]
            reason = "Correctly aligned with outcome"
        elif voted_upper == "APPROVE" and not policy_pass:
            # Voted APPROVE but policy blocked — missed a violation
            current -= dt["misalignment_penalty"] + dt["policy_miss_penalty"]
            reason = "Voted APPROVE but policy blocked — missed violation"
        elif not agent_aligned:
            # Voted against outcome — mild penalty
            current -= dt["misalignment_penalty"]
            reason = "Voted against final outcome"
        else:
            reason = "Neutral outcome"

        # Clamp
        current = max(dt["min_trust"], min(dt["max_trust"], round(current, 4)))
        self._dynamic_scores[agent_id] = current
        self._last_update[agent_id] = time.time()

        # Record in history
        entry = {
            "voted": voted_upper,
            "final_decision": final_upper,
            "policy_pass": policy_pass,
            "old_trust": old_score,
            "new_trust": current,
            "reason": reason,
            "timestamp": time.time(),
        }
        if agent_id not in self._history:
            self._history[agent_id] = []
        self._history[agent_id].append(entry)
        # Keep last 50 entries
        self._history[agent_id] = self._history[agent_id][-50:]

        return {
            "agent_id": agent_id,
            "old_trust": old_score,
            "new_trust": current,
            "reason": reason,
        }

    def initialize_agent(self, agent_id: str, initial_score: float = 0.5):
        """Set the initial dynamic score for an agent."""
        if agent_id not in self._dynamic_scores:
            self._dynamic_scores[agent_id] = max(0.0, min(1.0, initial_score))

    def get_history(self, agent_id: str) -> list[dict]:
        """Get the decision history for an agent."""
        return list(self._history.get(agent_id, []))

    def get_all_scores(self) -> dict[str, float]:
        return dict(self._dynamic_scores)
