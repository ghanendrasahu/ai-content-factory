from pathlib import Path

import ffmpeg

from app.core.paths import OUTPUT_DIR, ensure_directories
from app.logger import logger


class VideoOptimizer:

    @staticmethod
    def make_vertical(input_path: str, output_path: str, transcript=None):
        ensure_directories()

        input_file = Path(input_path)
        if not input_file.is_file():
            raise FileNotFoundError(f"Input video not found: {input_file}")

        output_file = Path(output_path)
        if output_file.parent == Path("."):
            output_file = OUTPUT_DIR / output_file

        output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            probe = ffmpeg.probe(str(input_file))
            has_audio = any(
                stream.get("codec_type") == "audio"
                for stream in probe.get("streams", [])
            )

            source = ffmpeg.input(str(input_file))

            video = source.video.filter(
                "scale",
                1080,
                1920,
                force_original_aspect_ratio="increase",
            ).filter(
                "crop",
                1080,
                1920,
                "(iw-ow)/2",
                "(ih-oh)/2",
            ).filter("setsar", 1)

            output_kwargs = dict(
                vcodec="libx264",
                preset="fast",
                crf=20,
                pix_fmt="yuv420p",
                movflags="+faststart",
                format="mp4",
            )

            if has_audio:
                stream = ffmpeg.output(
                    video,
                    source.audio,
                    str(output_file),
                    acodec="aac",
                    audio_bitrate="192k",
                    **output_kwargs,
                )
            else:
                stream = ffmpeg.output(
                    video,
                    str(output_file),
                    an=None,
                    **output_kwargs,
                )

            ffmpeg.run(
                stream,
                overwrite_output=True,
                capture_stdout=True,
                capture_stderr=True,
            )

            if not output_file.is_file() or output_file.stat().st_size == 0:
                raise FileNotFoundError(
                    f"Vertical output was not created: {output_file}"
                )

            return str(output_file)

        except ffmpeg.Error as e:
            stderr = e.stderr.decode(errors="ignore") if e.stderr else "No stderr"
            logger.error("FFmpeg vertical conversion failed: %s", stderr)
            raise
