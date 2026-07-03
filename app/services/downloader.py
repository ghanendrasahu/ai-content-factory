import yt_dlp
from pathlib import Path

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)


def download_video(url: str) -> str:

    output_path = TEMP_DIR / "input.mp4"

    ydl_opts = {
        "format": "mp4",
        "outtmpl": str(output_path),
        "quiet": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return str(output_path)