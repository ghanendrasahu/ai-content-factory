from pathlib import Path

import yt_dlp

from app.core.paths import DOWNLOAD_DIR, ensure_directories


class DownloadService:

    @staticmethod
    def download(url: str):
        ensure_directories()

        if not url:
            raise ValueError("Video URL is required")

        ydl_opts = {
            "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "quiet": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

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
        if not path.exists():
            raise FileNotFoundError(f"Downloaded video not found: {path}")

        return info.get("title", path.stem), str(path)
