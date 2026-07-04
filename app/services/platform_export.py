from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class PlatformPreset:
    name: str
    width: int
    height: int
    video_codec: str
    audio_codec: str
    video_bitrate: str
    audio_bitrate: str
    metadata: dict[str, str]


class PlatformExportPresets:
    @staticmethod
    def all() -> dict[str, PlatformPreset]:
        base = {
            "width": settings.TARGET_WIDTH,
            "height": settings.TARGET_HEIGHT,
            "video_codec": settings.CPU_ENCODER,
            "audio_codec": "aac",
            "audio_bitrate": settings.AUDIO_BITRATE,
        }
        return {
            "youtube_shorts": PlatformPreset(
                name="YouTube Shorts",
                video_bitrate="8M",
                metadata={"platform": "youtube_shorts", "format": "shorts"},
                **base,
            ),
            "instagram_reels": PlatformPreset(
                name="Instagram Reels",
                video_bitrate="6M",
                metadata={"platform": "instagram_reels", "format": "reels"},
                **base,
            ),
            "tiktok": PlatformPreset(
                name="TikTok",
                video_bitrate="6M",
                metadata={"platform": "tiktok", "format": "vertical"},
                **base,
            ),
            "facebook_reels": PlatformPreset(
                name="Facebook Reels",
                video_bitrate="6M",
                metadata={"platform": "facebook_reels", "format": "reels"},
                **base,
            ),
        }
