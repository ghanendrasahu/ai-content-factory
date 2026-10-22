from uuid import uuid4

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.ai.clip_detector import ClipDetector
from app.ai.transcriber import Transcriber
from app.api.deps import require_api_key
from app.core.paths import OUTPUT_DIR
from app.core.storage import jobs
from app.logger import logger
from app.models.job import Job
from app.schemas.job import DownloadJobRequest, PublishJobRequest

from app.services.clip_renderer import ClipRenderer
from app.services.download_service import DownloadService
from app.services.pipeline import Pipeline
from app.services.video_optimizer import VideoOptimizer
from app.services.youtube_publisher import (
    AuthError,
    InvalidRequestError,
    PublishError,
    QuotaError,
    YouTubePublisher,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _get_job_or_404(job_id: str) -> Job:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _fail_job(job: Job, error: Exception) -> None:
    job.set_state("failed", job.progress)
    job.error = str(error)


def _raise_service_error(error: Exception) -> None:
    if isinstance(error, (ValueError, FileNotFoundError)):
        raise HTTPException(status_code=400, detail=str(error)) from error
    raise HTTPException(status_code=500, detail="Internal processing error") from error


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
        _fail_job(job, e)


# =========================
# CREATE JOB
# =========================
@router.post("", dependencies=[Depends(require_api_key)])
async def create_job():
    job_id = str(uuid4())
    job = Job(job_id=job_id)
    jobs[job_id] = job
    return job


# =========================
# PUBLISH TO YOUTUBE
# =========================
@router.post("/{job_id}/publish", dependencies=[Depends(require_api_key)])
async def publish_job(job_id: str, request: PublishJobRequest | None = None):
    """Publish a rendered job to YouTube (real resumable upload)."""
    job = _get_job_or_404(job_id)

    if not job.final_video or not Path(job.final_video).is_file():
        raise HTTPException(
            status_code=400,
            detail="Job has no rendered video to publish - run /process first.",
        )

    options = request or PublishJobRequest()
    try:
        metadata = YouTubePublisher.build_metadata(
            title=options.title,
            description=options.description,
            tags=options.tags,
            privacy_status=options.privacy_status,
            content_pack=job.content_pack,
        )
        published = YouTubePublisher.publish(
            job.final_video,
            metadata,
            dry_run=options.dry_run,
        )
    except InvalidRequestError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except QuotaError as e:
        raise HTTPException(status_code=429, detail=str(e)) from e
    except AuthError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except PublishError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    job.published_video = published.to_dict()
    return job.published_video


# =========================
# GET JOB (SINGLE SOURCE OF TRUTH)
# =========================
@router.get("/{job_id}")
async def get_job(job_id: str):
    job = _get_job_or_404(job_id)

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
        "thumbnail_path": getattr(job, "thumbnail_path", None),
        "subtitle_path": getattr(job, "subtitle_path", None),
        "platform_exports": getattr(job, "platform_exports", {}),
        "published_video": getattr(job, "published_video", None),
        "elapsed_seconds": getattr(job, "elapsed_seconds", 0),
        "estimated_remaining_seconds": getattr(
            job,
            "estimated_remaining_seconds",
            None,
        ),
        "failure_report": getattr(job, "failure_report", None),
        # ERROR
        "error": getattr(job, "error", None),
    }


# =========================
# DOWNLOAD VIDEO
# =========================
@router.post("/{job_id}/download", dependencies=[Depends(require_api_key)])
async def download_video(job_id: str, request: DownloadJobRequest):
    job = _get_job_or_404(job_id)

    try:
        job.set_state("downloading", 10)
        title, path = DownloadService.download(str(request.url))
    except Exception as e:
        logger.exception("api.download.failed job_id=%s", job_id)
        _fail_job(job, e)
        _raise_service_error(e)

    job.video_url = str(request.url)
    job.video_path = path
    job.set_state("queued", 10)

    return {
        "job_id": job.job_id,
        "title": title,
        "status": job.status,
        "video_path": path,
    }


# =========================
# TRANSCRIBE
# =========================
@router.post("/{job_id}/transcribe", dependencies=[Depends(require_api_key)])
async def transcribe_video(job_id: str):
    job = _get_job_or_404(job_id)

    if not job.video_path:
        raise HTTPException(status_code=400, detail="Video not downloaded")

    try:
        job.set_state("transcribing", 30)
        result = Transcriber.transcribe(job.video_path)
    except Exception as e:
        logger.exception("api.transcribe.failed job_id=%s", job_id)
        _fail_job(job, e)
        _raise_service_error(e)

    job.transcript = result["transcript"]
    job.set_state("queued", 30)

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
    job = _get_job_or_404(job_id)

    if not job.transcript:
        raise HTTPException(status_code=400, detail="Transcript not found")

    try:
        job.set_state("detecting", 50)
        clips = ClipDetector.detect(job.transcript)
    except Exception as e:
        logger.exception("api.detect.failed job_id=%s", job_id)
        _fail_job(job, e)
        _raise_service_error(e)

    job.clips = clips
    job.set_state("queued", 50)

    return {
        "status": job.status,
        "clips_count": len(clips),
    }


# =========================
# RENDER CLIPS
# =========================
@router.post("/{job_id}/render-clips")
async def render_clips(job_id: str):
    job = _get_job_or_404(job_id)

    if not job.clips:
        raise HTTPException(status_code=400, detail="No clips found")

    if not job.video_path:
        raise HTTPException(status_code=400, detail="No video found")

    try:
        job.set_state("rendering", 70)
        output_files = ClipRenderer.render(job.video_path, job.clips, job.job_id)
    except Exception as e:
        logger.exception("api.render.failed job_id=%s", job_id)
        _fail_job(job, e)
        _raise_service_error(e)

    job.clip_outputs = output_files
    job.set_state("queued", 70)

    return {
        "status": job.status,
        "clips": output_files,
    }


# =========================
# MAKE VERTICAL VIDEO
# =========================
@router.post("/{job_id}/make-vertical")
async def make_vertical(job_id: str):
    job = _get_job_or_404(job_id)

    if not job.video_path:
        raise HTTPException(status_code=400, detail="No video found")

    source_path = job.clip_outputs[0] if job.clip_outputs else job.video_path
    output_path = OUTPUT_DIR / f"{job.job_id}_vertical.mp4"

    try:
        job.set_state("optimizing", 90)
        result = VideoOptimizer.make_vertical(
            source_path,
            str(output_path),
            job.transcript,
        )
    except Exception as e:
        logger.exception("api.optimize.failed job_id=%s", job_id)
        _fail_job(job, e)
        _raise_service_error(e)

    job.final_video = result
    job.set_state("completed", 100)

    return {
        "status": job.status,
        "output": result,
    }


# =========================
# FULL PIPELINE
# =========================
@router.post("/{job_id}/process")
async def process_job(job_id: str, background_tasks: BackgroundTasks):
    job = _get_job_or_404(job_id)

    if not job.video_url:
        raise HTTPException(status_code=400, detail="No video URL set")

    job.set_state("queued", 0)
    job.error = None

    background_tasks.add_task(run_pipeline_background, job_id)

    return {
        "job_id": job.job_id,
        "status": job.status,
        "message": "Processing started in background",
    }
