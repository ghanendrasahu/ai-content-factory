from pathlib import Path
from time import perf_counter

import yt_dlp

from app.config import settings
from app.core.paths import DOWNLOAD_DIR, ensure_directories
from app.logger import logger


class DownloadService:
    @staticmethod
    def download(url: str):
        ensure_directories()

        if not url:
            raise ValueError("Video URL is required")

        started_at = perf_counter()
        ydl_opts = {
            "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
            "format": settings.YTDLP_FORMAT,
            "merge_output_format": "mp4",
            "quiet": False,
            "noplaylist": True,
        }

        try:
            logger.info("download.start url=%s", url)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception:
            logger.exception("download.failed url=%s", url)
            raise

        requested_downloads = info.get("requested_downloads") or []
        if requested_downloads:
            file_path = requested_downloads[0].get("filepath")
        else:
            file_path = info.get("filepath")

        if not file_path:
            file_path = str(
                DOWNLOAD_DIR / f"{info.get('title', 'downloaded_video')}.mp4"
            )

        if not file_path.endswith(".mp4"):
            file_path = str(Path(file_path).with_suffix(".mp4"))

        path = Path(file_path)
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"Downloaded video not found: {path}")

        logger.info(
            "download.complete path=%s elapsed=%.2fs",
            path,
            perf_counter() - started_at,
        )

        return info.get("title", path.stem), str(path)
