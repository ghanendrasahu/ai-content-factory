from pathlib import Path
from time import perf_counter

import ffmpeg

from app.config import settings
from app.core.paths import OUTPUT_DIR, ensure_directories
from app.logger import logger
from app.services.hardware import HardwareDetector


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
            started_at = perf_counter()
            logger.info("optimizer.start input=%s output=%s", input_file, output_file)

            probe = ffmpeg.probe(str(input_file))
            hardware = HardwareDetector.detect()
            has_audio = any(
                stream.get("codec_type") == "audio"
                for stream in probe.get("streams", [])
            )

            source = ffmpeg.input(str(input_file))

            video = (
                source.video.filter(
                    "scale",
                    settings.TARGET_WIDTH,
                    settings.TARGET_HEIGHT,
                    force_original_aspect_ratio="increase",
                )
                .filter(
                    "crop",
                    settings.TARGET_WIDTH,
                    settings.TARGET_HEIGHT,
                    "(iw-ow)/2",
                    "(ih-oh)/2",
                )
                .filter("setsar", 1)
            )

            output_kwargs = dict(
                vcodec=hardware.video_encoder,
                preset=settings.VIDEO_PRESET,
                crf=settings.VIDEO_CRF,
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
                    audio_bitrate=settings.AUDIO_BITRATE,
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

            VideoOptimizer.verify_video(output_file)
            logger.info(
                "optimizer.complete output=%s elapsed=%.2fs",
                output_file,
                perf_counter() - started_at,
            )

            return str(output_file)

        except ffmpeg.Error as e:
            stderr = e.stderr.decode(errors="ignore") if e.stderr else "No stderr"
            logger.error("FFmpeg vertical conversion failed: %s", stderr)
            raise

    @staticmethod
    def verify_video(path: Path) -> None:
        metadata = ffmpeg.probe(str(path))
        video_stream = next(
            (
                stream
                for stream in metadata.get("streams", [])
                if stream.get("codec_type") == "video"
            ),
            None,
        )

        if not video_stream:
            raise ValueError(f"No video stream found in output: {path}")

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        codec = video_stream.get("codec_name")

        if width != settings.TARGET_WIDTH or height != settings.TARGET_HEIGHT:
            raise ValueError(
                f"Invalid output dimensions: {width}x{height}; "
                f"expected {settings.TARGET_WIDTH}x{settings.TARGET_HEIGHT}"
            )

        if codec != "h264":
            raise ValueError(f"Invalid output codec: {codec}; expected h264")
