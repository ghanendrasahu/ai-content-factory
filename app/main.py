from fastapi import FastAPI

from app.config import settings
from app.logger import logger
from app.api.jobs import router as jobs_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.include_router(jobs_router)


@app.on_event("startup")
async def startup():
    logger.info("AI Content Factory Started")


@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Content Factory API",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }