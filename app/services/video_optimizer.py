import cv2
import os
import ffmpeg
from app.services.subtitle_generator import generate_srt


class VideoOptimizer:

    @staticmethod
    def make_vertical(input_path: str, output_path: str, transcript: list):

        temp_video = output_path.replace(".mp4", "_temp.mp4")
        srt_path = output_path.replace(".mp4", ".srt")

        cap = cv2.VideoCapture(input_path)

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        out = cv2.VideoWriter(
            temp_video,
            fourcc,
            fps,
            (1080, 1920)
        )

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            center_x = width // 2
            crop_width = height * 9 // 16

            x1 = max(0, center_x - crop_width // 2)
            x2 = min(width, center_x + crop_width // 2)

            cropped = frame[:, x1:x2]
            resized = cv2.resize(cropped, (1080, 1920))

            out.write(resized)

        cap.release()
        out.release()
        cv2.destroyAllWindows()

        # ----------------------------
        # STEP 1: generate subtitles
        # ----------------------------
        generate_srt(transcript, srt_path)  
        # NOTE: replace [] properly in real pipeline (explained below)

        # ----------------------------
        # STEP 2: merge audio + subtitles
        # ----------------------------
        (
            ffmpeg
            .output(
                ffmpeg.input(temp_video).video,
                ffmpeg.input(input_path).audio,
                output_path,
                vf=f"subtitles={srt_path}",
                vcodec="libx264",
                acodec="aac",
                shortest=None
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )

        os.remove(temp_video)

        return output_path