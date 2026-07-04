from pathlib import Path
from time import time

from app.config import settings
from app.core.paths import DOWNLOAD_DIR, OUTPUT_DIR, TEMP_DIR, ensure_inside_directory
from app.logger import logger


class CleanupService:
    @staticmethod
    def cleanup_retention() -> dict[str, int]:
        removed = {
            "temp": CleanupService._cleanup_directory(
                TEMP_DIR, settings.CLEANUP_TEMP_MAX_AGE_HOURS
            ),
            "outputs": CleanupService._cleanup_directory(
                OUTPUT_DIR, settings.CLEANUP_OUTPUT_MAX_AGE_HOURS, enabled=False
            ),
            "downloads": CleanupService._cleanup_directory(
                DOWNLOAD_DIR,
                settings.CLEANUP_DOWNLOAD_MAX_AGE_HOURS,
                enabled=settings.CLEANUP_DELETE_DOWNLOADS,
            ),
        }
        logger.info("cleanup.retention result=%s", removed)
        return removed

    @staticmethod
    def _cleanup_directory(
        directory: Path, max_age_hours: int, enabled: bool = True
    ) -> int:
        if not enabled:
            return 0

        cutoff = time() - (max_age_hours * 3600)
        removed = 0
        for path in directory.glob("*"):
            target = ensure_inside_directory(path, directory)
            if target.is_file() and target.stat().st_mtime < cutoff:
                target.unlink(missing_ok=True)
                removed += 1
        return removed
