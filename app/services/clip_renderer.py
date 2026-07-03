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

            try:
                if end <= start:
                    raise ValueError(f"Invalid clip range: start={start}, end={end}")

                (
                    ffmpeg
                    .input(video_path, ss=start, to=end)
                    .output(
                        str(output_file),
                        vcodec="libx264",
                        acodec="aac",
                        preset="fast",
                        vf="scale=1080:1920"
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )

                output_files.append(str(output_file))

            except ffmpeg.Error as e:
                print(f"\nFFMPEG ERROR (clip {i+1})")
                print(e.stderr.decode() if e.stderr else "No stderr output")
                raise

            except Exception as e:
                print(f"\nGENERAL ERROR (clip {i+1}): {e}")
                raise

        return output_files