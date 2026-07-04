import json

from app.ai.chunker import TranscriptChunker
from app.ai.llm import LLM
from app.ai.parser import JsonParser
from app.ai.prompts import CLIP_PROMPT
from app.logger import logger


class ClipDetector:

    @staticmethod
    def detect(transcript: list):
        if not transcript:
            raise ValueError("Transcript is empty")

        chunks = TranscriptChunker.chunk(transcript)

        clips = []

        for chunk in chunks:

            prompt = CLIP_PROMPT.format(
                transcript=json.dumps(chunk, indent=2)
            )

            for _ in range(3):

                try:

                    response = LLM.generate(prompt)

                    result = JsonParser.parse(response)

                    clips.extend(ClipDetector._validate_clips(result))

                    break

                except Exception as e:
                    logger.warning("Clip detection parse failed: %s", e)
                    continue

        clips.sort(
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        return clips[:5]

    @staticmethod
    def _validate_clips(clips: list) -> list:
        valid_clips = []

        for clip in clips:
            if not isinstance(clip, dict):
                continue

            try:
                start = float(clip["start"])
                end = float(clip["end"])
                score = float(clip.get("score", 0))
            except (KeyError, TypeError, ValueError):
                continue

            if start < 0 or end <= start:
                continue

            valid_clips.append(
                {
                    "title": str(clip.get("title", "")),
                    "start": start,
                    "end": end,
                    "score": score,
                    "reason": str(clip.get("reason", "")),
                }
            )

        return valid_clips
