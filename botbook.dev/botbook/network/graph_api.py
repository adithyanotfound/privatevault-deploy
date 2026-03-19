from fastapi import APIRouter
from ..trust.service import TrustService

router = APIRouter()
trust = TrustService()

@router.get("/network/trust-top")
def top(limit: int = 20):

    scores = trust.graph.scores

    ranked = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return ranked[:limit]
