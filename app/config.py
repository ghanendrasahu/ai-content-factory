from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Content Factory"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    BASE_DIR: str = "."
    DOWNLOAD_DIR: str = "downloads"
    OUTPUT_DIR: str = "outputs"
    TEMP_DIR: str = "temp"
    DATA_DIR: str = "data"

    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.1-8b-instant"

    WHISPER_MODEL: str = "small"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    TARGET_WIDTH: int = 1080
    TARGET_HEIGHT: int = 1920
    VIDEO_CRF: int = 20
    VIDEO_PRESET: str = "fast"
    AUDIO_BITRATE: str = "192k"
    YTDLP_FORMAT: str = "bestvideo+bestaudio/best"
    FFMPEG_BINARY: str = "ffmpeg"
    FFPROBE_BINARY: str = "ffprobe"

    ENABLE_SUBTITLES: bool = False
    SUBTITLE_FONT_SIZE: int = 42
    SUBTITLE_POSITION_MARGIN: int = 180

    ENABLE_THUMBNAILS: bool = True
    THUMBNAIL_WIDTH: int = 1280
    THUMBNAIL_HEIGHT: int = 720

    ENABLE_PLATFORM_EXPORTS: bool = False
    CLIP_SELECTION_COUNT: int = 5
    MIN_CLIP_DURATION_SECONDS: float = 1.0
    MAX_CLIP_DURATION_SECONDS: float = 90.0

    ENABLE_GPU: bool = True
    NVIDIA_ENCODER: str = "h264_nvenc"
    CPU_ENCODER: str = "libx264"

    RETRY_ATTEMPTS: int = 3
    RETRY_INITIAL_DELAY_SECONDS: float = 0.5
    RETRY_BACKOFF_MULTIPLIER: float = 2.0

    CLEANUP_TEMP_MAX_AGE_HOURS: int = 24
    CLEANUP_OUTPUT_MAX_AGE_HOURS: int = 168
    CLEANUP_DOWNLOAD_MAX_AGE_HOURS: int = 168
    CLEANUP_DELETE_DOWNLOADS: bool = False

    STORAGE_BACKEND: str = "local"

    # --- YouTube publishing (Data API) -------------------------------------
    # OAuth2 client of a Google Cloud project with the youtube.upload scope.
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REFRESH_TOKEN: str = ""
    # Default metadata for published videos.
    YOUTUBE_CATEGORY_ID: str = "27"  # Science & Technology
    YOUTUBE_DEFAULT_PRIVACY: str = "private"  # private | unlisted | public
    YOUTUBE_TAGS: list[str] = []
    YOUTUBE_PUBLISH_MADE_FOR_KIDS: bool = False
    # Publish automatically at the end of the pipeline.
    YOUTUBE_PUBLISH_ENABLED: bool = False
    YOUTUBE_UPLOAD_CHUNK_BYTES: int = 8388608  # 8 MiB resumable chunks
    YOUTUBE_PUBLISH_TIMEOUT_SECONDS: int = 60

    # Durable job store (SQLite WAL; mounted via compose `./data`).
    JOB_STORE_DB: str = "jobs.db"

    # Non-empty list -> POST /jobs (and other mutating routes) require X-API-Key.
    API_KEYS: list[str] = []

    # Pipeline engine: "graph" (LangGraph state machine) or "linear".
    PIPELINE_ENGINE: str = "graph"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
