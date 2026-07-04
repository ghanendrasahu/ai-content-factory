from uuid import uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.ai.clip_detector import ClipDetector
from app.ai.transcriber import Transcriber
from app.core.paths import OUTPUT_DIR
from app.core.storage import jobs
from app.models.job import Job
from app.schemas.job import DownloadJobRequest

from app.services.download_service import DownloadService
from app.services.clip_renderer import ClipRenderer
from app.services.video_optimizer import VideoOptimizer
from app.services.pipeline import Pipeline

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# =========================
# BACKGROUND PIPELINE
# =========================
def run_pipeline_background(job_id: str):
    job = jobs.get(job_id)

    if not job:
        return

    try:
        Pipeline.run(job)
    except Exception as e:
        job.status = "failed"
        job.step = "failed"
        job.error = str(e)


# =========================
# CREATE JOB
# =========================
@router.post("")
async def create_job():
    job_id = str(uuid4())
    job = Job(job_id=job_id)
    jobs[job_id] = job
    return job


# =========================
# GET JOB (SINGLE SOURCE OF TRUTH)
# =========================
@router.get("/{job_id}")
async def get_job(job_id: str):

    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.job_id,
        "status": job.status,
        "step": getattr(job, "step", ""),
        "progress": getattr(job, "progress", 0),

        # INPUT VIDEO
        "video_path": getattr(job, "video_path", None),

        # OUTPUT VIDEO
        "final_video": getattr(job, "final_video", None),

        # CLIPS (AI detected)
        "clips": getattr(job, "clips", []),

        # RENDERED OUTPUTS
        "clip_outputs": getattr(job, "clip_outputs", []),

        # CONTENT PACK (future)
        "content_pack": getattr(job, "content_pack", None),

        # ERROR
        "error": getattr(job, "error", None),
    }


# =========================
# DOWNLOAD VIDEO
# =========================
@router.post("/{job_id}/download")
async def download_video(job_id: str, request: DownloadJobRequest):

    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    title, path = DownloadService.download(str(request.url))

    job.video_url = str(request.url)
    job.video_path = path
    job.status = "queued"
    job.step = "queued"
    job.progress = 10

    return {
        "job_id": job.job_id,
        "title": title,
        "status": job.status,
        "video_path": path,
    }


# =========================
# TRANSCRIBE
# =========================
@router.post("/{job_id}/transcribe")
async def transcribe_video(job_id: str):

    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.video_path:
        raise HTTPException(status_code=400, detail="Video not downloaded")

    result = Transcriber.transcribe(job.video_path)

    job.transcript = result["transcript"]
    job.status = "queued"
    job.step = "queued"
    job.progress = 30

    return {
        "status": job.status,
        "language": result["language"],
        "segments": len(result["transcript"]),
    }


# =========================
# DETECT CLIPS
# =========================
@router.post("/{job_id}/detect-clips")
async def detect_clips(job_id: str):

    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.transcript:
        raise HTTPException(status_code=400, detail="Transcript not found")

    clips = ClipDetector.detect(job.transcript)

    job.clips = clips
    job.status = "queued"
    job.step = "queued"
    job.progress = 50

    return {
        "status": job.status,
        "clips_count": len(clips),
    }


# =========================
# RENDER CLIPS
# =========================
@router.post("/{job_id}/render-clips")
async def render_clips(job_id: str):

    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.clips:
        raise HTTPException(status_code=400, detail="No clips found")

    if not job.video_path:
        raise HTTPException(status_code=400, detail="No video found")

    output_files = ClipRenderer.render(
        job.video_path,
        job.clips,
        job.job_id
    )

    job.clip_outputs = output_files
    job.status = "queued"
    job.step = "queued"
    job.progress = 70

    return {
        "status": job.status,
        "clips": output_files,
    }


# =========================
# MAKE VERTICAL VIDEO
# =========================
@router.post("/{job_id}/make-vertical")
async def make_vertical(job_id: str):

    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.video_path:
        raise HTTPException(status_code=400, detail="No video found")

    source_path = job.clip_outputs[0] if job.clip_outputs else job.video_path
    output_path = OUTPUT_DIR / f"{job.job_id}_vertical.mp4"

    result = VideoOptimizer.make_vertical(
        source_path,
        str(output_path),
        job.transcript,
    )

    job.final_video = result
    job.status = "completed"
    job.step = "completed"
    job.progress = 100

    return {
        "status": job.status,
        "output": result,
    }


# =========================
# FULL PIPELINE
# =========================
@router.post("/{job_id}/process")
async def process_job(job_id: str, background_tasks: BackgroundTasks):

    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.video_url:
        raise HTTPException(status_code=400, detail="No video URL set")

    job.status = "queued"
    job.step = "queued"
    job.progress = 0
    job.error = None

    background_tasks.add_task(run_pipeline_background, job_id)

    return {
        "job_id": job.job_id,
        "status": job.status,
        "message": "Processing started in background",
    }
