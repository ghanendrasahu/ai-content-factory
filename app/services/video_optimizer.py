import cv2
import numpy as np


class VideoOptimizer:

    @staticmethod
    def make_vertical(input_path: str, output_path: str):

        cap = cv2.VideoCapture(input_path)

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(
            output_path,
            fourcc,
            fps,
            (1080, 1920)
        )

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # simple center crop → vertical format
            center_x = width // 2
            crop_width = height * 9 // 16

            x1 = max(0, center_x - crop_width // 2)
            x2 = min(width, center_x + crop_width // 2)

            cropped = frame[:, x1:x2]

            resized = cv2.resize(cropped, (1080, 1920))

            out.write(resized)

        cap.release()
        out.release()

        return output_path