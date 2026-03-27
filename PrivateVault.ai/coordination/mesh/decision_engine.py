"""
decision_engine.py -- Top-Level Multi-Agent Decision Pipeline

Orchestrates the complete flow:
  1. Agent policy evaluation (each agent reasons independently)
  2. Trust-weighted quorum (consensus via DriftAwareQuorum)
  3. Hard policy enforcement (can override consensus)
  4. Post-decision trust updates
  5. Cryptographic proof generation
  6. Full audit trail

This is the single entry point for multi-agent governance decisions.
"""

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from coordination.mesh.trust_registry import TrustRegistry
from coordination.mesh.drift_aware_quorum import DriftAwareQuorum
from coordination.mesh.agent_policy_engine import PolicyEngine
from coordination.trust.trust_engine import TrustEngine
from coordination.trust.weight_config import get_weights


class MeshDecisionEngine:
    """Orchestrates the complete multi-agent decision pipeline."""

    def __init__(self, trust_registry: TrustRegistry = None,
                 trust_engine: TrustEngine = None,
                 tenant_id: str = None):
        self.trust_registry = trust_registry or TrustRegistry()
        self.trust_engine = trust_engine or TrustEngine()
        self.policy_engine = PolicyEngine()
        self.tenant_id = tenant_id
        self._audit_store: dict[str, dict] = {}

    def evaluate(self, action_id: str, quorum: DriftAwareQuorum) -> dict:
        """Simple consensus evaluation (used by demo script)."""
        result = quorum.get_result(action_id)
        return {"decision": result["consensus"], "details": result}

    def full_pipeline(self, request: dict,
                      agents: list[str],
                      config_override: dict = None) -> dict:
        """
        Run the FULL multi-agent decision pipeline.

        Args:
            request: {
                "action_id": "deal_001",  (optional, auto-generated)
                "action": "approve_discount",
                "amount": 300000,
                "context": {...}
            }
            agents: ["pricing_agent", "risk_agent", "revenue_agent"]
            config_override: optional weight overrides for this request

        Returns:
            Complete decision result with agent reasoning, consensus,
            policy enforcement, trust updates, and crypto proof.
        """
        start_time = time.time()
        action_id = request.get("action_id", f"mesh-{uuid.uuid4().hex[:8]}")
        action = request.get("action", "unknown")
        amount = float(request.get("amount", 0))
        context = request.get("context", {})
        tenant_id = request.get("tenant_id", self.tenant_id)

        # Get effective weights
        weights = get_weights(tenant_id, config_override)
        consensus_w = weights["consensus"]
        threshold = consensus_w["quorum_threshold"]

        print(f"\n{'='*60}")
        print(f"🔷 [MeshEngine] Multi-Agent Decision Pipeline")
        print(f"   Action: {action_id} | {action} | ${amount:,.0f}")
        print(f"   Agents: {', '.join(agents)}")
        print(f"   Threshold: {threshold}")
        print(f"{'='*60}")

        # --- STEP 1: Agent Independent Reasoning ---
        quorum = DriftAwareQuorum(
            threshold=threshold,
            trust_registry=self.trust_registry,
            tenant_id=tenant_id,
        )

        agent_reasoning = []
        events_log = []

        for agent_id in agents:
            static_trust = self.trust_registry.get(agent_id)
            self.trust_engine.initialize_agent(agent_id, static_trust)
            dynamic_trust = self.trust_engine.get_combined_score(
                agent_id, static_trust, tenant_id
            )

            # Agent evaluates independently
            decision, reason = self.policy_engine.evaluate(
                agent_id, request, tenant_id
            )

            # Submit vote to quorum
            quorum.submit_vote(
                action_id, agent_id, decision,
                signature=f"sig_{agent_id}_{action_id}",
                context={"stable": True, **context}
            )

            reasoning = {
                "agent": agent_id,
                "static_trust": round(static_trust, 4),
                "dynamic_trust": round(dynamic_trust, 4),
                "decision": decision,
                "reason": reason,
            }
            agent_reasoning.append(reasoning)

            emoji = "[OK]" if decision == "APPROVE" else "[X]"
            print(f"   {emoji} {agent_id} (s:{static_trust:.2f} d:{dynamic_trust:.2f}) -> {decision}")
            print(f"      -> {reason}")

            events_log.append({
                "seq": len(events_log) + 1,
                "type": "agent_reasoning",
                "agent": agent_id,
                "latency_ms": 5,
                "tokens": 0,
                "payload": f"{agent_id}: {decision} — {reason}",
            })

        # --- STEP 2: Trust-Weighted Consensus ---
        dynamic_weights = {}
        for agent_id in agents:
            static = self.trust_registry.get(agent_id)
            dynamic_weights[agent_id] = self.trust_engine.get_combined_score(
                agent_id, static, tenant_id
            )

        consensus_result = quorum.get_result(action_id, dynamic_weights)
        consensus_decision = consensus_result["consensus"]

        print(f"\n   [CONSENSUS] APPROVE={consensus_result['approve_score']:.2f} "
              f"| REJECT={consensus_result['reject_score']:.2f} "
              f"| Threshold={threshold}")
        print(f"   -> {consensus_decision}")

        events_log.append({
            "seq": len(events_log) + 1,
            "type": "consensus",
            "agent": "MeshEngine",
            "latency_ms": 2,
            "tokens": 0,
            "payload": (f"Consensus: {consensus_decision} "
                        f"(APPROVE={consensus_result['approve_score']:.2f} "
                        f"REJECT={consensus_result['reject_score']:.2f})"),
        })

        # --- STEP 3: Hard Policy Enforcement ---
        policy_checks = []
        policy_pass = True
        policy_reason = "All policy checks passed"

        pt = weights["policy_thresholds"]

        # Check 1: Amount limit
        max_discount = pt.get("max_discount_amount", 250_000)
        if amount > max_discount:
            policy_pass = False
            policy_reason = f"Amount ${amount:,.0f} exceeds max limit ${max_discount:,.0f}"
            policy_checks.append({
                "rule": "max_discount_amount",
                "pass": False,
                "detail": policy_reason,
            })
        else:
            policy_checks.append({
                "rule": "max_discount_amount",
                "pass": True,
                "detail": f"${amount:,.0f} ≤ ${max_discount:,.0f}",
            })

        # Check 2: Discount percent
        discount_pct = context.get("discount_percent", 0)
        max_pct = pt.get("max_discount_percent", 25)
        if discount_pct > max_pct:
            policy_pass = False
            if policy_reason == "All policy checks passed":
                policy_reason = f"Discount {discount_pct}% exceeds max {max_pct}%"
            policy_checks.append({
                "rule": "max_discount_percent",
                "pass": False,
                "detail": f"{discount_pct}% > {max_pct}%",
            })
        else:
            policy_checks.append({
                "rule": "max_discount_percent",
                "pass": True,
                "detail": f"{discount_pct}% ≤ {max_pct}%",
            })

        # Check 3: Hard block limit
        hard_limit = pt.get("human_review_limit", 25_000)
        if action in ("transfer", "pay_invoice") and amount > hard_limit:
            policy_pass = False
            if policy_reason == "All policy checks passed":
                policy_reason = f"Transfer ${amount:,.0f} exceeds hard limit ${hard_limit:,.0f}"
            policy_checks.append({
                "rule": "hard_block_limit",
                "pass": False,
                "detail": f"${amount:,.0f} > ${hard_limit:,.0f}",
            })
        else:
            policy_checks.append({
                "rule": "hard_block_limit",
                "pass": True,
                "detail": "Within limits",
            })

        # Check 4: KYC/Sanctions
        recipient = context.get("recipient", "")
        risky = ["unknown", "anon", "offshore", "sanction"]
        recipient_risky = any(r in recipient.lower() for r in risky) if recipient else False
        if recipient_risky:
            policy_pass = False
            if policy_reason == "All policy checks passed":
                policy_reason = f"Recipient '{recipient}' failed KYC/sanctions check"
            policy_checks.append({
                "rule": "kyc_sanctions",
                "pass": False,
                "detail": f"Recipient '{recipient}' flagged",
            })
        else:
            policy_checks.append({
                "rule": "kyc_sanctions",
                "pass": True,
                "detail": "Clean",
            })

        policy_tier = "pass" if policy_pass else "hard_block"
        emoji_p = "[OK]" if policy_pass else "[X]"
        print(f"\n   {emoji_p} Policy: {'PASS' if policy_pass else 'FAIL'} -- {policy_reason}")

        events_log.append({
            "seq": len(events_log) + 1,
            "type": "policy_enforcement",
            "agent": "PrivateVault",
            "latency_ms": 3,
            "tokens": 0,
            "payload": f"Policy: {'PASS' if policy_pass else 'FAIL'} — {policy_reason}",
        })

        # --- STEP 4: Final Decision ---
        if consensus_decision == "APPROVE" and policy_pass:
            final_decision = "ALLOW"
        else:
            final_decision = "BLOCK"

        if not policy_pass and consensus_decision == "APPROVE":
            final_reason = f"Policy enforcement overrode quorum consensus. {policy_reason}"
        elif consensus_decision != "APPROVE":
            final_reason = f"Quorum consensus: {consensus_decision}. Agents did not reach approval threshold."
        else:
            final_reason = "Approved by both quorum consensus and policy enforcement."

        emoji_f = "[OK]" if final_decision == "ALLOW" else "[X]"
        print(f"\n   {emoji_f} FINAL: {final_decision} -- {final_reason}")

        events_log.append({
            "seq": len(events_log) + 1,
            "type": "final_decision",
            "agent": "MeshEngine",
            "latency_ms": 0,
            "tokens": 0,
            "payload": f"FINAL: {final_decision} — {final_reason}",
        })

        # --- STEP 5: Trust Updates ---
        trust_updates = []
        final_for_trust = "APPROVE" if final_decision == "ALLOW" else "REJECT"
        for reasoning in agent_reasoning:
            update = self.trust_engine.record_outcome(
                agent_id=reasoning["agent"],
                voted=reasoning["decision"],
                final_decision=final_for_trust,
                policy_pass=policy_pass,
                tenant_id=tenant_id,
            )
            trust_updates.append(update)
            arrow = "^" if update["new_trust"] > update["old_trust"] else "v"
            print(f"   {arrow} {update['agent_id']}: {update['old_trust']:.3f} -> {update['new_trust']:.3f} ({update['reason']})")

        events_log.append({
            "seq": len(events_log) + 1,
            "type": "trust_update",
            "agent": "MeshEngine",
            "latency_ms": 1,
            "tokens": 0,
            "payload": f"Updated {len(trust_updates)} agent trust scores",
        })

        # --- STEP 6: Crypto Proof ---
        proof_payload = {
            "action_id": action_id,
            "request": {"action": action, "amount": amount},
            "agents": {r["agent"]: {"decision": r["decision"], "trust": r["dynamic_trust"]}
                       for r in agent_reasoning},
            "consensus": {
                "result": consensus_decision,
                "approve_score": consensus_result["approve_score"],
                "reject_score": consensus_result["reject_score"],
                "threshold": threshold,
            },
            "policy_pass": policy_pass,
            "final_decision": final_decision,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        serialized = json.dumps(proof_payload, sort_keys=True).encode()
        proof_hash = "sha256:" + hashlib.sha256(serialized).hexdigest()

        print(f"\n   [PROOF] {proof_hash[:40]}...")

        events_log.append({
            "seq": len(events_log) + 1,
            "type": "crypto_proof",
            "agent": "PrivateVault",
            "latency_ms": 1,
            "tokens": 0,
            "payload": f"Proof: {proof_hash[:30]}...",
        })

        total_ms = round((time.time() - start_time) * 1000)
        print(f"   [TIME] Total: {total_ms}ms")
        print(f"{'='*60}\n")

        # Build complete result
        result = {
            "action_id": action_id,
            "final_decision": final_decision,
            "final_reason": final_reason,
            "agent_reasoning": agent_reasoning,
            "consensus": {
                "approve_score": consensus_result["approve_score"],
                "reject_score": consensus_result["reject_score"],
                "abstain_score": consensus_result.get("abstain_score", 0),
                "threshold": threshold,
                "result": consensus_decision,
                "method": "trust_weighted_quorum",
                "votes": consensus_result.get("votes", []),
                "drift_detected": consensus_result.get("drift_detected", False),
            },
            "policy_enforcement": {
                "pass": policy_pass,
                "reason": policy_reason,
                "tier": policy_tier,
                "checks": policy_checks,
            },
            "trust_updates": trust_updates,
            "crypto_proof": {
                "hash": proof_hash,
                "payload_hash": "sha256:" + hashlib.sha256(
                    json.dumps({"action_id": action_id, "final": final_decision},
                               sort_keys=True).encode()
                ).hexdigest(),
                "timestamp": proof_payload["timestamp"],
            },
            "weights_used": {
                "quorum_threshold": threshold,
                "approve_weight": consensus_w.get("approve_weight", 1.0),
                "reject_weight": consensus_w.get("reject_weight", 1.0),
                "tenant_id": tenant_id,
            },
            "events_log": events_log,
            "total_time_ms": total_ms,
            "replay_id": f"mesh-{action_id}",
        }

        # Store for audit retrieval
        self._audit_store[action_id] = result
        return result

    def get_audit(self, action_id: str) -> Optional[dict]:
        """Get the full audit trail for a completed action."""
        return self._audit_store.get(action_id)

    def list_audits(self, limit: int = 50) -> list[dict]:
        """List recent mesh decision audits."""
        audits = []
        for aid, result in list(self._audit_store.items())[-limit:]:
            audits.append({
                "action_id": aid,
                "final_decision": result["final_decision"],
                "agents": [r["agent"] for r in result["agent_reasoning"]],
                "consensus": result["consensus"]["result"],
                "policy_pass": result["policy_enforcement"]["pass"],
                "total_time_ms": result["total_time_ms"],
                "timestamp": result["crypto_proof"]["timestamp"],
            })
        return audits
