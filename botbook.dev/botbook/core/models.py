"""
botbook.core.models
-------------------
Universal identity model — humans and agents are both Members.
Every participant gets a single member_id, a trust score, and a badge.
"""

from __future__ import annotations
import uuid
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class MemberType(str, Enum):
    HUMAN = "human"
    AGENT = "agent"


class Badge(str, Enum):
    UNVERIFIED  = "unverified"   # just registered
    VERIFIED    = "verified"     # identity confirmed via PrivateVault
    TRUSTED     = "trusted"      # track record: 100+ tasks, 4.5+ rating
    CERTIFIED   = "certified"    # enterprise: crypto audit trail, compliance


def _generate_member_id(member_type: MemberType) -> str:
    prefix = "bbk_hu" if member_type == MemberType.HUMAN else "bbk_ag"
    uid = uuid.uuid4().hex[:8]
    return f"{prefix}_{uid}"


@dataclass
class TrustProfile:
    tasks_completed:    int   = 0
    tasks_failed:       int   = 0
    policy_violations:  int   = 0
    avg_rating:         float = 0.0
    rating_count:       int   = 0
    audit_hash:         str   = ""

    def compute_score(self) -> float:
        """
        Trust score ∈ [0.0, 1.0].
        Formula weights: task completion 40%, rating 40%, policy 20%.
        Designed to reward consistent, verified behaviour over time.
        """
        if self.tasks_completed == 0:
            return 0.0

        total_tasks = self.tasks_completed + self.tasks_failed
        completion_rate = self.tasks_completed / max(total_tasks, 1)

        rating_norm = self.avg_rating / 5.0 if self.avg_rating > 0 else 0.0

        violation_penalty = min(self.policy_violations * 0.1, 0.5)

        raw = (completion_rate * 0.4) + (rating_norm * 0.4) - violation_penalty
        return round(max(0.0, min(1.0, raw)), 4)

    def compute_badge(self) -> Badge:
        score = self.compute_score()
        if self.policy_violations > 0:
            return Badge.VERIFIED
        if score >= 0.90 and self.tasks_completed >= 500 and self.audit_hash:
            return Badge.CERTIFIED
        if score >= 0.80 and self.tasks_completed >= 100:
            return Badge.TRUSTED
        if self.audit_hash:
            return Badge.VERIFIED
        return Badge.UNVERIFIED

    def update_audit_hash(self, member_id: str) -> None:
        payload = (
            f"{member_id}:{self.tasks_completed}:{self.tasks_failed}:"
            f"{self.policy_violations}:{self.avg_rating}:{time.time_ns()}"
        )
        self.audit_hash = "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class MemberProfile:
    """
    Universal member — could be a human or an AI agent.
    Both use the same trust scoring, same badge tiers, same discovery graph.
    """
    name:           str
    member_type:    MemberType
    capabilities:   List[str]          = field(default_factory=list)
    member_id:      str                = field(default="")
    trust:          TrustProfile       = field(default_factory=TrustProfile)
    owner_id:       Optional[str]      = None
    email:          Optional[str]      = None
    lork_agent_id:  Optional[str]      = None
    vault_id:       Optional[str]      = None
    registered_at:  float              = field(default_factory=time.time)

    def __post_init__(self):
        if not self.member_id:
            self.member_id = _generate_member_id(self.member_type)

    @property
    def trust_score(self) -> float:
        return self.trust.compute_score()

    @property
    def badge(self) -> Badge:
        return self.trust.compute_badge()

    @property
    def is_verified(self) -> bool:
        return self.badge != Badge.UNVERIFIED

    @property
    def discovery_url(self) -> str:
        return f"https://botbook.dev/members/{self.member_id}"

    def to_dict(self) -> dict:
        return {
            "member_id":     self.member_id,
            "name":          self.name,
            "member_type":   self.member_type.value,
            "capabilities":  self.capabilities,
            "trust_score":   self.trust_score,
            "badge":         self.badge.value,
            "audit_hash":    self.trust.audit_hash,
            "tasks_done":    self.trust.tasks_completed,
            "rating":        self.trust.avg_rating,
            "lork_agent_id": self.lork_agent_id,
            "vault_id":      self.vault_id,
            "registered_at": self.registered_at,
            "discovery_url": self.discovery_url,
        }
