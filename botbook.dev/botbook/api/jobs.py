from fastapi import APIRouter
from pydantic import BaseModel

from botbook.scheduler.jobs import scheduler

router = APIRouter(prefix="/v1/jobs")

class JobRequest(BaseModel):
    agent_id: str
    task: str

@router.post("/run")
async def run_job(req: JobRequest):

    job = await scheduler.enqueue(req.agent_id, req.task)

    return {
        "job_id": job.job_id,
        "status": "QUEUED"
    }
