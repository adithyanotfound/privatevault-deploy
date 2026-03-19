"""
botbook.api.routes
------------------
FastAPI routes. Async all the way down.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging

from .. import BotBook, MatchIntent
from ..core.models import MemberType, Badge

logger = logging.getLogger("botbook.api")

app = FastAPI(title="BotBook API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_bb = BotBook()


class RegisterAgentRequest(BaseModel):
    name: str
    capabilities: List[str]
    owner_id: Optional[str] = None


class RegisterHumanRequest(BaseModel):
    name: str
    email: str
    capabilities: Optional[List[str]] = []


class MatchRequest(BaseModel):
    task: str
    required_capabilities: Optional[List[str]] = []
    min_trust_score: float = 0.0
    min_badge: str = "unverified"
    member_type_filter: Optional[str] = None
    max_results: int = 10


class TaskResultRequest(BaseModel):
    member_id: str
    success: bool
    rating: Optional[float] = 5.0


@app.get("/health")
async def health():
    return {"status": "ok", "service": "botbook"}


@app.post("/v1/agents/register")
async def register_agent(req: RegisterAgentRequest):
    try:
        profile = await _bb.register_agent(
            name=req.name,
            capabilities=req.capabilities,
            owner_id=req.owner_id,
        )
        return profile.to_dict()
    except Exception as e:
        logger.error(f"Agent registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/humans/register")
async def register_human(req: RegisterHumanRequest):
    try:
        profile = await _bb.register_human(
            name=req.name,
            email=req.email,
            capabilities=req.capabilities,
        )
        return profile.to_dict()
    except Exception as e:
        logger.error(f"Human registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/match")
async def match_members(req: MatchRequest):

    try:
        badge = Badge(req.min_badge) if req.min_badge else Badge.UNVERIFIED
        mt = MemberType(req.member_type_filter) if req.member_type_filter else None

        intent = MatchIntent(
            task=req.task,
            required_capabilities=req.required_capabilities or [],
            min_trust_score=req.min_trust_score,
            min_badge=badge,
            member_type_filter=mt,
            max_results=req.max_results,
        )

        matches = _bb.match(intent)

        return {
            "results": [m.to_dict() for m in matches],
            "count": len(matches)
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/members/{member_id}")
async def get_member(member_id: str):

    profile = _bb.get_member(member_id)

    if not profile:
        raise HTTPException(status_code=404, detail=f"Member {member_id} not found")

    return profile.to_dict()


@app.get("/v1/members")
async def list_members(
    member_type: Optional[str] = None,
    min_badge: str = "unverified",
    limit: int = 50,
):

    mt = MemberType(member_type) if member_type else None
    badge = Badge(min_badge)

    members = _bb.list_members(member_type=mt, min_badge=badge)

    return {
        "members": [m.to_dict() for m in members[:limit]],
        "total": len(members)
    }


@app.post("/v1/trust/task-result")
async def record_task_result(req: TaskResultRequest):

    if req.success:
        _bb.record_task_completed(req.member_id, rating=req.rating or 5.0)
    else:
        _bb.record_task_failed(req.member_id)

    profile = _bb.get_member(req.member_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Member not found")

    return {
        "member_id": profile.member_id,
        "trust_score": profile.trust_score,
        "badge": profile.badge.value,
        "audit_hash": profile.trust.audit_hash,
    }


@app.get("/network")
async def network_view():

    members = _bb.list_members()

    return {
        "total_members": len(members),
        "agents": sum(1 for m in members if m.member_type == MemberType.AGENT),
        "humans": sum(1 for m in members if m.member_type == MemberType.HUMAN),
        "certified": sum(1 for m in members if m.badge == Badge.CERTIFIED),
        "trusted": sum(1 for m in members if m.badge == Badge.TRUSTED),
        "verified": sum(1 for m in members if m.badge == Badge.VERIFIED),
        "top_members": [m.to_dict() for m in members[:10]],
    }

