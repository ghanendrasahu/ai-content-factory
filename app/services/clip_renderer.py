from pathlib import Path
import ffmpeg

from app.logger import logger


OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


class ClipRenderer:

    @staticmethod
    def render(video_path: str, clips: list, job_id: str):

        output_files = []

        for i, clip in enumerate(clips):

            start = clip["start"]
            end = clip["end"]

            output_file = OUTPUT_DIR / f"{job_id}_clip_{i + 1}.mp4"

            try:

                if end <= start:
                    raise ValueError(
                        f"Invalid clip range: start={start}, end={end}"
                    )

                logger.info(
                    f"Rendering clip {i + 1}: {start:.2f}s - {end:.2f}s"
                )

                (
                    ffmpeg
                    .input(video_path, ss=start, to=end)
                    .output(
                        str(output_file),
                        vcodec="libx264",
                        acodec="aac",
                        preset="fast",
                        vf="scale=1080:1920",
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
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