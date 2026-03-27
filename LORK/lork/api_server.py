"""
LORK — Control Plane API Server
Event-sourced runtime: runs, inspect, replay, trace, graph, stats, fork
"""

import json
import time
from pathlib import Path
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LORK Control Plane", description="Event-sourced runtime for AI agents", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION & PATHS ---
PROJECT_ROOT = Path(__file__).parent.parent
MOCK_DATA_DIR = PROJECT_ROOT.parent / "demo-frontend" / "mock_data"

# If deployed as a standalone on Vercel, demo-frontend might be missing.
if not MOCK_DATA_DIR.exists():
    MOCK_DATA_DIR = PROJECT_ROOT / "mock_data"

def load_runs():
    if not MOCK_DATA_DIR.exists():
        return {}
    path = MOCK_DATA_DIR / "runs.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

# --- In-memory run store ---
runs_store = {}

@app.on_event("startup")
async def load_data():
    global runs_store
    runs_store = load_runs()

# --- ENDPOINTS ---

@app.get("/")
def root():
    return {
        "runtime": "LORK",
        "status": "running",
        "version": "0.1.0",
        "runs_recorded": len(runs_store)
    }

@app.get("/health")
def health():
    return {"status": "healthy", "service": "lork"}

@app.get("/api/v1/runs")
async def list_runs():
    """List all recorded runs"""
    result = []
    for run_id, run in runs_store.items():
        result.append({
            "run_id": run_id,
            "name": run.get("name", run_id),
            "description": run.get("description", ""),
            "status": run.get("status", "completed"),
            "created_at": run.get("created_at", ""),
            "task": run.get("task", ""),
            "event_count": len(run.get("events", [])),
            "total_latency_ms": sum(e.get("latency_ms", 0) for e in run.get("events", [])),
            "total_tokens": sum(e.get("tokens", 0) for e in run.get("events", []))
        })
    return result

@app.get("/api/v1/runs/{run_id}")
async def get_run(run_id: str):
    """Get full run data"""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return runs_store[run_id]

@app.get("/api/v1/runs/{run_id}/inspect")
async def inspect_run(run_id: str):
    """Inspect run — returns timeline with latency and token counts per step"""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    run = runs_store[run_id]
    events = run.get("events", [])

    timeline = []
    for e in events:
        entry = {
            "seq": e.get("seq"),
            "type": e.get("type"),
            "agent": e.get("agent"),
            "latency_ms": e.get("latency_ms", 0),
            "tokens": e.get("tokens", 0),
            "payload": e.get("payload", ""),
            "timestamp": e.get("timestamp", "")
        }
        if e.get("tool"):
            entry["tool"] = e["tool"]
            entry["input"] = e.get("input", "")
        timeline.append(entry)

    return {
        "run_id": run_id,
        "name": run.get("name"),
        "status": run.get("status"),
        "task": run.get("task"),
        "timeline": timeline
    }

@app.get("/api/v1/runs/{run_id}/graph")
async def graph_run(run_id: str):
    """Get execution graph for a run"""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    run = runs_store[run_id]
    return {
        "run_id": run_id,
        "graph": run.get("graph", [])
    }

@app.get("/api/v1/runs/{run_id}/stats")
async def stats_run(run_id: str):
    """Get per-agent performance stats"""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    run = runs_store[run_id]
    events = run.get("events", [])

    latency = defaultdict(int)
    tokens = defaultdict(int)
    event_count = defaultdict(int)

    for e in events:
        agent = e.get("agent", "-")
        latency[agent] += e.get("latency_ms", 0)
        tokens[agent] += e.get("tokens", 0)
        event_count[agent] += 1

    stats = []
    for agent in latency:
        stats.append({
            "agent": agent,
            "total_latency_ms": latency[agent],
            "total_tokens": tokens[agent],
            "event_count": event_count[agent],
            "avg_latency_ms": round(latency[agent] / max(event_count[agent], 1), 1)
        })

    return {
        "run_id": run_id,
        "stats": stats,
        "summary": {
            "total_agents": len(stats),
            "total_latency_ms": sum(s["total_latency_ms"] for s in stats),
            "total_tokens": sum(s["total_tokens"] for s in stats)
        }
    }

@app.get("/api/v1/runs/{run_id}/trace")
async def trace_run(run_id: str):
    """Full JSON event dump for programmatic analysis"""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return runs_store[run_id]

@app.get("/api/v1/runs/{run_id}/replay")
async def replay_run(run_id: str):
    """Get replay data — events in sequence for deterministic re-execution"""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    run = runs_store[run_id]
    events = run.get("events", [])

    replay_events = []
    cumulative_time = 0
    for e in events:
        cumulative_time += e.get("latency_ms", 0)
        replay_events.append({
            "seq": e.get("seq"),
            "type": e.get("type"),
            "agent": e.get("agent"),
            "latency_ms": e.get("latency_ms", 0),
            "tokens": e.get("tokens", 0),
            "payload": e.get("payload", ""),
            "tool": e.get("tool"),
            "input": e.get("input"),
            "cumulative_time_ms": cumulative_time,
            "timestamp": e.get("timestamp", "")
        })

    return {
        "run_id": run_id,
        "name": run.get("name"),
        "total_events": len(replay_events),
        "total_time_ms": cumulative_time,
        "events": replay_events
    }

@app.post("/api/v1/runs/{run_id}/fork")
async def fork_run(run_id: str, fork_at_seq: int = 1):
    """Fork a run from a specific event sequence — create new run from history"""
    if run_id not in runs_store:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    run = runs_store[run_id]
    events = run.get("events", [])

    forked_events = [e for e in events if e.get("seq", 0) <= fork_at_seq]

    import uuid
    fork_id = f"fork-{uuid.uuid4().hex[:8]}"
    forked_run = {
        "name": f"{run.get('name', run_id)}-fork",
        "description": f"Forked from {run_id} at seq {fork_at_seq}",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "forked",
        "task": run.get("task", ""),
        "events": forked_events,
        "graph": run.get("graph", []),
        "forked_from": run_id,
        "fork_point": fork_at_seq
    }

    runs_store[fork_id] = forked_run

    return {
        "fork_id": fork_id,
        "forked_from": run_id,
        "fork_point": fork_at_seq,
        "events_copied": len(forked_events),
        "message": f"Run forked successfully. Use /api/v1/runs/{fork_id} to inspect."
    }

@app.post("/api/v1/runs/record")
async def record_run(run_data: dict):
    """Record a new run from the live orchestrator (supports both single and mesh runs)."""
    import uuid as _uuid
    run_id = run_data.get("run_id", f"run-{_uuid.uuid4().hex[:8]}")
    raw_events = run_data.get("events", [])
    events = []
    for i, e in enumerate(raw_events):
        events.append({
            "seq": e.get("seq", i+1), "type": e.get("type","unknown"),
            "agent": e.get("agent","unknown"), "latency_ms": e.get("latency_ms",0),
            "tokens": e.get("tokens",0), "payload": e.get("payload",""),
            "tool": e.get("tool"), "input": e.get("input"),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    run_record = {
        "name": run_data.get("name", run_id),
        "description": run_data.get("description",""),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": run_data.get("status","completed"),
        "task": run_data.get("task",""),
        "events": events,
        "graph": run_data.get("graph",[]),
        "type": run_data.get("type", "single"),  # "single" or "mesh"
    }
    # Store mesh-specific data if present
    if run_data.get("mesh_data"):
        run_record["mesh_data"] = run_data["mesh_data"]
    runs_store[run_id] = run_record
    return {"run_id": run_id, "events_recorded": len(events), "status": "recorded",
            "type": run_record["type"]}


@app.get("/api/v1/runs/{run_id}/mesh_votes")
def mesh_votes(run_id: str):
    """Get mesh agent vote breakdown for a mesh-type run."""
    run = runs_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    mesh_data = run.get("mesh_data", {})
    if not mesh_data:
        raise HTTPException(status_code=400,
                            detail="Not a mesh run. Use /inspect for single-agent runs.")

    return {
        "run_id": run_id,
        "type": "mesh",
        "agent_reasoning": mesh_data.get("agent_reasoning", []),
        "consensus": mesh_data.get("consensus", {}),
        "policy_enforcement": mesh_data.get("policy_enforcement", {}),
        "trust_updates": mesh_data.get("trust_updates", []),
        "crypto_proof": mesh_data.get("crypto_proof", {}),
        "weights_used": mesh_data.get("weights_used", {}),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

