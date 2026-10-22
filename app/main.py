import shutil

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.jobs import router as jobs_router
from app.api.settings import router as settings_router
from app.config import settings
from app.core.paths import DOWNLOAD_DIR, OUTPUT_DIR, TEMP_DIR, ensure_directories
from app.core.storage import jobs
from app.services.cleanup import CleanupService
from app.services.hardware import HardwareDetector

app = FastAPI(title="AI Content Factory")
ensure_directories()

# ------------------------
# CORS
# ------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# Static Files
# ------------------------
app.mount("/downloads", StaticFiles(directory=str(DOWNLOAD_DIR)), name="downloads")
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")
app.mount("/temp", StaticFiles(directory=str(TEMP_DIR)), name="temp")

# The settings router must be registered first: the jobs router owns
# "/jobs/{job_id}", and Starlette matches routes in registration order.
app.include_router(settings_router)
app.include_router(jobs_router)


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/health")
def health_check():
    hardware = HardwareDetector.detect()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checks": {
            "ffmpeg": shutil.which(settings.FFMPEG_BINARY) is not None,
            "ffprobe": shutil.which(settings.FFPROBE_BINARY) is not None,
            "yt_dlp": True,
            "groq_configured": bool(settings.GROQ_API_KEY),
            "whisper_model": settings.WHISPER_MODEL,
            "disk": {
                "downloads": DOWNLOAD_DIR.exists(),
                "outputs": OUTPUT_DIR.exists(),
                "temp": TEMP_DIR.exists(),
            },
            "hardware": {
                "has_nvidia_gpu": hardware.has_nvidia_gpu,
                "video_encoder": hardware.video_encoder,
                "whisper_device": hardware.whisper_device,
            },
        },
    }


@app.get("/ready")
def readiness_check():
    directories = {
        "downloads": DOWNLOAD_DIR,
        "outputs": OUTPUT_DIR,
        "temp": TEMP_DIR,
    }
    directory_status = {
        name: path.exists() and path.is_dir() for name, path in directories.items()
    }
    ready = all(directory_status.values())

    return {
        "status": "ready" if ready else "not_ready",
        "directories": directory_status,
    }


@app.get("/metrics")
def metrics():
    hardware = HardwareDetector.detect()
    status_counts: dict[str, int] = {}
    for job in jobs.values():
        status_counts[job.status] = status_counts.get(job.status, 0) + 1

    return {
        "jobs": {
            "total": len(jobs),
            "by_status": status_counts,
        },
        "hardware": {
            "has_nvidia_gpu": hardware.has_nvidia_gpu,
            "video_encoder": hardware.video_encoder,
            "whisper_device": hardware.whisper_device,
        },
        "cleanup": CleanupService.cleanup_retention(),
    }
