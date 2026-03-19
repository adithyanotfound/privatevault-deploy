from fastapi import APIRouter
from ..trust.service import TrustService

router = APIRouter()
trust = TrustService()

@router.get("/trust/{member_id}")
def get_trust(member_id):

    return {
        "member_id": member_id,
        "trust_score": trust.trust_score(member_id)
    }

@router.post("/trust/recompute")
def recompute():

    scores = trust.recompute()

    return {
        "nodes": len(scores)
    }
