from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.jobs import router as jobs_router
from app.config import settings
from app.core.paths import DOWNLOAD_DIR, OUTPUT_DIR, TEMP_DIR, ensure_directories

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

app.include_router(jobs_router)


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/ready")
def readiness_check():
    directories = {
        "downloads": DOWNLOAD_DIR,
        "outputs": OUTPUT_DIR,
        "temp": TEMP_DIR,
    }
    directory_status = {
        name: path.exists() and path.is_dir()
        for name, path in directories.items()
    }
    ready = all(directory_status.values())

    return {
        "status": "ready" if ready else "not_ready",
        "directories": directory_status,
    }
