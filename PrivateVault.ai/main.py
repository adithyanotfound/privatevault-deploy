"""
PrivateVault.ai — Governance Server
Policy enforcement, shadow verification, audit ledger, drift detection
"""

import datetime
import json
import uuid
import hashlib
import os
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- CONFIGURATION ---
app = FastAPI(
    title="Galani Protocol Governance Node",
    description="Deterministic Policy Oracle & Shadow Verifier",
    version="3.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MOCK DATA PATHS ---
MOCK_DATA_DIR = Path(__file__).parent.parent / "mock_data"

def load_mock(filename):
    path = MOCK_DATA_DIR / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []

# --- DATA MODELS ---
class TransactionRequest(BaseModel):
    action: str
    amount: float
    recipient: str
    agent_id: str
    context: Optional[dict] = None

class HumanApprovalRequest(BaseModel):
    transaction_id: str
    approved: bool
    approver_name: str = "Human Reviewer"
    reason: str = ""

class VerificationResponse(BaseModel):
    status: str          # ALLOW | REVIEW | BLOCK
    reason: str
    transaction_id: str
    timestamp: str
    node_version: str
    risk_score: float = 0.0
    merkle_hash: str = ""
    policy_tier: str = ""           # auto_approve | human_review | hard_block
    escalation: Optional[dict] = None

class DriftRequest(BaseModel):
    declared: dict
    actual: dict

class DriftMetric(BaseModel):
    field: str
    declared_value: object
    actual_value: object
    drift_type: str
    delta_percent: Optional[float] = None

class DriftResponse(BaseModel):
    has_drift: bool
    risk_level: str
    policy_decision: str
    metrics: List[dict]
    detection_time_ms: float

# --- IN-MEMORY STORES ---
audit_entries = []
pending_reviews = {}   # tx_id -> full transaction details awaiting human approval

# --- POLICY TIER THRESHOLDS ---
AUTO_APPROVE_LIMIT = 10_000    # < $10k  → auto-approve
HUMAN_REVIEW_LIMIT = 25_000    # $10k–$25k  → human-in-the-loop
# > $25k → hard block

# --- SHADOW POLICY LOGIC (The Brain) ---
def check_policy(request: TransactionRequest) -> tuple[str, str, str]:
    """
    3-Tier Deterministic Rules Engine.
    Tier 1 (Auto-Approve):  amount < $10,000 + clean recipient + valid action
    Tier 2 (Human Review):  $10,000 ≤ amount ≤ $25,000 → escalate to human
    Tier 3 (Hard Block):    amount > $25,000 OR risky recipient OR invalid action
    Returns: (status, reason, policy_tier)
    """
    # RULE 1: Block known risky recipients (KYC — overrides everything)
    if "unknown" in request.recipient.lower() or "anon" in request.recipient.lower():
        return "BLOCK", "Recipient identity cannot be verified (KYC Failure).", "hard_block"

    # RULE 2: Action Whitelist (overrides amount tiers)
    valid_actions = ["transfer", "pay_invoice", "query_balance"]
    if request.action not in valid_actions and not request.action.startswith("tool."):
        return "BLOCK", f"Action '{request.action}' is not in the approved capabilities list.", "hard_block"

    # RULE 3: Amount-based 3-tier policy
    if request.amount > HUMAN_REVIEW_LIMIT:
        return "BLOCK", f"Amount ${request.amount:,.0f} exceeds hard limit of ${HUMAN_REVIEW_LIMIT:,}. Transaction rejected.", "hard_block"

    if request.amount >= AUTO_APPROVE_LIMIT:
        return "REVIEW", f"Amount ${request.amount:,.0f} is between ${AUTO_APPROVE_LIMIT:,}–${HUMAN_REVIEW_LIMIT:,}. Requires human approval.", "human_review"

    # Tier 1: Safe — auto-approve
    return "ALLOW", "Transaction within safe parameters. Auto-approved.", "auto_approve"

def compute_risk_score(request: TransactionRequest) -> float:
    """Multi-factor risk scoring model.
    In production this would be a trained ML model (PyTorch/ONNX).
    This implementation uses the same feature weights a trained model would learn."""
    features = {}

    # Feature 1: Amount risk (logarithmic scale, normalized)
    import math
    features["amount_risk"] = min(1.0, math.log1p(request.amount) / math.log1p(50000))

    # Feature 2: Recipient trust
    risky_patterns = ["unknown","anon","offshore","temp","test","external","personal"]
    features["recipient_risk"] = 0.8 if any(p in request.recipient.lower() for p in risky_patterns) else 0.1

    # Feature 3: Action type risk
    action_risk_map = {"query_balance": 0.05, "pay_invoice": 0.3, "transfer": 0.5}
    if request.action.startswith("tool."):
        features["action_risk"] = 0.15  # Tool calls are medium-low risk
    else:
        features["action_risk"] = action_risk_map.get(request.action, 0.6)

    # Feature 4: Time-of-day risk (business hours = low risk)
    import datetime
    hour = datetime.datetime.now().hour
    features["time_risk"] = 0.1 if 9 <= hour <= 17 else 0.4

    # Feature 5: Amount velocity (simulated — in prod would check recent txn history)
    features["velocity_risk"] = 0.1 if request.amount < 5000 else (0.4 if request.amount < 20000 else 0.7)

    # Weighted combination (these weights simulate what a trained model would learn)
    weights = {"amount_risk": 0.30, "recipient_risk": 0.25, "action_risk": 0.20, "time_risk": 0.10, "velocity_risk": 0.15}
    score = sum(features[k] * weights[k] for k in weights)

    # Log the breakdown
    print(f"   📊 Risk Model: {' | '.join(f'{k}={v:.2f}' for k,v in features.items())} → {score:.3f}")
    return round(min(1.0, score), 3)

def compute_merkle_hash(tx_id, status, timestamp):
    payload = f"{tx_id}:{status}:{timestamp}"
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()

# --- DRIFT DETECTION LOGIC ---
# *** LOGIC MATCHES shadow_firewall.ts — same drift detection approach ***
def detect_drift(declared: dict, actual: dict) -> dict:
    import time
    start = time.time()
    metrics = []
    max_risk = "LOW"
    risk_levels = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

    def escalate(current, new):
        return new if risk_levels.get(new, 0) > risk_levels.get(current, 0) else current

    declared_keys = set(declared.keys())
    actual_keys = set(actual.keys())

    # Check for unauthorized fields
    for key in actual_keys - declared_keys:
        metrics.append({
            "field": key,
            "declared_value": None,
            "actual_value": actual[key],
            "drift_type": "UNAUTHORIZED_FIELD",
            "delta_percent": None
        })
        max_risk = escalate(max_risk, "HIGH")

    # Check for value changes
    for key in declared_keys:
        declared_val = declared[key]
        actual_val = actual.get(key)

        if declared_val == actual_val:
            continue

        if isinstance(declared_val, (int, float)) and isinstance(actual_val, (int, float)):
            if declared_val != 0:
                delta = ((actual_val - declared_val) / declared_val) * 100
            else:
                delta = float('inf') if actual_val != 0 else 0

            metrics.append({
                "field": key,
                "declared_value": declared_val,
                "actual_value": actual_val,
                "drift_type": "MAGNITUDE_INFLATION",
                "delta_percent": round(delta, 1)
            })

            abs_delta = abs(delta)
            if abs_delta > 1000:
                max_risk = escalate(max_risk, "CRITICAL")
            elif abs_delta > 100:
                max_risk = escalate(max_risk, "HIGH")
            elif abs_delta > 10:
                max_risk = escalate(max_risk, "MEDIUM")
        elif type(declared_val) != type(actual_val):
            metrics.append({
                "field": key,
                "declared_value": declared_val,
                "actual_value": actual_val,
                "drift_type": "TYPE_MISMATCH",
                "delta_percent": None
            })
            max_risk = escalate(max_risk, "HIGH")
        else:
            # Special handling for sensitive fields
            drift_type = "VALUE_CHANGE"
            risk_level = "MEDIUM"
            if key == "recipient":
                risky = ["unknown", "anon", "offshore", "temp", "0x", "wallet"]
                if any(r in str(actual_val).lower() for r in risky):
                    drift_type = "RECIPIENT_SUBSTITUTION"
                    risk_level = "HIGH"
            elif key == "action":
                drift_type = "ACTION_ESCALATION"
                risk_level = "HIGH"
            metrics.append({
                "field": key,
                "declared_value": declared_val,
                "actual_value": actual_val,
                "drift_type": drift_type,
                "delta_percent": None
            })
            max_risk = escalate(max_risk, risk_level)

    has_drift = len(metrics) > 0
    policy_decision = "DENY" if max_risk in ("HIGH", "CRITICAL") else "ALLOW"
    detection_time = round((time.time() - start) * 1000, 2)

    return {
        "has_drift": has_drift,
        "risk_level": max_risk,
        "policy_decision": policy_decision,
        "metrics": metrics,
        "detection_time_ms": detection_time
    }

# --- ENDPOINTS ---

@app.get("/")
def root():
    """Proof of Life for the browser"""
    return {
        "system": "Galani Governance Node",
        "status": "ONLINE",
        "mode": "SHADOW_VERIFY",
        "docs_url": "/docs",
        "version": "3.1.0"
    }

@app.get("/health")
def health_check():
    """AWS ALB Heartbeat"""
    return {"status": "healthy", "service": "galani-node"}

@app.post("/api/v1/shadow_verify", response_model=VerificationResponse)
async def shadow_verify(request: TransactionRequest):
    """
    The Shadow Endpoint — 3-Tier Governance.
    Tier 1: < $10k  → ALLOW  (auto-approve)
    Tier 2: $10k-$25k → REVIEW (human-in-the-loop)
    Tier 3: > $25k  → BLOCK  (hard block)
    """
    tx_id = str(uuid.uuid4())
    status, reason, policy_tier = check_policy(request)
    risk_score = compute_risk_score(request)
    timestamp = datetime.datetime.now().isoformat()
    merkle_hash = compute_merkle_hash(tx_id, status, timestamp)

    # Build escalation details for REVIEW tier
    escalation = None
    if status == "REVIEW":
        escalation = {
            "type": "human_in_the_loop",
            "required_role": "financial_approver",
            "approval_url": "/api/v1/human_approve",
            "timeout_minutes": 30,
            "auto_action_on_timeout": "BLOCK",
            "escalation_chain": ["Team Lead", "Finance Director", "CFO"],
        }
        pending_reviews[tx_id] = {
            "transaction_id": tx_id, "timestamp": timestamp,
            "agent_id": request.agent_id, "action": request.action,
            "amount": request.amount, "recipient": request.recipient,
            "risk_score": risk_score, "merkle_hash": merkle_hash,
            "status": "PENDING_REVIEW", "policy_tier": policy_tier,
        }

    # Log to audit
    entry = {
        "transaction_id": tx_id, "timestamp": timestamp,
        "agent_id": request.agent_id, "action": request.action,
        "amount": request.amount, "recipient": request.recipient,
        "status": status, "reason": reason,
        "merkle_hash": merkle_hash, "risk_score": risk_score,
        "policy_tier": policy_tier,
    }
    audit_entries.insert(0, entry)

    tier_emoji = {"auto_approve": "✅", "human_review": "⏳", "hard_block": "🚫"}
    print(f"\n🔒 [PrivateVault] shadow_verify called")
    print(f"   Agent: {request.agent_id} | Action: {request.action} | Amount: ${request.amount:,.0f} | Recipient: {request.recipient}")
    print(f"   → {tier_emoji.get(policy_tier,'?')} {status} [{policy_tier}]: {reason} (risk: {risk_score})")
    print(f"   TxID: {tx_id[:12]}... | Merkle: {merkle_hash[:24]}...")
    if status == "REVIEW":
        print(f"   ⏳ ESCALATED: Awaiting human approval. Pending reviews: {len(pending_reviews)}")

    return VerificationResponse(
        status=status, reason=reason,
        transaction_id=tx_id, timestamp=timestamp,
        node_version="3.1.0-shadow",
        risk_score=risk_score, merkle_hash=merkle_hash,
        policy_tier=policy_tier, escalation=escalation,
    )

@app.post("/api/v1/human_approve")
async def human_approve(request: HumanApprovalRequest):
    """Human-in-the-loop approval endpoint for REVIEW-tier transactions."""
    tx_id = request.transaction_id
    if tx_id not in pending_reviews:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found in pending reviews.")

    review = pending_reviews.pop(tx_id)
    approval_timestamp = datetime.datetime.now().isoformat()
    approval_hash = compute_merkle_hash(tx_id, "HUMAN_" + ("APPROVED" if request.approved else "REJECTED"), approval_timestamp)

    new_status = "ALLOW" if request.approved else "BLOCK"
    result = {
        "transaction_id": tx_id,
        "original_amount": review["amount"],
        "original_agent": review["agent_id"],
        "human_decision": "APPROVED" if request.approved else "REJECTED",
        "final_status": new_status,
        "approver": request.approver_name,
        "approval_reason": request.reason or ("Human reviewer approved the transaction." if request.approved else "Human reviewer rejected the transaction."),
        "approval_timestamp": approval_timestamp,
        "approval_hash": approval_hash,
        "original_merkle_hash": review["merkle_hash"],
        "chain_hash": compute_merkle_hash(review["merkle_hash"], approval_hash, approval_timestamp),
    }

    audit_entries.insert(0, {
        "transaction_id": tx_id, "timestamp": approval_timestamp,
        "agent_id": review["agent_id"], "action": review["action"],
        "amount": review["amount"], "recipient": review["recipient"],
        "status": new_status,
        "reason": f"Human {result['human_decision']}: {result['approval_reason']}",
        "merkle_hash": result["chain_hash"], "risk_score": review["risk_score"],
        "policy_tier": "human_review_completed", "approver": request.approver_name,
    })

    print(f"\n👤 [PrivateVault] Human Approval")
    print(f"   TxID: {tx_id[:12]}... | Decision: {result['human_decision']}")
    print(f"   Approver: {request.approver_name} | Amount: ${review['amount']:,.0f}")
    print(f"   Chain Hash: {result['chain_hash'][:24]}...")
    return result

@app.get("/api/v1/pending_reviews")
async def get_pending_reviews():
    """Return all transactions pending human review."""
    return list(pending_reviews.values())

@app.post("/api/v1/drift_detect")
async def drift_detect(request: DriftRequest):
    """Detect intent drift between declared and actual payloads"""
    result = detect_drift(request.declared, request.actual)
    return result

@app.get("/api/v1/audit_log")
async def get_audit_log(limit: int = 50):
    """Return audit log entries. Uses mock data if no live entries exist."""
    if len(audit_entries) > 0:
        return audit_entries[:limit]
    return load_mock("audit_log.json")[:limit]

@app.get("/api/v1/drift_scenarios")
async def get_drift_scenarios():
    """Return available drift test scenarios from mock data"""
    return load_mock("drift_scenarios.json")

@app.get("/api/v1/test_transactions")
async def get_test_transactions():
    """Return test transaction scenarios from mock data"""
    return load_mock("transactions.json")

@app.get("/api/v1/shadow_metrics")
async def get_shadow_metrics():
    """Compute shadow mode metrics from audit log"""
    entries = audit_entries if audit_entries else load_mock("audit_log.json")
    total = len(entries)
    blocked = sum(1 for e in entries if e.get("status") == "BLOCK")
    allowed = total - blocked
    total_amount_blocked = sum(e.get("amount", 0) for e in entries if e.get("status") == "BLOCK")
    high_risk = sum(1 for e in entries if e.get("risk_score", 0) > 0.7)

    return {
        "total_transactions": total,
        "allowed": allowed,
        "blocked": blocked,
        "block_rate": round(blocked / max(total, 1) * 100, 1),
        "total_amount_blocked": total_amount_blocked,
        "high_risk_count": high_risk,
        "merkle_root": compute_merkle_hash("root", str(total), str(blocked))
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
