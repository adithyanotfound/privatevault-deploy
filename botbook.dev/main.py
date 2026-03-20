"""
BotBook.dev — Agent Operating System API
Agent registration, trust scoring, capability matching, CLI simulation
"""

import json
import hashlib
import time
import uuid
import os
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="BotBook", description="Agent Operating System", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MOCK DATA ---
MOCK_DATA_DIR = Path(__file__).parent.parent / "mock_data"

def load_mock(filename):
    path = MOCK_DATA_DIR / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []

# --- TRUST SCORE COMPUTATION ---
# *** EXACT SAME FORMULA as botbook/core/models.py ***
def compute_trust_score(trust_data: dict) -> float:
    """
    Trust score ∈ [0.0, 1.0].
    Formula weights: task completion 40%, rating 40%, policy 20%.
    Designed to reward consistent, verified behaviour over time.
    """
    tasks_completed = trust_data.get("tasks_completed", 0)
    tasks_failed = trust_data.get("tasks_failed", 0)
    policy_violations = trust_data.get("policy_violations", 0)
    avg_rating = trust_data.get("avg_rating", 0.0)

    if tasks_completed == 0:
        return 0.0

    total_tasks = tasks_completed + tasks_failed
    completion_rate = tasks_completed / max(total_tasks, 1)
    rating_norm = avg_rating / 5.0 if avg_rating > 0 else 0.0
    violation_penalty = min(policy_violations * 0.1, 0.5)

    raw = (completion_rate * 0.4) + (rating_norm * 0.4) - violation_penalty
    return round(max(0.0, min(1.0, raw)), 4)

# --- BADGE COMPUTATION ---
# *** EXACT SAME LOGIC as botbook/core/models.py ***
def compute_badge(trust_data: dict, trust_score: float, audit_hash: str) -> str:
    policy_violations = trust_data.get("policy_violations", 0)
    tasks_completed = trust_data.get("tasks_completed", 0)

    if policy_violations > 0:
        return "verified"
    if trust_score >= 0.90 and tasks_completed >= 500 and audit_hash:
        return "certified"
    if trust_score >= 0.80 and tasks_completed >= 100:
        return "trusted"
    if audit_hash:
        return "verified"
    return "unverified"

def generate_lork_id(name, member_id):
    payload = f"{name}:{member_id}"
    return "lork_" + hashlib.sha256(payload.encode()).hexdigest()[:12]

def generate_vault_id(member_id, name):
    payload = f"{member_id}:{name}"
    return "vault_" + hashlib.sha256(payload.encode()).hexdigest()[:12]

def generate_audit_hash(member_id, trust_data):
    payload = (
        f"{member_id}:{trust_data.get('tasks_completed', 0)}:"
        f"{trust_data.get('tasks_failed', 0)}:"
        f"{trust_data.get('policy_violations', 0)}:"
        f"{trust_data.get('avg_rating', 0)}:{time.time_ns()}"
    )
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()

def enrich_agent(agent_data: dict) -> dict:
    """Add computed fields to an agent from mock data"""
    trust_data = agent_data.get("trust", {})
    trust_score = compute_trust_score(trust_data)
    member_id = agent_data.get("member_id", "bbk_ag_" + uuid.uuid4().hex[:8])
    name = agent_data.get("name", "unknown")
    audit_hash = generate_audit_hash(member_id, trust_data)
    badge = compute_badge(trust_data, trust_score, audit_hash)

    lork_id = generate_lork_id(name, member_id) if agent_data.get("member_type") == "agent" else None
    vault_id = generate_vault_id(member_id, name)

    return {
        "member_id": member_id,
        "name": name,
        "member_type": agent_data.get("member_type", "agent"),
        "capabilities": agent_data.get("capabilities", []),
        "trust_score": trust_score,
        "badge": badge,
        "tasks_completed": trust_data.get("tasks_completed", 0),
        "tasks_failed": trust_data.get("tasks_failed", 0),
        "policy_violations": trust_data.get("policy_violations", 0),
        "avg_rating": trust_data.get("avg_rating", 0),
        "rating_count": trust_data.get("rating_count", 0),
        "audit_hash": audit_hash,
        "lork_agent_id": lork_id,
        "vault_id": vault_id,
        "owner_id": agent_data.get("owner_id"),
        "email": agent_data.get("email"),
        "discovery_url": f"https://botbook.dev/members/{member_id}",
    }

# --- In-memory agent store (loaded from mock on startup) ---
agents_store = []

@app.on_event("startup")
async def load_agents():
    global agents_store
    raw_agents = load_mock("agents.json")
    agents_store = [enrich_agent(a) for a in raw_agents]

# --- ENDPOINTS ---

@app.get("/")
def root():
    return {
        "runtime": "BotBook",
        "status": "running",
        "version": "0.1.0",
        "agents_registered": len(agents_store)
    }

@app.get("/health")
def health():
    return {"status": "healthy", "service": "botbook"}

@app.get("/api/v1/agents")
async def list_agents():
    """List all registered agents and humans"""
    return agents_store

@app.get("/api/v1/agents/{member_id}")
async def get_agent(member_id: str):
    """Get a specific agent by member_id"""
    for agent in agents_store:
        if agent["member_id"] == member_id:
            return agent
    raise HTTPException(status_code=404, detail=f"Agent {member_id} not found")

class RegisterAgentRequest(BaseModel):
    name: str
    member_type: str = "agent"
    capabilities: List[str] = []
    owner_id: Optional[str] = None
    email: Optional[str] = None

@app.post("/api/v1/agents")
async def register_agent(request: RegisterAgentRequest):
    """Register a new agent"""
    agent_data = {
        "name": request.name,
        "member_type": request.member_type,
        "capabilities": request.capabilities,
        "member_id": f"bbk_{'hu' if request.member_type == 'human' else 'ag'}_{uuid.uuid4().hex[:8]}",
        "owner_id": request.owner_id,
        "email": request.email,
        "trust": {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "policy_violations": 0,
            "avg_rating": 0,
            "rating_count": 0
        }
    }
    enriched = enrich_agent(agent_data)
    agents_store.append(enriched)
    return enriched

class RecordTaskRequest(BaseModel):
    member_id: str
    rating: float = 4.5
    success: bool = True

@app.post("/api/v1/agents/record_task")
async def record_task(request: RecordTaskRequest):
    """Record a completed task for an agent (updates trust score)"""
    for agent in agents_store:
        if agent["member_id"] == request.member_id:
            if request.success:
                agent["tasks_completed"] += 1
            else:
                agent["tasks_failed"] = agent.get("tasks_failed", 0) + 1

            # Recompute trust
            trust_data = {
                "tasks_completed": agent["tasks_completed"],
                "tasks_failed": agent.get("tasks_failed", 0),
                "policy_violations": agent.get("policy_violations", 0),
                "avg_rating": request.rating,
                "rating_count": agent.get("rating_count", 0) + 1
            }
            agent["avg_rating"] = request.rating
            agent["rating_count"] = trust_data["rating_count"]
            agent["trust_score"] = compute_trust_score(trust_data)
            agent["audit_hash"] = generate_audit_hash(agent["member_id"], trust_data)
            agent["badge"] = compute_badge(trust_data, agent["trust_score"], agent["audit_hash"])
            return agent
    raise HTTPException(status_code=404, detail=f"Agent {request.member_id} not found")

class MatchRequest(BaseModel):
    task: str = ""
    required_capabilities: List[str] = []
    min_trust_score: float = 0.0
    max_results: int = 5

@app.post("/api/v1/match")
async def match_agents(request: MatchRequest):
    """Find best agents for a task by capability + trust score"""
    matches = [
        a for a in agents_store
        if a["member_type"] == "agent"
        and a["trust_score"] >= request.min_trust_score
        and (
            len(request.required_capabilities) == 0
            or any(c in a["capabilities"] for c in request.required_capabilities)
        )
    ]
    matches.sort(key=lambda a: a["trust_score"], reverse=True)
    return matches[:request.max_results]

@app.get("/api/v1/trust_breakdown/{member_id}")
async def trust_breakdown(member_id: str):
    """Get detailed trust score breakdown for an agent"""
    for agent in agents_store:
        if agent["member_id"] == member_id:
            tasks_completed = agent["tasks_completed"]
            tasks_failed = agent.get("tasks_failed", 0)
            policy_violations = agent.get("policy_violations", 0)
            avg_rating = agent["avg_rating"]

            total_tasks = tasks_completed + tasks_failed
            completion_rate = tasks_completed / max(total_tasks, 1) if tasks_completed > 0 else 0
            rating_norm = avg_rating / 5.0 if avg_rating > 0 else 0
            violation_penalty = min(policy_violations * 0.1, 0.5)

            return {
                "member_id": member_id,
                "name": agent["name"],
                "final_score": agent["trust_score"],
                "breakdown": {
                    "completion_rate": round(completion_rate, 4),
                    "completion_weight": 0.4,
                    "completion_contribution": round(completion_rate * 0.4, 4),
                    "rating_normalized": round(rating_norm, 4),
                    "rating_weight": 0.4,
                    "rating_contribution": round(rating_norm * 0.4, 4),
                    "violation_penalty": round(violation_penalty, 4),
                    "penalty_weight": 0.2,
                },
                "raw_data": {
                    "tasks_completed": tasks_completed,
                    "tasks_failed": tasks_failed,
                    "total_tasks": total_tasks,
                    "avg_rating": avg_rating,
                    "policy_violations": policy_violations
                },
                "badge": agent["badge"],
                "badge_criteria": {
                    "certified": "score >= 0.90 AND tasks >= 500 AND has audit_hash",
                    "trusted": "score >= 0.80 AND tasks >= 100",
                    "verified": "has audit_hash",
                    "unverified": "default"
                }
            }
    raise HTTPException(status_code=404, detail=f"Agent {member_id} not found")

# --- CLI SIMULATION ENDPOINT ---
CLI_OUTPUTS = {
    "init": {
        "command": "botbook init",
        "lines": [
            {"type": "success", "text": "Project initialized"},
            {"type": "output", "text": ""},
            {"type": "output", "text": "Structure created:"},
            {"type": "output", "text": ""},
            {"type": "output", "text": "  agents/"},
            {"type": "output", "text": "  tools/"},
            {"type": "output", "text": "  memory/"},
            {"type": "output", "text": "  workflows/"},
            {"type": "output", "text": ""},
            {"type": "output", "text": "Next steps:"},
            {"type": "output", "text": ""},
            {"type": "output", "text": "  botbook make sales_agent"},
            {"type": "output", "text": '  botbook run sales_agent "task"'},
        ]
    },
    "make": {
        "command": "botbook make finance_agent && botbook make compliance_agent && botbook make sales_agent",
        "lines": [
            {"type": "success", "text": "Created agent: agents/finance_agent.py"},
            {"type": "success", "text": "Created agent: agents/compliance_agent.py"},
            {"type": "success", "text": "Created agent: agents/sales_agent.py"},
        ]
    },
    "run": {
        "command": 'botbook run finance_agent "Analyze Q3 revenue trends for GalaniPay"',
        "lines": [
            {"type": "output", "text": "⚡ Running agent: finance_agent"},
            {"type": "output", "text": "Run ID: a3f2b1c4"},
            {"type": "output", "text": ""},
            {"type": "success", "text": "[finance_agent] Q3 Revenue Analysis:"},
            {"type": "output", "text": "  1. SaaS subscriptions grew 23% QoQ ($4.2M → $5.17M)"},
            {"type": "output", "text": "  2. Enterprise deals up 31% — 3 new Fortune 500 clients"},
            {"type": "output", "text": "  3. Anomaly: Marketing spend spiked 67% in September"},
            {"type": "output", "text": "  4. Recommendation: Investigate Sept marketing ROI"},
        ]
    },
    "workflow": {
        "command": 'botbook workflow fintech_pipeline.yaml "Prepare Q3 board report"',
        "lines": [
            {"type": "output", "text": "===================="},
            {"type": "output", "text": "Running agent: finance_agent"},
            {"type": "output", "text": "===================="},
            {"type": "output", "text": "⚡ Running agent: finance_agent"},
            {"type": "output", "text": "Run ID: b7c8d9e0"},
            {"type": "success", "text": "Output: Q3 revenue analysis shows 23% growth..."},
            {"type": "output", "text": ""},
            {"type": "output", "text": "===================="},
            {"type": "output", "text": "Running agent: compliance_agent"},
            {"type": "output", "text": "===================="},
            {"type": "output", "text": "⚡ Running agent: compliance_agent"},
            {"type": "output", "text": "Run ID: c1d2e3f4"},
            {"type": "success", "text": "Output: Compliance checks passed. No regulatory issues."},
            {"type": "output", "text": ""},
            {"type": "output", "text": "===================="},
            {"type": "output", "text": "Running agent: sales_agent"},
            {"type": "output", "text": "===================="},
            {"type": "output", "text": "⚡ Running agent: sales_agent"},
            {"type": "output", "text": "Run ID: d5e6f7g8"},
            {"type": "success", "text": "Output: Recommended outreach strategy targeting..."},
            {"type": "output", "text": ""},
            {"type": "success", "text": "✓ Workflow complete — 3 agents executed successfully"},
        ]
    },
    "inspect": {
        "command": "botbook inspect",
        "lines": [
            {"type": "output", "text": "Last Run"},
            {"type": "output", "text": "────────"},
            {"type": "output", "text": "Agent: sales_agent"},
            {"type": "output", "text": "Task: Prepare Q3 board report..."},
            {"type": "output", "text": "Run ID: d5e6f7g8"},
            {"type": "output", "text": "Status: SUCCESS"},
            {"type": "output", "text": "Duration: 2.3s"},
            {"type": "output", "text": "Tokens used: 1,847"},
        ]
    },
    "logs": {
        "command": "botbook logs",
        "lines": [
            {"type": "output", "text": "Agent: finance_agent   | Task: Prepare Q3...  | Time: 12:15:00 | ✓"},
            {"type": "output", "text": "Agent: compliance_agent| Task: Prepare Q3...  | Time: 12:15:03 | ✓"},
            {"type": "output", "text": "Agent: sales_agent     | Task: Prepare Q3...  | Time: 12:15:06 | ✓"},
            {"type": "output", "text": ""},
            {"type": "output", "text": "Total: 3 runs | 0 failures"},
        ]
    }
}

@app.get("/api/v1/cli/{command}")
async def simulate_cli(command: str):
    """Simulate BotBook CLI command output"""
    if command in CLI_OUTPUTS:
        return CLI_OUTPUTS[command]
    raise HTTPException(status_code=404, detail=f"Unknown CLI command: {command}")

# ─── LIVE EXECUTION ENDPOINTS ─────────────────────────────────────

class ExecuteRequest(BaseModel):
    task: str
    agent_name: str

class PipelineRequest(BaseModel):
    task: str
    agent_names: List[str]

@app.post("/api/v1/execute_live")
async def execute_live(request: ExecuteRequest):
    from orchestrator import LiveOrchestrator
    orch = LiveOrchestrator(
        vault_url="http://localhost:8000",
        lork_url="http://localhost:8002",
        agents_store=agents_store,
        gemini_key=os.getenv("GEMINI_API_KEY",""),
    )
    return StreamingResponse(
        orch.execute_stream(request.task, request.agent_name),
        media_type="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"},
    )

@app.post("/api/v1/execute_pipeline")
async def execute_pipeline(request: PipelineRequest):
    from orchestrator import LiveOrchestrator, PipelineOrchestrator
    orch = LiveOrchestrator(
        vault_url="http://localhost:8000",
        lork_url="http://localhost:8002",
        agents_store=agents_store,
        gemini_key=os.getenv("GEMINI_API_KEY",""),
    )
    pipe = PipelineOrchestrator(orch)
    return StreamingResponse(
        pipe.execute_pipeline(request.task, request.agent_names),
        media_type="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
