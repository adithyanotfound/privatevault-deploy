"""
drift_aware_quorum.py — Trust-Weighted Voting with Drift Detection

Collects votes from mesh agents, weights them by trust, and determines
whether consensus threshold is met. "Drift-aware" means it checks if
any agent's context has destabilized since voting.

Core formula:
  approve_score = Σ (trust_weight × approve_multiplier) for APPROVE votes
  reject_score  = Σ (trust_weight × reject_multiplier)  for REJECT votes

  consensus = APPROVE  if approve_score ≥ threshold
            = REJECT   if reject_score  ≥ threshold
            = DEADLOCK otherwise
"""

import time
from typing import Optional
from coordination.mesh.trust_registry import TrustRegistry
from coordination.trust.weight_config import get_weights


class DriftAwareQuorum:
    """Trust-weighted quorum with drift detection."""

    def __init__(self, threshold: float = 1.5,
                 trust_registry: TrustRegistry = None,
                 tenant_id: str = None):
        self.threshold = threshold
        self.trust_registry = trust_registry or TrustRegistry()
        self.tenant_id = tenant_id
        self._votes: dict[str, list[dict]] = {}  # action_id → list of votes

    def submit_vote(self, action_id: str, agent_id: str, decision: str,
                    signature: str = "", context: dict = None):
        """
        Submit a trust-weighted vote.

        Args:
            action_id: unique identifier for the action being voted on
            agent_id: the voting agent
            decision: "APPROVE", "REJECT", or "ABSTAIN"
            signature: cryptographic signature (for audit)
            context: optional context, context.stable=False triggers drift
        """
        if action_id not in self._votes:
            self._votes[action_id] = []

        trust_score = self.trust_registry.get(agent_id)

        vote = {
            "agent_id": agent_id,
            "decision": decision.upper(),
            "trust_score": trust_score,
            "signature": signature,
            "context": context or {},
            "timestamp": time.time(),
            "drift_flagged": not (context or {}).get("stable", True),
        }
        self._votes[action_id].append(vote)

    def get_result(self, action_id: str,
                   dynamic_weights: dict = None) -> dict:
        """
        Compute the consensus result for an action.

        Args:
            action_id: the action to evaluate
            dynamic_weights: optional {agent_id: dynamic_trust} to override static

        Returns:
            Full result dict with scores, votes, and consensus
        """
        votes = self._votes.get(action_id, [])
        if not votes:
            return {
                "approve_score": 0.0,
                "reject_score": 0.0,
                "abstain_score": 0.0,
                "threshold": self.threshold,
                "consensus": "NO_VOTES",
                "votes": [],
                "drift_detected": False,
                "total_agents": 0,
            }

        w = get_weights(self.tenant_id)
        consensus_w = w.get("consensus", {})
        approve_mult = consensus_w.get("approve_weight", 1.0)
        reject_mult = consensus_w.get("reject_weight", 1.0)
        abstain_mult = consensus_w.get("abstain_weight", 0.0)

        approve_score = 0.0
        reject_score = 0.0
        abstain_score = 0.0
        drift_detected = False
        vote_details = []

        for vote in votes:
            agent_id = vote["agent_id"]
            decision = vote["decision"]

            # Use dynamic weight if available, else static
            if dynamic_weights and agent_id in dynamic_weights:
                weight = dynamic_weights[agent_id]
            else:
                weight = vote["trust_score"]

            if vote.get("drift_flagged"):
                drift_detected = True

            if decision == "APPROVE":
                weighted = weight * approve_mult
                approve_score += weighted
            elif decision == "REJECT":
                weighted = weight * reject_mult
                reject_score += weighted
            else:  # ABSTAIN
                weighted = weight * abstain_mult
                abstain_score += weighted

            vote_details.append({
                "agent_id": agent_id,
                "decision": decision,
                "static_trust": vote["trust_score"],
                "effective_weight": round(weight, 4),
                "weighted_score": round(weighted, 4),
                "drift_flagged": vote.get("drift_flagged", False),
                "timestamp": vote["timestamp"],
            })

        # Determine consensus
        approve_score = round(approve_score, 4)
        reject_score = round(reject_score, 4)
        abstain_score = round(abstain_score, 4)

        if approve_score >= self.threshold:
            consensus = "APPROVE"
        elif reject_score >= self.threshold:
            consensus = "REJECT"
        else:
            consensus = consensus_w.get("deadlock_action", "BLOCK")

        return {
            "approve_score": approve_score,
            "reject_score": reject_score,
            "abstain_score": abstain_score,
            "threshold": self.threshold,
            "consensus": consensus,
            "votes": vote_details,
            "drift_detected": drift_detected,
            "total_agents": len(votes),
            "method": "trust_weighted_quorum",
        }

    def clear(self, action_id: str = None):
        """Clear votes for a specific action or all actions."""
        if action_id:
            self._votes.pop(action_id, None)
        else:
            self._votes.clear()

    def get_votes(self, action_id: str) -> list[dict]:
        """Get raw votes for an action."""
        return list(self._votes.get(action_id, []))
