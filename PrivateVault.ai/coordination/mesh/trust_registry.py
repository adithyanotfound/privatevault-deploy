"""
trust_registry.py — Per-Agent Static Trust Score Store

Stores the baseline trust score for each agent in the mesh.
On startup, these are loaded from BotBook's agent registry.
Follows the SAME trust formula as BotBook main.py:
  trust = (completion_rate × 0.4) + (rating_norm × 0.4) − violation_penalty
"""

from typing import Optional


class TrustRegistry:
    """In-memory trust score store for mesh agents."""

    def __init__(self):
        self._scores: dict[str, float] = {}

    def set_score(self, agent_id: str, score: float):
        """Set the static trust score for an agent (clamped to [0, 1])."""
        self._scores[agent_id] = max(0.0, min(1.0, float(score)))

    def get(self, agent_id: str) -> float:
        """Get the static trust score. Returns 0.5 for unknown agents."""
        return self._scores.get(agent_id, 0.5)

    def get_all(self) -> dict[str, float]:
        """Get all stored trust scores."""
        return dict(self._scores)

    def bulk_set(self, scores: dict[str, float]):
        """Set multiple scores at once."""
        for agent_id, score in scores.items():
            self.set_score(agent_id, score)

    def has_agent(self, agent_id: str) -> bool:
        return agent_id in self._scores

    def remove(self, agent_id: str):
        self._scores.pop(agent_id, None)

    def count(self) -> int:
        return len(self._scores)

    def load_from_botbook_agents(self, agents_store: list[dict]):
        """
        Load trust scores from BotBook's enriched agent store.
        This is the bridge between BotBook's trust scoring and the mesh.
        """
        for agent in agents_store:
            if agent.get("member_type") == "agent":
                name = agent.get("name", "")
                trust = agent.get("trust_score", 0.5)
                if name:
                    self.set_score(name, trust)
