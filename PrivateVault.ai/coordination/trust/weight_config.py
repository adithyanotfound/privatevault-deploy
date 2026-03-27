"""
weight_config.py — Enterprise-Adjustable Weight Configuration

Central config for all tunable parameters across the governance stack.
Different enterprises (tenants) can override any weight to match their
risk appetite and compliance requirements.

Priority order (highest → lowest):
  1. Per-request override (config_override in request body)
  2. Per-tenant config (stored via /mesh/configure)
  3. Global defaults (DEFAULT_WEIGHTS below)
"""

import copy
import json
import os
from typing import Optional

# ──────────────────────────────────────────────────
# SYSTEM DEFAULTS — used when no override is set
# ──────────────────────────────────────────────────
DEFAULT_WEIGHTS = {
    # Trust score computation (matches BotBook main.py formula)
    "trust_formula": {
        "completion_rate": 0.4,
        "rating_normalized": 0.4,
        "violation_penalty_max": 0.5,
        "violation_penalty_per": 0.1,
    },

    # Multi-agent consensus
    "consensus": {
        "quorum_threshold": 1.5,       # Min trust-weighted score to pass
        "approve_weight": 1.0,         # Multiplier for APPROVE votes
        "reject_weight": 1.0,          # Multiplier for REJECT votes
        "abstain_weight": 0.0,         # Multiplier for ABSTAIN votes
        "deadlock_action": "BLOCK",    # What happens on deadlock
    },

    # Risk scoring weights (matches PrivateVault main.py)
    "risk_scoring": {
        "amount_risk": 0.30,
        "recipient_risk": 0.25,
        "action_risk": 0.20,
        "time_risk": 0.10,
        "velocity_risk": 0.15,
    },

    # Dynamic trust adjustment after mesh decisions
    "dynamic_trust": {
        "alignment_boost": 0.05,       # Trust increase when agent votes with outcome
        "misalignment_penalty": 0.03,  # Trust decrease when agent votes against outcome
        "policy_miss_penalty": 0.05,   # Extra penalty: voted APPROVE but policy blocked
        "decay_rate": 0.001,           # Time-based trust decay (per hour)
        "static_dynamic_blend": 0.6,   # α: combined = α×static + (1-α)×dynamic
        "min_trust": 0.05,             # Floor — agent never goes below this
        "max_trust": 1.0,              # Ceiling
    },

    # Policy enforcement thresholds (matches PrivateVault main.py)
    "policy_thresholds": {
        "auto_approve_limit": 10_000,
        "human_review_limit": 25_000,
        "max_discount_amount": 250_000,
        "max_discount_percent": 25,
    },

    # Agent role-specific policy rules
    "agent_policies": {
        "pricing_agent": {
            "approve_below_percent": 20,
            "reject_above_percent": 30,
        },
        "risk_agent": {
            "approve_below_amount": 200_000,
            "reject_above_amount": 300_000,
        },
        "revenue_agent": {
            "approve_if_net_positive": True,
            "reject_loss_threshold_percent": 5,
        },
        "compliance_agent": {
            "block_sanctioned": True,
            "require_kyc": True,
        },
        "margin_agent": {
            "approve_above_margin_percent": 15,
            "reject_below_margin_percent": 10,
        },
    },

    # Agent matching weights (matches BotBook main.py)
    "agent_matching": {
        "nlp_relevance": 0.40,
        "capability_match": 0.20,
        "trust_score": 0.20,
        "experience": 0.10,
        "reliability": 0.10,
    },
}


# ──────────────────────────────────────────────────
# IN-MEMORY TENANT OVERRIDES
# ──────────────────────────────────────────────────
_tenant_overrides: dict[str, dict] = {}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (override wins)."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def get_weights(tenant_id: Optional[str] = None,
                request_override: Optional[dict] = None) -> dict:
    """
    Get weights with full priority resolution:
      request_override > tenant_override > global_defaults
    """
    weights = copy.deepcopy(DEFAULT_WEIGHTS)

    # Layer 1: Apply tenant overrides
    if tenant_id and tenant_id in _tenant_overrides:
        weights = _deep_merge(weights, _tenant_overrides[tenant_id])

    # Layer 2: Apply per-request overrides
    if request_override:
        weights = _deep_merge(weights, request_override)

    return weights


def set_tenant_weights(tenant_id: str, weights_patch: dict):
    """Set weight overrides for a specific tenant."""
    if tenant_id in _tenant_overrides:
        _tenant_overrides[tenant_id] = _deep_merge(
            _tenant_overrides[tenant_id], weights_patch
        )
    else:
        _tenant_overrides[tenant_id] = copy.deepcopy(weights_patch)


def get_tenant_weights(tenant_id: str) -> Optional[dict]:
    """Get the raw overrides for a tenant (not merged with defaults)."""
    return copy.deepcopy(_tenant_overrides.get(tenant_id))


def reset_tenant_weights(tenant_id: str):
    """Reset a tenant back to system defaults."""
    _tenant_overrides.pop(tenant_id, None)


def list_tenants() -> list[str]:
    """List all tenants with custom weight configurations."""
    return list(_tenant_overrides.keys())


# ──────────────────────────────────────────────────
# LOAD FROM ENV ON IMPORT (optional)
# ──────────────────────────────────────────────────
_env_config = os.getenv("MESH_WEIGHTS_CONFIG")
if _env_config:
    try:
        _loaded = json.loads(_env_config)
        if isinstance(_loaded, dict):
            for tid, overrides in _loaded.items():
                if isinstance(overrides, dict):
                    set_tenant_weights(tid, overrides)
    except json.JSONDecodeError:
        pass
