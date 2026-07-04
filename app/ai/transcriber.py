from faster_whisper import WhisperModel
from pathlib import Path

from app.config import settings

_model = None


def _get_model():
    global _model

    if _model is None:
        _model = WhisperModel(
            settings.WHISPER_MODEL,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
        )

    return _model


class Transcriber:

    @staticmethod
    def transcribe(video_path: str):
        input_file = Path(video_path)
        if not input_file.is_file():
            raise FileNotFoundError(f"Video file not found: {input_file}")

        segments, info = _get_model().transcribe(str(input_file))

        transcript = []

        for segment in segments:
            transcript.append(
                {
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                }
            )

        return {
            "language": info.language,
            "transcript": transcript,
        }
