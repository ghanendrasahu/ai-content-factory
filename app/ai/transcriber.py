from faster_whisper import WhisperModel

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8",
)


class Transcriber:

    @staticmethod
    def transcribe(video_path: str):

        segments, info = model.transcribe(video_path)

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