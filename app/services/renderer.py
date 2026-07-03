from pathlib import Path
import ffmpeg

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


class ClipRenderer:

    @staticmethod
    def render(video_path: str, clips: list):

        output_files = []

        for i, clip in enumerate(clips):

            output_file = OUTPUT_DIR / f"clip_{i+1}.mp4"

            try:
                (
                    ffmpeg
                    .input(video_path, ss=clip["start"], to=clip["end"])
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
                print(e.stderr.decode() if e.stderr else "FFmpeg error")
                raise

        return output_files