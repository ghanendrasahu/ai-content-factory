import os
from pathlib import Path
import ffmpeg


OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


class ClipRenderer:

    @staticmethod
    def render(video_path: str, clips: list):

        output_files = []

        for i, clip in enumerate(clips):

            start = clip["start"]
            end = clip["end"]

            output_file = OUTPUT_DIR / f"clip_{i+1}.mp4"

            (
                ffmpeg
                .input(video_path, ss=start, to=end)
                .output(
                    str(output_file),
                    codec="libx264",
                    preset="fast",
                    vf="scale=1080:1920"
                )
                .overwrite_output()
                .run(quiet=True)
            )

            output_files.append(str(output_file))

        return output_files