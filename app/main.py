from fastapi import FastAPI
from app.schemas.download import DownloadRequest, DownloadResponse
from app.services.downloader import Downloader
from app.config import settings
from app.logger import logger

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)


@app.on_event("startup")
async def startup():
    logger.info("AI Content Factory Started")


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
@app.post("/download", response_model=DownloadResponse)
async def download_video(request: DownloadRequest):

    result = Downloader.download(request.url)

    return result