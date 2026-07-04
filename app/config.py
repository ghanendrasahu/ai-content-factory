from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Content Factory"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    BASE_DIR: str = "."
    DOWNLOAD_DIR: str = "downloads"
    OUTPUT_DIR: str = "outputs"
    TEMP_DIR: str = "temp"

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

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
