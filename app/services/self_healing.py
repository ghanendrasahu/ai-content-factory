import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TypeVar

from app.config import settings
from app.logger import logger

T = TypeVar("T")


class ErrorCategory(str, Enum):
    DOWNLOAD = "download"
    WHISPER = "whisper"
    GROQ = "groq"
    FFMPEG = "ffmpeg"
    FILE_IO = "file_io"
    UNKNOWN = "unknown"


@dataclass
class FailureReport:
    category: ErrorCategory
    message: str
    attempts: int
    recovered: bool = False
    strategy: str = "retry"
    errors: list[str] = field(default_factory=list)


class ErrorClassifier:
    @staticmethod
    def classify(error: Exception) -> ErrorCategory:
        text = f"{type(error).__name__}: {error}".lower()
        if "youtube" in text or "yt_dlp" in text or "download" in text:
            return ErrorCategory.DOWNLOAD
        if "whisper" in text or "transcrib" in text:
            return ErrorCategory.WHISPER
        if "groq" in text or "api_key" in text or "llm" in text:
            return ErrorCategory.GROQ
        if "ffmpeg" in text or "ffprobe" in text or "codec" in text:
            return ErrorCategory.FFMPEG
        if "file" in text or "path" in text or "permission" in text:
            return ErrorCategory.FILE_IO
        return ErrorCategory.UNKNOWN


class RetryManager:
    def __init__(
        self,
        attempts: int | None = None,
        initial_delay: float | None = None,
        backoff: float | None = None,
    ):
        self.attempts = attempts or settings.RETRY_ATTEMPTS
        self.initial_delay = initial_delay or settings.RETRY_INITIAL_DELAY_SECONDS
        self.backoff = backoff or settings.RETRY_BACKOFF_MULTIPLIER

    def run(self, operation: Callable[[], T], label: str) -> T:
        delay = self.initial_delay
        errors: list[str] = []

        for attempt in range(1, self.attempts + 1):
            try:
                result = operation()
                if attempt > 1:
                    logger.info("retry.recovered label=%s attempt=%s", label, attempt)
                return result
            except Exception as exc:
                errors.append(str(exc))
                category = ErrorClassifier.classify(exc)
                logger.warning(
                    "retry.failed label=%s attempt=%s category=%s error=%s",
                    label,
                    attempt,
                    category.value,
                    exc,
                )
                if attempt == self.attempts:
                    logger.error(
                        "retry.exhausted label=%s category=%s errors=%s",
                        label,
                        category.value,
                        errors,
                    )
                    raise

                time.sleep(delay)
                delay *= self.backoff


class RecoveryStrategies:
    @staticmethod
    def diagnose(error: Exception) -> FailureReport:
        category = ErrorClassifier.classify(error)
        return FailureReport(
            category=category,
            message=str(error),
            attempts=settings.RETRY_ATTEMPTS,
            strategy=RecoveryStrategies._strategy_for(category),
        )

    @staticmethod
    def _strategy_for(category: ErrorCategory) -> str:
        strategies = {
            ErrorCategory.DOWNLOAD: "retry yt-dlp and verify URL availability",
            ErrorCategory.WHISPER: "retry transcription and fall back to CPU settings",
            ErrorCategory.GROQ: "retry LLM call and use safe content fallback",
            ErrorCategory.FFMPEG: "retry FFmpeg with CPU-compatible H.264 output",
            ErrorCategory.FILE_IO: "verify path exists and configured directories are writable",
            ErrorCategory.UNKNOWN: "inspect structured logs",
        }
        return strategies[category]
