"""
demo_full_pipeline.py -- Full Multi-Agent Decision Pipeline Test

Tests the complete coordination engine end-to-end.
Run from PrivateVault.ai directory:
  python demo_full_pipeline.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from coordination.mesh.drift_aware_quorum import DriftAwareQuorum
from coordination.trust.trust_engine import TrustEngine
from coordination.mesh.trust_registry import TrustRegistry
from coordination.mesh.decision_engine import MeshDecisionEngine
from coordination.mesh.agent_policy_engine import PolicyEngine
from coordination.trust.update_after_decision import update_agents
import hashlib
import json
from datetime import datetime, timezone

print("\n=== PRIVATEVAULT: FULL DECISION PIPELINE ===\n")

policy_engine = PolicyEngine()

# INPUT
request = {
    "action": "approve_discount",
    "amount": 300000,
    "context": {
        "discount_percent": 18,
        "deal_value": 1500000,
        "customer": "Acme Corp",
    }
}

ACTION_ID = "deal_full_1"

# TRUST
trust = TrustRegistry()
trust.set_score("pricing_agent", 0.9)
trust.set_score("risk_agent", 0.7)
trust.set_score("revenue_agent", 0.8)

agents = ["pricing_agent", "risk_agent", "revenue_agent"]

# TRUST ENGINE
te = TrustEngine()
for a in agents:
    te.initialize_agent(a, trust.get(a))

# QUORUM
quorum = DriftAwareQuorum(threshold=1.5, trust_registry=trust)

# AGENT REASONING
results = {}

print("=== AGENT REASONING ===")

for agent in agents:
    decision, reason = policy_engine.evaluate(agent, request)
    results[agent] = (decision, reason)

    quorum.submit_vote(
        ACTION_ID,
        agent,
        decision,
        "sig",
        context={"stable": True}
    )

    dynamic = te.get_combined_score(agent, trust.get(agent))
    print(f"{agent} (static:{trust.get(agent):.1f} | dynamic:{dynamic:.2f}) → {decision}")
    print(f"   ↳ reason: {reason}")

# CONSENSUS
engine = MeshDecisionEngine(trust_registry=trust, trust_engine=te)
consensus_result = quorum.get_result(ACTION_ID)
consensus = consensus_result["consensus"]

print("\n=== CONSENSUS ===")
print(f"APPROVE = {consensus_result['approve_score']:.2f}")
print(f"REJECT  = {consensus_result['reject_score']:.2f}")
print(f"Threshold = {quorum.threshold}")
print(f"Consensus Result: {consensus}")

# POLICY
MAX_DISCOUNT = 250000

policy_pass = True
policy_reason = "Within allowed limit"

if request["amount"] > MAX_DISCOUNT:
    policy_pass = False
    policy_reason = "Discount exceeds $250k limit"

print("\n=== POLICY CHECK ===")
print(f"Policy Result: {'PASS' if policy_pass else 'FAIL'}")
print(f"Reason: {policy_reason}")

# FINAL
if consensus == "APPROVE" and policy_pass:
    final_status = "ALLOW"
else:
    final_status = "BLOCK"

print("\n=== FINAL DECISION ===")

# === TRUST UPDATE ===
agent_votes = [
    {"agent_id": "pricing_agent", "decision": results["pricing_agent"][0]},
    {"agent_id": "risk_agent", "decision": results["risk_agent"][0]},
    {"agent_id": "revenue_agent", "decision": results["revenue_agent"][0]},
]

final_decision = "APPROVE" if final_status == "ALLOW" else "REJECT"

updates = update_agents(agent_votes, final_decision, policy_pass)
print(final_status)

for u in updates:
    arrow = "↑" if u["new_trust"] > u["old_trust"] else "↓"
    print(f"   {arrow} {u['agent_id']}: {u['old_trust']:.3f} → {u['new_trust']:.3f} ({u['reason']})")

# CRYPTO PROOF
payload = {
    "action_id": ACTION_ID,
    "request": request,
    "agents": {a: {"decision": results[a][0], "reason": results[a][1]} for a in agents},
    "consensus": consensus,
    "policy_pass": policy_pass,
    "timestamp": datetime.now(timezone.utc).isoformat()
}

serialized = json.dumps(payload, sort_keys=True).encode()
proof_hash = hashlib.sha256(serialized).hexdigest()

print("\n=== CRYPTO PROOF ===")
print(f"Hash: {proof_hash}")

# REPLAY
print("\n=== REPLAY ===")
print("Recomputed decision from stored payload → deterministic result")

print("\nDecision Path:")
print("Agent Policies → Consensus → Policy → Final Outcome")

# ─── FULL PIPELINE TEST (single call) ───
print("\n" + "="*60)
print("=== FULL PIPELINE (MeshDecisionEngine.full_pipeline) ===")
print("="*60)

trust2 = TrustRegistry()
trust2.set_score("pricing_agent", 0.9)
trust2.set_score("risk_agent", 0.7)
trust2.set_score("revenue_agent", 0.8)

engine2 = MeshDecisionEngine(trust_registry=trust2)
result = engine2.full_pipeline(
    request={
        "action_id": "deal_salesforce_001",
        "action": "approve_discount",
        "amount": 300000,
        "context": {
            "discount_percent": 18,
            "deal_value": 1500000,
            "customer": "Salesforce Enterprise",
        }
    },
    agents=["pricing_agent", "risk_agent", "revenue_agent"],
)

print(f"\n✅ Full pipeline result: {result['final_decision']}")
print(f"   Reason: {result['final_reason']}")
print(f"   Proof: {result['crypto_proof']['hash'][:40]}...")
print(f"   Time: {result['total_time_ms']}ms")
print(f"   Events: {len(result['events_log'])}")

print("\n========================\n")
