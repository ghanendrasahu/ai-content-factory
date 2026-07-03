from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.ai.clip_detector import ClipDetector
from app.ai.transcriber import Transcriber
from app.core.storage import jobs
from app.models.job import Job
from app.schemas.job import DownloadJobRequest

from app.services.download_service import DownloadService
from app.services.clip_renderer import ClipRenderer
from app.services.video_optimizer import VideoOptimizer


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


# ---------------------------------------------------------------------
# Create Job
# ---------------------------------------------------------------------

@router.post("")
async def create_job():

    job_id = str(uuid4())

    job = Job(job_id=job_id)

    jobs[job_id] = job

    return job


# ---------------------------------------------------------------------
# Get Job
# ---------------------------------------------------------------------

@router.get("/{job_id}")
async def get_job(job_id: str):

    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


# ---------------------------------------------------------------------
# Download Video
# ---------------------------------------------------------------------

@router.post("/{job_id}/download")
async def download_video(job_id: str, request: DownloadJobRequest):

    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

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


# ---------------------------------------------------------------------
# Transcribe Video
# ---------------------------------------------------------------------

@router.post("/{job_id}/transcribe")
async def transcribe_video(job_id: str):

    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.video_path:
        raise HTTPException(status_code=400, detail="Video not downloaded")

    result = Transcriber.transcribe(job.video_path)

    job.transcript = result["transcript"]
    job.status = "transcribed"

    return {
        "status": job.status,
        "language": result["language"],
        "segments": len(result["transcript"]),
    }


# ---------------------------------------------------------------------
# Detect Clips
# ---------------------------------------------------------------------

@router.post("/{job_id}/detect-clips")
async def detect_clips(job_id: str):

    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.transcript:
        raise HTTPException(status_code=400, detail="Transcript not found")

    clips = ClipDetector.detect(job.transcript)

    job.clips = clips
    job.status = "clips_detected"

    return {
        "status": job.status,
        "clips_count": len(clips)
    }


# ---------------------------------------------------------------------
# Render Clips
# ---------------------------------------------------------------------

@router.post("/{job_id}/render-clips")
async def render_clips(job_id: str):

    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.clips:
        raise HTTPException(status_code=400, detail="No clips found")

    if not job.video_path:
        raise HTTPException(status_code=400, detail="No video found")

    output_files = ClipRenderer.render(job.video_path, job.clips)

    job.status = "rendered"

    return {
        "status": job.status,
        "clips": output_files
    }


# ---------------------------------------------------------------------
# Make Vertical Video
# ---------------------------------------------------------------------

@router.post("/{job_id}/make-vertical")
async def make_vertical(job_id: str):

    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.video_path:
        raise HTTPException(status_code=400, detail="No video found")

    output_path = f"outputs/{job.job_id}_vertical.mp4"

    result = VideoOptimizer.make_vertical(
        job.video_path,
        output_path,
        job.transcript
    )

    job.status = "vertical_ready"

    return {
        "status": job.status,
        "output": result
    }