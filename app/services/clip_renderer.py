from pathlib import Path

import ffmpeg

from app.core.paths import OUTPUT_DIR, ensure_directories
from app.logger import logger


class ClipRenderer:

    @staticmethod
    def render(video_path: str, clips: list, job_id: str):
        ensure_directories()

        input_file = Path(video_path)
        if not input_file.is_file():
            raise FileNotFoundError(f"Input video not found: {input_file}")

        probe = ffmpeg.probe(str(input_file))
        has_audio = any(
            stream.get("codec_type") == "audio"
            for stream in probe.get("streams", [])
        )

        output_files = []

        for i, clip in enumerate(clips):
            start = float(clip["start"])
            end = float(clip["end"])

            output_file = OUTPUT_DIR / f"{job_id}_clip_{i + 1}.mp4"

            try:
                if end <= start:
                    raise ValueError(
                        f"Invalid clip range: start={start}, end={end}"
                    )

                logger.info(
                    f"Rendering clip {i + 1}: {start:.2f}s - {end:.2f}s"
                )

                source = ffmpeg.input(str(input_file), ss=start, t=end - start)
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
                        f"Rendered clip was not created: {output_file}"
                    )

                output_files.append(str(output_file))

                logger.info(f"Clip {i + 1} rendered successfully.")

            except ffmpeg.Error:
                logger.exception(
                    f"FFmpeg failed while rendering clip {i + 1}"
                )
                raise

            except Exception:
                logger.exception(
                    f"Unexpected error while rendering clip {i + 1}"
                )
                raise

        return output_files
