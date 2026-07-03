from pathlib import Path

import yt_dlp

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


class DownloadService:

    @staticmethod
    def download(url: str):

        ydl_opts = {
            "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "quiet": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            file_path = ydl.prepare_filename(info)

        if not file_path.endswith(".mp4"):
            file_path = str(Path(file_path).with_suffix(".mp4"))

        return info["title"], file_path