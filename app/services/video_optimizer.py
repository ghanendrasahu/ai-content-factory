import ffmpeg
from app.services.subtitle_generator import generate_srt


class VideoOptimizer:

    @staticmethod
    def make_vertical(input_path: str, output_path: str, transcript: list):

        srt_path = output_path.replace(".mp4", ".srt")

        generate_srt(transcript, srt_path)

        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                vf=(
                    f"crop=ih*9/16:ih,"
                    f"scale=1080:1920,"
                    f"subtitles={srt_path}"
                ),
                vcodec="libx264",
                acodec="aac",
                preset="veryfast",
                movflags="+faststart"
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )

        return output_path