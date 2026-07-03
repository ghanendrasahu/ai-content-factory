from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.core.storage import jobs
from app.models.job import Job

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


@router.post("")
async def create_job():

    job_id = str(uuid4())

    job = Job(job_id=job_id)

    jobs[job_id] = job

    return job


@router.get("/{job_id}")
async def get_job(job_id: str):

    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return job