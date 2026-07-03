from uuid import uuid4
from app.ai.transcriber import Transcriber
from fastapi import APIRouter, HTTPException
from app.schemas.job import DownloadJobRequest
from app.services.download_service import DownloadService
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
@router.post("/{job_id}/download")
async def download_video(
    job_id: str,
    request: DownloadJobRequest,
):

    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    title, path = DownloadService.download(str(request.url))

    job.video_url = str(request.url)
    job.video_path = path
    job.status = "downloaded"

    return {
        "job_id": job.job_id,
        "title": title,
        "status": job.status,
        "video_path": path,
    }
@router.post("/{job_id}/transcribe")
async def transcribe_video(job_id: str):

    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    if not job.video_path:
        raise HTTPException(
            status_code=400,
            detail="Video not downloaded.",
        )

    result = Transcriber.transcribe(job.video_path)

    job.transcript = result["transcript"]
    job.status = "transcribed"

    return {
        "status": job.status,
        "language": result["language"],
        "segments": len(result["transcript"]),
    }