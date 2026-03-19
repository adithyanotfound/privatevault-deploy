import uuid
import time
from dataclasses import dataclass
from typing import Dict

from botbook.events.bus import bus

@dataclass
class Job:
    job_id: str
    agent_id: str
    task: str
    created_at: float


class JobScheduler:

    def __init__(self):
        self.jobs: Dict[str, Job] = {}

    async def enqueue(self, agent_id: str, task: str):

        job_id = "bbk_job_" + uuid.uuid4().hex[:10]

        job = Job(
            job_id=job_id,
            agent_id=agent_id,
            task=task,
            created_at=time.time()
        )

        self.jobs[job_id] = job

        await bus.publish("agent.jobs", {
            "job_id": job_id,
            "agent_id": agent_id,
            "task": task
        })

        return job


scheduler = JobScheduler()
