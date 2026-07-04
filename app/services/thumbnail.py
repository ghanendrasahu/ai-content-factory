from pathlib import Path

import ffmpeg

from app.config import settings
from app.core.paths import OUTPUT_DIR, ensure_directories
from app.logger import logger


class ThumbnailGenerator:
    @staticmethod
    def generate(video_path: str, title: str, job_id: str) -> str:
        ensure_directories()
        input_file = Path(video_path)
        if not input_file.is_file():
            raise FileNotFoundError(f"Thumbnail input video not found: {input_file}")

        output_file = OUTPUT_DIR / f"{job_id}_thumbnail.jpg"
        safe_title = (title or "AI Content Factory").replace(":", "\\:")

        stream = (
            ffmpeg.input(str(input_file), ss=0.5)
            .filter("scale", settings.THUMBNAIL_WIDTH, settings.THUMBNAIL_HEIGHT)
            .filter(
                "drawtext",
                text=safe_title[:80],
                fontcolor="white",
                fontsize=54,
                box=1,
                boxcolor="black@0.55",
                boxborderw=24,
                x="(w-text_w)/2",
                y="h-(text_h*3)",
            )
            .output(str(output_file), vframes=1, format="image2", vcodec="mjpeg")
            .overwrite_output()
        )
        ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
        logger.info("thumbnail.generated output=%s", output_file)
        return str(output_file)
