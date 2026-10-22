"""Runtime settings for dashboards and clients.

Only non-secret configuration is exposed - never API keys, tokens or
credentials.
"""

from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("")
async def get_settings() -> dict:
    """Feature flags and limits the UI can adapt to."""
    return {
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
        },
        "pipeline": {
            "engine": settings.PIPELINE_ENGINE,
            "clip_selection_count": settings.CLIP_SELECTION_COUNT,
            "min_clip_duration_seconds": settings.MIN_CLIP_DURATION_SECONDS,
            "max_clip_duration_seconds": settings.MAX_CLIP_DURATION_SECONDS,
            "target": {
                "width": settings.TARGET_WIDTH,
                "height": settings.TARGET_HEIGHT,
            },
        },
        "features": {
            "subtitles": settings.ENABLE_SUBTITLES,
            "thumbnails": settings.ENABLE_THUMBNAILS,
            "platform_exports": settings.ENABLE_PLATFORM_EXPORTS,
            "youtube_publish": settings.YOUTUBE_PUBLISH_ENABLED,
            "gpu": settings.ENABLE_GPU,
        },
        "media": {
            "subtitle_format": settings.SUBTITLE_FORMAT,
            "thumbnail_template": settings.THUMBNAIL_TEMPLATE,
            "thumbnail_size": {
                "width": settings.THUMBNAIL_WIDTH,
                "height": settings.THUMBNAIL_HEIGHT,
            },
        },
        "integrations": {
            "llm_configured": bool(settings.GROQ_API_KEY),
            "youtube_configured": bool(
                settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_REFRESH_TOKEN
            ),
            "api_key_required": bool(settings.API_KEYS),
        },
    }
