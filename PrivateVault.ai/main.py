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

class VerificationResponse(BaseModel):
    status: str
    reason: str
    transaction_id: str
    timestamp: str
    node_version: str
    risk_score: float = 0.0
    merkle_hash: str = ""

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

# --- IN-MEMORY AUDIT LOG ---
audit_entries = []

# --- SHADOW POLICY LOGIC (The Brain) ---
# *** LOGIC UNCHANGED — same rules as original ***
def check_policy(request: TransactionRequest) -> tuple[str, str]:
    """
    Deterministic rules engine.
    In production, this would query a database or evaluating a smart contract.
    """
    # RULE 1: Cap on unverified automated transfers
    if request.amount > 10000:
        return "BLOCK", "Amount exceeds automated authorization limit (k). Human Approval Required."

    # RULE 2: Block known risky recipients
    if "unknown" in request.recipient.lower() or "anon" in request.recipient.lower():
        return "BLOCK", "Recipient identity cannot be verified (KYC Failure)."

    # RULE 3: Action Whitelist
    valid_actions = ["transfer", "pay_invoice", "query_balance"]
    # Allow tool.* actions (governed tool calls from orchestrator)
    if request.action not in valid_actions and not request.action.startswith("tool."):
        return "BLOCK", f"Action '{request.action}' is not in the approved capabilities list."

    # Otherwise, safe
    return "ALLOW", "Transaction within safe parameters."

def compute_risk_score(request: TransactionRequest) -> float:
    """Compute a risk score between 0.0 and 1.0"""
    score = 0.0
    # Amount factor
    score += min(1.0, request.amount / 50000) * 0.4
    # Recipient factor
    if "unknown" in request.recipient.lower() or "anon" in request.recipient.lower():
        score += 0.3
    # Action factor
    valid_actions = ["transfer", "pay_invoice", "query_balance"]
    if request.action not in valid_actions and not request.action.startswith("tool."):
        score += 0.3
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
            metrics.append({
                "field": key,
                "declared_value": declared_val,
                "actual_value": actual_val,
                "drift_type": "VALUE_CHANGE",
                "delta_percent": None
            })
            max_risk = escalate(max_risk, "MEDIUM")

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
    The Shadow Endpoint.
    Agents send their intent here. We return ALLOW/BLOCK.
    We do NOT execute the trade. We only validate the intent.
    """
    tx_id = str(uuid.uuid4())
    status, reason = check_policy(request)
    risk_score = compute_risk_score(request)
    timestamp = datetime.datetime.now().isoformat()
    merkle_hash = compute_merkle_hash(tx_id, status, timestamp)

    # Log to audit
    entry = {
        "transaction_id": tx_id,
        "timestamp": timestamp,
        "agent_id": request.agent_id,
        "action": request.action,
        "amount": request.amount,
        "recipient": request.recipient,
        "status": status,
        "reason": reason,
        "merkle_hash": merkle_hash,
        "risk_score": risk_score
    }
    audit_entries.insert(0, entry)
    print(f"\n🔒 [PrivateVault] shadow_verify called")
    print(f"   Agent: {request.agent_id} | Action: {request.action} | Amount: ${request.amount:,.0f} | Recipient: {request.recipient}")
    print(f"   → {status}: {reason} (risk: {risk_score})")
    print(f"   TxID: {tx_id[:12]}... | Merkle: {merkle_hash[:24]}...")

    return VerificationResponse(
        status=status,
        reason=reason,
        transaction_id=tx_id,
        timestamp=timestamp,
        node_version="3.1.0-shadow",
        risk_score=risk_score,
        merkle_hash=merkle_hash,
    )

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
    # Fall back to mock data
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
